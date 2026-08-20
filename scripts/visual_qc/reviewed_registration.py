import math

import numpy as np

BOARD_COORDINATE_MAX_CHECK_ERROR = 0.05


def _signed_area(points):
    return 0.5 * sum(
        points[index][0] * points[(index + 1) % 4][1]
        - points[(index + 1) % 4][0] * points[index][1]
        for index in range(4)
    )


def _orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_cross(a, b, c, d):
    return (
        _orientation(a, b, c) * _orientation(a, b, d) < 0
        and _orientation(c, d, a) * _orientation(c, d, b) < 0
    )


def _validate_anchor_order(source, target):
    source_area = _signed_area(source)
    target_area = _signed_area(target)
    if abs(source_area) < 1e-6 or abs(target_area) < 1e-6:
        raise ValueError("solve anchors are degenerate")
    if source_area * target_area < 0:
        raise ValueError("solve anchor winding must be consistent")
    for points in (source, target):
        turns = [
            _orientation(points[index], points[(index + 1) % 4], points[(index + 2) % 4])
            for index in range(4)
        ]
        if any(abs(turn) < 1e-6 for turn in turns) or not (
            all(turn > 0 for turn in turns) or all(turn < 0 for turn in turns)
        ):
            raise ValueError("solve anchor quadrilaterals must be convex")
        if _segments_cross(points[0], points[1], points[2], points[3]) or _segments_cross(
            points[1], points[2], points[3], points[0]
        ):
            raise ValueError("solve anchor order must not cross")


def _point(value, label):
    if (
        not isinstance(value, dict)
        or set(value) != {"x", "y"}
        or any(
            not isinstance(value[key], (int, float))
            or isinstance(value[key], bool)
            or not math.isfinite(value[key])
            or not 0 <= value[key] <= 1
            for key in ("x", "y")
        )
    ):
        raise ValueError(f"{label} must be a finite normalized point")
    return {"x": float(value["x"]), "y": float(value["y"])}


def solve_homography(pairs):
    if not isinstance(pairs, list) or len(pairs) != 4:
        raise ValueError("reviewed registration requires exactly four solve anchors")
    rows = []
    values = []
    source = []
    target = []
    for index, pair in enumerate(pairs):
        board = _point(pair.get("board"), f"solve anchor {index} board")
        image = _point(pair.get("image"), f"solve anchor {index} image")
        source.append((board["x"], board["y"]))
        target.append((image["x"], image["y"]))
        x, y = source[-1]
        u, v = target[-1]
        rows.extend(
            [
                [x, y, 1, 0, 0, 0, -u * x, -u * y],
                [0, 0, 0, x, y, 1, -v * x, -v * y],
            ]
        )
        values.extend([u, v])
    if len(set(source)) != 4 or len(set(target)) != 4:
        raise ValueError("solve anchors must be distinct")
    _validate_anchor_order(source, target)
    coefficients = np.asarray(rows, dtype=float)
    condition = np.linalg.cond(coefficients)
    if not math.isfinite(condition) or condition > 1e12:
        raise ValueError("solve anchors are degenerate")
    try:
        solution = np.linalg.solve(coefficients, np.asarray(values, dtype=float))
    except np.linalg.LinAlgError as error:
        raise ValueError("solve anchors are degenerate") from error
    matrix = [*solution.tolist(), 1.0]
    if not all(math.isfinite(value) for value in matrix):
        raise ValueError("registration matrix must be finite")
    denominators = []
    for y in (0.0, 0.5, 1.0):
        for x in (0.0, 0.5, 1.0):
            denominator = matrix[6] * x + matrix[7] * y + matrix[8]
            if not math.isfinite(denominator) or abs(denominator) < 1e-6:
                raise ValueError("registration projection is undefined inside the board plane")
            denominators.append(denominator)
            projected_x = (matrix[0] * x + matrix[1] * y + matrix[2]) / denominator
            projected_y = (matrix[3] * x + matrix[4] * y + matrix[5]) / denominator
            if not (-0.1 <= projected_x <= 1.1 and -0.1 <= projected_y <= 1.1):
                raise ValueError("registration projection leaves the normalized image plane")
    if min(denominators) < 0 < max(denominators):
        raise ValueError("registration projection has an internal singularity")
    return [round(value, 9) for value in matrix]


def project_point(matrix, point):
    point = _point(point, "projection point")
    if not isinstance(matrix, list) or len(matrix) != 9:
        raise ValueError("registration matrix must contain nine values")
    x, y = point["x"], point["y"]
    denominator = matrix[6] * x + matrix[7] * y + matrix[8]
    if not math.isfinite(denominator) or abs(denominator) < 1e-9:
        raise ValueError("registration projection is undefined")
    return {
        "x": (matrix[0] * x + matrix[1] * y + matrix[2]) / denominator,
        "y": (matrix[3] * x + matrix[4] * y + matrix[5]) / denominator,
    }


def build_review(*, solve_anchors, independent_check_points, selection_basis, review_note):
    matrix = solve_homography(solve_anchors)
    if not isinstance(independent_check_points, list) or len(independent_check_points) < 1:
        raise ValueError("reviewed registration requires an independent check point")
    checks = []
    errors = []
    for index, pair in enumerate(independent_check_points):
        board = _point(pair.get("board"), f"check point {index} board")
        image = _point(pair.get("image"), f"check point {index} image")
        projected = project_point(matrix, board)
        error = math.hypot(projected["x"] - image["x"], projected["y"] - image["y"])
        errors.append(error)
        checks.append(
            {
                "landmark_id": pair["landmark_id"],
                "label": pair["label"],
                "selection_basis": pair.get("selection_basis", "reviewed_landmark"),
                "board": board,
                "image": image,
                "projected_error": round(error, 6),
            }
        )
    if max(errors) > BOARD_COORDINATE_MAX_CHECK_ERROR:
        raise ValueError("independent check error exceeds the board-coordinate guardrail")
    anchors = [
        {
            "landmark_id": pair["landmark_id"],
            "label": pair["label"],
            "selection_basis": pair.get("selection_basis", "reviewed_landmark"),
            "board": _point(pair["board"], "solve anchor board"),
            "image": _point(pair["image"], "solve anchor image"),
        }
        for pair in solve_anchors
    ]
    return {
        "method": "reviewed_manual_four_point",
        "review_status": "reviewed",
        "review_scope": "board_coordinate_alignment",
        "selection_basis": selection_basis,
        "board_to_image_matrix": matrix,
        "solve_anchors": anchors,
        "independent_check_points": checks,
        "error": {
            "unit": "normalized_image_plane",
            "rms": round(math.sqrt(sum(value * value for value in errors) / len(errors)), 6),
            "maximum": round(max(errors), 6),
            "threshold_status": "not_declared",
            "technical_guardrail": {
                "purpose": "board_coordinate_association_only",
                "maximum_normalized_check_error": BOARD_COORDINATE_MAX_CHECK_ERROR,
                "status": "passed",
            },
        },
        "review_note": review_note,
        "field_accuracy_claim_allowed": False,
    }
