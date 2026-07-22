from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

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
    package_path = Path(package_path).resolve()
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
    expected_package_path = (
        library_root / "packages" / package_id / "source-package.json"
    ).resolve()
    if package_path != expected_package_path:
        raise IntakeValidationError("source package path does not match package_id")

    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries or len(raw_entries) > 500:
        raise IntakeValidationError("entries must contain 1 to 500 records")
    seen_sides: set[str] = set()
    normalized = []
    originals_root = (library_root / "objects" / "originals").resolve()
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
        object_file = (library_root / expected_object_path).resolve()
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


def _store_object(source: Path, destination: Path, expected_sha256: str) -> None:
    if destination.exists():
        _assert_object_integrity(destination, expected_sha256)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
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
        temporary_path.unlink()
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
    package_dir = library_root / "packages" / payload["package_id"]
    if package_dir.exists():
        return _reuse_existing_package(
            package_dir=package_dir,
            requested_payload=payload,
            project_root=project_root,
            library_root=library_root,
        )

    sources = {
        side_id: Path(path).expanduser().resolve()
        for side_id, path in image_assignments
    }
    for entry in payload["entries"]:
        _store_object(
            sources[entry["side_id"]],
            library_root / entry["object_path"],
            entry["sha256"],
        )

    packages_root = library_root / "packages"
    packages_root.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(
        tempfile.mkdtemp(prefix=f".{payload['package_id']}.", dir=packages_root)
    )
    try:
        write_json_atomic(temporary_dir / "source-package.json", payload)
        intake_result = create_validated_intake_manifest(
            output_path=temporary_dir / f"{payload['batch_id']}.intake.json",
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
            raise IntakeValidationError("archived intake manifest is not deterministic")
        try:
            os.rename(temporary_dir, package_dir)
        except OSError:
            if not package_dir.exists():
                raise
            return _reuse_existing_package(
                package_dir=package_dir,
                requested_payload=payload,
                project_root=project_root,
                library_root=library_root,
            )
    finally:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)

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
