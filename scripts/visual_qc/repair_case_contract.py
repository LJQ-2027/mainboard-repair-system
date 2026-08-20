from __future__ import annotations

import copy
import math
from pathlib import PurePosixPath
import re

from scripts.visual_qc.repair_case_identity import (
    derive_model_identity_resolved,
    validate_device_identity,
)


REPAIR_CASE_SCHEMA_V1 = "VISUAL-QC-REPAIR-CASE-SOURCE-V1"
REPAIR_CASE_SCHEMA_V2 = "VISUAL-QC-REPAIR-CASE-SOURCE-V2"
REPAIR_CASE_SCHEMA_V3 = "VISUAL-QC-REPAIR-CASE-SOURCE-V3"
REPAIR_CASE_SCHEMA_VERSION = REPAIR_CASE_SCHEMA_V1
REPAIR_CASE_SCHEMA_VERSIONS = {
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
    REPAIR_CASE_SCHEMA_V3,
}
SOURCE_ORIGIN = "milo_supplied"
EVIDENCE_MODES = {"package_linked", "supporting_only"}
CASE_ROLES = {
    "before_repair",
    "after_repair",
    "golden_reference",
    "supplemental",
}
CAPTURE_STAGES = {"before_repair", "after_repair", "golden_reference"}
CLAIM_STATUSES = {"reported", "suspected", "documented"}
OUTCOME_STATUSES = {
    "unknown",
    "repair_completed",
    "not_repaired",
    "non_repairable",
    "needs_followup",
}
COMPLETENESS_STATES = {
    "photos_only",
    "symptom_linked",
    "diagnosis_linked",
    "repair_outcome_linked",
}
FIXED_FALSE_BOUNDARIES = {
    "visual_defect_confirmed": False,
    "golden_approved": False,
    "training_label_allowed": False,
    "repair_instruction_allowed": False,
    "field_accuracy_claim_allowed": False,
}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
MIME_EXTENSIONS_V3 = {
    **MIME_EXTENSIONS,
    "image/heic": ".heic",
}
MAX_SUPPORTING_FILE_BYTES = 100 * 1024 * 1024
MAX_SUPPORTING_FILES = 50

COMMON_MANIFEST_FIELDS = {
    "schema_version",
    "repair_case_id",
    "revision",
    "previous_manifest_sha256",
    "source_origin",
    "board_key",
    "board_id",
    "package_links",
    "supporting_evidence",
    "reported_symptoms",
    "findings",
    "repair_actions",
    "outcome",
    "corrections",
    "completeness",
    "boundaries",
}
V1_MANIFEST_FIELDS = COMMON_MANIFEST_FIELDS | {"device_models"}
V2_MANIFEST_FIELDS = COMMON_MANIFEST_FIELDS | {"device_identity"}
V3_MANIFEST_FIELDS = V2_MANIFEST_FIELDS | {
    "evidence_mode",
    "supporting_evidence_contexts",
}
MANIFEST_FIELDS = V1_MANIFEST_FIELDS
PACKAGE_LINK_FIELDS = {
    "package_id",
    "source_package_manifest_sha256",
    "capture_stage",
    "role",
    "entry_ids",
}
SUPPORTING_EVIDENCE_FIELDS = {
    "evidence_id",
    "original_filename",
    "object_path",
    "mime_type",
    "byte_size",
    "sha256",
    "description",
}
SUPPORTING_EVIDENCE_CONTEXT_FIELDS = {
    "evidence_id",
    "evidence_role",
    "source_capture_stage",
    "source_board_area",
}
SUPPORTING_EVIDENCE_ROLES = {"repair_in_progress_photo"}
SYMPTOM_FIELDS = {
    "symptom_id",
    "text",
    "source_wording",
    "fault_code",
    "evidence_refs",
}
FINDING_FIELDS = {
    "finding_id",
    "claim_status",
    "description",
    "defect_category",
    "designator",
    "side_id",
    "region",
    "evidence_refs",
}
ACTION_FIELDS = {
    "action_id",
    "description",
    "action_category",
    "target_designator",
    "side_id",
    "region",
    "evidence_refs",
}
OUTCOME_FIELDS = {
    "status",
    "description",
    "verification_description",
    "evidence_refs",
}
CORRECTION_FIELDS = {
    "correction_id",
    "corrects_fact_id",
    "description",
    "replacement_fact_id",
    "evidence_refs",
}
REGION_FIELDS = {"x", "y", "width", "height"}
PACKAGE_REFERENCE_FIELDS = {"kind", "package_id", "entry_id"}
SUPPORTING_REFERENCE_FIELDS = {"kind", "evidence_id"}


