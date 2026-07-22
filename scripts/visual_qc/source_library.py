from __future__ import annotations

import copy
from contextlib import contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from scripts.visual_qc.intake import (
    CAPTURE_STAGES,
    CHECKLIST_ITEMS,
    IntakeValidationError,
    SHA256,
    _image_evidence,
    _require_safe_id,
    validate_intake_batch,
    write_json_atomic,
)
from scripts.visual_qc.intake_builder import (
    build_intake_manifest,
    create_validated_intake_manifest,
)
from scripts.visual_qc.proxy_inventory import (
    known_proxy_hashes,
    proxy_inventory_sha256,
)
from scripts.visual_qc.server.catalog import BoardCatalog, CatalogError
from scripts.visual_qc.server.storage import MIME_EXTENSIONS


SOURCE_PACKAGE_SCHEMA_VERSION = "VISUAL-QC-SOURCE-PACKAGE-V1"
SOURCE_ORIGIN = "milo_supplied"
PACKAGE_FIELDS = {
    "schema_version",
    "package_id",
    "batch_id",
    "source_origin",
    "physical_source_confirmed",
    "proxy_inventory_sha256",
    "board_key",
    "board_id",
    "capture_stage",
    "capture_session_id",
    "capture_setup_id",
    "capture_checklist",
    "entries",
}
ENTRY_FIELDS = {
    "entry_id",
    "side_id",
    "original_filename",
    "object_path",
    "mime_type",
    "width",
    "height",
    "byte_size",
    "sha256",
}
REPARSE_POINT_ATTRIBUTE = 0x400
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return path.is_symlink() or bool(
        getattr(metadata, "st_file_attributes", 0) & REPARSE_POINT_ATTRIBUTE
    )


def _absolute_lexical_path(path: Path) -> Path:
    absolute = Path(os.path.abspath(Path(path).expanduser()))
    if os.name != "nt":
        return absolute

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_long_path = kernel32.GetLongPathNameW
    get_long_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    get_long_path.restype = ctypes.c_uint32
    existing = absolute
    suffix: list[str] = []
    while not existing.exists() and existing != existing.parent:
        suffix.append(existing.name)
        existing = existing.parent
    size = get_long_path(str(existing), None, 0)
    if size:
        buffer = ctypes.create_unicode_buffer(size)
        if get_long_path(str(existing), buffer, size):
            existing = Path(buffer.value)
    for part in reversed(suffix):
        existing = existing / part
    return existing


def _assert_controlled_path(
    library_root: Path, candidate: Path, label: str
) -> Path:
    library_root = Path(library_root).resolve()
    candidate = _absolute_lexical_path(candidate)
    try:
        relative = candidate.relative_to(library_root)
    except ValueError as exc:
        raise IntakeValidationError(f"{label} escapes controlled library") from exc

    current = library_root
    for part in relative.parts:
        current = current / part
        if _is_reparse_or_symlink(current):
            raise IntakeValidationError(
                f"{label} contains a reparse point or symlink: {current}"
            )
    resolved = candidate.resolve(strict=False)
    if resolved != library_root and library_root not in resolved.parents:
        raise IntakeValidationError(f"{label} escapes controlled library")
    return candidate


