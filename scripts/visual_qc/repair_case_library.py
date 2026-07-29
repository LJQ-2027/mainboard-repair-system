from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import shutil
import tempfile
import zipfile

from scripts.visual_qc.intake import (
    IntakeValidationError,
    _require_safe_id,
    write_json_atomic,
)
from scripts.visual_qc.heic_derivative import (
    HEIC_MIME_TYPE,
    inspect_heic_source,
    is_heic_path,
)
from scripts.visual_qc.repair_case_contract import (
    FIXED_FALSE_BOUNDARIES,
    MAX_SUPPORTING_FILE_BYTES,
    MAX_SUPPORTING_FILES,
    MIME_EXTENSIONS,
    MIME_EXTENSIONS_V3,
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
    REPAIR_CASE_SCHEMA_V3,
    derive_completeness,
    validate_repair_case_manifest,
)
from scripts.visual_qc.repair_case_identity import (
    derive_model_identity_resolved,
    validate_identity_transition,
)
from scripts.visual_qc.server.catalog import BoardCatalog, CatalogError
from scripts.visual_qc.server.storage import detect_image_mime_type
from scripts.visual_qc.source_library import (
    _assert_controlled_path,
    _ensure_directory_durable,
    _fsync_directory,
    _is_reparse_or_symlink,
    _package_lock,
    _resolve_library_root,
    _write_completion_marker,
    validate_source_package,
)


ROLE_CAPTURE_STAGE = {
    "before_repair": "before_repair",
    "after_repair": "after_repair",
    "golden_reference": "golden_reference",
}
COMMON_CASE_RECORD_FIELDS = {
    "supporting_evidence_descriptions",
    "reported_symptoms",
    "findings",
    "repair_actions",
    "outcome",
    "corrections",
}
V1_CASE_RECORD_FIELDS = COMMON_CASE_RECORD_FIELDS | {"device_models"}
V2_CASE_RECORD_FIELDS = COMMON_CASE_RECORD_FIELDS | {"device_identity"}
V3_CASE_RECORD_FIELDS = COMMON_CASE_RECORD_FIELDS | {
    "device_identity",
    "evidence_mode",
    "supporting_evidence_contexts",
}


def resolve_package_links(
    *,
    project_root: Path,
    library_root: Path,
    assignments: list[tuple[str, Path]],
    board_key: str,
) -> list[dict]:
    if not isinstance(assignments, list) or not assignments:
        raise IntakeValidationError("at least one source package is required")
    board_key = _require_safe_id(board_key, "board_key")
    links = []
    seen_packages: set[str] = set()
    for role, package_path in assignments:
        if role not in {*ROLE_CAPTURE_STAGE, "supplemental"}:
            raise IntakeValidationError(f"invalid repair case package role: {role}")
        package = validate_source_package(
            Path(package_path), Path(project_root), Path(library_root)
        )
        package_id = package["package_id"]
        if package_id in seen_packages:
            raise IntakeValidationError(
                f"duplicate repair case source package: {package_id}"
            )
        seen_packages.add(package_id)
        if package["board_key"] != board_key:
            raise IntakeValidationError(
                f"source package board does not match repair case: {package_id}"
            )
        expected_stage = ROLE_CAPTURE_STAGE.get(role)
        if expected_stage is not None and package["capture_stage"] != expected_stage:
            raise IntakeValidationError(
                f"source package role does not match capture stage: {package_id}"
            )
        links.append(
            {
                "package_id": package_id,
                "source_package_manifest_sha256": package["manifest_sha256"],
                "capture_stage": package["capture_stage"],
                "role": role,
                "entry_ids": [entry["entry_id"] for entry in package["entries"]],
            }
        )
    return links


def _assert_regular_source(path: Path) -> Path:
    path = Path(path).expanduser().absolute()
    current = path
    while current != current.parent:
        if _is_reparse_or_symlink(current):
            raise IntakeValidationError(
                f"supporting source contains a reparse point or symlink: {current}"
            )
        current = current.parent
    return path


