from __future__ import annotations

import cv2
import numpy as np


def _normalization_matrix(width: int, height: int) -> np.ndarray:
    return np.asarray(
        [[width - 1, 0, 0], [0, height - 1, 0], [0, 0, 1]],
        dtype=np.float64,
    )


def _warp_to_board_plane(
    image: np.ndarray,
    board_to_image_matrix: list[float],
    output_size: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    output_width, output_height = output_size
    image_height, image_width = image.shape[:2]
    normalized = np.asarray(board_to_image_matrix, dtype=np.float64).reshape(3, 3)
    board_to_image_pixels = (
        _normalization_matrix(image_width, image_height)
        @ normalized
        @ np.linalg.inv(_normalization_matrix(output_width, output_height))
    )
    image_to_board_pixels = np.linalg.inv(board_to_image_pixels)
    warped = cv2.warpPerspective(
        image,
        image_to_board_pixels,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    source_mask = np.full(image.shape[:2], 255, dtype=np.uint8)
    mask = cv2.warpPerspective(
        source_mask,
        image_to_board_pixels,
        output_size,
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return warped, mask


def _normalized_grayscale(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    valid = gray[mask > 0]
    if not valid.size:
        return gray
    mean = float(np.mean(valid))
    standard_deviation = max(1.0, float(np.std(valid)))
    normalized = (gray.astype(np.float32) - mean) * (45.0 / standard_deviation) + 128.0
    return np.clip(normalized, 0, 255).astype(np.uint8)


def generate_difference_candidates(
    golden_image: np.ndarray,
    golden_board_to_image_matrix: list[float],
    capture_image: np.ndarray,
    capture_board_to_image_matrix: list[float],
    *,
    maximum_dimension: int = 1200,
) -> tuple[dict, bytes]:
    if golden_image is None or capture_image is None:
        raise ValueError("golden and capture images are required")
    aspect_ratio = golden_image.shape[1] / golden_image.shape[0]
    if aspect_ratio >= 1:
        output_width = maximum_dimension
        output_height = max(2, round(maximum_dimension / aspect_ratio))
    else:
        output_height = maximum_dimension
        output_width = max(2, round(maximum_dimension * aspect_ratio))
    output_size = (output_width, output_height)

    golden, golden_mask = _warp_to_board_plane(
        golden_image,
        golden_board_to_image_matrix,
        output_size,
    )
    capture, capture_mask = _warp_to_board_plane(
        capture_image,
        capture_board_to_image_matrix,
        output_size,
    )
    overlap = cv2.bitwise_and(golden_mask, capture_mask)
    overlap_fraction = float(np.mean(overlap > 0))
    if overlap_fraction < 0.2:
        raise ValueError("reviewed registrations do not share enough board coverage")

    golden_gray = _normalized_grayscale(golden, overlap)
    capture_gray = _normalized_grayscale(capture, overlap)
    difference = cv2.absdiff(golden_gray, capture_gray)
    difference[overlap == 0] = 0
    valid_difference = difference[overlap > 0]
    threshold = max(24.0, float(np.percentile(valid_difference, 96)))
    binary = np.where((difference >= threshold) & (overlap > 0), 255, 0).astype(np.uint8)
    kernel = np.ones((7, 7), dtype=np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    board_area = output_width * output_height
    candidates = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        area_fraction = area / board_area
        if area_fraction < 0.0004:
            continue
        x, y, width, height = cv2.boundingRect(contour)
        region_mask = np.zeros_like(binary)
        cv2.drawContours(region_mask, [contour], -1, 255, -1)
        values = difference[region_mask > 0]
        candidates.append(
            {
                "candidate_id": f"candidate_{len(candidates) + 1:03d}",
                "source": "model_candidate",
                "review_status": "pending",
                "board_bbox": [
                    x / output_width,
                    y / output_height,
                    (x + width) / output_width,
                    (y + height) / output_height,
                ],
                "area_fraction": area_fraction,
                "mean_difference": float(np.mean(values)) if values.size else 0,
                "maximum_difference": int(np.max(values)) if values.size else 0,
            }
        )
    candidates.sort(
        key=lambda candidate: (
            -candidate["area_fraction"],
            candidate["board_bbox"][1],
            candidate["board_bbox"][0],
        )
    )
    for index, candidate in enumerate(candidates[:50], start=1):
        candidate["candidate_id"] = f"candidate_{index:03d}"
    candidates = candidates[:50]

    color_map = cv2.applyColorMap(difference, cv2.COLORMAP_TURBO)
    heatmap = cv2.addWeighted(capture, 0.58, color_map, 0.42, 0)
    heatmap[overlap == 0] = 0
    for candidate in candidates:
        left, top, right, bottom = candidate["board_bbox"]
        cv2.rectangle(
            heatmap,
            (round(left * output_width), round(top * output_height)),
            (round(right * output_width), round(bottom * output_height)),
            (255, 255, 255),
            2,
        )
    ok, encoded = cv2.imencode(".png", heatmap)
    if not ok:
        raise RuntimeError("unable to encode difference heatmap")

    result = {
        "schema_version": "VISUAL-QC-DIFFERENCE-CANDIDATES-V1",
        "status": "candidate_review_required",
        "source": "model_candidate",
        "requires_human_review": True,
        "automatic_repair_action": False,
        "evidence": {
            "overlap_fraction": overlap_fraction,
            "difference_threshold": threshold,
            "output_width": output_width,
            "output_height": output_height,
        },
        "candidates": candidates,
    }
    return result, encoded.tobytes()
