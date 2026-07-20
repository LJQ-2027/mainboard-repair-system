from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import cv2
import numpy as np


@dataclass(frozen=True)
class RegistrationConfig:
    max_dimension: int = 1600
    ratio_test: float = 0.78
    minimum_keypoints: int = 12
    minimum_matches: int = 12
    minimum_inliers: int = 10
    minimum_inlier_ratio: float = 0.35
    minimum_reference_coverage: float = 0.08
    maximum_reprojection_rms: float = 0.03
    ransac_reprojection_pixels: float = 4.0


def _as_color(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("image is required")
    if image.ndim == 2:
        return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_GRAY2BGR)
    if image.ndim == 3 and image.shape[2] == 3:
        return image.astype(np.uint8, copy=False)
    if image.ndim == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_BGRA2BGR)
    raise ValueError("image must be grayscale, BGR, or BGRA")


def _resize_for_features(image: np.ndarray, max_dimension: int) -> tuple[np.ndarray, float]:
    largest = max(image.shape[:2])
    if largest <= max_dimension:
        return image, 1.0
    scale = max_dimension / largest
    size = (
        max(2, round(image.shape[1] * scale)),
        max(2, round(image.shape[0] * scale)),
    )
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA), scale


def _normalization_matrix(width: int, height: int) -> np.ndarray:
    return np.array(
        [[width - 1, 0, 0], [0, height - 1, 0], [0, 0, 1]],
        dtype=np.float64,
    )

def _pixel_to_normalized_homography(
    matrix: np.ndarray,
    source_size: tuple[int, int],
    target_size: tuple[int, int],
) -> np.ndarray:
    source_scale = _normalization_matrix(*source_size)
    target_scale = _normalization_matrix(*target_size)
    normalized = np.linalg.inv(target_scale) @ matrix @ source_scale
    return normalized / normalized[2, 2]


def _polygon_area(points: np.ndarray) -> float:
    x = points[:, 0]
    y = points[:, 1]
    return abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def locate_board_contour(image: np.ndarray) -> dict:
    color = _as_color(image)
    height, width = color.shape[:2]
    border_pixels = np.concatenate(
        [color[0], color[-1], color[:, 0], color[:, -1]],
        axis=0,
    )
    background = np.median(border_pixels.astype(np.float32), axis=0)
    distance = np.linalg.norm(color.astype(np.float32) - background, axis=2)
    mask = np.where(distance > 18, 255, 0).astype(np.uint8)
    kernel_size = max(3, round(min(width, height) * 0.015))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {"status": "not_found", "area_fraction": 0.0, "polygon": [], "bbox": None}
    largest = max(contours, key=cv2.contourArea)
    area_fraction = float(cv2.contourArea(largest) / (width * height))
    if area_fraction < 0.03:
        return {"status": "not_found", "area_fraction": area_fraction, "polygon": [], "bbox": None}
    box = cv2.boxPoints(cv2.minAreaRect(largest))
    polygon = [[float(x / (width - 1)), float(y / (height - 1))] for x, y in box]
    x, y, box_width, box_height = cv2.boundingRect(largest)
    return {
        "status": "candidate",
        "area_fraction": area_fraction,
        "polygon": polygon,
        "bbox": {
            "x": x / (width - 1),
            "y": y / (height - 1),
            "width": box_width / width,
            "height": box_height / height,
        },
    }


def _detector(name: str):
    if name == "orb":
        return cv2.ORB_create(nfeatures=5000, fastThreshold=8)
    if name == "akaze":
        return cv2.AKAZE_create()
    raise ValueError(f"Unsupported detector: {name}")


def _failure(code: str, message: str, *, attempts: list[dict], contour: dict) -> dict:
    return {
        "schema_version": "VISUAL-QC-REGISTRATION-CANDIDATE-V1",
        "status": "manual_required",
        "method": None,
        "review_status": None,
        "requires_human_review": False,
        "requires_manual_registration": True,
        "board_to_image_matrix": None,
        "evidence": {"attempts": attempts, "board_contour": contour},
        "failure": {"code": code, "message": message},
        "fallback": {
            "method": "reviewed_manual_four_point",
            "reason_code": code,
        },
    }


