from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib import error, parse, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.repair_evidence_link_contract import (  # noqa: E402
    canonical_json_bytes,
    canonical_sha256,
)
from scripts.visual_qc.repair_evidence_link_library import (  # noqa: E402
    RepairEvidenceLinkLibraryError,
    _is_reparse_or_symlink,
    validate_repair_evidence_link_revision_on_disk,
)


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_CREDENTIAL_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
DETAIL_SCHEMA_VERSION = "VISUAL-QC-REPAIR-EVIDENCE-LINK-DETAIL-V1"
ASSOCIATION_STATUSES = (
    "related", "possibly_related", "not_related", "insufficient_evidence"
)
VISIBILITY_STATUSES = ("not_assessed", "visible", "not_visible", "occluded")
HEALTH_REASONS = {
    "server_case_identity_mismatch", "image_identity_mismatch",
    "qualified_handoff_mismatch", "registration_job_mismatch",
    "registration_review_mismatch", "board_asset_mismatch",
    "server_case_missing", "image_missing", "registration_job_missing",
    "registration_review_missing", "board_asset_missing",
}


class SyncError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class RejectRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(
        self, _request, _file_pointer, _code, _message, _headers, _new_url
    ):
        raise SyncError(
            "redirect_rejected", "Visual-QC API redirects are not allowed."
        )


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise SyncError("invalid_arguments", "Synchronization arguments are invalid.")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        description="Synchronize one immutable repair-evidence link revision.",
        allow_abbrev=False,
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--library-root", required=True, type=Path)
    parser.add_argument("--api-base", required=True)
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--actor-id")
    parser.add_argument("--allow-http-localhost", action="store_true")
    return parser