def _expect_object(value, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} fields are invalid.")
    return value


def _safe_id(value, label: str) -> str:
    if not isinstance(value, str) or SAFE_ID.fullmatch(value) is None:
        raise ValueError(f"{label} is invalid.")
    return value


def _required_text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text.")
    return value


def _optional_text(value, label: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, label)


def _sha256(value, label: str) -> str:
    if not isinstance(value, str) or LOWER_SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be lowercase SHA-256.")
    return value


def _unique_id(value: str, seen: set[str], label: str) -> None:
    if value in seen:
        raise ValueError(f"duplicate {label}: {value}")
    seen.add(value)


def _is_allowed_string(value, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _has_strict_boolean_fields(value, fields: set[str]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == fields
        and all(type(value[field]) is bool for field in fields)
    )


def _validate_region(value, label: str) -> None:
    if value is None:
        return
    region = _expect_object(value, REGION_FIELDS, label)
    values = []
    for field in ("x", "y", "width", "height"):
        number = region[field]
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise ValueError(f"{label} must be a normalized region.")
        try:
            normalized_number = float(number)
        except OverflowError:
            raise ValueError(
                f"{label} must be a normalized region."
            ) from None
        if not math.isfinite(normalized_number):
            raise ValueError(f"{label} must be a normalized region.")
        values.append(normalized_number)
    x, y, width, height = values
    if (
        x < 0
        or y < 0
        or width <= 0
        or height <= 0
        or x + width > 1
        or y + height > 1
    ):
        raise ValueError(f"{label} must be a normalized region.")


def _validate_package_links(
    value,
    *,
    allow_empty: bool = False,
) -> tuple[set[tuple[str, str]], set[str]]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or len(value) > 100
    ):
        minimum = 0 if allow_empty else 1
        raise ValueError(
            f"package_links must contain {minimum} to 100 records."
        )
    targets: set[tuple[str, str]] = set()
    package_ids: set[str] = set()
    for index, raw in enumerate(value):
        link = _expect_object(
            raw, PACKAGE_LINK_FIELDS, f"package_links[{index}]"
        )
        package_id = _safe_id(link["package_id"], "package_id")
        _unique_id(package_id, package_ids, "package_id")
        _sha256(
            link["source_package_manifest_sha256"],
            "source_package_manifest_sha256",
        )
        if not _is_allowed_string(link["capture_stage"], CAPTURE_STAGES):
            raise ValueError("capture_stage is invalid.")
        if not _is_allowed_string(link["role"], CASE_ROLES):
            raise ValueError("package role is invalid.")
        entry_ids = link["entry_ids"]
        if (
            not isinstance(entry_ids, list)
            or not entry_ids
            or len(entry_ids) > 500
        ):
            raise ValueError("entry_ids must contain 1 to 500 records.")
        seen_entries: set[str] = set()
        for entry_id in entry_ids:
            entry_id = _safe_id(entry_id, "entry_id")
            _unique_id(entry_id, seen_entries, "entry_id")
            targets.add((package_id, entry_id))
    return targets, package_ids


