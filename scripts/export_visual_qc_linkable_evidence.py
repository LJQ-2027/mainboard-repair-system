from __future__ import annotations

import argparse
import base64
import ctypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import sys
from urllib import error, parse, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.repair_evidence_export import (  # noqa: E402
    RepairEvidenceExportError,
    SERVER_CASE_SCHEMA_VERSION,
    build_linkable_physical_evidence,
)
from scripts.visual_qc.repair_evidence_link_contract import (  # noqa: E402
    canonical_json_bytes,
)
from scripts.visual_qc.source_library import (  # noqa: E402
    _absolute_lexical_path,
    _fsync_directory,
    _is_reparse_or_symlink,
)

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_SERVER_CASE_RESPONSE_BYTES = 1024 * 1024


@dataclass
class OutputBinding:
    path: Path
    directory_identities: tuple[
        tuple[Path, tuple[int, int]], ...
    ]
    windows_handles: tuple[int, ...] = ()
    parent_fd: int | None = None

    def close(self) -> None:
        if os.name == "nt":
            close_handle = ctypes.WinDLL(
                "kernel32", use_last_error=True
            ).CloseHandle
            close_handle.argtypes = [ctypes.c_void_p]
            close_handle.restype = ctypes.c_int
            for handle in reversed(self.windows_handles):
                close_handle(handle)
            self.windows_handles = ()
        elif self.parent_fd is not None:
            os.close(self.parent_fd)
            self.parent_fd = None


class RejectRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(
        self,
        _request,
        _file_pointer,
        _code,
        _message,
        _headers,
        _new_url,
    ):
        raise RepairEvidenceExportError(
            "redirect_rejected",
            "Visual-QC API redirects are not allowed.",
        )


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise RepairEvidenceExportError(
            "invalid_arguments",
            "Export arguments are invalid.",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        description="Export one linkable Visual-QC physical evidence snapshot."
    )
    parser.add_argument("--api-base")
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--actor-id")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--physical-evidence-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-http-localhost", action="store_true")
    return parser


def _load_credentials(path: Path | None) -> dict:
    payload = {}
    if path is not None:
        try:
            loaded = json.loads(path.read_bytes().decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RepairEvidenceExportError(
                "invalid_credentials",
                "Credential configuration is invalid.",
            ) from exc
        if not isinstance(loaded, dict):
            raise RepairEvidenceExportError(
                "invalid_credentials",
                "Credential configuration is invalid.",
            )
        payload = loaded
    return {
        "username": payload.get("username")
        or os.environ.get("VISUAL_QC_API_USERNAME"),
        "password": payload.get("password")
        or os.environ.get("VISUAL_QC_API_PASSWORD"),
        "actor_id": payload.get("actor_id")
        or os.environ.get("VISUAL_QC_API_ACTOR_ID")
        or os.environ.get("VISUAL_QC_ACTOR_ID"),
    }


def _transport_configuration(
    api_base: str | None,
    *,
    credentials: dict,
    actor_id: str | None,
    allow_http_localhost: bool,
) -> tuple[str, str, str | None]:
    if not api_base:
        raise RepairEvidenceExportError(
            "api_base_required",
            "API base is required.",
        )
    parsed = parse.urlsplit(api_base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
        or "\\" in parsed.path
        or any(
            segment in {".", ".."}
            for segment in parse.unquote(parsed.path).split("/")
        )
    ):
        raise RepairEvidenceExportError(
            "invalid_api_base",
            "API base is invalid.",
        )
    loopback = parsed.hostname.lower() in {"127.0.0.1", "localhost", "::1"}
    explicit_local_http = (
        parsed.scheme == "http" and loopback and allow_http_localhost
    )
    if parsed.scheme == "http" and not explicit_local_http:
        raise RepairEvidenceExportError(
            "insecure_transport",
            "HTTP is allowed only for an explicitly enabled loopback API.",
        )

    resolved_actor = actor_id or credentials["actor_id"]
    if (
        not isinstance(resolved_actor, str)
        or SAFE_ID.fullmatch(resolved_actor) is None
    ):
        raise RepairEvidenceExportError(
            "invalid_actor_id",
            "Actor identity is invalid.",
        )
    username = credentials["username"]
    password = credentials["password"]
    has_username = isinstance(username, str) and bool(username)
    has_password = isinstance(password, str) and bool(password)
    if has_username != has_password:
        raise RepairEvidenceExportError(
            "invalid_credentials",
            "Credential configuration is invalid.",
        )
    if not explicit_local_http and not (has_username and has_password):
        raise RepairEvidenceExportError(
            "credentials_required",
            "Credentials are required for this API.",
        )
    authorization = None
    if has_username and has_password:
        token = base64.b64encode(
            f"{username}:{password}".encode("utf-8")
        ).decode("ascii")
        authorization = f"Basic {token}"
    normalized = parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "")
    )
    return normalized, resolved_actor, authorization