def _safe_file_bytes(path: Path, *, label: str, maximum: int) -> bytes:
    path = Path(path).expanduser().absolute()
    for candidate in (path, *path.parents):
        if _is_reparse_or_symlink(candidate):
            raise SyncError("unsafe_path", f"{label} path is unsafe.")
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise SyncError("input_unavailable", f"{label} is unavailable.") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise SyncError("unsafe_path", f"{label} path is unsafe.")
    if metadata.st_size < 1 or metadata.st_size > maximum:
        raise SyncError("input_invalid", f"{label} has an invalid size.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SyncError("input_unavailable", f"{label} is unavailable.") from exc
    try:
        before = os.fstat(descriptor)
        content = os.read(descriptor, maximum + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_size,
        item.st_nlink,
        getattr(item, "st_mtime_ns", None),
    )
    if (
        len(content) < 1
        or len(content) > maximum
        or identity(before) != identity(after)
        or len(content) != after.st_size
    ):
        raise SyncError("input_changed", f"{label} changed while reading.")
    return content


def _load_credentials(path: Path | None) -> dict:
    if path is None:
        return {"username": None, "password": None, "actor_id": None}
    content = _safe_file_bytes(
        path, label="Credential configuration", maximum=MAX_CREDENTIAL_BYTES
    )
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncError(
            "invalid_credentials", "Credential configuration is invalid."
        ) from exc
    if not isinstance(payload, dict) or set(payload) - {
        "username", "password", "actor_id"
    }:
        raise SyncError("invalid_credentials", "Credential configuration is invalid.")
    return {
        "username": payload.get("username"),
        "password": payload.get("password"),
        "actor_id": payload.get("actor_id"),
    }


def _transport_configuration(
    api_base: str,
    *,
    credentials: dict,
    actor_id: str | None,
    allow_http_localhost: bool,
) -> tuple[str, str, str | None]:
    parsed = parse.urlsplit(api_base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
        or "\\" in parsed.path
        or any(segment in {".", ".."} for segment in parse.unquote(parsed.path).split("/"))
    ):
        raise SyncError("invalid_api_base", "API base is invalid.")
    loopback = parsed.hostname.lower() in {"127.0.0.1", "localhost", "::1"}
    explicit_local_http = (
        parsed.scheme == "http" and loopback and allow_http_localhost
    )
    if parsed.scheme == "http" and not explicit_local_http:
        raise SyncError(
            "insecure_transport",
            "HTTP is allowed only for an explicitly enabled loopback API.",
        )
    username = credentials["username"]
    password = credentials["password"]
    has_username = isinstance(username, str) and bool(username)
    has_password = isinstance(password, str) and bool(password)
    if has_username != has_password:
        raise SyncError("invalid_credentials", "Credential configuration is invalid.")
    resolved_actor = actor_id or credentials["actor_id"]
    if not isinstance(resolved_actor, str) or SAFE_ID.fullmatch(resolved_actor) is None:
        raise SyncError("invalid_actor_id", "Actor identity is invalid.")
    credentialless_local_actor = (
        not has_username
        and not has_password
        and resolved_actor == "milo-visual-data-operator"
        and explicit_local_http
    )
    if not (has_username and has_password) and not credentialless_local_actor:
        raise SyncError(
            "credentials_required", "Credentials are required for this API."
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


def _validated_snapshot(manifest_path: Path, library_root: Path) -> tuple[dict, str, bytes]:
    manifest_path = Path(manifest_path).expanduser().absolute()
    library_root = Path(library_root).expanduser().absolute()
    before = _safe_file_bytes(
        manifest_path, label="Repair-evidence link manifest", maximum=16 * 1024 * 1024
    )
    try:
        manifest = validate_repair_evidence_link_revision_on_disk(
            manifest_path, project_root=PROJECT_ROOT, library_root=library_root
        )
    except RepairEvidenceLinkLibraryError as exc:
        raise SyncError("invalid_revision", "Repair-evidence link revision is invalid.") from exc
    canonical = canonical_json_bytes(manifest)
    after = _safe_file_bytes(
        manifest_path, label="Repair-evidence link manifest", maximum=16 * 1024 * 1024
    )
    # The controlled library writes human-readable JSON while the wire payload
    # is canonicalized below.  Byte identity across the validation window is
    # the anti-race guarantee; requiring the library's on-disk layout to be
    # the compact wire layout would reject every normally staged revision.
    if before != after:
        raise SyncError(
            "manifest_changed", "Repair-evidence link manifest changed during validation."
        )
    return manifest, canonical_sha256(manifest), after


def _load_json_object(content: bytes) -> dict:
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise SyncError("malformed_response", "Server response is malformed.")
            result[key] = value
        return result

    try:
        result = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=lambda _token: (_ for _ in ()).throw(
                SyncError("malformed_response", "Server response is malformed.")
            ),
        )
    except SyncError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncError("malformed_response", "Server response is malformed.") from exc
    if not isinstance(result, dict):
        raise SyncError("malformed_response", "Server response is malformed.")
    return result


def _open_no_redirect(http_request, *, timeout: float):
    return request.build_opener(RejectRedirectHandler()).open(
        http_request, timeout=timeout
    )


def _post_projection(
    api_base: str, payload: dict, *, actor_id: str, authorization: str | None
) -> tuple[int, dict]:
    content = canonical_json_bytes(payload)
    if len(content) > 16 * 1024 * 1024:
        raise SyncError("request_too_large", "Projection request is too large.")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Actor-Id": actor_id,
        "X-Actor-Role": "reviewer",
    }
    if authorization is not None:
        headers["Authorization"] = authorization
    http_request = request.Request(
        f"{api_base}/admin/repair-evidence-links",
        data=content,
        headers=headers,
        method="POST",
    )
    try:
        with _open_no_redirect(http_request, timeout=60) as response:
            status = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            declared_length = response.headers.get("Content-Length")
            if status not in {200, 201}:
                raise SyncError("http_error", "Visual-QC API returned an unexpected status.")
            if content_type.split(";", 1)[0].strip().lower() != "application/json":
                raise SyncError("invalid_content_type", "Visual-QC API response is not JSON.")
            if declared_length is not None:
                try:
                    size = int(declared_length)
                except (TypeError, ValueError) as exc:
                    raise SyncError("malformed_response", "Server response is malformed.") from exc
                if size < 0 or size > MAX_RESPONSE_BYTES:
                    raise SyncError("response_too_large", "Visual-QC API response is too large.")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise SyncError("response_too_large", "Visual-QC API response is too large.")
    except SyncError:
        raise
    except error.HTTPError as exc:
        raise SyncError("http_error", "Visual-QC API rejected the projection.") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise SyncError("transport_failure", "Visual-QC API request failed.") from exc
    return status, _load_json_object(body)