def _validate_supporting_evidence(
    value,
    *,
    allowed_mime_extensions: dict[str, str] = MIME_EXTENSIONS,
) -> tuple[set[str], dict[str, str]]:
    if not isinstance(value, list) or len(value) > MAX_SUPPORTING_FILES:
        raise ValueError("supporting_evidence exceeds its record limit.")
    evidence_ids: set[str] = set()
    evidence_mime_types: dict[str, str] = {}
    for index, raw in enumerate(value):
        evidence = _expect_object(
            raw,
            SUPPORTING_EVIDENCE_FIELDS,
            f"supporting_evidence[{index}]",
        )
        evidence_id = _safe_id(evidence["evidence_id"], "evidence_id")
        _unique_id(evidence_id, evidence_ids, "evidence_id")
        filename = evidence["original_filename"]
        if (
            not isinstance(filename, str)
            or not filename.strip()
            or PurePosixPath(filename).name != filename
            or "\\" in filename
        ):
            raise ValueError("original_filename is invalid.")
        mime_type = evidence["mime_type"]
        if (
            not isinstance(mime_type, str)
            or mime_type not in allowed_mime_extensions
        ):
            raise ValueError("supporting evidence MIME type is invalid.")
        extension = allowed_mime_extensions[mime_type]
        byte_size = evidence["byte_size"]
        if (
            isinstance(byte_size, bool)
            or not isinstance(byte_size, int)
            or byte_size < 1
            or byte_size > MAX_SUPPORTING_FILE_BYTES
        ):
            raise ValueError("supporting evidence byte_size is invalid.")
        digest = _sha256(evidence["sha256"], "supporting evidence sha256")
        expected_path = (
            f"objects/case-evidence/{digest[:2]}/{digest}{extension}"
        )
        if evidence["object_path"] != expected_path:
            raise ValueError("supporting evidence object_path is invalid.")
        _required_text(evidence["description"], "supporting evidence description")
        evidence_mime_types[evidence_id] = mime_type
    return evidence_ids, evidence_mime_types


def _validate_supporting_evidence_contexts(
    value,
    *,
    supporting_targets: set[str],
    supporting_mime_types: dict[str, str],
    require_complete_coverage: bool,
) -> None:
    if not isinstance(value, list) or len(value) > MAX_SUPPORTING_FILES:
        raise ValueError("supporting_evidence_contexts exceeds its record limit.")
    context_ids: set[str] = set()
    image_mime_types = {"image/png", "image/jpeg", "image/heic"}
    for index, raw in enumerate(value):
        context = _expect_object(
            raw,
            SUPPORTING_EVIDENCE_CONTEXT_FIELDS,
            f"supporting_evidence_contexts[{index}]",
        )
        evidence_id = _safe_id(context["evidence_id"], "evidence_id")
        if evidence_id not in supporting_targets:
            raise ValueError("supporting evidence context does not resolve.")
        _unique_id(evidence_id, context_ids, "supporting evidence context")
        if not _is_allowed_string(
            context["evidence_role"],
            SUPPORTING_EVIDENCE_ROLES,
        ):
            raise ValueError("supporting evidence role is invalid.")
        _required_text(context["source_capture_stage"], "source_capture_stage")
        _required_text(context["source_board_area"], "source_board_area")
        if supporting_mime_types[evidence_id] not in image_mime_types:
            raise ValueError(
                "repair_in_progress_photo requires image supporting evidence."
            )
    if require_complete_coverage and context_ids != supporting_targets:
        raise ValueError(
            "supporting_only requires context for every supporting evidence."
        )