def _assert_safe_output(
    output: Path, credential_file: Path | None
) -> OutputBinding:
    output = _absolute_lexical_path(output)
    if credential_file is not None:
        credential = _absolute_lexical_path(credential_file)
        if output == credential:
            raise RepairEvidenceExportError(
                "unsafe_output",
                "Output conflicts with protected input.",
            )
    if output.exists() or output.is_symlink():
        raise RepairEvidenceExportError(
            "output_exists",
            "Output already exists.",
        )

    existing = output.parent
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    for candidate in (existing, *existing.parents):
        if _is_reparse_or_symlink(candidate):
            raise RepairEvidenceExportError(
                "unsafe_output",
                "Output parent is unsafe.",
            )
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RepairEvidenceExportError(
            "output_unavailable",
            "Output parent could not be created.",
        ) from exc
    for candidate in (output.parent, *output.parent.parents):
        if _is_reparse_or_symlink(candidate):
            raise RepairEvidenceExportError(
                "unsafe_output",
                "Output parent is unsafe.",
            )
    if output.exists() or output.is_symlink() or output.is_dir():
        raise RepairEvidenceExportError(
            "output_exists",
            "Output already exists.",
        )
    binding = OutputBinding(
        path=output,
        directory_identities=tuple(
            (candidate, _filesystem_identity(candidate.lstat()))
            for candidate in (output.parent, *output.parent.parents)
        ),
    )
    try:
        if os.name == "nt":
            binding.windows_handles = _open_windows_directory_chain(
                tuple(
                    candidate
                    for candidate, _identity in reversed(
                        binding.directory_identities
                    )
                )
            )
        else:
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            binding.parent_fd = os.open(output.parent, flags)
            opened = os.fstat(binding.parent_fd)
            expected = binding.directory_identities[0][1]
            if (
                not stat.S_ISDIR(opened.st_mode)
                or _filesystem_identity(opened) != expected
            ):
                raise RepairEvidenceExportError(
                    "unsafe_output",
                    "Output parent identity changed.",
                )
        _validate_output_binding(binding)
        return binding
    except Exception:
        binding.close()
        raise


def _filesystem_identity(metadata) -> tuple[int, int]:
    return (metadata.st_dev, metadata.st_ino)


def _normalized_windows_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        value = f"\\\\{value[8:]}"
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.normpath(value))


def _windows_handle_path(handle: int) -> str:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    get_final_path.restype = ctypes.c_uint32
    required = get_final_path(handle, None, 0, 0)
    if not required:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = get_final_path(handle, buffer, len(buffer), 0)
    if not written or written >= len(buffer):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.value


