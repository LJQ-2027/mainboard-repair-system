import argparse
import json
import math
import re
import sys
from pathlib import Path


DEFECT_CATEGORIES = (
    "burn_or_heat_damage",
    "corrosion_or_oxidation",
    "missing_component",
    "displaced_component",
    "connector_damage",
    "shield_or_structure_damage",
    "solder_anomaly",
    "foreign_material",
    "unknown_visible_anomaly",
)
CAPTURE_STAGES = {"golden_reference", "before_repair", "after_repair"}
QC_RESULTS = {"image_invalid", "needs_review", "no_visible_anomaly", "confirmed_anomaly"}
REVIEW_STATUSES = {"suspected", "confirmed", "not_defect"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _catalog_asset(root, value):
    return (root / "assets/cross-source-registration" / value).resolve()


def _normalized_point(point):
    return (
        isinstance(point, dict)
        and all(isinstance(point.get(axis), (int, float)) and 0 <= point[axis] <= 1 for axis in ("x", "y"))
    )


def _project_point(matrix, point):
    denominator = matrix[6] * point["x"] + matrix[7] * point["y"] + matrix[8]
    if not math.isfinite(denominator) or abs(denominator) < 1e-12:
        return None
    return {
        "x": (matrix[0] * point["x"] + matrix[1] * point["y"] + matrix[2]) / denominator,
        "y": (matrix[3] * point["x"] + matrix[4] * point["y"] + matrix[5]) / denominator,
    }


def _matrix_determinant(matrix):
    return (
        matrix[0] * (matrix[4] * matrix[8] - matrix[5] * matrix[7])
        - matrix[1] * (matrix[3] * matrix[8] - matrix[5] * matrix[6])
        + matrix[2] * (matrix[3] * matrix[7] - matrix[4] * matrix[6])
    )


def _invert_matrix(matrix):
    determinant = _matrix_determinant(matrix)
    if abs(determinant) < 1e-12:
        return None
    return [
        (matrix[4] * matrix[8] - matrix[5] * matrix[7]) / determinant,
        (matrix[2] * matrix[7] - matrix[1] * matrix[8]) / determinant,
        (matrix[1] * matrix[5] - matrix[2] * matrix[4]) / determinant,
        (matrix[5] * matrix[6] - matrix[3] * matrix[8]) / determinant,
        (matrix[0] * matrix[8] - matrix[2] * matrix[6]) / determinant,
        (matrix[2] * matrix[3] - matrix[0] * matrix[5]) / determinant,
        (matrix[3] * matrix[7] - matrix[4] * matrix[6]) / determinant,
        (matrix[1] * matrix[6] - matrix[0] * matrix[7]) / determinant,
        (matrix[0] * matrix[4] - matrix[1] * matrix[3]) / determinant,
    ]


def _geometry_points_for_projection(geometry):
    points = geometry.get("points", [])
    if geometry.get("type") == "rectangle" and len(points) == 2:
        first, second = points
        return [
            first,
            {"x": second["x"], "y": first["y"]},
            second,
            {"x": first["x"], "y": second["y"]},
        ]
    return points


def _projection_errors(matrix, pairs):
    errors = []
    for pair in pairs:
        projected = _project_point(matrix, pair["board"])
        if projected is None:
            return None
        errors.append(math.hypot(
            projected["x"] - pair["image"]["x"],
            projected["y"] - pair["image"]["y"],
        ))
    return errors


def _validate_geometry(geometry, label, errors):
    if not isinstance(geometry, dict) or geometry.get("type") not in {"rectangle", "polygon"}:
        errors.append(f"{label} must be rectangle or polygon geometry")
        return
    points = geometry.get("points")
    required = 2 if geometry["type"] == "rectangle" else 3
    if not isinstance(points, list) or len(points) < required or (
        geometry["type"] == "rectangle" and len(points) != 2
    ):
        errors.append(f"{label} has an invalid point count")
        return
    if any(not _normalized_point(point) for point in points):
        errors.append(f"{label} points must use normalized coordinates")
    if geometry["type"] == "rectangle" and (
        points[0].get("x") == points[1].get("x") or points[0].get("y") == points[1].get("y")
    ):
        errors.append(f"{label} rectangle must have positive width and height")


def _board_contract(root, visual_case, errors):
    catalog = _load_json(root / "knowledge-base/repair-workbench-boards.json")
    entry = catalog.get("boards", {}).get(visual_case.get("board_key"))
    if not entry:
        errors.append("board_key does not resolve in the board catalog")
        return None, None, None
    dataset = _load_json(_catalog_asset(root, entry["data"]))
    manifest = _load_json(_catalog_asset(root, entry["side_manifest"]))
    if visual_case.get("board_id") != dataset.get("board_id"):
        errors.append("board_id does not match the board catalog dataset")
    side_ids = {side.get("side_id") for side in manifest.get("sides", [])}
    if visual_case.get("side_id") not in side_ids:
        errors.append("side_id does not resolve in the board side manifest")
    return dataset, manifest, entry


def validate_visual_qc_case(visual_case, root, training_ready=False):
    root = Path(root).resolve()
    errors = []
    schema_version = visual_case.get("schema_version")
    if schema_version not in {"VISUAL-QC-CASE-V1", "VISUAL-QC-CASE-V2"}:
        errors.append("schema_version must be VISUAL-QC-CASE-V1 or VISUAL-QC-CASE-V2")
    if not isinstance(visual_case.get("case_id"), str) or not visual_case["case_id"].strip():
        errors.append("case_id is required")
    expected_storage_scopes = (
        {"local_only"}
        if schema_version == "VISUAL-QC-CASE-V1"
        else {"local_only", "server_authoritative_with_local_draft"}
    )
    if visual_case.get("storage_scope") not in expected_storage_scopes:
        errors.append("storage_scope is unsupported for this schema version")
    if visual_case.get("capture_stage") not in CAPTURE_STAGES:
        errors.append("capture_stage is unsupported")
    dataset, _, board_entry = _board_contract(root, visual_case, errors)

    image = visual_case.get("image", {})
    if not isinstance(image.get("file_name"), str) or not image["file_name"].strip():
        errors.append("image file_name is required")
    if image.get("mime_type") not in {"image/jpeg", "image/png", "image/webp"}:
        errors.append("image mime_type is unsupported")
    if not all(isinstance(image.get(axis), int) and image[axis] > 0 for axis in ("width", "height")):
        errors.append("image width and height must be positive integers")
    if not isinstance(image.get("sha256"), str) or not SHA256_PATTERN.fullmatch(image["sha256"]):
        errors.append("image sha256 must contain 64 lowercase hexadecimal characters")
    if image.get("evidence_role") not in {"physical_capture", "proxy_sample"}:
        errors.append("image evidence_role is unsupported")

    quality = visual_case.get("quality", {})
    if quality.get("status") not in {"good", "usable", "retake"}:
        errors.append("quality status is unsupported")
    if not isinstance(quality.get("score"), (int, float)) or not 0 <= quality["score"] <= 100:
        errors.append("quality score must be between 0 and 100")

    registration = visual_case.get("registration", {})
    supported_registration_methods = (
        {"reviewed_manual_homography"}
        if schema_version == "VISUAL-QC-CASE-V1"
        else {
            "reviewed_manual_homography",
            "reviewed_manual_four_point",
            "automatic_feature_homography",
        }
    )
    if registration.get("method") not in supported_registration_methods:
        errors.append("registration method is unsupported")
    if registration.get("status") not in {"draft", "reviewed"}:
        errors.append("registration status is unsupported")
    matrix = registration.get("matrix")
    if matrix is not None and (
        not isinstance(matrix, list)
        or len(matrix) != 9
        or any(
            not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in matrix
        )
    ):
        errors.append("registration matrix must contain nine numeric values")
    anchors = registration.get("solve_anchors", [])
    if not isinstance(anchors, list) or len(anchors) > 4 or any(
        not _normalized_point(anchor.get("board")) or not _normalized_point(anchor.get("image"))
        for anchor in anchors
    ):
        errors.append("registration solve_anchors must contain up to four normalized pairs")
    checks = registration.get("check_points", [])
    if any(
        not _normalized_point(check.get("board")) or not _normalized_point(check.get("image"))
        for check in checks
    ):
        errors.append("registration check_points must use normalized pairs")
    if registration.get("status") == "reviewed":
        if matrix is None:
            errors.append("reviewed registration requires a matrix")
        elif registration.get("method") == "automatic_feature_homography":
            if not registration.get("server_review_id"):
                errors.append("reviewed automatic registration requires a server review id")
        elif len(anchors) != 4 or not checks:
            errors.append(
                "reviewed manual registration requires a matrix, four anchors, and check points"
            )
    matrix_valid = (
        isinstance(matrix, list)
        and len(matrix) == 9
        and all(isinstance(value, (int, float)) and math.isfinite(value) for value in matrix)
    )
    if matrix_valid:
        if abs(_matrix_determinant(matrix)) < 1e-12:
            errors.append("registration matrix must be invertible")
        elif len(anchors) == 4:
            anchor_errors = _projection_errors(matrix, anchors)
            if anchor_errors is None or max(anchor_errors) > 1e-5:
                errors.append("registration matrix does not project the declared solve anchors")
        if checks:
            check_errors = _projection_errors(matrix, checks)
            recorded_error = registration.get("error", {})
            if recorded_error.get("count") != len(checks):
                errors.append("registration error count does not match check_points")
            if check_errors is None:
                errors.append("registration matrix cannot project the declared check_points")
            else:
                expected_rms = math.sqrt(sum(value * value for value in check_errors) / len(check_errors))
                expected_maximum = max(check_errors)
                if (
                    not isinstance(recorded_error.get("rms"), (int, float))
                    or abs(recorded_error["rms"] - expected_rms) > 1e-5
                ):
                    errors.append("registration RMS does not match check_points")
                if (
                    not isinstance(recorded_error.get("maximum"), (int, float))
                    or abs(recorded_error["maximum"] - expected_maximum) > 1e-5
                ):
                    errors.append("registration maximum error does not match check_points")

    known_entities = {}
    geometry_path = (board_entry or {}).get("geometry_by_side", {}).get(visual_case.get("side_id"))
    if geometry_path:
        geometry = _load_json(_catalog_asset(root, geometry_path))
        known_entities.update({
            component.get("component_id"): component
            for component in geometry.get("components", [])
            if component.get("component_id")
        })
    inverse_matrix = _invert_matrix(matrix) if matrix_valid else None
    for annotation in visual_case.get("annotations", []):
        annotation_id = annotation.get("annotation_id", "unknown")
        if annotation.get("category") not in DEFECT_CATEGORIES:
            errors.append(f"{annotation_id} category is unsupported")
        if annotation.get("source") not in {"human_annotation", "model_candidate"}:
            errors.append(f"{annotation_id} source is unsupported")
        if annotation.get("review_status") not in REVIEW_STATUSES:
            errors.append(f"{annotation_id} review_status is unsupported")
        _validate_geometry(annotation.get("image_geometry"), f"{annotation_id} image_geometry", errors)
        _validate_geometry(annotation.get("board_geometry"), f"{annotation_id} board_geometry", errors)
        image_geometry = annotation.get("image_geometry", {})
        board_geometry = annotation.get("board_geometry", {})
        if inverse_matrix and image_geometry.get("points") and board_geometry.get("points"):
            expected_board_points = [
                _project_point(inverse_matrix, point)
                for point in _geometry_points_for_projection(image_geometry)
            ]
            actual_board_points = board_geometry.get("points", [])
            if (
                any(point is None for point in expected_board_points)
                or len(actual_board_points) != len(expected_board_points)
                or any(
                    math.hypot(expected["x"] - actual["x"], expected["y"] - actual["y"]) > 1e-5
                    for expected, actual in zip(expected_board_points, actual_board_points)
                )
            ):
                errors.append(
                    f"{annotation_id} board_geometry does not match the registration matrix"
                )
        component = annotation.get("component")
        if component:
            entity = known_entities.get(component.get("component_id"))
            if entity is None or entity.get("designator") != component.get("designator"):
                errors.append(
                    f"{annotation_id} component does not resolve on the selected board side"
                )

    qc_result = visual_case.get("qc_result", {})
    if qc_result.get("status") not in QC_RESULTS:
        errors.append("qc_result status is unsupported")
    if qc_result.get("status") in {"no_visible_anomaly", "confirmed_anomaly"} and (
        registration.get("status") != "reviewed" or not qc_result.get("reviewed_at")
    ):
        errors.append("final QC result requires reviewed registration and reviewed_at")

    if training_ready:
        if registration.get("status") != "reviewed":
            errors.append("training cases require reviewed registration")
        if image.get("evidence_role") != "physical_capture":
            errors.append("training cases require physical capture images")
        if quality.get("status") == "retake":
            errors.append("training cases cannot use retake-quality images")
        if any(
            annotation.get("source") != "human_annotation"
            or annotation.get("review_status") not in {"confirmed", "not_defect"}
            for annotation in visual_case.get("annotations", [])
        ):
            errors.append(
                "training annotations must be confirmed human annotations or rejected non-defects"
            )
        if qc_result.get("status") not in {"no_visible_anomaly", "confirmed_anomaly"}:
            errors.append("training cases require a final human QC result")
        confirmed_count = sum(
            annotation.get("source") == "human_annotation"
            and annotation.get("review_status") == "confirmed"
            for annotation in visual_case.get("annotations", [])
        )
        if qc_result.get("status") == "confirmed_anomaly" and confirmed_count == 0:
            errors.append("confirmed_anomaly requires at least one confirmed annotation")
        if qc_result.get("status") == "no_visible_anomaly" and confirmed_count:
            errors.append("no_visible_anomaly cannot contain confirmed annotations")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate visual QC case files")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--training-ready", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    failed = False
    for value in args.paths:
        path = Path(value)
        document = _load_json(path)
        cases = document if isinstance(document, list) else [document]
        for visual_case in cases:
            errors = validate_visual_qc_case(visual_case, root, args.training_ready)
            if errors:
                failed = True
                print(f"{path}: {visual_case.get('case_id', 'unknown')}", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
