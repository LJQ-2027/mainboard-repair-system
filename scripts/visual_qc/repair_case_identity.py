from __future__ import annotations

import copy
from collections.abc import Callable


IDENTITY_FIELDS = {
    "reported_models",
    "catalog_models",
    "mapping_status",
    "resolved_models",
    "resolution_note",
    "evidence_refs",
}
IDENTITY_STATUSES = {
    "exact_catalog_match",
    "confirmed_alias",
    "unresolved_alias",
    "conflict",
}
RESOLVED_IDENTITY_STATUSES = {"exact_catalog_match", "confirmed_alias"}
MAX_IDENTITY_MODELS = 20


def _string_list(value, label: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{label} is invalid.")
    if len(value) > MAX_IDENTITY_MODELS:
        raise ValueError(
            f"{label} must contain at most {MAX_IDENTITY_MODELS} records."
        )
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} is invalid.")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicates.")
    return list(value)


def validate_device_identity(
    value: dict,
    *,
    catalog_models: list[str],
    validate_evidence_refs: Callable[[list[dict]], None],
) -> dict:
    if not isinstance(value, dict) or set(value) != IDENTITY_FIELDS:
        raise ValueError("device_identity fields are invalid.")
    identity = copy.deepcopy(value)
    reported = _string_list(
        identity["reported_models"], "reported_models", allow_empty=False
    )
    catalog = _string_list(
        identity["catalog_models"], "catalog_models", allow_empty=False
    )
    expected_catalog = _string_list(
        catalog_models, "catalog_models", allow_empty=False
    )
    if catalog != expected_catalog:
        raise ValueError("catalog_models do not match board catalog order.")
    status = identity["mapping_status"]
    if not isinstance(status, str) or status not in IDENTITY_STATUSES:
        raise ValueError("mapping_status is invalid.")
    resolved = _string_list(
        identity["resolved_models"], "resolved_models", allow_empty=True
    )
    if any(model not in catalog for model in resolved):
        raise ValueError("resolved_models must be catalog compatible.")
    note = identity["resolution_note"]
    if note is not None and (
        not isinstance(note, str) or not note.strip()
    ):
        raise ValueError("resolution_note is invalid.")
    refs = identity["evidence_refs"]
    validate_evidence_refs(refs)

    if status == "exact_catalog_match":
        if not reported or reported != resolved:
            raise ValueError(
                "exact_catalog_match requires identical reported_models "
                "and resolved_models."
            )
        if any(model not in catalog for model in reported):
            raise ValueError(
                "exact_catalog_match reported_models must be in catalog_models."
            )
        if note is not None:
            raise ValueError(
                "exact_catalog_match cannot have a resolution note."
            )
    elif status == "confirmed_alias":
        if not resolved:
            raise ValueError("confirmed_alias requires resolved_models.")
        if note is None:
            raise ValueError("confirmed_alias requires a resolution note.")
        if not refs:
            raise ValueError("confirmed_alias requires evidence.")
    else:
        if resolved:
            raise ValueError(f"{status} cannot contain resolved_models.")
        if note is not None:
            raise ValueError(f"{status} cannot contain a resolution note.")
        if not refs:
            raise ValueError(f"{status} requires evidence.")
    return identity


def derive_model_identity_resolved(value: dict) -> bool:
    return value["mapping_status"] in RESOLVED_IDENTITY_STATUSES


def validate_identity_transition(
    previous: dict,
    current: dict,
    *,
    has_new_correction: bool,
) -> None:
    previous_status = previous["mapping_status"]
    current_status = current["mapping_status"]
    if previous["reported_models"] != current["reported_models"][
        : len(previous["reported_models"])
    ]:
        raise ValueError("device identity removes or rewrites reported models.")
    previous_refs = previous["evidence_refs"]
    if previous_refs != current["evidence_refs"][: len(previous_refs)]:
        raise ValueError("device identity removes or rewrites evidence.")
    if previous_status in RESOLVED_IDENTITY_STATUSES:
        if current != previous:
            raise ValueError("resolved device identity is immutable.")
        return
    allowed = {
        "unresolved_alias": {
            "unresolved_alias",
            "confirmed_alias",
            "conflict",
        },
        "conflict": {"conflict", "confirmed_alias"},
    }
    if current_status not in allowed.get(previous_status, set()):
        raise ValueError("device identity transition is not allowed.")
    if (
        previous_status == "conflict"
        and current_status == "confirmed_alias"
        and not has_new_correction
    ):
        raise ValueError(
            "conflict resolution requires a new correction record."
        )
    if (
        current_status != previous_status
        and len(current["evidence_refs"]) == len(previous_refs)
    ):
        raise ValueError(
            "device identity status changes require new evidence."
        )
    changed_names = (
        previous["reported_models"] != current["reported_models"]
        or previous["catalog_models"] != current["catalog_models"]
    )
    if changed_names and len(current["evidence_refs"]) == len(previous_refs):
        raise ValueError("device identity name changes require new evidence.")