def _open_windows_directory_chain(
    directories: tuple[Path, ...],
) -> tuple[int, ...]:
    class FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [
            ("file_attributes", ctypes.c_uint32),
            ("reparse_tag", ctypes.c_uint32),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    get_information = kernel32.GetFileInformationByHandleEx
    get_information.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    get_information.restype = ctypes.c_int
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int
    handles = []
    invalid_handle = ctypes.c_void_p(-1).value
    try:
        for directory in directories:
            handle = create_file(
                str(directory),
                0x80000000,  # GENERIC_READ
                0x00000001 | 0x00000002,  # share read/write, not delete
                None,
                3,  # OPEN_EXISTING
                0x02000000 | 0x00200000,
                None,
            )
            if handle in {None, invalid_handle}:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
            attributes = FileAttributeTagInfo()
            if not get_information(
                handle,
                9,  # FileAttributeTagInfo
                ctypes.byref(attributes),
                ctypes.sizeof(attributes),
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            if (
                not attributes.file_attributes & 0x00000010
                or attributes.file_attributes & 0x00000400
            ):
                raise RepairEvidenceExportError(
                    "unsafe_output",
                    "Output parent is unsafe.",
                )
            expected = _normalized_windows_path(
                str(directory.resolve(strict=True))
            )
            actual = _normalized_windows_path(
                _windows_handle_path(handle)
            )
            if actual != expected:
                raise RepairEvidenceExportError(
                    "unsafe_output",
                    "Output parent identity changed.",
                )
        return tuple(handles)
    except Exception:
        for handle in reversed(handles):
            close_handle(handle)
        raise


def _validate_output_binding(
    binding: OutputBinding,
    *,
    expected_output_identity: tuple[int, int] | None = None,
) -> None:
    for candidate, expected_identity in binding.directory_identities:
        try:
            metadata = candidate.lstat()
        except OSError as exc:
            raise RepairEvidenceExportError(
                "unsafe_output",
                "Output parent identity changed.",
            ) from exc
        if (
            _is_reparse_or_symlink(candidate)
            or not stat.S_ISDIR(metadata.st_mode)
            or _filesystem_identity(metadata) != expected_identity
        ):
            raise RepairEvidenceExportError(
                "unsafe_output",
                "Output parent identity changed.",
            )
    if expected_output_identity is None:
        if binding.path.exists() or binding.path.is_symlink():
            raise RepairEvidenceExportError(
                "output_exists",
                "Output already exists.",
            )
        return
    try:
        metadata = binding.path.lstat()
    except OSError as exc:
        raise RepairEvidenceExportError(
            "publication_failed",
            "Published output identity is unavailable.",
        ) from exc
    if (
        _is_reparse_or_symlink(binding.path)
        or not stat.S_ISREG(metadata.st_mode)
        or _filesystem_identity(metadata) != expected_output_identity
    ):
        raise RepairEvidenceExportError(
            "unsafe_output",
            "Published output identity is invalid.",
        )


def _unlink_matching_file(
    path: Path, expected_identity: tuple[int, int] | None
) -> None:
    if expected_identity is None:
        return
    try:
        metadata = path.lstat()
        if (
            not _is_reparse_or_symlink(path)
            and stat.S_ISREG(metadata.st_mode)
            and _filesystem_identity(metadata) == expected_identity
        ):
            path.unlink()
    except OSError:
        pass


def _unlink_matching_at(
    binding: OutputBinding,
    name: str,
    expected_identity: tuple[int, int] | None,
) -> None:
    if binding.parent_fd is None or expected_identity is None:
        return
    try:
        metadata = os.stat(
            name,
            dir_fd=binding.parent_fd,
            follow_symlinks=False,
        )
        if (
            stat.S_ISREG(metadata.st_mode)
            and _filesystem_identity(metadata) == expected_identity
        ):
            os.unlink(name, dir_fd=binding.parent_fd)
    except OSError:
        pass


def _create_temporary_output(
    binding: OutputBinding,
) -> tuple[int, Path | str]:
    if os.name == "nt":
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{binding.path.name}.",
            suffix=".tmp",
            dir=binding.path.parent,
        )
        return descriptor, Path(temporary_name)
    if binding.parent_fd is None:
        raise RepairEvidenceExportError(
            "unsafe_output",
            "Output directory lock is unavailable.",
        )
    for _attempt in range(100):
        name = f".{binding.path.name}.{secrets.token_hex(16)}.tmp"
        try:
            descriptor = os.open(
                name,
                os.O_RDWR | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=binding.parent_fd,
            )
            return descriptor, name
        except FileExistsError:
            continue
    raise RepairEvidenceExportError(
        "publication_failed",
        "Output temporary file could not be created.",
    )


def _load_json_object(content: bytes) -> dict:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RepairEvidenceExportError(
                    "malformed_response",
                    "Server response JSON is malformed.",
                )
            result[key] = value
        return result

    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda _token: (_ for _ in ()).throw(
                RepairEvidenceExportError(
                    "malformed_response",
                    "Server response JSON is malformed.",
                )
            ),
        )
    except RepairEvidenceExportError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RepairEvidenceExportError(
            "malformed_response",
            "Server response JSON is malformed.",
        ) from exc
    if not isinstance(payload, dict):
        raise RepairEvidenceExportError(
            "malformed_response",
            "Server response must be a JSON object.",
        )
    return payload