def _validate_evidence_refs(
    refs,
    *,
    package_targets: set[tuple[str, str]],
    supporting_targets: set[str],
    label: str,
) -> None:
    if not isinstance(refs, list) or len(refs) > 100:
        raise ValueError(f"{label} evidence_refs are invalid.")
    seen: set[tuple[str, ...]] = set()
    for reference in refs:
        if not isinstance(reference, dict):
            raise ValueError(f"{label} evidence reference is invalid.")
        if reference.get("kind") == "package_entry":
            _expect_object(
                reference, PACKAGE_REFERENCE_FIELDS, "package evidence reference"
            )
            package_id = _safe_id(reference["package_id"], "package_id")
            entry_id = _safe_id(reference["entry_id"], "entry_id")
            key = ("package_entry", package_id, entry_id)
            if (package_id, entry_id) not in package_targets:
                raise ValueError(f"{label} evidence reference does not resolve.")
        elif reference.get("kind") == "supporting_evidence":
            _expect_object(
                reference,
                SUPPORTING_REFERENCE_FIELDS,
                "supporting evidence reference",
            )
            evidence_id = _safe_id(reference["evidence_id"], "evidence_id")
            key = ("supporting_evidence", evidence_id)
            if evidence_id not in supporting_targets:
                raise ValueError(f"{label} evidence reference does not resolve.")
        else:
            raise ValueError(f"{label} evidence reference kind is invalid.")
        if key in seen:
            raise ValueError(f"{label} contains a duplicate evidence reference.")
        seen.add(key)


def derive_completeness(payload: dict) -> str:
    symptoms = payload.get("reported_symptoms")
    findings = payload.get("findings")
    actions = payload.get("repair_actions")
    outcome = payload.get("outcome")
    if not isinstance(symptoms, list) or not symptoms:
        return "photos_only"
    documented = isinstance(findings, list) and any(
        isinstance(item, dict) and item.get("claim_status") == "documented"
        for item in findings
    )
    if not documented:
        return "symptom_linked"
    if (
        isinstance(actions, list)
        and actions
        and isinstance(outcome, dict)
        and _is_allowed_string(
            outcome.get("status"),
            OUTCOME_STATUSES - {"unknown"},
        )
    ):
        return "repair_outcome_linked"
    return "diagnosis_linked"