def _read_stable_supporting_file(path: Path) -> bytes:
    path = _assert_regular_source(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise IntakeValidationError(
            f"unable to open supporting source: {path}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise IntakeValidationError(
                f"supporting source must be one regular non-hard-linked file: {path}"
            )
        if before.st_size < 1 or before.st_size > MAX_SUPPORTING_FILE_BYTES:
            raise IntakeValidationError(
                f"supporting source size is invalid: {path}"
            )
        chunks = []
        byte_size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            byte_size += len(chunk)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            getattr(before, "st_mtime_ns", None),
            before.st_nlink,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            getattr(after, "st_mtime_ns", None),
            after.st_nlink,
        )
        if identity_before != identity_after or byte_size != after.st_size:
            raise IntakeValidationError(
                f"supporting source changed while reading: {path}"
            )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _detect_supporting_mime(
    path: Path,
    content: bytes,
    *,
    schema_version: str,
) -> str:
    extension = path.suffix.lower()
    if schema_version == REPAIR_CASE_SCHEMA_V3 and is_heic_path(path):
        inspection = inspect_heic_source(path)
        digest = hashlib.sha256(content).hexdigest()
        if (
            inspection.get("sha256") != digest
            or inspection.get("byte_size") != len(content)
            or inspection.get("mime_type") != HEIC_MIME_TYPE
        ):
            raise IntakeValidationError(
                f"HEIC inspection does not match supporting source bytes: {path}"
            )
        return HEIC_MIME_TYPE
    image_mime = detect_image_mime_type(content)
    if extension == ".pdf" and content.startswith(b"%PDF-"):
        return "application/pdf"
    if extension in {".txt", ".csv"}:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IntakeValidationError(
                f"supporting text must be UTF-8: {path}"
            ) from exc
        if b"\x00" in content:
            raise IntakeValidationError(
                f"supporting text contains null bytes: {path}"
            )
        return "text/csv" if extension == ".csv" else "text/plain"
    if extension == ".xls" and content.startswith(
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    ):
        return "application/vnd.ms-excel"
    if extension == ".xlsx" and content.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as workbook:
                names = set(workbook.namelist())
        except (OSError, zipfile.BadZipFile) as exc:
            raise IntakeValidationError(
                f"supporting XLSX container is invalid: {path}"
            ) from exc
        if {
            "[Content_Types].xml",
            "xl/workbook.xml",
        }.issubset(names):
            return (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
    if extension == ".png" and image_mime == "image/png":
        return "image/png"
    if extension in {".jpg", ".jpeg"} and image_mime == "image/jpeg":
        return "image/jpeg"
    raise IntakeValidationError(f"unsupported supporting evidence format: {path}")


def inspect_supporting_evidence(
    assignments: list[tuple[str, Path]],
    descriptions: dict[str, str],
    *,
    schema_version: str = REPAIR_CASE_SCHEMA_V1,
) -> list[dict]:
    if not isinstance(assignments, list) or len(assignments) > MAX_SUPPORTING_FILES:
        raise IntakeValidationError(
            f"supporting files may contain at most {MAX_SUPPORTING_FILES} records"
        )
    if not isinstance(descriptions, dict):
        raise IntakeValidationError("supporting evidence descriptions are invalid")
    inspected = []
    seen_ids: set[str] = set()
    for evidence_id, raw_path in assignments:
        evidence_id = _require_safe_id(evidence_id, "evidence_id")
        if evidence_id in seen_ids:
            raise IntakeValidationError(
                f"duplicate supporting evidence_id: {evidence_id}"
            )
        seen_ids.add(evidence_id)
        description = descriptions.get(evidence_id)
        if not isinstance(description, str) or not description.strip():
            raise IntakeValidationError(
                f"supporting evidence description is required: {evidence_id}"
            )
        path = Path(raw_path).expanduser()
        content = _read_stable_supporting_file(path)
        mime_type = _detect_supporting_mime(
            path,
            content,
            schema_version=schema_version,
        )
        digest = hashlib.sha256(content).hexdigest()
        mime_extensions = (
            MIME_EXTENSIONS_V3
            if schema_version == REPAIR_CASE_SCHEMA_V3
            else MIME_EXTENSIONS
        )
        extension = mime_extensions[mime_type]
        inspected.append(
            {
                "record": {
                    "evidence_id": evidence_id,
                    "original_filename": path.name,
                    "object_path": (
                        f"objects/case-evidence/{digest[:2]}/"
                        f"{digest}{extension}"
                    ),
                    "mime_type": mime_type,
                    "byte_size": len(content),
                    "sha256": digest,
                    "description": description,
                },
                "content": content,
            }
        )
    extra_descriptions = set(descriptions) - seen_ids
    if extra_descriptions:
        raise IntakeValidationError(
            "supporting evidence descriptions contain unknown IDs"
        )
    return inspected


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_stored_object(path: Path, expected_sha256: str) -> None:
    if _is_reparse_or_symlink(path):
        raise IntakeValidationError(
            f"supporting evidence object is a reparse point or symlink: {path}"
        )
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise IntakeValidationError(
            f"supporting evidence object is missing: {path}"
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise IntakeValidationError(
            f"supporting evidence object is not a regular file: {path}"
        )
    if _hash_file(path) != expected_sha256:
        raise IntakeValidationError(
            f"supporting evidence object integrity mismatch: {path}"
        )


def store_supporting_evidence(
    *,
    library_root: Path,
    inspected: list[dict],
    project_root: Path | None = None,
) -> list[Path]:
    effective_project_root = (
        Path.cwd() if project_root is None else Path(project_root)
    )
    library_root = _resolve_library_root(effective_project_root, library_root)
    _ensure_directory_durable(library_root)
    created = []
    for item in inspected:
        record = item["record"]
        content = item["content"]
        destination = _assert_controlled_path(
            library_root,
            library_root / record["object_path"],
            "supporting evidence object path",
        )
        if destination.exists():
            _assert_stored_object(destination, record["sha256"])
            continue
        _ensure_directory_durable(destination.parent)
        _assert_controlled_path(
            library_root, destination, "supporting evidence object path"
        )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{record['sha256']}.",
            suffix=".staging",
            dir=destination.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            if _hash_file(temporary_path) != record["sha256"]:
                raise IntakeValidationError(
                    "supporting evidence changed before publication"
                )
            try:
                os.link(temporary_path, destination)
            except FileExistsError:
                _assert_stored_object(destination, record["sha256"])
            else:
                created.append(destination)
            temporary_path.unlink(missing_ok=True)
            _assert_controlled_path(
                library_root, destination, "supporting evidence object path"
            )
            _assert_stored_object(destination, record["sha256"])
            _fsync_directory(destination.parent)
        finally:
            temporary_path.unlink(missing_ok=True)
    return created


def _strict_json(path: Path, label: str) -> tuple[dict, str]:
    def object_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate field: {key}")
            result[key] = value
        return result

    try:
        content = path.read_bytes()
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=object_hook)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise IntakeValidationError(f"invalid {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise IntakeValidationError(f"invalid {label}: root must be an object")
    return payload, hashlib.sha256(content).hexdigest()


def _catalog_board(project_root: Path, board_key: str) -> tuple[dict, list[str]]:
    identity_error = f"board catalog identity is invalid: {board_key}"
    try:
        catalog = BoardCatalog(project_root)
        board = catalog.resolve_board(board_key)
        raw = catalog.catalog["boards"][board_key]
    except (
        CatalogError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        AttributeError,
    ) as exc:
        raise IntakeValidationError(identity_error) from exc
    if (
        not isinstance(board, dict)
        or not isinstance(board.get("board_id"), str)
        or not board["board_id"].strip()
        or not isinstance(raw, dict)
    ):
        raise IntakeValidationError(identity_error)
    models = (
        raw["compatible_models"]
        if "compatible_models" in raw
        else [raw.get("model")]
    )
    if (
        not isinstance(models, list)
        or not models
        or any(not isinstance(model, str) or not model.strip() for model in models)
        or len(models) != len(set(models))
    ):
        raise IntakeValidationError(
            f"board catalog compatible models are invalid: {board_key}"
        )
    return board, list(models)


def _fact_ids(payload: dict) -> set[str]:
    return {
        *(item["symptom_id"] for item in payload["reported_symptoms"]),
        *(item["finding_id"] for item in payload["findings"]),
        *(item["action_id"] for item in payload["repair_actions"]),
    }


def _validate_case_record(case_record: dict) -> tuple[dict, str]:
    fields = set(case_record) if isinstance(case_record, dict) else set()
    if fields == V1_CASE_RECORD_FIELDS:
        schema_version = REPAIR_CASE_SCHEMA_V1
    elif fields == V2_CASE_RECORD_FIELDS:
        schema_version = REPAIR_CASE_SCHEMA_V2
    elif fields == V3_CASE_RECORD_FIELDS:
        schema_version = REPAIR_CASE_SCHEMA_V3
    else:
        raise IntakeValidationError("repair case record fields are invalid")
    descriptions = case_record["supporting_evidence_descriptions"]
    if not isinstance(descriptions, dict):
        raise IntakeValidationError(
            "supporting_evidence_descriptions must be an object"
        )
    return copy.deepcopy(case_record), schema_version


def _assert_prefix(previous: list, current: list, label: str) -> None:
    if current[: len(previous)] != previous:
        raise IntakeValidationError(
            f"repair case revision changes historical {label}"
        )


def _manifest_content_without_revision(payload: dict) -> dict:
    return {
        key: copy.deepcopy(value)
        for key, value in payload.items()
        if key not in {"revision", "previous_manifest_sha256"}
    }


def _evidence_reference_target(reference: dict) -> tuple[str, ...]:
    if reference["kind"] == "package_entry":
        return (
            "package_entry",
            reference["package_id"],
            reference["entry_id"],
        )
    return ("supporting_evidence", reference["evidence_id"])


def _manifest_evidence_targets(payload: dict) -> set[tuple[str, ...]]:
    targets = {
        (
            "package_entry",
            link["package_id"],
            entry_id,
        )
        for link in payload["package_links"]
        for entry_id in link["entry_ids"]
    }
    targets.update(
        ("supporting_evidence", evidence["evidence_id"])
        for evidence in payload["supporting_evidence"]
    )
    return targets


def _validate_revision_transition(
    previous: dict,
    current: dict,
    *,
    catalog_models: list[str],
) -> None:
    if (
        current["repair_case_id"] != previous["repair_case_id"]
        or current["board_key"] != previous["board_key"]
        or current["board_id"] != previous["board_id"]
        or current["source_origin"] != previous["source_origin"]
    ):
        raise IntakeValidationError(
            "repair case revision changes historical identity"
        )
    _assert_prefix(
        previous["package_links"],
        current["package_links"],
        "package links",
    )
    _assert_prefix(
        previous["supporting_evidence"],
        current["supporting_evidence"],
        "supporting evidence",
    )
    if (
        previous["outcome"]["status"] != "unknown"
        and current["outcome"] != previous["outcome"]
    ):
        raise IntakeValidationError(
            "repair case revision changes historical outcome"
        )
    for field in (
        "reported_symptoms",
        "findings",
        "repair_actions",
        "corrections",
    ):
        _assert_prefix(previous[field], current[field], field)

    previous_version = previous["schema_version"]
    current_version = current["schema_version"]
    if previous_version == REPAIR_CASE_SCHEMA_V1:
        if current_version == REPAIR_CASE_SCHEMA_V1:
            if current["device_models"] != previous["device_models"]:
                raise IntakeValidationError(
                    "repair case revision changes historical device_models"
                )
            return
        identity = current["device_identity"]
        if (
            identity["mapping_status"] != "exact_catalog_match"
            or identity["reported_models"] != previous["device_models"]
            or identity["resolved_models"] != previous["device_models"]
            or identity["catalog_models"] != catalog_models
        ):
            raise IntakeValidationError(
                "V1 to V2 migration requires an exact catalog identity "
                "matching historical device models"
            )
        return
    if current_version == REPAIR_CASE_SCHEMA_V1:
        raise IntakeValidationError("V2 to V1 repair case downgrade is not allowed")
    try:
        previous_identity = previous["device_identity"]
        current_identity = current["device_identity"]
        validate_identity_transition(
            previous_identity,
            current_identity,
            has_new_correction=(
                len(current["corrections"]) > len(previous["corrections"])
            ),
        )
        requires_new_evidence = (
            previous_identity["mapping_status"]
            != current_identity["mapping_status"]
            or previous_identity["reported_models"]
            != current_identity["reported_models"]
            or previous_identity["catalog_models"]
            != current_identity["catalog_models"]
        )
        previous_ref_count = len(previous_identity["evidence_refs"])
        appended_refs = current_identity["evidence_refs"][previous_ref_count:]
        prior_targets = _manifest_evidence_targets(previous)
        if requires_new_evidence and not any(
            _evidence_reference_target(reference) not in prior_targets
            for reference in appended_refs
        ):
            raise ValueError(
                "identity transition requires newly published identity evidence."
            )
    except ValueError as exc:
        raise IntakeValidationError(
            f"invalid repair case identity transition: {exc}"
        ) from exc


def _prepare_repair_case_revision(
    *,
    project_root: Path,
    library_root: Path,
    repair_case_id: str,
    board_key: str,
    package_assignments: list[tuple[str, Path]],
    case_record: dict,
    supporting_assignments: list[tuple[str, Path]],
    previous_manifest_path: Path | None,
) -> tuple[dict, list[dict]]:
    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    repair_case_id = _require_safe_id(repair_case_id, "repair_case_id")
    board_key = _require_safe_id(board_key, "board_key")
    record, schema_version = _validate_case_record(case_record)
    board, catalog_models = _catalog_board(project_root, board_key)
    if schema_version == REPAIR_CASE_SCHEMA_V1:
        models = record["device_models"]
        if (
            not isinstance(models, list)
            or not models
            or any(model not in catalog_models for model in models)
        ):
            raise IntakeValidationError(
                f"device_models do not match board catalog: {board_key}"
            )

    previous = None
    previous_sha256 = None
    revision = 1
    historical_fact_ids: set[str] = set()
    if previous_manifest_path is not None:
        previous = validate_repair_case_revision(
            manifest_path=previous_manifest_path,
            project_root=project_root,
            library_root=library_root,
        )
        previous_path = Path(previous_manifest_path)
        _, previous_sha256 = _strict_json(
            previous_path, "previous repair case manifest"
        )
        if previous["repair_case_id"] != repair_case_id:
            raise IntakeValidationError("previous manifest repair_case_id mismatch")
        if previous["board_key"] != board_key:
            raise IntakeValidationError("previous manifest board mismatch")
        revision = previous["revision"] + 1
        historical_fact_ids = _fact_ids(previous)

    evidence_mode = (
        record["evidence_mode"]
        if schema_version == REPAIR_CASE_SCHEMA_V3
        else "package_linked"
    )
    if evidence_mode == "supporting_only":
        if package_assignments:
            raise IntakeValidationError(
                "supporting_only forbids source package assignments"
            )
        links = []
    else:
        links = resolve_package_links(
            project_root=project_root,
            library_root=library_root,
            assignments=package_assignments,
            board_key=board_key,
        )
    if not links and not supporting_assignments:
        raise IntakeValidationError(
            "repair case requires a source package or supporting evidence"
        )
    inspected = inspect_supporting_evidence(
        supporting_assignments,
        record["supporting_evidence_descriptions"],
        schema_version=schema_version,
    )
    new_supporting = [copy.deepcopy(item["record"]) for item in inspected]
    supporting = new_supporting
    if previous is not None:
        _assert_prefix(previous["package_links"], links, "package links")
        prior_ids = {
            item["evidence_id"] for item in previous["supporting_evidence"]
        }
        if any(item["evidence_id"] in prior_ids for item in new_supporting):
            raise IntakeValidationError(
                "new supporting evidence duplicates a historical evidence_id"
            )
        supporting = copy.deepcopy(previous["supporting_evidence"]) + new_supporting

    if schema_version == REPAIR_CASE_SCHEMA_V1:
        identity_field = {
            "device_models": copy.deepcopy(record["device_models"])
        }
        boundaries = copy.deepcopy(FIXED_FALSE_BOUNDARIES)
    else:
        try:
            model_identity_resolved = derive_model_identity_resolved(
                record["device_identity"]
            )
        except (KeyError, TypeError) as exc:
            raise IntakeValidationError(
                "invalid repair case device_identity"
            ) from exc
        identity_field = {
            "device_identity": copy.deepcopy(record["device_identity"])
        }
        if schema_version == REPAIR_CASE_SCHEMA_V3:
            identity_field.update(
                {
                    "evidence_mode": copy.deepcopy(record["evidence_mode"]),
                    "supporting_evidence_contexts": copy.deepcopy(
                        record["supporting_evidence_contexts"]
                    ),
                }
            )
        boundaries = {
            **copy.deepcopy(FIXED_FALSE_BOUNDARIES),
            "model_identity_resolved": model_identity_resolved,
        }

    payload = {
        "schema_version": schema_version,
        "repair_case_id": repair_case_id,
        "revision": revision,
        "previous_manifest_sha256": previous_sha256,
        "source_origin": "milo_supplied",
        "board_key": board_key,
        "board_id": board["board_id"],
        **identity_field,
        "package_links": links,
        "supporting_evidence": supporting,
        "reported_symptoms": copy.deepcopy(record["reported_symptoms"]),
        "findings": copy.deepcopy(record["findings"]),
        "repair_actions": copy.deepcopy(record["repair_actions"]),
        "outcome": copy.deepcopy(record["outcome"]),
        "corrections": copy.deepcopy(record["corrections"]),
        "completeness": "photos_only",
        "boundaries": boundaries,
    }
    payload["completeness"] = derive_completeness(payload)
    try:
        validated = validate_repair_case_manifest(
            payload,
            historical_fact_ids=historical_fact_ids,
            catalog_models=(
                catalog_models
                if schema_version
                in {REPAIR_CASE_SCHEMA_V2, REPAIR_CASE_SCHEMA_V3}
                else None
            ),
        )
    except ValueError as exc:
        raise IntakeValidationError(f"invalid repair case manifest: {exc}") from exc
    if previous is not None:
        _validate_revision_transition(
            previous,
            validated,
            catalog_models=catalog_models,
        )
    if (
        previous is not None
        and _manifest_content_without_revision(validated)
        == _manifest_content_without_revision(previous)
    ):
        raise IntakeValidationError("repair case revision adds no evidence or context")
    return validated, inspected


def build_repair_case_revision(
    *,
    project_root: Path,
    library_root: Path,
    repair_case_id: str,
    board_key: str,
    package_assignments: list[tuple[str, Path]],
    case_record: dict,
    supporting_assignments: list[tuple[str, Path]],
    previous_manifest_path: Path | None,
) -> dict:
    payload, _ = _prepare_repair_case_revision(
        project_root=project_root,
        library_root=library_root,
        repair_case_id=repair_case_id,
        board_key=board_key,
        package_assignments=package_assignments,
        case_record=case_record,
        supporting_assignments=supporting_assignments,
        previous_manifest_path=previous_manifest_path,
    )
    return payload


def _revision_result(
    *,
    state: str,
    manifest_path: Path,
    payload: dict,
    manifest_sha256: str,
) -> dict:
    return {
        "state": state,
        "repair_case_id": payload["repair_case_id"],
        "revision": payload["revision"],
        "schema_version": payload["schema_version"],
        "evidence_mode": payload.get("evidence_mode", "package_linked"),
        "identity_status": (
            "exact_catalog_match"
            if payload["schema_version"] == REPAIR_CASE_SCHEMA_V1
            else payload["device_identity"]["mapping_status"]
        ),
        "completeness": payload["completeness"],
        "manifest_sha256": manifest_sha256,
        "manifest_path": manifest_path.resolve(),
        "package_count": len(payload["package_links"]),
        "supporting_evidence_count": len(payload["supporting_evidence"]),
    }


def _validate_revision_storage_path(
    *,
    manifest_path: Path,
    library_root: Path,
    payload: dict,
) -> None:
    repair_case_id = payload.get("repair_case_id")
    revision = payload.get("revision")
    try:
        repair_case_id = _require_safe_id(repair_case_id, "repair_case_id")
    except (TypeError, IntakeValidationError) as exc:
        raise IntakeValidationError(
            "repair case manifest identity is invalid"
        ) from exc
    if type(revision) is not int or revision < 1:
        raise IntakeValidationError("repair case revision is invalid")
    expected = (
        library_root
        / "cases"
        / repair_case_id
        / "revisions"
        / f"{revision:04d}"
        / "repair-case.json"
    )
    if manifest_path != expected:
        raise IntakeValidationError(
            "repair case manifest path does not match case and revision"
        )
    marker = _assert_controlled_path(
        library_root,
        manifest_path.parent / ".complete",
        "repair case completion marker",
    )
    if (
        not marker.is_file()
        or _is_reparse_or_symlink(marker)
        or marker.read_bytes() != b"complete\n"
    ):
        raise IntakeValidationError("repair case revision is incomplete")


def validate_repair_case_revision(
    *,
    manifest_path: Path,
    project_root: Path,
    library_root: Path,
) -> dict:
    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    manifest_path = _assert_controlled_path(
        library_root, Path(manifest_path), "repair case manifest path"
    )
    if not manifest_path.is_file() or _is_reparse_or_symlink(manifest_path):
        raise IntakeValidationError("repair case manifest is missing or unsafe")
    payload, _ = _strict_json(manifest_path, "repair case manifest")
    _validate_revision_storage_path(
        manifest_path=manifest_path,
        library_root=library_root,
        payload=payload,
    )
    manifest_board_key = _require_safe_id(
        payload.get("board_key"), "board_key"
    )

    historical_fact_ids: set[str] = set()
    previous = None
    if payload.get("revision") != 1:
        if not isinstance(payload.get("revision"), int):
            raise IntakeValidationError("repair case revision is invalid")
        previous_path = (
            library_root
            / "cases"
            / payload.get("repair_case_id", "")
            / "revisions"
            / f"{payload['revision'] - 1:04d}"
            / "repair-case.json"
        )
        previous = validate_repair_case_revision(
            manifest_path=previous_path,
            project_root=project_root,
            library_root=library_root,
        )
        _, previous_sha256 = _strict_json(
            previous_path, "previous repair case manifest"
        )
        if payload.get("previous_manifest_sha256") != previous_sha256:
            raise IntakeValidationError(
                "previous manifest SHA-256 does not match revision chain"
            )
        historical_fact_ids = _fact_ids(previous)

    board, catalog_models = _catalog_board(
        project_root, manifest_board_key
    )
    try:
        validated = validate_repair_case_manifest(
            payload,
            historical_fact_ids=historical_fact_ids,
            catalog_models=(
                catalog_models
                if payload.get("schema_version")
                in {REPAIR_CASE_SCHEMA_V2, REPAIR_CASE_SCHEMA_V3}
                else None
            ),
        )
    except ValueError as exc:
        raise IntakeValidationError(f"invalid repair case manifest: {exc}") from exc
    if validated["board_id"] != board["board_id"]:
        raise IntakeValidationError("repair case board_id does not match catalog")
    if (
        validated["schema_version"] == REPAIR_CASE_SCHEMA_V1
        and any(
            model not in catalog_models for model in validated["device_models"]
        )
    ):
        raise IntakeValidationError(
            "repair case device_models do not match board catalog"
        )

    if (
        validated["schema_version"] == REPAIR_CASE_SCHEMA_V3
        and validated["evidence_mode"] == "supporting_only"
    ):
        expected_links = []
    else:
        expected_links = resolve_package_links(
            project_root=project_root,
            library_root=library_root,
            assignments=[
                (
                    link["role"],
                    library_root
                    / "packages"
                    / link["package_id"]
                    / "source-package.json",
                )
                for link in validated["package_links"]
            ],
            board_key=validated["board_key"],
        )
    if validated["package_links"] != expected_links:
        raise IntakeValidationError(
            "repair case source package evidence does not match manifest"
        )
    for evidence in validated["supporting_evidence"]:
        object_path = _assert_controlled_path(
            library_root,
            library_root / evidence["object_path"],
            "supporting evidence object path",
        )
        _assert_stored_object(object_path, evidence["sha256"])
        if object_path.stat().st_size != evidence["byte_size"]:
            raise IntakeValidationError(
                "supporting evidence object byte size mismatch"
            )
    if previous is not None:
        _validate_revision_transition(
            previous,
            validated,
            catalog_models=catalog_models,
        )
    return validated


def stage_repair_case_revision(
    *,
    project_root: Path,
    library_root: Path,
    repair_case_id: str,
    board_key: str,
    package_assignments: list[tuple[str, Path]],
    case_record: dict,
    supporting_assignments: list[tuple[str, Path]],
    previous_manifest_path: Path | None,
) -> dict:
    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    payload, inspected = _prepare_repair_case_revision(
        project_root=project_root,
        library_root=library_root,
        repair_case_id=repair_case_id,
        board_key=board_key,
        package_assignments=package_assignments,
        case_record=case_record,
        supporting_assignments=supporting_assignments,
        previous_manifest_path=previous_manifest_path,
    )
    _ensure_directory_durable(library_root)
    cases_root = _assert_controlled_path(
        library_root,
        library_root / "cases",
        "repair case library path",
    )
    _ensure_directory_durable(cases_root)
    _assert_controlled_path(
        library_root, cases_root, "repair case library path"
    )
    case_root = _assert_controlled_path(
        library_root,
        cases_root / payload["repair_case_id"],
        "repair case path",
    )
    _ensure_directory_durable(case_root)
    _assert_controlled_path(library_root, case_root, "repair case path")
    revisions_root = _assert_controlled_path(
        library_root,
        case_root / "revisions",
        "repair case revisions path",
    )
    _ensure_directory_durable(revisions_root)
    _assert_controlled_path(
        library_root, revisions_root, "repair case revisions path"
    )
    target = _assert_controlled_path(
        library_root,
        revisions_root / f"{payload['revision']:04d}",
        "repair case revision path",
    )
    manifest_path = target / "repair-case.json"

    with _package_lock(cases_root, payload["repair_case_id"]):
        for controlled_path, label in (
            (cases_root, "repair case library path"),
            (case_root, "repair case path"),
            (revisions_root, "repair case revisions path"),
            (target, "repair case revision path"),
        ):
            _assert_controlled_path(
                library_root, controlled_path, label
            )
        if target.exists():
            existing = validate_repair_case_revision(
                manifest_path=manifest_path,
                project_root=project_root,
                library_root=library_root,
            )
            _, existing_sha256 = _strict_json(
                manifest_path, "repair case manifest"
            )
            if existing != payload:
                raise IntakeValidationError(
                    f"repair case revision conflict: {payload['repair_case_id']}"
                )
            return _revision_result(
                state="existing",
                manifest_path=manifest_path,
                payload=existing,
                manifest_sha256=existing_sha256,
            )

        completed = sorted(
            path
            for path in revisions_root.iterdir()
            if path.is_dir()
            and path.name.isdigit()
            and (path / ".complete").is_file()
        )
        expected_prior_count = payload["revision"] - 1
        if len(completed) != expected_prior_count:
            raise IntakeValidationError(
                "repair case revision chain has a gap or fork"
            )
        temporary = Path(
            tempfile.mkdtemp(
                prefix=f".{payload['revision']:04d}.",
                suffix=".staging",
                dir=revisions_root,
            )
        )
        published_incomplete = False
        created_objects = []
        try:
            write_json_atomic(temporary / "repair-case.json", payload)
            created_objects = store_supporting_evidence(
                library_root=library_root,
                inspected=inspected,
                project_root=project_root,
            )
            _fsync_directory(temporary)
            try:
                temporary.rename(target)
            except FileExistsError:
                raise IntakeValidationError(
                    f"repair case revision conflict: {payload['repair_case_id']}"
                )
            published_incomplete = True
            _fsync_directory(revisions_root)
            _write_completion_marker(target / ".complete")
            _fsync_directory(target)
            _fsync_directory(revisions_root)
            published_incomplete = False
        except Exception:
            if published_incomplete and target.exists():
                shutil.rmtree(target)
                _fsync_directory(revisions_root)
            for object_path in created_objects:
                object_path.unlink(missing_ok=True)
                _fsync_directory(object_path.parent)
            raise
        finally:
            if temporary.exists():
                shutil.rmtree(temporary, ignore_errors=True)

    validated = validate_repair_case_revision(
        manifest_path=manifest_path,
        project_root=project_root,
        library_root=library_root,
    )
    _, manifest_sha256 = _strict_json(manifest_path, "repair case manifest")
    return _revision_result(
        state="created",
        manifest_path=manifest_path,
        payload=validated,
        manifest_sha256=manifest_sha256,
    )