def _open_no_redirect(http_request, *, timeout: float):
    opener = request.build_opener(RejectRedirectHandler())
    return opener.open(http_request, timeout=timeout)


def _fetch_server_case(
    api_base: str,
    case_id: str,
    *,
    actor_id: str,
    authorization: str | None,
) -> dict:
    headers = {
        "Accept": "application/json",
        "X-Actor-Id": actor_id,
        "X-Actor-Role": "reviewer",
    }
    if authorization is not None:
        headers["Authorization"] = authorization
    endpoint = (
        f"{api_base}/admin/cases/{parse.quote(case_id, safe='')}"
    )
    http_request = request.Request(
        endpoint,
        headers=headers,
        method="GET",
    )
    try:
        with _open_no_redirect(http_request, timeout=60) as response:
            status = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            if status != 200:
                raise RepairEvidenceExportError(
                    "http_error",
                    "Visual-QC API returned an unexpected status.",
                )
            media_type = content_type.split(";", 1)[0].strip().lower()
            if media_type != "application/json":
                raise RepairEvidenceExportError(
                    "invalid_content_type",
                    "Visual-QC API response is not JSON.",
                )
            declared_length = response.headers.get("Content-Length")
            if declared_length is not None:
                try:
                    parsed_length = int(declared_length)
                except (TypeError, ValueError) as exc:
                    raise RepairEvidenceExportError(
                        "malformed_response",
                        "Visual-QC API response length is invalid.",
                    ) from exc
                if parsed_length < 0:
                    raise RepairEvidenceExportError(
                        "malformed_response",
                        "Visual-QC API response length is invalid.",
                    )
                if parsed_length > MAX_SERVER_CASE_RESPONSE_BYTES:
                    raise RepairEvidenceExportError(
                        "response_too_large",
                        "Visual-QC API response is too large.",
                    )
            content = response.read(MAX_SERVER_CASE_RESPONSE_BYTES + 1)
            if len(content) > MAX_SERVER_CASE_RESPONSE_BYTES:
                raise RepairEvidenceExportError(
                    "response_too_large",
                    "Visual-QC API response is too large.",
                )
    except RepairEvidenceExportError:
        raise
    except error.HTTPError as exc:
        codes = {
            401: "authentication_failed",
            403: "authorization_failed",
            404: "case_not_found",
        }
        raise RepairEvidenceExportError(
            codes.get(exc.code, "http_error"),
            f"Visual-QC API returned HTTP {exc.code}.",
        ) from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RepairEvidenceExportError(
            "transport_failure",
            "Visual-QC API request failed.",
        ) from exc
    payload = _load_json_object(content)
    if payload.get("schema_version") != SERVER_CASE_SCHEMA_VERSION:
        raise RepairEvidenceExportError(
            "invalid_schema_version",
            "Server case schema version is invalid.",
        )
    if payload.get("case_id") != case_id:
        raise RepairEvidenceExportError(
            "identity_mismatch",
            "Server response identity does not match the requested case.",
        )
    return payload