def validate_repair_case_manifest(
    payload: dict,
    *,
    historical_fact_ids: set[str] | None = None,
    catalog_models: list[str] | None = None,
) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("repair case manifest fields are invalid.")
    schema_version = payload.get("schema_version")
    if not _is_allowed_string(
        schema_version,
        REPAIR_CASE_SCHEMA_VERSIONS,
    ):
        raise ValueError("schema_version is invalid.")
    manifest_fields = {
        REPAIR_CASE_SCHEMA_V1: V1_MANIFEST_FIELDS,
        REPAIR_CASE_SCHEMA_V2: V2_MANIFEST_FIELDS,
        REPAIR_CASE_SCHEMA_V3: V3_MANIFEST_FIELDS,
    }[schema_version]
    manifest = _expect_object(
        payload,
        manifest_fields,
        "repair case manifest",
    )
    _safe_id(manifest["repair_case_id"], "repair_case_id")
    revision = manifest["revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("revision must be a positive integer.")
    previous = manifest["previous_manifest_sha256"]
    if revision == 1:
        if previous is not None:
            raise ValueError("revision 1 cannot have a previous manifest.")
    elif previous is None:
        raise ValueError("later revision requires previous_manifest_sha256.")
    else:
        _sha256(previous, "previous_manifest_sha256")
    if manifest["source_origin"] != SOURCE_ORIGIN:
        raise ValueError("source_origin must be milo_supplied.")
    _safe_id(manifest["board_key"], "board_key")
    _required_text(manifest["board_id"], "board_id")

    if schema_version == REPAIR_CASE_SCHEMA_V1:
        models = manifest["device_models"]
        if not isinstance(models, list) or not models or len(models) > 20:
            raise ValueError("device_models must contain 1 to 20 records.")
        seen_models: set[str] = set()
        for model in models:
            model = _required_text(model, "device model")
            _unique_id(model, seen_models, "device model")

    evidence_mode = "package_linked"
    if schema_version == REPAIR_CASE_SCHEMA_V3:
        evidence_mode = manifest["evidence_mode"]
        if not _is_allowed_string(evidence_mode, EVIDENCE_MODES):
            raise ValueError("evidence_mode is invalid.")

    package_targets, _ = _validate_package_links(
        manifest["package_links"],
        allow_empty=evidence_mode == "supporting_only",
    )
    supporting_targets, supporting_mime_types = _validate_supporting_evidence(
        manifest["supporting_evidence"],
        allowed_mime_extensions=(
            MIME_EXTENSIONS_V3
            if schema_version == REPAIR_CASE_SCHEMA_V3
            else MIME_EXTENSIONS
        ),
    )
    if schema_version == REPAIR_CASE_SCHEMA_V3:
        if evidence_mode == "supporting_only":
            if manifest["package_links"]:
                raise ValueError("supporting_only forbids package links.")
            if not manifest["supporting_evidence"]:
                raise ValueError("supporting_only requires supporting evidence.")
        _validate_supporting_evidence_contexts(
            manifest["supporting_evidence_contexts"],
            supporting_targets=supporting_targets,
            supporting_mime_types=supporting_mime_types,
            require_complete_coverage=evidence_mode == "supporting_only",
        )
    identity = None
    if schema_version in {REPAIR_CASE_SCHEMA_V2, REPAIR_CASE_SCHEMA_V3}:
        if catalog_models is None:
            version_label = (
                "V2"
                if schema_version == REPAIR_CASE_SCHEMA_V2
                else "V3"
            )
            raise ValueError(
                f"catalog_models is required for {version_label} manifests."
            )
        identity = validate_device_identity(
            manifest["device_identity"],
            catalog_models=catalog_models,
            validate_evidence_refs=lambda refs: _validate_evidence_refs(
                refs,
                package_targets=package_targets,
                supporting_targets=supporting_targets,
                label="device identity",
            ),
        )

    fact_ids: set[str] = set()
    symptoms = manifest["reported_symptoms"]
    if not isinstance(symptoms, list) or len(symptoms) > 100:
        raise ValueError("reported_symptoms are invalid.")
    for index, raw in enumerate(symptoms):
        item = _expect_object(raw, SYMPTOM_FIELDS, f"reported_symptoms[{index}]")
        fact_id = _safe_id(item["symptom_id"], "symptom_id")
        _unique_id(fact_id, fact_ids, "symptom_id")
        _required_text(item["text"], "symptom text")
        _optional_text(item["source_wording"], "source_wording")
        _optional_text(item["fault_code"], "fault_code")
        _validate_evidence_refs(
            item["evidence_refs"],
            package_targets=package_targets,
            supporting_targets=supporting_targets,
            label=f"symptom {fact_id}",
        )

    findings = manifest["findings"]
    if not isinstance(findings, list) or len(findings) > 500:
        raise ValueError("findings are invalid.")
    for index, raw in enumerate(findings):
        item = _expect_object(raw, FINDING_FIELDS, f"findings[{index}]")
        fact_id = _safe_id(item["finding_id"], "finding_id")
        if fact_id in fact_ids:
            raise ValueError(f"duplicate finding_id: {fact_id}")
        fact_ids.add(fact_id)
        if not _is_allowed_string(item["claim_status"], CLAIM_STATUSES):
            raise ValueError("claim_status is invalid.")
        _required_text(item["description"], "finding description")
        _optional_text(item["defect_category"], "defect_category")
        if item["designator"] is not None:
            _safe_id(item["designator"], "designator")
        if item["side_id"] is not None:
            _safe_id(item["side_id"], "side_id")
        _validate_region(item["region"], "finding normalized region")
        _validate_evidence_refs(
            item["evidence_refs"],
            package_targets=package_targets,
            supporting_targets=supporting_targets,
            label=f"finding {fact_id}",
        )

    actions = manifest["repair_actions"]
    if not isinstance(actions, list) or len(actions) > 500:
        raise ValueError("repair_actions are invalid.")
    for index, raw in enumerate(actions):
        item = _expect_object(raw, ACTION_FIELDS, f"repair_actions[{index}]")
        fact_id = _safe_id(item["action_id"], "action_id")
        if fact_id in fact_ids:
            raise ValueError(f"duplicate action_id: {fact_id}")
        fact_ids.add(fact_id)
        _required_text(item["description"], "repair action description")
        _optional_text(item["action_category"], "action_category")
        if item["target_designator"] is not None:
            _safe_id(item["target_designator"], "target_designator")
        if item["side_id"] is not None:
            _safe_id(item["side_id"], "side_id")
        _validate_region(item["region"], "repair action normalized region")
        _validate_evidence_refs(
            item["evidence_refs"],
            package_targets=package_targets,
            supporting_targets=supporting_targets,
            label=f"repair action {fact_id}",
        )

    outcome = _expect_object(manifest["outcome"], OUTCOME_FIELDS, "outcome")
    if not _is_allowed_string(outcome["status"], OUTCOME_STATUSES):
        raise ValueError("outcome status is invalid.")
    _optional_text(outcome["description"], "outcome description")
    _optional_text(
        outcome["verification_description"], "outcome verification_description"
    )
    if outcome["status"] != "unknown" and outcome["description"] is None:
        raise ValueError("non-unknown outcome requires a description.")
    _validate_evidence_refs(
        outcome["evidence_refs"],
        package_targets=package_targets,
        supporting_targets=supporting_targets,
        label="outcome",
    )

    historical = set(historical_fact_ids or ())
    corrections = manifest["corrections"]
    if not isinstance(corrections, list) or len(corrections) > 500:
        raise ValueError("corrections are invalid.")
    correction_ids: set[str] = set()
    corrected_targets: set[str] = set()
    for index, raw in enumerate(corrections):
        item = _expect_object(raw, CORRECTION_FIELDS, f"corrections[{index}]")
        correction_id = _safe_id(item["correction_id"], "correction_id")
        if correction_id in fact_ids:
            raise ValueError(f"duplicate correction_id: {correction_id}")
        _unique_id(correction_id, correction_ids, "correction_id")
        target = _safe_id(item["corrects_fact_id"], "corrects_fact_id")
        replacement = _safe_id(
            item["replacement_fact_id"], "replacement_fact_id"
        )
        if target in correction_ids or target not in fact_ids | historical:
            raise ValueError("correction target does not resolve.")
        if replacement not in fact_ids:
            raise ValueError("correction replacement does not resolve.")
        if target == replacement:
            raise ValueError("correction target and replacement must differ.")
        _unique_id(target, corrected_targets, "corrected fact")
        _required_text(item["description"], "correction description")
        _validate_evidence_refs(
            item["evidence_refs"],
            package_targets=package_targets,
            supporting_targets=supporting_targets,
            label=f"correction {correction_id}",
        )

    completeness = manifest["completeness"]
    if not _is_allowed_string(completeness, COMPLETENESS_STATES):
        raise ValueError("completeness is invalid.")
    expected_completeness = derive_completeness(manifest)
    if completeness != expected_completeness:
        raise ValueError(
            f"completeness must be derived as {expected_completeness}."
        )
    if schema_version == REPAIR_CASE_SCHEMA_V1:
        if (
            not _has_strict_boolean_fields(
                manifest["boundaries"],
                set(FIXED_FALSE_BOUNDARIES),
            )
            or manifest["boundaries"] != FIXED_FALSE_BOUNDARIES
        ):
            raise ValueError("boundaries must remain fixed false.")
    else:
        expected_boundaries = {
            **FIXED_FALSE_BOUNDARIES,
            "model_identity_resolved": derive_model_identity_resolved(identity),
        }
        if not _has_strict_boolean_fields(
            manifest["boundaries"],
            set(expected_boundaries),
        ):
            raise ValueError("boundaries must contain strict boolean values.")
        if manifest["boundaries"] != expected_boundaries:
            raise ValueError(
                "model_identity_resolved must match derived device identity."
            )
    return copy.deepcopy(manifest)
