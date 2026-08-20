"""Export a reduced, linkable physical-evidence snapshot from server V3."""

from __future__ import annotations

import copy
import re

from scripts.visual_qc.repair_evidence_link_contract import (
    PHYSICAL_EVIDENCE_SCHEMA_VERSION,
    RepairEvidenceLinkContractError,
    canonical_sha256,
    validate_physical_evidence_snapshot,
)


SERVER_CASE_SCHEMA_VERSION = "VISUAL-QC-SERVER-CASE-V3"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
QUALIFIED_HANDOFF_FIELDS = {
    "schema_version",
    "handoff_schema_version",
    "source_package_manifest_sha256",
    "archived_intake_manifest_sha256",
    "acceptance_report_sha256",
    "acceptance_action",
    "registration_review_required",
    "field_accuracy_claim_allowed",
}
CAPTURE_STAGES = {"golden_reference", "before_repair", "after_repair"}


class RepairEvidenceExportError(ValueError):
    """A stable, operator-safe export failure."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _error(code: str, message: str):
    raise RepairEvidenceExportError(code, message)


def _object(value, code: str, label: str) -> dict:
    if not isinstance(value, dict):
        _error(code, f"{label} is malformed.")
    return value


def _safe_id(value, code: str, label: str) -> str:
    if not isinstance(value, str) or SAFE_ID.fullmatch(value) is None:
        _error(code, f"{label} identity is invalid.")
    return value


def _sha256(value, code: str, label: str) -> str:
    if not isinstance(value, str) or LOWER_SHA256.fullmatch(value) is None:
        _error(code, f"{label} hash is invalid.")
    return value


def _qualified_handoff(value) -> dict:
    handoff = _object(
        value, "invalid_qualified_handoff", "Qualified handoff"
    )
    if set(handoff) != QUALIFIED_HANDOFF_FIELDS:
        _error(
            "invalid_qualified_handoff",
            "Qualified handoff fields are invalid.",
        )
    if (
        handoff.get("schema_version")
        != "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1"
        or handoff.get("handoff_schema_version")
        != "VISUAL-QC-PHYSICAL-HANDOFF-V1"
        or handoff.get("acceptance_action")
        not in {
            "automatic_candidate_review_required",
            "manual_registration_required",
        }
        or handoff.get("registration_review_required") is not True
        or handoff.get("field_accuracy_claim_allowed") is not False
    ):
        _error(
            "invalid_qualified_handoff",
            "Qualified handoff provenance is invalid.",
        )
    for field in (
        "source_package_manifest_sha256",
        "archived_intake_manifest_sha256",
        "acceptance_report_sha256",
    ):
        _sha256(
            handoff.get(field),
            "invalid_qualified_handoff",
            "Qualified handoff",
        )
    return copy.deepcopy(handoff)


def _registration_review(value) -> dict:
    review = _object(
        value,
        "invalid_registration_review",
        "Registration review",
    )
    matrix = review.get("board_to_image_matrix")
    anchors = review.get("anchors")
    checks = review.get("check_points")
    error = review.get("error")
    if (
        review.get("status") != "reviewed"
        or review.get("decision") != "accept_manual"
        or review.get("method") != "reviewed_manual_four_point"
        or not isinstance(matrix, list)
        or len(matrix) != 9
        or not isinstance(anchors, list)
        or len(anchors) != 4
        or not isinstance(checks, list)
        or not checks
        or not isinstance(error, dict)
        or set(error) != {"count", "rms", "maximum"}
    ):
        _error(
            "invalid_registration_review",
            "Registration review is not a completed manual four-point review.",
        )
    return review


def _contract_registration_points(points, *, label: str) -> list[dict]:
    """Normalize the server's persisted [x, y] coordinates for V1 export.

    The server API exposes reviewed anchor coordinates as pairs, while the
    portable evidence contract intentionally uses named x/y points.  This is
    a representation-only conversion: values, pairing, and ordering remain
    unchanged and the contract validator still checks their geometry.
    """

    normalized = []
    for index, pair in enumerate(points):
        if not isinstance(pair, dict):
            _error(
                "invalid_registration_review",
                f"{label} {index} is malformed.",
            )
        board = pair.get("board")
        image = pair.get("image")
        if isinstance(board, list):
            if len(board) != 2:
                _error(
                    "invalid_registration_review",
                    f"{label} {index} board coordinate is malformed.",
                )
            board = {"x": board[0], "y": board[1]}
        if isinstance(image, list):
            if len(image) != 2:
                _error(
                    "invalid_registration_review",
                    f"{label} {index} image coordinate is malformed.",
                )
            image = {"x": image[0], "y": image[1]}
        normalized.append({"board": board, "image": image})
    return normalized


def build_linkable_physical_evidence(
    server_case: dict, *, physical_evidence_id: str
) -> dict:
    """Build and validate one deterministic reduced physical-evidence snapshot."""

    case = _object(server_case, "invalid_server_case", "Server case")
    if case.get("schema_version") != SERVER_CASE_SCHEMA_VERSION:
        _error(
            "invalid_schema_version",
            "Server case schema version is invalid.",
        )

    evidence_id = _safe_id(
        physical_evidence_id,
        "invalid_physical_evidence_id",
        "Physical evidence",
    )
    case_id = _safe_id(case.get("case_id"), "invalid_case", "Server case")
    board_key = _safe_id(case.get("board_key"), "invalid_case", "Board key")
    board_id = _safe_id(case.get("board_id"), "invalid_case", "Board")
    side_id = _safe_id(case.get("side_id"), "invalid_case", "Board side")
    capture_stage = case.get("capture_stage")
    if capture_stage not in CAPTURE_STAGES:
        _error("invalid_case", "Capture stage is invalid.")
    if case.get("evidence_role") != "physical_capture":
        _error(
            "invalid_evidence_role",
            "Only physical capture evidence can be exported.",
        )

    intake = _object(case.get("intake"), "invalid_intake", "Intake")
    if set(intake) != {"batch_id", "entry_id"}:
        _error("invalid_intake", "Intake fields are invalid.")
    batch_id = _safe_id(
        intake.get("batch_id"), "invalid_intake", "Intake batch"
    )
    entry_id = _safe_id(
        intake.get("entry_id"), "invalid_intake", "Intake entry"
    )
    qualified_handoff = _qualified_handoff(case.get("qualified_handoff"))

    image = _object(case.get("image"), "invalid_image", "Image")
    image_id = _safe_id(image.get("image_id"), "invalid_image", "Image")
    image_sha256 = _sha256(
        image.get("sha256"), "invalid_image", "Image"
    )
    if (
        ("side_id" in image and image["side_id"] != side_id)
        or ("board_id" in image and image["board_id"] != board_id)
        or ("board_key" in image and image["board_key"] != board_key)
    ):
        _error(
            "identity_mismatch",
            "Image board identity does not match the server case.",
        )

    job = _object(case.get("job"), "invalid_job", "Job")
    job_id = _safe_id(job.get("job_id"), "invalid_job", "Job")
    if job.get("case_id") != case_id:
        _error(
            "identity_mismatch",
            "Job identity does not match the server case.",
        )
    if job.get("status") != "succeeded":
        _error(
            "job_not_succeeded",
            "Registration job has not succeeded.",
        )

    if "server_registration_review" not in case:
        _error(
            "missing_registration_review",
            "A reviewed manual registration is required.",
        )
    review = _registration_review(case["server_registration_review"])
    review_id = _safe_id(
        review.get("review_id"),
        "invalid_registration_review",
        "Registration review",
    )
    if review.get("case_id") != case_id or review.get("job_id") != job_id:
        _error(
            "identity_mismatch",
            "Registration review identity does not match the case and job.",
        )

    snapshot = {
        "schema_version": PHYSICAL_EVIDENCE_SCHEMA_VERSION,
        "physical_evidence_id": evidence_id,
        "server_case_id": case_id,
        "intake": {
            "batch_id": batch_id,
            "entry_id": entry_id,
        },
        "board_key": board_key,
        "board_id": board_id,
        "side_id": side_id,
        "capture_stage": capture_stage,
        "evidence_role": "physical_capture",
        "qualified_handoff": qualified_handoff,
        "qualified_handoff_sha256": canonical_sha256(qualified_handoff),
        "image_id": image_id,
        "image_sha256": image_sha256,
        "job_id": job_id,
        "registration_review_id": review_id,
        "registration": {
            "method": "reviewed_manual_four_point",
            "board_to_image_matrix": copy.deepcopy(
                review["board_to_image_matrix"]
            ),
            "solve_anchors": _contract_registration_points(
                review["anchors"], label="solve anchor"
            ),
            "independent_check_points": _contract_registration_points(
                review["check_points"], label="independent check point"
            ),
            "error": copy.deepcopy(review["error"]),
        },
        "physical_evidence_snapshot_sha256": "",
    }
    snapshot["physical_evidence_snapshot_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in snapshot.items()
            if key != "physical_evidence_snapshot_sha256"
        }
    )
    try:
        return validate_physical_evidence_snapshot(snapshot)
    except RepairEvidenceLinkContractError as exc:
        raise RepairEvidenceExportError(
            "invalid_registration_review"
            if exc.code.startswith(("invalid_registration", "registration_"))
            or exc.code
            in {
                "invalid_number",
                "invalid_homography",
                "invalid_homography_horizon",
                "invalid_registration_anchors",
                "invalid_registration_projection",
                "limit_exceeded",
            }
            else "invalid_server_case",
            "Server case evidence cannot satisfy the physical evidence contract.",
        ) from exc