def _attempt_registration(
    detector_name: str,
    reference_gray: np.ndarray,
    capture_gray: np.ndarray,
    config: RegistrationConfig,
) -> tuple[dict, np.ndarray | None]:
    detector = _detector(detector_name)
    reference_keypoints, reference_descriptors = detector.detectAndCompute(reference_gray, None)
    capture_keypoints, capture_descriptors = detector.detectAndCompute(capture_gray, None)
    attempt = {
        "detector": detector_name,
        "reference_keypoints": len(reference_keypoints),
        "capture_keypoints": len(capture_keypoints),
        "matches": 0,
        "inliers": 0,
        "status": "failed",
        "failure_code": None,
    }
    if (
        reference_descriptors is None
        or capture_descriptors is None
        or min(len(reference_keypoints), len(capture_keypoints)) < config.minimum_keypoints
    ):
        attempt["failure_code"] = "insufficient_keypoints"
        return attempt, None

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(reference_descriptors, capture_descriptors, k=2)
    matches = [
        first
        for pair in pairs
        if len(pair) == 2
        for first, second in [pair]
        if first.distance < config.ratio_test * second.distance
    ]
    attempt["matches"] = len(matches)
    if len(matches) < config.minimum_matches:
        attempt["failure_code"] = "insufficient_matches"
        return attempt, None

    source = np.float32([reference_keypoints[item.queryIdx].pt for item in matches])
    target = np.float32([capture_keypoints[item.trainIdx].pt for item in matches])
    matrix, mask = cv2.findHomography(
        source,
        target,
        cv2.RANSAC,
        config.ransac_reprojection_pixels,
    )
    if matrix is None or mask is None:
        attempt["failure_code"] = "homography_not_found"
        return attempt, None
    inlier_mask = mask.reshape(-1).astype(bool)
    inlier_count = int(inlier_mask.sum())
    attempt["inliers"] = inlier_count
    attempt["inlier_ratio"] = inlier_count / len(matches)
    attempt["source_points"] = source
    attempt["target_points"] = target
    attempt["inlier_mask"] = inlier_mask
    if inlier_count < config.minimum_inliers:
        attempt["failure_code"] = "low_inlier_count"
        return attempt, None
    if attempt["inlier_ratio"] < config.minimum_inlier_ratio:
        attempt["failure_code"] = "low_inlier_ratio"
        return attempt, None
    attempt["status"] = "candidate"
    return attempt, matrix


