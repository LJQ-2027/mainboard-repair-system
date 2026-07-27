"""Pure Visual-QC repair-evidence link contracts.

V1 linkability is reviewed_manual_four_point only. Future automatic support
requires an explicit contract with equivalent auditable correspondences.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re


PHYSICAL_EVIDENCE_SCHEMA_VERSION = (
    "VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1"
)
REPAIR_EVIDENCE_LINK_SCHEMA_VERSION = (
    "VISUAL-QC-REPAIR-EVIDENCE-LINK-V1"
)
REPAIR_CASE_SCHEMA_VERSIONS = {
    "VISUAL-QC-REPAIR-CASE-SOURCE-V1",
    "VISUAL-QC-REPAIR-CASE-SOURCE-V2",
}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_RESERVED_BASENAME = re.compile(
    r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$",
    re.IGNORECASE,
)
WINDOWS_FORBIDDEN_PATH_CHARACTERS = frozenset('<>:"|?*\\')

# V1 bounds keep pure validation deterministic for owner-authored manifests.
MAX_POLYGON_POINTS = 256
MAX_REPAIR_CASE_REFERENCES = 100
MAX_PHYSICAL_EVIDENCE = 500
MAX_BINDINGS = 5000
MAX_COMPILED_SOURCES = 100
MAX_EVIDENCE_DESCRIPTORS = 100
MAX_EVIDENCE_BASES = 3
MAX_CHECK_POINTS = 1000
HOMOGRAPHY_EPSILON = 1e-12
TRIANGLE_RELATIVE_EPSILON = 1e-9
# Reviewed solve anchors are serialized with at least six decimal places.
SOLVE_CORRESPONDENCE_TOLERANCE = 1e-6
# Projection bounds allow only normalized-coordinate floating-point noise.
PROJECTION_BOUNDS_TOLERANCE = 1e-12
# Error summaries are persisted floats, so compare recomputed values with
# tight absolute and relative allowances for decimal serialization.
ERROR_ABSOLUTE_TOLERANCE = 1e-12
ERROR_RELATIVE_TOLERANCE = 1e-6

FIXED_FALSE_BOUNDARIES = {
    "visual_defect_confirmed": False,
    "qc_annotation_created": False,
    "golden_approved": False,
    "training_label_allowed": False,
    "repair_causality_confirmed": False,
    "repair_instruction_allowed": False,
    "field_accuracy_claim_allowed": False,
}

PHYSICAL_FIELDS = {
    "schema_version",
    "physical_evidence_id",
    "server_case_id",
    "intake",
    "board_key",
    "board_id",
    "side_id",
    "capture_stage",
    "evidence_role",
    "qualified_handoff",
    "qualified_handoff_sha256",
    "image_id",
    "image_sha256",
    "job_id",
    "registration_review_id",
    "registration",
    "physical_evidence_snapshot_sha256",
}
INTAKE_FIELDS = {"batch_id", "entry_id"}
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
REGISTRATION_FIELDS = {
    "method",
    "board_to_image_matrix",
    "solve_anchors",
    "independent_check_points",
    "error",
}
REGISTRATION_POINT_FIELDS = {"board", "image"}
POINT_FIELDS = {"x", "y"}
ERROR_FIELDS = {"count", "rms", "maximum"}

LINK_FIELDS = {
    "schema_version",
    "link_set_id",
    "revision",
    "previous_manifest_sha256",
    "source_origin",
    "repair_case_references",
    "board",
    "physical_evidence",
    "bindings",
    "boundaries",
}
REPAIR_REFERENCE_FIELDS = {
    "repair_case_reference_id",
    "repair_case_id",
    "revision",
    "schema_version",
    "manifest_sha256",
    "board_key",
    "board_id",
}
BOARD_FIELDS = {
    "board_key",
    "board_id",
    "catalog_asset",
    "compiled_sources",
    "board_snapshot_sha256",
}
CATALOG_ASSET_FIELDS = {"path", "sha256", "entry_sha256"}
COMPILED_SOURCE_FIELDS = {"kind", "path", "sha256"}
BINDING_FIELDS = {
    "binding_id",
    "repair_case_reference_id",
    "source_fact",
    "target",
    "physical_evidence_id",
    "association_status",
    "visibility_status",
    "evidence_bases",
    "supersedes_binding_id",
    "boundaries",
}
SOURCE_FACT_FIELDS = {"kind", "fact_id", "display", "fact_sha256"}
DISPLAY_FIELDS = {"text", "claim_status"}
WHOLE_BOARD_FIELDS = {"kind", "side_id"}
BOARD_REGION_FIELDS = {"kind", "side_id", "region"}
DESIGNATOR_FIELDS = {"kind", "side_id", "engineering"}
RECTANGLE_FIELDS = {"kind", "x", "y", "width", "height"}
POLYGON_FIELDS = {"kind", "points"}
ENGINEERING_FIELDS = {
    "component_id",
    "designator",
    "technician_category",
    "location",
    "evidence_descriptors",
    "geometry_source_status",
    "semantic_identity_proven",
    "engineering_snapshot_sha256",
}
POINT_LOCATION_FIELDS = {"kind", "point"}
FOOTPRINT_LOCATION_FIELDS = {"kind", "rectangle"}
BASIS_FIELDS = {"kind"}
OBSERVATION_FIELDS = {"kind", "observation_code"}
BINDING_BOUNDARY_FIELDS = set(FIXED_FALSE_BOUNDARIES) | {
    "model_identity_resolved"
}


class RepairEvidenceLinkContractError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _error(code: str, message: str):
    raise RepairEvidenceLinkContractError(code, message)


def canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except UnicodeEncodeError:
        _error(
            "invalid_unicode_scalar",
            "canonical JSON contains a lone Unicode surrogate.",
        )


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_json_object_strict(path: Path) -> dict:
    display_name = Path(path).name

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _error(
                    "duplicate_json_key",
                    f"{display_name} contains duplicate key {key!r}.",
                )
            result[key] = value
        return result

    try:
        content = Path(path).read_bytes()
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda token: _error(
                "invalid_json_constant",
                f"{display_name} contains non-finite number {token}.",
            ),
        )
    except RepairEvidenceLinkContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError):
        _error("invalid_utf8_json", f"{display_name} is not strict UTF-8 JSON.")
    except OSError:
        _error("json_read_failed", f"{display_name} could not be read.")
    if not isinstance(value, dict):
        _error("json_root_not_object", f"{display_name} root must be an object.")
    _reject_lone_surrogates(value)
    return value


def _string_has_lone_surrogate(value: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in value)


def _reject_lone_surrogates(value) -> None:
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            if _string_has_lone_surrogate(current):
                _error(
                    "invalid_unicode_scalar",
                    "JSON contains a lone Unicode surrogate.",
                )
        elif isinstance(current, dict):
            stack.extend(current.keys())
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def _expect_fields(value, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        _error("invalid_fields", f"{label} fields are invalid.")
    return value


def _safe_id(value, label: str) -> str:
    if not isinstance(value, str) or SAFE_ID.fullmatch(value) is None:
        _error("invalid_id", f"{label} is not a safe identifier.")
    return value


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _error("invalid_text", f"{label} must be non-empty text.")
    if _string_has_lone_surrogate(value):
        _error(
            "invalid_unicode_scalar",
            f"{label} contains a lone Unicode surrogate.",
        )
    return value


def _sha256(value, label: str) -> str:
    if not isinstance(value, str) or LOWER_SHA256.fullmatch(value) is None:
        _error("invalid_sha256", f"{label} must be lowercase SHA-256.")
    return value


def _positive_integer(value, label: str, code="invalid_revision") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        _error(code, f"{label} must be a positive integer.")
    return value


def _finite_number(
    value,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    code: str = "invalid_number",
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _error(code, f"{label} must be a finite number.")
    try:
        number = float(value)
    except OverflowError:
        _error(code, f"{label} must be a finite number.")
    if not math.isfinite(number):
        _error(code, f"{label} must be a finite number.")
    if minimum is not None and number < minimum:
        _error(code, f"{label} is below its minimum.")
    if maximum is not None and number > maximum:
        _error(code, f"{label} exceeds its maximum.")
    return number


def _normalized_point(value, label: str, *, code="invalid_number") -> tuple[float, float]:
    point = _expect_fields(value, POINT_FIELDS, label)
    return (
        _finite_number(
            point["x"], f"{label}.x", minimum=0, maximum=1, code=code
        ),
        _finite_number(
            point["y"], f"{label}.y", minimum=0, maximum=1, code=code
        ),
    )


def _normalized_rectangle(value, label: str) -> tuple[float, float, float, float]:
    rectangle = _expect_fields(value, RECTANGLE_FIELDS, label)
    if rectangle["kind"] != "normalized_rectangle":
        _error("invalid_geometry", f"{label}.kind is invalid.")
    x = _finite_number(
        rectangle["x"], f"{label}.x", minimum=0, maximum=1,
        code="invalid_geometry",
    )
    y = _finite_number(
        rectangle["y"], f"{label}.y", minimum=0, maximum=1,
        code="invalid_geometry",
    )
    width = _finite_number(
        rectangle["width"], f"{label}.width", minimum=0,
        maximum=1, code="invalid_geometry",
    )
    height = _finite_number(
        rectangle["height"], f"{label}.height", minimum=0,
        maximum=1, code="invalid_geometry",
    )
    if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        _error("invalid_geometry", f"{label} is outside normalized bounds.")
    return x, y, width, height


def _orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (
        b[1] - a[1]
    ) * (c[0] - a[0])


def _point_on_segment(a, b, point, tolerance=1e-12) -> bool:
    return (
        min(a[0], b[0]) - tolerance
        <= point[0]
        <= max(a[0], b[0]) + tolerance
        and min(a[1], b[1]) - tolerance
        <= point[1]
        <= max(a[1], b[1]) + tolerance
        and abs(_orientation(a, b, point)) <= tolerance
    )


def _segments_intersect(a, b, c, d) -> bool:
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    if (o1 > 0 > o2 or o2 > 0 > o1) and (
        o3 > 0 > o4 or o4 > 0 > o3
    ):
        return True
    return any(
        (
            abs(o1) <= 1e-12 and _point_on_segment(a, b, c),
            abs(o2) <= 1e-12 and _point_on_segment(a, b, d),
            abs(o3) <= 1e-12 and _point_on_segment(c, d, a),
            abs(o4) <= 1e-12 and _point_on_segment(c, d, b),
        )
    )


def _normalized_polygon(value, label: str) -> list[tuple[float, float]]:
    polygon = _expect_fields(value, POLYGON_FIELDS, label)
    if polygon["kind"] != "normalized_polygon":
        _error("invalid_geometry", f"{label}.kind is invalid.")
    raw_points = polygon["points"]
    if not isinstance(raw_points, list) or len(raw_points) < 3:
        _error("invalid_geometry", f"{label} requires at least three points.")
    if len(raw_points) > MAX_POLYGON_POINTS:
        _error(
            "limit_exceeded",
            f"{label} exceeds the {MAX_POLYGON_POINTS}-point limit.",
        )
    points = [
        _normalized_point(
            point, f"{label}.points[{index}]", code="invalid_geometry"
        )
        for index, point in enumerate(raw_points)
    ]
    area = abs(
        sum(
            points[index][0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * points[index][1]
            for index in range(len(points))
        )
        / 2
    )
    if area <= 1e-12:
        _error("invalid_geometry", f"{label} is degenerate.")
    edge_count = len(points)
    for first in range(edge_count):
        first_next = (first + 1) % edge_count
        for second in range(first + 1, edge_count):
            second_next = (second + 1) % edge_count
            if (
                first == second
                or first_next == second
                or second_next == first
            ):
                continue
            if _segments_intersect(
                points[first],
                points[first_next],
                points[second],
                points[second_next],
            ):
                _error("invalid_geometry", f"{label} self-intersects.")
    return points


def _validate_boundaries(value, *, binding: bool) -> None:
    fields = BINDING_BOUNDARY_FIELDS if binding else set(FIXED_FALSE_BOUNDARIES)
    if not isinstance(value, dict) or set(value) != fields:
        _error("invalid_boundaries", "boundary fields are invalid.")
    for field in FIXED_FALSE_BOUNDARIES:
        if type(value[field]) is not bool or value[field] is not False:
            _error("invalid_boundaries", "governance boundaries must remain false.")
    if binding and type(value["model_identity_resolved"]) is not bool:
        _error(
            "invalid_boundaries",
            "model_identity_resolved must be a strict boolean.",
        )


def _validate_qualified_handoff(value) -> dict:
    handoff = _expect_fields(
        value, QUALIFIED_HANDOFF_FIELDS, "qualified_handoff"
    )
    if (
        handoff["schema_version"]
        != "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1"
        or handoff["handoff_schema_version"]
        != "VISUAL-QC-PHYSICAL-HANDOFF-V1"
        or handoff["acceptance_action"]
        not in {
            "automatic_candidate_review_required",
            "manual_registration_required",
        }
        or handoff["registration_review_required"] is not True
        or handoff["field_accuracy_claim_allowed"] is not False
    ):
        _error(
            "invalid_qualified_handoff",
            "qualified_handoff fixed values are invalid.",
        )
    for field in (
        "source_package_manifest_sha256",
        "archived_intake_manifest_sha256",
        "acceptance_report_sha256",
    ):
        _sha256(handoff[field], f"qualified_handoff.{field}")
    return handoff


def _validate_registration_point(
    value, label: str
) -> tuple[tuple[float, float], tuple[float, float]]:
    point = _expect_fields(value, REGISTRATION_POINT_FIELDS, label)
    return (
        _normalized_point(point["board"], f"{label}.board"),
        _normalized_point(point["image"], f"{label}.image"),
    )


def _validate_anchor_quad(
    points: list[tuple[float, float]], label: str
) -> None:
    if len(set(points)) != 4:
        _error(
            "invalid_registration_anchors",
            f"{label} anchor points must be distinct.",
        )
    scale = max(
        max(point[0] for point in points) - min(point[0] for point in points),
        max(point[1] for point in points) - min(point[1] for point in points),
    )
    tolerance = max(
        HOMOGRAPHY_EPSILON,
        scale * scale * TRIANGLE_RELATIVE_EPSILON,
    )
    for first in range(2):
        for second in range(first + 1, 3):
            for third in range(second + 1, 4):
                if abs(
                    _orientation(
                        points[first], points[second], points[third]
                    )
                ) <= tolerance:
                    _error(
                        "invalid_registration_anchors",
                        f"{label} anchors contain a degenerate triangle.",
                    )


def _validate_homography_projection(
    matrix: list[float], point: tuple[float, float], label: str
) -> tuple[float, float]:
    x, y = point
    denominator = matrix[6] * x + matrix[7] * y + matrix[8]
    if (
        not math.isfinite(denominator)
        or abs(denominator) <= HOMOGRAPHY_EPSILON
    ):
        _error(
            "invalid_registration_projection",
            f"{label} has an invalid homogeneous denominator.",
        )
    projected_x = (
        matrix[0] * x + matrix[1] * y + matrix[2]
    ) / denominator
    projected_y = (
        matrix[3] * x + matrix[4] * y + matrix[5]
    ) / denominator
    if (
        not math.isfinite(projected_x)
        or not math.isfinite(projected_y)
        or not -PROJECTION_BOUNDS_TOLERANCE
        <= projected_x
        <= 1 + PROJECTION_BOUNDS_TOLERANCE
        or not -PROJECTION_BOUNDS_TOLERANCE
        <= projected_y
        <= 1 + PROJECTION_BOUNDS_TOLERANCE
    ):
        _error(
            "invalid_registration_projection",
            f"{label} projects outside normalized image coordinates.",
        )
    return projected_x, projected_y


def _validate_board_domain_denominator(matrix: list[float]) -> None:
    denominators = [
        matrix[6] * x + matrix[7] * y + matrix[8]
        for x, y in (
            (0.0, 0.0),
            (1.0, 0.0),
            (0.0, 1.0),
            (1.0, 1.0),
        )
    ]
    all_positive = all(
        math.isfinite(value) and value > HOMOGRAPHY_EPSILON
        for value in denominators
    )
    all_negative = all(
        math.isfinite(value) and value < -HOMOGRAPHY_EPSILON
        for value in denominators
    )
    if not (all_positive or all_negative):
        _error(
            "invalid_homography_horizon",
            "registration denominator crosses or touches the board domain.",
        )


def _validate_registration(value) -> None:
    registration = _expect_fields(
        value, REGISTRATION_FIELDS, "registration"
    )
    if registration["method"] != "reviewed_manual_four_point":
        _error(
            "invalid_registration_method",
            "V1 requires reviewed_manual_four_point registration.",
        )
    matrix = registration["board_to_image_matrix"]
    if not isinstance(matrix, list) or len(matrix) != 9:
        _error("invalid_registration", "registration matrix must contain nine numbers.")
    supplied_matrix = [
        _finite_number(number, f"registration matrix item {index}")
        for index, number in enumerate(matrix)
    ]
    coefficient_scale = max(abs(number) for number in supplied_matrix)
    if coefficient_scale == 0:
        _error(
            "invalid_homography",
            "registration matrix must be a nonsingular homography.",
        )
    matrix = [
        number / coefficient_scale for number in supplied_matrix
    ]
    determinant = (
        matrix[0] * (matrix[4] * matrix[8] - matrix[5] * matrix[7])
        - matrix[1] * (matrix[3] * matrix[8] - matrix[5] * matrix[6])
        + matrix[2] * (matrix[3] * matrix[7] - matrix[4] * matrix[6])
    )
    if (
        not math.isfinite(determinant)
        or abs(determinant) <= HOMOGRAPHY_EPSILON
    ):
        _error(
            "invalid_homography",
            "registration matrix must be a nonsingular homography.",
        )
    _validate_board_domain_denominator(matrix)
    anchors = registration["solve_anchors"]
    if not isinstance(anchors, list) or len(anchors) != 4:
        _error("invalid_registration", "registration requires exactly four solve anchors.")
    anchor_pairs = [
        _validate_registration_point(point, f"solve anchor {index}")
        for index, point in enumerate(anchors)
    ]
    _validate_anchor_quad(
        [pair[0] for pair in anchor_pairs], "board"
    )
    _validate_anchor_quad(
        [pair[1] for pair in anchor_pairs], "image"
    )
    checks = registration["independent_check_points"]
    if not isinstance(checks, list) or not checks:
        _error(
            "invalid_registration",
            "registration requires an independent check point.",
        )
    if len(checks) > MAX_CHECK_POINTS:
        _error(
            "limit_exceeded",
            "registration independent_check_points exceed the "
            f"{MAX_CHECK_POINTS}-item limit.",
        )
    check_pairs = [
        _validate_registration_point(
            point, f"independent check point {index}"
        )
        for index, point in enumerate(checks)
    ]
    for index, pair in enumerate(anchor_pairs):
        projected = _validate_homography_projection(
            matrix, pair[0], f"solve anchor {index}"
        )
        if math.dist(projected, pair[1]) > SOLVE_CORRESPONDENCE_TOLERANCE:
            _error(
                "registration_correspondence_mismatch",
                f"solve anchor {index} does not match the homography.",
            )
    check_errors = []
    for index, pair in enumerate(check_pairs):
        projected = _validate_homography_projection(
            matrix, pair[0], f"independent check point {index}"
        )
        check_errors.append(math.dist(projected, pair[1]))
    error = _expect_fields(registration["error"], ERROR_FIELDS, "registration error")
    count = _positive_integer(
        error["count"], "registration error count", code="invalid_number"
    )
    rms = _finite_number(error["rms"], "registration error rms", minimum=0)
    maximum = _finite_number(
        error["maximum"], "registration error maximum", minimum=0
    )
    if count != len(checks):
        _error("invalid_registration", "registration error summary is inconsistent.")
    computed_rms = math.sqrt(
        sum(item * item for item in check_errors) / len(check_errors)
    )
    computed_maximum = max(check_errors)
    if (
        not math.isclose(
            rms,
            computed_rms,
            rel_tol=ERROR_RELATIVE_TOLERANCE,
            abs_tol=ERROR_ABSOLUTE_TOLERANCE,
        )
        or not math.isclose(
            maximum,
            computed_maximum,
            rel_tol=ERROR_RELATIVE_TOLERANCE,
            abs_tol=ERROR_ABSOLUTE_TOLERANCE,
        )
    ):
        _error(
            "registration_error_mismatch",
            "registration error summary does not match check correspondences.",
        )


def validate_physical_evidence_snapshot(value: dict) -> dict:
    snapshot = _expect_fields(
        value, PHYSICAL_FIELDS, "physical evidence snapshot"
    )
    if snapshot["schema_version"] != PHYSICAL_EVIDENCE_SCHEMA_VERSION:
        _error("invalid_schema_version", "physical evidence schema version is invalid.")
    for field in (
        "physical_evidence_id",
        "server_case_id",
        "board_key",
        "board_id",
        "side_id",
        "capture_stage",
        "image_id",
        "job_id",
        "registration_review_id",
    ):
        _safe_id(snapshot[field], field)
    intake = _expect_fields(snapshot["intake"], INTAKE_FIELDS, "intake")
    _safe_id(intake["batch_id"], "intake.batch_id")
    _safe_id(intake["entry_id"], "intake.entry_id")
    if snapshot["evidence_role"] != "physical_capture":
        _error("invalid_evidence_role", "evidence_role must be physical_capture.")
    handoff = _validate_qualified_handoff(snapshot["qualified_handoff"])
    _sha256(snapshot["qualified_handoff_sha256"], "qualified_handoff_sha256")
    if snapshot["qualified_handoff_sha256"] != canonical_sha256(handoff):
        _error(
            "qualified_handoff_hash_mismatch",
            "qualified_handoff_sha256 does not match canonical content.",
        )
    _sha256(snapshot["image_sha256"], "image_sha256")
    _validate_registration(snapshot["registration"])
    _sha256(
        snapshot["physical_evidence_snapshot_sha256"],
        "physical_evidence_snapshot_sha256",
    )
    expected = canonical_sha256(
        {
            key: item
            for key, item in snapshot.items()
            if key != "physical_evidence_snapshot_sha256"
        }
    )
    if snapshot["physical_evidence_snapshot_sha256"] != expected:
        _error(
            "physical_snapshot_hash_mismatch",
            "physical evidence snapshot hash does not match canonical content.",
        )
    return copy.deepcopy(snapshot)


def _repository_path(value, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or any(
            character in WINDOWS_FORBIDDEN_PATH_CHARACTERS
            or ord(character) < 32
            or 127 <= ord(character) <= 159
            for character in value
        )
    ):
        _error(
            "invalid_repository_path",
            f"{label} must be a Windows-safe repository-relative POSIX path.",
        )
    segments = value.split("/")
    for segment in segments:
        basename = segment.split(".", 1)[0].rstrip(" .")
        if (
            not segment
            or segment in {".", ".."}
            or segment.endswith((" ", "."))
            or WINDOWS_RESERVED_BASENAME.fullmatch(basename) is not None
        ):
            _error(
                "invalid_repository_path",
                f"{label} contains an unsafe Windows path segment.",
            )
    return value


def _validate_repair_reference(value) -> dict:
    reference = _expect_fields(
        value, REPAIR_REFERENCE_FIELDS, "repair case reference"
    )
    for field in (
        "repair_case_reference_id",
        "repair_case_id",
        "board_key",
        "board_id",
    ):
        _safe_id(reference[field], field)
    _positive_integer(reference["revision"], "repair case revision")
    if reference["schema_version"] not in REPAIR_CASE_SCHEMA_VERSIONS:
        _error("invalid_schema_version", "repair case schema version is invalid.")
    _sha256(reference["manifest_sha256"], "repair case manifest_sha256")
    return reference


def _validate_board(value) -> dict:
    board = _expect_fields(value, BOARD_FIELDS, "board snapshot")
    _safe_id(board["board_key"], "board.board_key")
    _safe_id(board["board_id"], "board.board_id")
    asset = _expect_fields(
        board["catalog_asset"], CATALOG_ASSET_FIELDS, "catalog_asset"
    )
    _repository_path(asset["path"], "catalog_asset.path")
    _sha256(asset["sha256"], "catalog_asset.sha256")
    _sha256(asset["entry_sha256"], "catalog_asset.entry_sha256")
    sources = board["compiled_sources"]
    if not isinstance(sources, list) or not sources:
        _error(
            "invalid_board_snapshot",
            "compiled_sources must be a non-empty array.",
        )
    if len(sources) > MAX_COMPILED_SOURCES:
        _error(
            "limit_exceeded",
            f"compiled_sources exceed the {MAX_COMPILED_SOURCES}-item limit.",
        )
    seen_sources = set()
    for index, raw_source in enumerate(sources):
        source = _expect_fields(
            raw_source, COMPILED_SOURCE_FIELDS, f"compiled source {index}"
        )
        _safe_id(source["kind"], "compiled source kind")
        path = _repository_path(source["path"], "compiled source path")
        _sha256(source["sha256"], "compiled source sha256")
        key = (source["kind"], path, source["sha256"])
        if key in seen_sources:
            _error("duplicate_id", "compiled source records must be unique.")
        seen_sources.add(key)
    _sha256(board["board_snapshot_sha256"], "board_snapshot_sha256")
    expected = canonical_sha256(
        {
            key: item
            for key, item in board.items()
            if key != "board_snapshot_sha256"
        }
    )
    if board["board_snapshot_sha256"] != expected:
        _error(
            "board_snapshot_hash_mismatch",
            "board_snapshot_sha256 does not match canonical content.",
        )
    return board


def _validate_source_fact(value) -> dict:
    fact = _expect_fields(value, SOURCE_FACT_FIELDS, "source_fact")
    kind = fact["kind"]
    if kind not in {
        "reported_symptom",
        "finding",
        "repair_action",
        "outcome",
    }:
        _error("invalid_source_fact", "source fact kind is invalid.")
    fact_id = fact["fact_id"]
    if kind == "outcome":
        if fact_id != "outcome":
            _error("invalid_source_fact", "outcome fact_id must be outcome.")
    else:
        try:
            _safe_id(fact_id, "source fact_id")
        except RepairEvidenceLinkContractError:
            _error("invalid_source_fact", "source fact_id is invalid.")
    display = _expect_fields(fact["display"], DISPLAY_FIELDS, "source fact display")
    _text(display["text"], "source fact display text")
    claim_status = display["claim_status"]
    if kind == "finding":
        if claim_status not in {"reported", "suspected", "documented"}:
            _error("invalid_source_fact", "finding claim_status is invalid.")
    elif claim_status is not None:
        _error(
            "invalid_source_fact",
            "only findings may contain a claim_status.",
        )
    _sha256(fact["fact_sha256"], "fact_sha256")
    expected = canonical_sha256(
        {key: item for key, item in fact.items() if key != "fact_sha256"}
    )
    if fact["fact_sha256"] != expected:
        _error(
            "source_fact_hash_mismatch",
            "fact_sha256 does not match canonical content.",
        )
    return fact


def _validate_engineering(value) -> dict:
    engineering = _expect_fields(
        value, ENGINEERING_FIELDS, "engineering snapshot"
    )
    for field in ("component_id", "designator", "technician_category"):
        _safe_id(engineering[field], f"engineering.{field}")
    status = engineering["geometry_source_status"]
    if status not in {"high", "medium", "low"}:
        _error(
            "invalid_engineering_geometry",
            "geometry_source_status is invalid.",
        )
    location = engineering["location"]
    if not isinstance(location, dict):
        _error("invalid_engineering_geometry", "engineering location is invalid.")
    if location.get("kind") == "normalized_point":
        location = _expect_fields(
            location, POINT_LOCATION_FIELDS, "engineering point location"
        )
        _normalized_point(
            location["point"],
            "engineering point",
            code="invalid_engineering_geometry",
        )
    elif location.get("kind") == "normalized_footprint":
        location = _expect_fields(
            location, FOOTPRINT_LOCATION_FIELDS, "engineering footprint location"
        )
        if status == "low":
            _error(
                "invalid_engineering_geometry",
                "low geometry may only use a conservative point.",
            )
        try:
            _normalized_rectangle(
                {"kind": "normalized_rectangle", **location["rectangle"]},
                "engineering footprint",
            )
        except TypeError:
            _error(
                "invalid_engineering_geometry",
                "engineering footprint is invalid.",
            )
        except RepairEvidenceLinkContractError as caught:
            if caught.code == "invalid_fields":
                _error(
                    "invalid_engineering_geometry",
                    "engineering footprint fields are invalid.",
                )
            raise
    else:
        _error(
            "invalid_engineering_geometry",
            "engineering location kind is invalid.",
        )
    descriptors = engineering["evidence_descriptors"]
    if not isinstance(descriptors, list) or not descriptors:
        _error(
            "invalid_engineering_evidence",
            "evidence_descriptors must be a non-empty array.",
        )
    if len(descriptors) > MAX_EVIDENCE_DESCRIPTORS:
        _error(
            "limit_exceeded",
            "evidence_descriptors exceed the "
            f"{MAX_EVIDENCE_DESCRIPTORS}-item limit.",
        )
    for descriptor in descriptors:
        _text(descriptor, "engineering evidence descriptor")
    if len(set(descriptors)) != len(descriptors):
        _error(
            "invalid_engineering_evidence",
            "engineering evidence descriptors must be unique.",
        )
    if type(engineering["semantic_identity_proven"]) is not bool:
        _error(
            "invalid_engineering_identity",
            "semantic_identity_proven must be a strict boolean.",
        )
    _sha256(
        engineering["engineering_snapshot_sha256"],
        "engineering_snapshot_sha256",
    )
    expected = canonical_sha256(
        {
            key: item
            for key, item in engineering.items()
            if key != "engineering_snapshot_sha256"
        }
    )
    if engineering["engineering_snapshot_sha256"] != expected:
        _error(
            "engineering_snapshot_hash_mismatch",
            "engineering snapshot hash does not match canonical content.",
        )
    return engineering


def _validate_target(value) -> tuple[str, str, dict | None]:
    if not isinstance(value, dict):
        _error("invalid_target", "target must be an object.")
    kind = value.get("kind")
    if kind == "whole_board":
        target = _expect_fields(value, WHOLE_BOARD_FIELDS, "whole_board target")
        _safe_id(target["side_id"], "target.side_id")
        return kind, target["side_id"], None
    if kind == "board_region":
        target = _expect_fields(value, BOARD_REGION_FIELDS, "board_region target")
        _safe_id(target["side_id"], "target.side_id")
        region = target["region"]
        if not isinstance(region, dict):
            _error("invalid_geometry", "board region must be an object.")
        if region.get("kind") == "normalized_rectangle":
            _normalized_rectangle(region, "board region")
        elif region.get("kind") == "normalized_polygon":
            _normalized_polygon(region, "board region")
        else:
            _error("invalid_geometry", "board region kind is invalid.")
        return kind, target["side_id"], None
    if kind == "designator":
        target = _expect_fields(value, DESIGNATOR_FIELDS, "designator target")
        _safe_id(target["side_id"], "target.side_id")
        engineering = _validate_engineering(target["engineering"])
        return kind, target["side_id"], engineering
    _error("invalid_target", "target kind is invalid.")


def _validate_evidence_bases(value, visibility: str) -> set[str]:
    if not isinstance(value, list) or not value:
        _error("invalid_evidence_basis", "evidence_bases must be non-empty.")
    if len(value) > MAX_EVIDENCE_BASES:
        _error(
            "limit_exceeded",
            f"evidence_bases exceed the {MAX_EVIDENCE_BASES}-item limit.",
        )
    kinds = set()
    observation_code = None
    for index, raw_basis in enumerate(value):
        if not isinstance(raw_basis, dict):
            _error("invalid_evidence_basis", f"evidence basis {index} is invalid.")
        kind = raw_basis.get("kind")
        if kind in {"repair_case_fact", "engineering_identity"}:
            _expect_fields(raw_basis, BASIS_FIELDS, f"{kind} basis")
        elif kind == "human_observation":
            basis = _expect_fields(
                raw_basis, OBSERVATION_FIELDS, "human_observation basis"
            )
            observation_code = basis["observation_code"]
            if observation_code not in {
                "target_visible",
                "target_not_visible",
                "target_occluded",
            }:
                _error(
                    "observation_visibility_mismatch",
                    "human observation code is invalid.",
                )
        else:
            _error("invalid_evidence_basis", "evidence basis kind is invalid.")
        if kind in kinds:
            _error("duplicate_evidence_basis", "evidence basis kinds must be unique.")
        kinds.add(kind)
    expected_code = {
        "visible": "target_visible",
        "not_visible": "target_not_visible",
        "occluded": "target_occluded",
    }.get(visibility)
    if observation_code is not None and observation_code != expected_code:
        _error(
            "observation_visibility_mismatch",
            "human observation must match visibility_status.",
        )
    return kinds


def _validate_binding(value) -> tuple[dict, str, str]:
    item = _expect_fields(value, BINDING_FIELDS, "binding")
    _safe_id(item["binding_id"], "binding_id")
    _safe_id(
        item["repair_case_reference_id"], "repair_case_reference_id"
    )
    _validate_source_fact(item["source_fact"])
    target_kind, side_id, engineering = _validate_target(item["target"])
    _safe_id(item["physical_evidence_id"], "physical_evidence_id")
    if item["association_status"] not in {
        "related",
        "possibly_related",
        "not_related",
        "insufficient_evidence",
    }:
        _error("invalid_association_status", "association_status is invalid.")
    visibility = item["visibility_status"]
    if visibility not in {
        "not_assessed",
        "visible",
        "not_visible",
        "occluded",
    }:
        _error("invalid_visibility_status", "visibility_status is invalid.")
    bases = _validate_evidence_bases(item["evidence_bases"], visibility)
    if (
        target_kind == "designator"
        and item["association_status"] == "related"
        and (
            not engineering["semantic_identity_proven"]
            or not {"repair_case_fact", "engineering_identity"}.issubset(bases)
        )
    ):
        _error(
            "related_designator_not_proven",
            "related designator requires source and proven engineering identity.",
        )
    supersedes = item["supersedes_binding_id"]
    if supersedes is not None:
        _safe_id(supersedes, "supersedes_binding_id")
    _validate_boundaries(item["boundaries"], binding=True)
    return item, side_id, target_kind


def _validate_supersession(bindings: list[dict], revision: int) -> None:
    parent_by_binding = {
        item["binding_id"]: item["supersedes_binding_id"] for item in bindings
    }
    binding_positions = {
        item["binding_id"]: index for index, item in enumerate(bindings)
    }
    if revision == 1 and any(parent is not None for parent in parent_by_binding.values()):
        _error(
            "invalid_supersession",
            "revision 1 bindings cannot supersede another binding.",
        )
    replacements = {}
    for binding_id, parent in parent_by_binding.items():
        if parent is None:
            continue
        if parent == binding_id or parent not in parent_by_binding:
            _error(
                "invalid_supersession",
                "superseded binding must resolve in the same link set.",
            )
        if parent in replacements:
            _error(
                "duplicate_replacement",
                "one binding cannot have two active replacements.",
            )
        replacements[parent] = binding_id
    state = {binding_id: 0 for binding_id in parent_by_binding}
    for start in parent_by_binding:
        if state[start] == 2:
            continue
        path = []
        current = start
        while current is not None and state[current] == 0:
            state[current] = 1
            path.append(current)
            current = parent_by_binding[current]
        if current is not None and state[current] == 1:
            _error("supersession_cycle", "binding supersession contains a cycle.")
        for binding_id in path:
            state[binding_id] = 2
    for binding_id, parent in parent_by_binding.items():
        if (
            parent is not None
            and binding_positions[parent] >= binding_positions[binding_id]
        ):
            _error(
                "invalid_supersession",
                "a replacement must follow the binding it supersedes.",
            )


def validate_repair_evidence_link_manifest(value: dict) -> dict:
    """Validate only the pure, self-contained V1 contract.

    Prior-manifest checks for exact revision increments, actual parent hashes,
    and append-only preservation require the Task 3 on-disk validator.
    Publisher-derived identity booleans are structurally checked here, not
    derived from external repair-case or engineering authorities.
    """
    manifest = _expect_fields(value, LINK_FIELDS, "repair evidence link manifest")
    if manifest["schema_version"] != REPAIR_EVIDENCE_LINK_SCHEMA_VERSION:
        _error("invalid_schema_version", "link schema version is invalid.")
    _safe_id(manifest["link_set_id"], "link_set_id")
    revision = _positive_integer(manifest["revision"], "revision")
    previous = manifest["previous_manifest_sha256"]
    if revision == 1:
        if previous is not None:
            _error("invalid_revision", "revision 1 must not have a parent.")
    elif previous is None:
        _error("invalid_revision", "later revisions require a parent hash.")
    else:
        _sha256(previous, "previous_manifest_sha256")
    if manifest["source_origin"] != "codex_operator":
        _error("invalid_source_origin", "source_origin must be codex_operator.")
    _validate_boundaries(manifest["boundaries"], binding=False)

    raw_references = manifest["repair_case_references"]
    if not isinstance(raw_references, list) or not raw_references:
        _error(
            "invalid_repair_case_references",
            "repair_case_references must be non-empty.",
        )
    if len(raw_references) > MAX_REPAIR_CASE_REFERENCES:
        _error(
            "limit_exceeded",
            "repair_case_references exceed the "
            f"{MAX_REPAIR_CASE_REFERENCES}-item limit.",
        )
    references = {}
    repair_case_ids = set()
    repair_case_revisions = set()
    for raw_reference in raw_references:
        reference = _validate_repair_reference(raw_reference)
        reference_id = reference["repair_case_reference_id"]
        if reference_id in references:
            _error("duplicate_id", "repair_case_reference_id must be unique.")
        case_revision = (
            reference["repair_case_id"],
            reference["revision"],
        )
        if case_revision in repair_case_revisions:
            _error(
                "duplicate_repair_case_revision",
                "one repair-case revision cannot have multiple references.",
            )
        references[reference_id] = reference
        repair_case_ids.add(reference["repair_case_id"])
        repair_case_revisions.add(case_revision)
    if len(repair_case_ids) != 1:
        _error(
            "identity_mismatch",
            "all repair case references must name one repair case.",
        )

    board = _validate_board(manifest["board"])
    board_identity = (board["board_key"], board["board_id"])
    for reference in references.values():
        if (reference["board_key"], reference["board_id"]) != board_identity:
            _error(
                "identity_mismatch",
                "repair case reference board does not match link board.",
            )

    raw_physical = manifest["physical_evidence"]
    if not isinstance(raw_physical, list) or not raw_physical:
        _error(
            "invalid_physical_evidence",
            "physical_evidence must be non-empty.",
        )
    if len(raw_physical) > MAX_PHYSICAL_EVIDENCE:
        _error(
            "limit_exceeded",
            "physical_evidence exceed the "
            f"{MAX_PHYSICAL_EVIDENCE}-item limit.",
        )
    physical = {}
    for raw_snapshot in raw_physical:
        snapshot = validate_physical_evidence_snapshot(raw_snapshot)
        evidence_id = snapshot["physical_evidence_id"]
        if evidence_id in physical:
            _error("duplicate_id", "physical_evidence_id must be unique.")
        if (snapshot["board_key"], snapshot["board_id"]) != board_identity:
            _error(
                "identity_mismatch",
                "physical evidence board does not match link board.",
            )
        physical[evidence_id] = snapshot

    raw_bindings = manifest["bindings"]
    if not isinstance(raw_bindings, list) or not raw_bindings:
        _error("invalid_bindings", "bindings must be non-empty.")
    if len(raw_bindings) > MAX_BINDINGS:
        _error(
            "limit_exceeded",
            f"bindings exceed the {MAX_BINDINGS}-item limit.",
        )
    bindings = []
    binding_ids = set()
    for raw_binding in raw_bindings:
        item, side_id, _target_kind = _validate_binding(raw_binding)
        binding_id = item["binding_id"]
        if binding_id in binding_ids:
            _error("duplicate_id", "binding_id must be unique.")
        binding_ids.add(binding_id)
        if item["repair_case_reference_id"] not in references:
            _error(
                "unresolved_reference",
                "binding repair_case_reference_id does not resolve.",
            )
        evidence = physical.get(item["physical_evidence_id"])
        if evidence is None:
            _error(
                "unresolved_reference",
                "binding physical_evidence_id does not resolve.",
            )
        reference = references[item["repair_case_reference_id"]]
        if (
            (reference["board_key"], reference["board_id"]) != board_identity
            or (evidence["board_key"], evidence["board_id"]) != board_identity
            or evidence["side_id"] != side_id
        ):
            _error(
                "identity_mismatch",
                "binding board or side identity is inconsistent.",
            )
        bindings.append(item)
    _validate_supersession(bindings, revision)
    return copy.deepcopy(manifest)
