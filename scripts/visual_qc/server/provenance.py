from __future__ import annotations

import json
import re


SCHEMA_VERSION = "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1"
HANDOFF_SCHEMA_VERSION = "VISUAL-QC-PHYSICAL-HANDOFF-V1"
ALLOWED_ACTIONS = {
    "automatic_candidate_review_required",
    "manual_registration_required",
}
FIELDS = {
    "schema_version",
    "handoff_schema_version",
    "source_package_manifest_sha256",
    "archived_intake_manifest_sha256",
    "acceptance_report_sha256",
    "acceptance_action",
    "registration_review_required",
    "field_accuracy_claim_allowed",
}
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class QualifiedHandoffError(ValueError):
    pass


def normalize_qualified_handoff(raw: str | dict) -> dict:
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as exc:
        raise QualifiedHandoffError("Qualified handoff JSON is invalid.") from exc
    if not isinstance(payload, dict) or set(payload) != FIELDS:
        raise QualifiedHandoffError("Qualified handoff fields are invalid.")
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or payload["handoff_schema_version"] != HANDOFF_SCHEMA_VERSION
        or payload["acceptance_action"] not in ALLOWED_ACTIONS
        or payload["registration_review_required"] is not True
        or payload["field_accuracy_claim_allowed"] is not False
        or any(
            not isinstance(payload[field], str)
            or not LOWER_SHA256.fullmatch(payload[field])
            for field in (
                "source_package_manifest_sha256",
                "archived_intake_manifest_sha256",
                "acceptance_report_sha256",
            )
        )
    ):
        raise QualifiedHandoffError("Qualified handoff values are invalid.")
    return {field: payload[field] for field in sorted(FIELDS)}


def serialize_qualified_handoff(payload: dict | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(
        normalize_qualified_handoff(payload),
        sort_keys=True,
        separators=(",", ":"),
    )