def _sanity_metrics(
    matrix: np.ndarray,
    attempt: dict,
    reference_shape: tuple[int, int],
    capture_shape: tuple[int, int],
) -> dict:
    reference_height, reference_width = reference_shape
    capture_height, capture_width = capture_shape
    inlier_source = attempt["source_points"][attempt["inlier_mask"]]
    inlier_target = attempt["target_points"][attempt["inlier_mask"]]
    x_span = float(np.ptp(inlier_source[:, 0]) / max(1, reference_width - 1))
    y_span = float(np.ptp(inlier_source[:, 1]) / max(1, reference_height - 1))
    coverage = x_span * y_span

    projected = cv2.perspectiveTransform(inlier_source.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    normalized_delta = projected - inlier_target
    normalized_delta[:, 0] /= max(1, capture_width - 1)
    normalized_delta[:, 1] /= max(1, capture_height - 1)
    errors = np.linalg.norm(normalized_delta, axis=1)

    corners = np.array(
        [[0, 0], [reference_width - 1, 0], [reference_width - 1, reference_height - 1], [0, reference_height - 1]],
        dtype=np.float32,
    )
    projected_corners = cv2.perspectiveTransform(corners.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    normalized_corners = projected_corners / np.array(
        [max(1, capture_width - 1), max(1, capture_height - 1)],
        dtype=np.float32,
    )
    return {
        "reference_coverage": coverage,
        "reprojection_rms": float(math.sqrt(float(np.mean(errors * errors)))),
        "reprojection_maximum": float(errors.max(initial=0)),
        "projected_quad": normalized_corners.tolist(),
        "projected_area": _polygon_area(normalized_corners),
        "projected_convex": bool(cv2.isContourConvex(projected_corners.astype(np.float32))),
    }


def register_board_image(
    reference: np.ndarray,
    capture: np.ndarray,
    config: RegistrationConfig | None = None,
) -> dict:
    config = config or RegistrationConfig()
    reference_color = _as_color(reference)
    capture_color = _as_color(capture)
    contour = locate_board_contour(capture_color)
    reference_original_size = (reference_color.shape[1], reference_color.shape[0])
    capture_original_size = (capture_color.shape[1], capture_color.shape[0])

    reference_working, reference_scale = _resize_for_features(reference_color, config.max_dimension)
    capture_working, capture_scale = _resize_for_features(capture_color, config.max_dimension)
    reference_gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(
        cv2.cvtColor(reference_working, cv2.COLOR_BGR2GRAY)
    )
    capture_gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(
        cv2.cvtColor(capture_working, cv2.COLOR_BGR2GRAY)
    )

    attempts = []
    failure_code = "homography_not_found"
    for detector_name in ("orb", "akaze"):
        attempt, working_matrix = _attempt_registration(
            detector_name,
            reference_gray,
            capture_gray,
            config,
        )
        attempts.append({key: value for key, value in attempt.items() if key not in {"source_points", "target_points", "inlier_mask"}})
        failure_code = attempt.get("failure_code") or failure_code
        if working_matrix is None:
            continue

        reference_to_working = np.diag([reference_scale, reference_scale, 1.0])
        capture_to_working = np.diag([capture_scale, capture_scale, 1.0])
        pixel_matrix = np.linalg.inv(capture_to_working) @ working_matrix @ reference_to_working
        normalized_matrix = _pixel_to_normalized_homography(
            pixel_matrix,
            reference_original_size,
            capture_original_size,
        )
        metrics = _sanity_metrics(
            working_matrix,
            attempt,
            reference_gray.shape,
            capture_gray.shape,
        )
        if metrics["reference_coverage"] < config.minimum_reference_coverage:
            failure_code = "insufficient_reference_coverage"
            attempts[-1]["status"] = "failed"
            attempts[-1]["failure_code"] = failure_code
            continue
        if (
            not metrics["projected_convex"]
            or not np.isfinite(normalized_matrix).all()
            or not 0.08 <= metrics["projected_area"] <= 1.8
        ):
            failure_code = "invalid_projected_shape"
            attempts[-1]["status"] = "failed"
            attempts[-1]["failure_code"] = failure_code
            continue
        if metrics["reprojection_rms"] > config.maximum_reprojection_rms:
            failure_code = "high_reprojection_error"
            attempts[-1]["status"] = "failed"
            attempts[-1]["failure_code"] = failure_code
            continue

        evidence = {
            "detector": detector_name,
            "reference_keypoints": attempt["reference_keypoints"],
            "capture_keypoints": attempt["capture_keypoints"],
            "match_count": attempt["matches"],
            "inlier_count": attempt["inliers"],
            "inlier_ratio": attempt["inlier_ratio"],
            **metrics,
            "board_contour": contour,
            "attempts": attempts,
            "technical_thresholds": asdict(config),
        }
        return {
            "schema_version": "VISUAL-QC-REGISTRATION-CANDIDATE-V1",
            "status": "candidate",
            "method": "automatic_feature_homography",
            "review_status": "draft",
            "requires_human_review": True,
            "requires_manual_registration": False,
            "board_to_image_matrix": normalized_matrix.reshape(-1).tolist(),
            "evidence": evidence,
            "failure": None,
            "fallback": {"method": "reviewed_manual_four_point", "reason_code": None},
        }

    return _failure(
        failure_code,
        "Automatic registration did not produce a technically valid candidate.",
        attempts=attempts,
        contour=contour,
    )