def _is_safe_id(value: object) -> bool:
    return isinstance(value, str) and SAFE_ID.fullmatch(value) is not None


def _is_nonnegative_integer(value: object) -> bool:
    return type(value) is int and value >= 0


def _exact_keys(value: object, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _validate_receipt(status: int, receipt: dict, manifest: dict, digest: str) -> dict:
    expected_keys = {
        "schema_version", "link_set_id", "revision", "manifest_sha256",
        "repair_case_id", "board", "server_case_ids", "counts", "health",
        "imported_at", "binding_states", "manifest",
    }
    if not _exact_keys(receipt, expected_keys):
        raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
    references = manifest.get("repair_case_references")
    board = manifest.get("board")
    physical = manifest.get("physical_evidence")
    bindings = manifest.get("bindings")
    if (
        receipt["schema_version"] != DETAIL_SCHEMA_VERSION
        or not _is_safe_id(receipt["link_set_id"])
        or receipt["link_set_id"] != manifest.get("link_set_id")
        or type(receipt["revision"]) is not int
        or receipt["revision"] < 1
        or receipt["revision"] != manifest.get("revision")
        or not isinstance(receipt["manifest_sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", receipt["manifest_sha256"]) is None
        or receipt["manifest_sha256"] != digest
        or not isinstance(receipt["imported_at"], str)
        or not receipt["imported_at"]
        or not isinstance(references, list)
        or not isinstance(board, dict)
        or not isinstance(physical, list)
        or not isinstance(bindings, list)
        or receipt["manifest"] != manifest
        or canonical_sha256(receipt["manifest"]) != digest
    ):
        raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
    repair_case_ids = {item.get("repair_case_id") for item in references if isinstance(item, dict)}
    server_case_ids = [item.get("server_case_id") for item in physical if isinstance(item, dict)]
    if (
        len(repair_case_ids) != 1
        or not all(_is_safe_id(value) for value in repair_case_ids)
        or receipt["repair_case_id"] not in repair_case_ids
        or not _exact_keys(receipt["board"], {"board_key", "board_id"})
        or receipt["board"] != {"board_key": board.get("board_key"), "board_id": board.get("board_id")}
        or not all(_is_safe_id(value) for value in receipt["board"].values())
        or not isinstance(receipt["server_case_ids"], list)
        or not receipt["server_case_ids"]
        or len(set(receipt["server_case_ids"])) != len(receipt["server_case_ids"])
        or any(not _is_safe_id(value) for value in receipt["server_case_ids"])
        or set(receipt["server_case_ids"]) != set(server_case_ids)
    ):
        raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
    health = receipt["health"]
    if (
        not _exact_keys(health, {"state", "reasons"})
        or health["state"] != "active"
        or not isinstance(health["reasons"], list)
        or health["reasons"]
        or len(set(health["reasons"])) != len(health["reasons"])
        or any(reason not in HEALTH_REASONS for reason in health["reasons"])
    ):
        raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
    association = {name: 0 for name in ASSOCIATION_STATUSES}
    visibility = {name: 0 for name in VISIBILITY_STATUSES}
    binding_ids = set()
    for binding in bindings:
        if not isinstance(binding, dict) or not _is_safe_id(binding.get("binding_id")):
            raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
        binding_ids.add(binding["binding_id"])
        if binding.get("association_status") not in association or binding.get("visibility_status") not in visibility:
            raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
        association[binding["association_status"]] += 1
        visibility[binding["visibility_status"]] += 1
    states = receipt["binding_states"]
    if not isinstance(states, list) or len(states) != len(binding_ids):
        raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
    source_superseded = 0
    binding_superseded = 0
    observed_binding_ids = set()
    for state in states:
        if not _exact_keys(
            state,
            {
                "binding_id", "source_fact_superseded", "replacement_fact_id",
                "binding_superseded", "replacement_binding_id",
            },
        ) or not _is_safe_id(state["binding_id"]):
            raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
        for superseded_key, replacement_key in (
            ("source_fact_superseded", "replacement_fact_id"),
            ("binding_superseded", "replacement_binding_id"),
        ):
            replacement = state[replacement_key]
            if (
                type(state[superseded_key]) is not bool
                or (replacement is not None and not _is_safe_id(replacement))
                or state[superseded_key] != (replacement is not None)
            ):
                raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
        observed_binding_ids.add(state["binding_id"])
        source_superseded += state["source_fact_superseded"]
        binding_superseded += state["binding_superseded"]
    counts = receipt["counts"]
    if (
        not _exact_keys(counts, {"association", "visibility", "source_fact_superseded", "binding_superseded"})
        or not _exact_keys(counts["association"], set(ASSOCIATION_STATUSES))
        or not _exact_keys(counts["visibility"], set(VISIBILITY_STATUSES))
        or any(not _is_nonnegative_integer(value) for value in counts["association"].values())
        or any(not _is_nonnegative_integer(value) for value in counts["visibility"].values())
        or not _is_nonnegative_integer(counts["source_fact_superseded"])
        or not _is_nonnegative_integer(counts["binding_superseded"])
        or counts["association"] != association
        or counts["visibility"] != visibility
        or counts["source_fact_superseded"] != source_superseded
        or counts["binding_superseded"] != binding_superseded
        or observed_binding_ids != binding_ids
    ):
        raise SyncError("invalid_receipt", "Projection receipt is invalid or not active.")
    return {
        "status": "ok",
        "state": "accepted",
        "link_set_id": manifest["link_set_id"],
        "revision": manifest["revision"],
        "manifest_sha256": digest,
        "projection_state": "active",
    }


def _emit(payload: dict, *, error_output: bool = False) -> None:
    print(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        file=sys.stderr if error_output else sys.stdout,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        credentials = _load_credentials(arguments.credential_file)
        api_base, actor_id, authorization = _transport_configuration(
            arguments.api_base,
            credentials=credentials,
            actor_id=arguments.actor_id,
            allow_http_localhost=arguments.allow_http_localhost,
        )
        manifest, digest, manifest_bytes = _validated_snapshot(
            arguments.manifest, arguments.library_root
        )
        # Re-read after all preflight work, immediately before the single POST.
        current = _safe_file_bytes(
            arguments.manifest,
            label="Repair-evidence link manifest",
            maximum=16 * 1024 * 1024,
        )
        if current != manifest_bytes:
            raise SyncError("manifest_changed", "Repair-evidence link manifest changed before synchronization.")
        status, response = _post_projection(
            api_base,
            {"manifest": manifest, "manifest_sha256": digest},
            actor_id=actor_id,
            authorization=authorization,
        )
        receipt = _validate_receipt(status, response, manifest, digest)
    except SyncError as exc:
        _emit({"status": "failed", "code": exc.code, "message": exc.message}, error_output=True)
        return 2
    except Exception:
        _emit(
            {"status": "failed", "code": "sync_failed", "message": "Repair-evidence link synchronization failed."},
            error_output=True,
        )
        return 1
    _emit(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
