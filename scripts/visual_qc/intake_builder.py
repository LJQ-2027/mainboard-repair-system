from __future__ import annotations

import os
from pathlib import Path
import tempfile

from scripts.visual_qc.intake import (
    BATCH_SCHEMA_VERSION,
    CAPTURE_STAGES,
    IntakeValidationError,
    _image_evidence,
    _require_safe_id,
    validate_intake_batch,
    write_json_atomic,
)
from scripts.visual_qc.server.catalog import BoardCatalog, CatalogError


CONFIRMED_CAPTURE_CHECKLIST = {
    "board_and_side_confirmed": True,
    "focus_and_lens_confirmed": True,
    "lighting_and_occlusion_confirmed": True,
}


def parse_image_assignment(raw: str) -> tuple[str, Path]:
    if not isinstance(raw, str) or "=" not in raw:
        raise IntakeValidationError("image assignment must use side_id=path")
    side_id, raw_path = raw.split("=", 1)
    side_id = side_id.strip()
    raw_path = raw_path.strip()
    if not side_id or not raw_path:
        raise IntakeValidationError("image assignment must use side_id=path")
    return side_id, Path(raw_path).expanduser()


def build_intake_manifest(
    *,
    project_root: Path,
    batch_id: str,
    board_key: str,
    capture_session_id: str,
    capture_stage: str,
    capture_setup_id: str,
    image_assignments: list[tuple[str, Path]],
    capture_checklist_confirmed: bool,
) -> dict:
    batch_id = _require_safe_id(batch_id, "batch_id")
    board_key = _require_safe_id(board_key, "board_key")
    capture_session_id = _require_safe_id(
        capture_session_id, "capture_session_id"
    )
    capture_setup_id = _require_safe_id(capture_setup_id, "capture_setup_id")
    if capture_stage not in CAPTURE_STAGES:
        raise IntakeValidationError(f"invalid capture_stage: {capture_stage}")
    if not capture_checklist_confirmed:
        raise IntakeValidationError("explicit capture checklist confirmation is required")
    if not image_assignments:
        raise IntakeValidationError("at least one image assignment is required")

    project_root = Path(project_root).resolve()
    catalog = BoardCatalog(project_root)
    try:
        catalog.resolve_board(board_key)
    except CatalogError as exc:
        raise IntakeValidationError(str(exc)) from exc

    seen_sides: set[str] = set()
    seen_paths: set[Path] = set()
    rows = []
    for raw_side_id, raw_path in image_assignments:
        side_id = _require_safe_id(raw_side_id, "side_id")
        if side_id in seen_sides:
            raise IntakeValidationError(f"duplicate side_id: {side_id}")
        seen_sides.add(side_id)

        try:
            catalog.resolve_side(board_key, side_id)
        except CatalogError as exc:
            raise IntakeValidationError(str(exc)) from exc

        path = Path(raw_path).expanduser().resolve()
        if path in seen_paths:
            raise IntakeValidationError(f"duplicate resolved image path: {path}")
        seen_paths.add(path)
        if not path.is_file():
            raise IntakeValidationError(f"image file does not exist: {path}")
        if path == project_root or project_root in path.parents:
            raise IntakeValidationError(
                "project reference or proxy image cannot enter physical intake"
            )
        evidence = _image_evidence(path)

        entry_id = _require_safe_id(
            f"{capture_session_id}-{side_id}", "generated entry_id"
        )
        rows.append(
            {
                "entry_id": entry_id,
                "file_path": str(path),
                "board_key": board_key,
                "side_id": side_id,
                "capture_stage": capture_stage,
                "capture_session_id": capture_session_id,
                "capture_setup_id": capture_setup_id,
                "capture_checklist": dict(CONFIRMED_CAPTURE_CHECKLIST),
                "expected_sha256": evidence["sha256"],
            }
        )

    return {
        "schema_version": BATCH_SCHEMA_VERSION,
        "batch_id": batch_id,
        "entries": sorted(rows, key=lambda row: row["side_id"]),
    }


def create_validated_intake_manifest(
    *,
    output_path: Path,
    force: bool = False,
    **builder_options: object,
) -> dict:
    output_path = Path(output_path).expanduser().resolve()
    if output_path.exists() and not force:
        raise IntakeValidationError(f"output already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_intake_manifest(**builder_options)
    source_paths = {Path(entry["file_path"]).resolve() for entry in manifest["entries"]}
    if output_path in source_paths:
        raise IntakeValidationError("output path cannot replace a source image")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".validation.json",
        dir=output_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        write_json_atomic(temporary_path, manifest)
        validated_batch = validate_intake_batch(
            temporary_path, Path(builder_options["project_root"])
        )
        if force:
            os.replace(temporary_path, output_path)
        else:
            try:
                os.link(temporary_path, output_path)
            except FileExistsError as exc:
                raise IntakeValidationError(
                    "output appeared while the manifest was being validated"
                ) from exc
            temporary_path.unlink()
    finally:
        temporary_path.unlink(missing_ok=True)

    return {
        "output_path": output_path,
        "manifest": manifest,
        "validated_batch": validated_batch,
    }