def _fsync_directory(path: Path) -> None:
    path = Path(path)
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return

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
    handle = create_file(
        str(path),
        0x40000000,  # GENERIC_WRITE
        0x00000001 | 0x00000002 | 0x00000004,
        None,
        3,  # OPEN_EXISTING
        0x02000000,  # FILE_FLAG_BACKUP_SEMANTICS
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle in {None, invalid_handle}:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel32.FlushFileBuffers(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(handle)


def _ensure_directory_durable(path: Path) -> None:
    path = Path(path)
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        if current == current.parent:
            break
        current = current.parent
    path.mkdir(parents=True, exist_ok=True)
    for created in reversed(missing):
        _fsync_directory(created)
        if created.parent.exists():
            _fsync_directory(created.parent)


def _write_completion_marker(path: Path) -> None:
    with path.open("x", encoding="ascii", newline="\n") as handle:
        handle.write("complete\n")
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def _package_lock(packages_root: Path, package_id: str):
    locks_root = packages_root / ".locks"
    _ensure_directory_durable(locks_root)
    _assert_controlled_path(packages_root.parent, locks_root, "package lock path")
    lock_path = locks_root / f"{package_id}.lock"
    _assert_controlled_path(packages_root.parent, lock_path, "package lock path")
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        if os.name == "nt":
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _resolve_library_root(project_root: Path, library_root: Path) -> Path:
    project_root = Path(project_root).resolve()
    library_root = Path(library_root).expanduser().resolve()
    if library_root == project_root or project_root in library_root.parents:
        raise IntakeValidationError(
            "controlled source library must be outside the project repository"
        )
    return library_root


def _canonical_object_path(sha256: str, mime_type: str) -> str:
    extension = MIME_EXTENSIONS.get(mime_type)
    if extension is None:
        raise IntakeValidationError(f"unsupported source MIME type: {mime_type}")
    return f"objects/originals/{sha256[:2]}/{sha256}{extension}"


def build_source_package(
    *,
    project_root: Path,
    library_root: Path,
    package_id: str,
    batch_id: str,
    board_key: str,
    capture_session_id: str,
    capture_stage: str,
    capture_setup_id: str,
    image_assignments: list[tuple[str, Path]],
    milo_physical_source_confirmed: bool,
    capture_checklist_confirmed: bool,
) -> dict:
    project_root = Path(project_root).resolve()
    _resolve_library_root(project_root, library_root)
    package_id = _require_safe_id(package_id, "package_id")
    if not milo_physical_source_confirmed:
        raise IntakeValidationError(
            "explicit Milo-supplied physical source confirmation is required"
        )

    intake = build_intake_manifest(
        project_root=project_root,
        batch_id=batch_id,
        board_key=board_key,
        capture_session_id=capture_session_id,
        capture_stage=capture_stage,
        capture_setup_id=capture_setup_id,
        image_assignments=image_assignments,
        capture_checklist_confirmed=capture_checklist_confirmed,
    )
    catalog = BoardCatalog(project_root)
    board = catalog.resolve_board(board_key)
    entries = []
    for intake_entry in intake["entries"]:
        source_path = Path(intake_entry["file_path"])
        evidence = _image_evidence(source_path)
        entries.append(
            {
                "entry_id": intake_entry["entry_id"],
                "side_id": intake_entry["side_id"],
                "original_filename": source_path.name,
                "object_path": _canonical_object_path(
                    evidence["sha256"], evidence["mime_type"]
                ),
                **evidence,
            }
        )

    return {
        "schema_version": SOURCE_PACKAGE_SCHEMA_VERSION,
        "package_id": package_id,
        "batch_id": intake["batch_id"],
        "source_origin": SOURCE_ORIGIN,
        "physical_source_confirmed": True,
        "proxy_inventory_sha256": proxy_inventory_sha256(project_root),
        "board_key": board_key,
        "board_id": board["board_id"],
        "capture_stage": capture_stage,
        "capture_session_id": capture_session_id,
        "capture_setup_id": capture_setup_id,
        "capture_checklist": copy.deepcopy(
            intake["entries"][0]["capture_checklist"]
        ),
        "entries": entries,
    }


def _read_package(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeValidationError(f"invalid source package: {exc}") from exc
    if not isinstance(payload, dict):
        raise IntakeValidationError("invalid source package: root must be an object")
    return payload


def validate_source_package(
    package_path: Path, project_root: Path, library_root: Path
) -> dict:
    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    package_path = _assert_controlled_path(
        library_root, package_path, "source package path"
    )
    package_dir = package_path.parent
    completion_marker = _assert_controlled_path(
        library_root, package_dir / ".complete", "source package completion marker"
    )
    if not completion_marker.is_file():
        raise IntakeValidationError("source package is incomplete")
    payload = _read_package(package_path)
    if set(payload) != PACKAGE_FIELDS:
        raise IntakeValidationError("invalid source package fields")
    if payload.get("schema_version") != SOURCE_PACKAGE_SCHEMA_VERSION:
        raise IntakeValidationError(
            f"schema_version must be {SOURCE_PACKAGE_SCHEMA_VERSION}"
        )

    package_id = _require_safe_id(payload.get("package_id"), "package_id")
    batch_id = _require_safe_id(payload.get("batch_id"), "batch_id")
    board_key = _require_safe_id(payload.get("board_key"), "board_key")
    session_id = _require_safe_id(
        payload.get("capture_session_id"), "capture_session_id"
    )
    setup_id = _require_safe_id(payload.get("capture_setup_id"), "capture_setup_id")
    if payload.get("source_origin") != SOURCE_ORIGIN:
        raise IntakeValidationError("source_origin must be milo_supplied")
    if payload.get("physical_source_confirmed") is not True:
        raise IntakeValidationError("physical_source_confirmed must be true")
    inventory_sha256 = payload.get("proxy_inventory_sha256")
    if (
        not isinstance(inventory_sha256, str)
        or not LOWER_SHA256.fullmatch(inventory_sha256)
    ):
        raise IntakeValidationError("invalid proxy_inventory_sha256")
    if payload.get("capture_stage") not in CAPTURE_STAGES:
        raise IntakeValidationError("invalid capture_stage")
    checklist = payload.get("capture_checklist")
    if (
        not isinstance(checklist, dict)
        or set(checklist) != CHECKLIST_ITEMS
        or not all(checklist.get(item) is True for item in CHECKLIST_ITEMS)
    ):
        raise IntakeValidationError("incomplete capture checklist")

    catalog = BoardCatalog(project_root)
    try:
        board = catalog.resolve_board(board_key)
    except CatalogError as exc:
        raise IntakeValidationError(str(exc)) from exc
    if payload.get("board_id") != board["board_id"]:
        raise IntakeValidationError("source package board_id does not match catalog")
    expected_package_path = library_root / "packages" / package_id / "source-package.json"
    if package_path != expected_package_path:
        raise IntakeValidationError("source package path does not match package_id")

    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries or len(raw_entries) > 500:
        raise IntakeValidationError("entries must contain 1 to 500 records")
    seen_sides: set[str] = set()
    normalized = []
    originals_root = library_root / "objects" / "originals"
    try:
        proxy_hashes = known_proxy_hashes(project_root)
    except (OSError, ValueError, KeyError) as exc:
        raise IntakeValidationError(f"invalid proxy inventory: {exc}") from exc
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
            raise IntakeValidationError(f"invalid source package entry fields: {index}")
        side_id = _require_safe_id(entry.get("side_id"), "side_id")
        if side_id in seen_sides:
            raise IntakeValidationError(f"duplicate side_id: {side_id}")
        seen_sides.add(side_id)
        try:
            catalog.resolve_side(board_key, side_id)
        except CatalogError as exc:
            raise IntakeValidationError(str(exc)) from exc
        expected_entry_id = _require_safe_id(
            f"{session_id}-{side_id}", "generated entry_id"
        )
        if entry.get("entry_id") != expected_entry_id:
            raise IntakeValidationError("source package entry_id does not match session/side")

        filename = entry.get("original_filename")
        if not isinstance(filename, str) or not filename or Path(filename).name != filename:
            raise IntakeValidationError("invalid original_filename")
        sha256 = entry.get("sha256")
        mime_type = entry.get("mime_type")
        if not isinstance(sha256, str) or not SHA256.fullmatch(sha256):
            raise IntakeValidationError("invalid source package sha256")
        expected_object_path = _canonical_object_path(sha256, mime_type)
        if entry.get("object_path") != expected_object_path:
            raise IntakeValidationError("invalid object_path")
        object_file = _assert_controlled_path(
            library_root, library_root / expected_object_path, "source object path"
        )
        if originals_root not in object_file.parents:
            raise IntakeValidationError("invalid object_path containment")
        try:
            evidence = _image_evidence(object_file)
        except (IntakeValidationError, OSError) as exc:
            raise IntakeValidationError(
                f"object integrity failure: {expected_object_path}"
            ) from exc
        for field in ("mime_type", "width", "height", "byte_size", "sha256"):
            if entry.get(field) != evidence[field]:
                raise IntakeValidationError(
                    f"object integrity mismatch: {expected_object_path}"
                )
        if evidence["sha256"] in proxy_hashes:
            raise IntakeValidationError(
                f"known reference or revoked proxy object: {expected_object_path}"
            )
        normalized.append({**copy.deepcopy(entry), "object_file": object_file})

    return {
        **{key: copy.deepcopy(payload[key]) for key in PACKAGE_FIELDS if key != "entries"},
        "entries": normalized,
        "package_path": package_path,
        "batch_id": batch_id,
        "capture_session_id": session_id,
        "capture_setup_id": setup_id,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_object_integrity(path: Path, expected_sha256: str) -> None:
    try:
        actual = _sha256_file(path)
    except OSError as exc:
        raise IntakeValidationError(f"object integrity failure: {path}") from exc
    if actual != expected_sha256:
        raise IntakeValidationError(f"object integrity mismatch: {path}")


def _store_object(
    source: Path, destination: Path, expected_sha256: str, library_root: Path
) -> None:
    _assert_controlled_path(library_root, destination, "source object path")
    if destination.exists():
        _assert_object_integrity(destination, expected_sha256)
        return
    _ensure_directory_durable(destination.parent)
    _assert_controlled_path(library_root, destination, "source object path")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{expected_sha256}.", suffix=".staging", dir=destination.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as target, source.open("rb") as incoming:
            shutil.copyfileobj(incoming, target, length=1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        _assert_object_integrity(temporary_path, expected_sha256)
        try:
            os.link(temporary_path, destination)
        except FileExistsError:
            _assert_object_integrity(destination, expected_sha256)
        _assert_controlled_path(library_root, destination, "source object path")
        _assert_object_integrity(destination, expected_sha256)
        temporary_path.unlink()
        _fsync_directory(destination.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def _archived_assignments(payload: dict, library_root: Path) -> list[tuple[str, Path]]:
    return [
        (entry["side_id"], library_root / entry["object_path"])
        for entry in payload["entries"]
    ]


def _build_archived_intake(payload: dict, project_root: Path, library_root: Path) -> dict:
    return build_intake_manifest(
        project_root=project_root,
        batch_id=payload["batch_id"],
        board_key=payload["board_key"],
        capture_session_id=payload["capture_session_id"],
        capture_stage=payload["capture_stage"],
        capture_setup_id=payload["capture_setup_id"],
        image_assignments=_archived_assignments(payload, library_root),
        capture_checklist_confirmed=True,
    )


def _result(
    *, package_dir: Path, payload: dict, state: str, validated_source: dict
) -> dict:
    return {
        "state": state,
        "package_id": payload["package_id"],
        "batch_id": payload["batch_id"],
        "entry_count": len(payload["entries"]),
        "source_package_path": (
            package_dir / "source-package.json"
        ).resolve(),
        "intake_manifest_path": (
            package_dir / f"{payload['batch_id']}.intake.json"
        ).resolve(),
        "validated_source_package": validated_source,
    }


def _reuse_existing_package(
    *,
    package_dir: Path,
    requested_payload: dict,
    project_root: Path,
    library_root: Path,
) -> dict:
    _assert_controlled_path(library_root, package_dir, "source package directory")
    completion_marker = _assert_controlled_path(
        library_root, package_dir / ".complete", "source package completion marker"
    )
    if not completion_marker.is_file():
        raise IntakeValidationError(
            f"source package is incomplete: {requested_payload['package_id']}"
        )
    source_path = package_dir / "source-package.json"
    existing_payload = _read_package(source_path)
    validated_source = validate_source_package(
        source_path, project_root, library_root
    )
    if existing_payload != requested_payload:
        raise IntakeValidationError(
            f"source package conflict: {requested_payload['package_id']}"
        )

    intake_path = package_dir / f"{requested_payload['batch_id']}.intake.json"
    _assert_controlled_path(library_root, intake_path, "source package intake path")
    expected_intake = _build_archived_intake(
        requested_payload, project_root, library_root
    )
    try:
        existing_intake = json.loads(intake_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeValidationError("source package intake manifest is invalid") from exc
    if existing_intake != expected_intake:
        raise IntakeValidationError(
            f"source package conflict: {requested_payload['package_id']}"
        )
    validate_intake_batch(intake_path, project_root)
    return _result(
        package_dir=package_dir,
        payload=requested_payload,
        state="reused",
        validated_source=validated_source,
    )


def stage_source_package(
    *,
    project_root: Path,
    library_root: Path,
    package_id: str,
    batch_id: str,
    board_key: str,
    capture_session_id: str,
    capture_stage: str,
    capture_setup_id: str,
    image_assignments: list[tuple[str, Path]],
    milo_physical_source_confirmed: bool,
    capture_checklist_confirmed: bool,
) -> dict:
    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    options = {
        "project_root": project_root,
        "library_root": library_root,
        "package_id": package_id,
        "batch_id": batch_id,
        "board_key": board_key,
        "capture_session_id": capture_session_id,
        "capture_stage": capture_stage,
        "capture_setup_id": capture_setup_id,
        "image_assignments": image_assignments,
        "milo_physical_source_confirmed": milo_physical_source_confirmed,
        "capture_checklist_confirmed": capture_checklist_confirmed,
    }
    payload = build_source_package(**options)
    _ensure_directory_durable(library_root)
    packages_root = library_root / "packages"
    _ensure_directory_durable(packages_root)
    _assert_controlled_path(library_root, packages_root, "packages root")
    package_dir = library_root / "packages" / payload["package_id"]

    sources = {
        side_id: Path(path).expanduser().resolve()
        for side_id, path in image_assignments
    }
    for entry in payload["entries"]:
        destination = _assert_controlled_path(
            library_root,
            library_root / entry["object_path"],
            "source object path",
        )
        _store_object(
            sources[entry["side_id"]],
            destination,
            entry["sha256"],
            library_root,
        )

    with _package_lock(packages_root, payload["package_id"]):
        _assert_controlled_path(library_root, package_dir, "source package directory")
        if package_dir.exists():
            return _reuse_existing_package(
                package_dir=package_dir,
                requested_payload=payload,
                project_root=project_root,
                library_root=library_root,
            )

        created_dir = False
        try:
            package_dir.mkdir()
            created_dir = True
            _assert_controlled_path(
                library_root, package_dir, "source package directory"
            )
            write_json_atomic(package_dir / "source-package.json", payload)
            intake_result = create_validated_intake_manifest(
                output_path=package_dir / f"{payload['batch_id']}.intake.json",
                project_root=project_root,
                batch_id=payload["batch_id"],
                board_key=payload["board_key"],
                capture_session_id=payload["capture_session_id"],
                capture_stage=payload["capture_stage"],
                capture_setup_id=payload["capture_setup_id"],
                image_assignments=_archived_assignments(payload, library_root),
                capture_checklist_confirmed=True,
            )
            if intake_result["manifest"] != _build_archived_intake(
                payload, project_root, library_root
            ):
                raise IntakeValidationError(
                    "archived intake manifest is not deterministic"
                )
            _fsync_directory(package_dir)
            marker = _assert_controlled_path(
                library_root,
                package_dir / ".complete",
                "source package completion marker",
            )
            _write_completion_marker(marker)
            _fsync_directory(package_dir)
            _fsync_directory(packages_root)
        except Exception:
            if created_dir:
                shutil.rmtree(package_dir, ignore_errors=True)
            raise

    validated_source = validate_source_package(
        package_dir / "source-package.json", project_root, library_root
    )
    validate_intake_batch(
        package_dir / f"{payload['batch_id']}.intake.json", project_root
    )
    return _result(
        package_dir=package_dir,
        payload=payload,
        state="created",
        validated_source=validated_source,
    )