def _publish_snapshot(binding: OutputBinding, snapshot: dict) -> None:
    _validate_output_binding(binding)
    output = binding.path
    content = canonical_json_bytes(snapshot)
    descriptor, temporary = _create_temporary_output(binding)
    temporary_identity = None
    published = False
    publication_complete = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_identity = _filesystem_identity(os.fstat(handle.fileno()))
        _validate_output_binding(binding)
        try:
            if os.name == "nt":
                os.link(temporary, output)
            else:
                os.link(
                    temporary,
                    output.name,
                    src_dir_fd=binding.parent_fd,
                    dst_dir_fd=binding.parent_fd,
                    follow_symlinks=False,
                )
            published = True
        except FileExistsError as exc:
            raise RepairEvidenceExportError(
                "output_exists",
                "Output appeared during publication.",
            ) from exc
        except OSError as exc:
            raise RepairEvidenceExportError(
                "publication_failed",
                "Output could not be published.",
            ) from exc
        _validate_output_binding(
            binding,
            expected_output_identity=temporary_identity,
        )
        if os.name == "nt":
            _unlink_matching_file(temporary, temporary_identity)
            _fsync_directory(output.parent)
        else:
            _unlink_matching_at(
                binding, str(temporary), temporary_identity
            )
            os.fsync(binding.parent_fd)
        _validate_output_binding(
            binding,
            expected_output_identity=temporary_identity,
        )
        publication_complete = True
    finally:
        if os.name == "nt":
            _unlink_matching_file(temporary, temporary_identity)
        else:
            _unlink_matching_at(
                binding, str(temporary), temporary_identity
            )
        if published and not publication_complete:
            if os.name == "nt":
                _unlink_matching_file(output, temporary_identity)
            else:
                _unlink_matching_at(
                    binding, output.name, temporary_identity
                )


def _emit(payload: dict, *, error_output: bool = False) -> None:
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        file=sys.stderr if error_output else sys.stdout,
    )


def main(argv: list[str] | None = None) -> int:
    output_binding = None
    try:
        arguments = build_parser().parse_args(argv)
        credentials = _load_credentials(arguments.credential_file)
        api_base, actor_id, authorization = _transport_configuration(
            arguments.api_base or os.environ.get("VISUAL_QC_API_BASE"),
            credentials=credentials,
            actor_id=arguments.actor_id,
            allow_http_localhost=arguments.allow_http_localhost,
        )
        output_binding = _assert_safe_output(
            arguments.output, arguments.credential_file
        )
        server_case = _fetch_server_case(
            api_base,
            arguments.case_id,
            actor_id=actor_id,
            authorization=authorization,
        )
        snapshot = build_linkable_physical_evidence(
            server_case,
            physical_evidence_id=arguments.physical_evidence_id,
        )
        _publish_snapshot(output_binding, snapshot)
    except RepairEvidenceExportError as exc:
        _emit(
            {
                "status": "failed",
                "code": exc.code,
                "message": exc.message,
            },
            error_output=True,
        )
        return 2
    except Exception:
        _emit(
            {
                "status": "failed",
                "code": "export_failed",
                "message": "Evidence export could not be completed.",
            },
            error_output=True,
        )
        return 1
    finally:
        if output_binding is not None:
            output_binding.close()

    _emit(
        {
            "status": "ok",
            "case_id": snapshot["server_case_id"],
            "physical_evidence_id": snapshot["physical_evidence_id"],
            "physical_evidence_snapshot_sha256": snapshot[
                "physical_evidence_snapshot_sha256"
            ],
            "output": str(arguments.output),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
