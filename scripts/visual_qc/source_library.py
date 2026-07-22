from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.visual_qc.intake import (
    CAPTURE_STAGES,
    CHECKLIST_ITEMS,
    IntakeValidationError,
    SHA256,
    _image_evidence,
    _require_safe_id,
)
from scripts.visual_qc.intake_builder import build_intake_manifest
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
