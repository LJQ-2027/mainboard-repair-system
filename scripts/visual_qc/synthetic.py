from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib

import cv2
import numpy as np


@dataclass(frozen=True)
class SyntheticTransformConfig:
    rotation_degrees: float = 5.0
    perspective_jitter: float = 0.05
    crop_fraction: float = 0.02
    brightness_delta: float = -10.0
    contrast: float = 1.0
    shadow_strength: float = 0.1
    max_dimension: int | None = None


def _resize_for_limit(image: np.ndarray, max_dimension: int | None) -> np.ndarray:
    if not max_dimension or max(image.shape[:2]) <= max_dimension:
        return image.copy()
    scale = max_dimension / max(image.shape[:2])
    width = max(2, round(image.shape[1] * scale))
    height = max(2, round(image.shape[0] * scale))
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


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
    source_width, source_height = source_size
    target_width, target_height = target_size
    source_scale = _normalization_matrix(source_width, source_height)
    target_scale = _normalization_matrix(target_width, target_height)
    normalized = np.linalg.inv(target_scale) @ matrix @ source_scale
    return normalized / normalized[2, 2]


def _target_corners(
    width: int,
    height: int,
    config: SyntheticTransformConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    corners = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float64,
    )
    center = np.array([(width - 1) / 2, (height - 1) / 2], dtype=np.float64)
    angle = np.deg2rad(config.rotation_degrees)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]],
        dtype=np.float64,
    )
    crop_scale = 1 + 2 * max(0.0, config.crop_fraction)
    transformed = ((corners - center) * crop_scale) @ rotation.T + center
    jitter = max(0.0, config.perspective_jitter) * min(width, height)
    if jitter:
        transformed += rng.uniform(-jitter, jitter, size=(4, 2))
    return transformed.astype(np.float32)


def _apply_lighting(
    image: np.ndarray,
    config: SyntheticTransformConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    adjusted = image.astype(np.float32) * config.contrast + config.brightness_delta
    strength = float(np.clip(config.shadow_strength, 0, 0.8))
    if strength:
        height, width = image.shape[:2]
        x = np.linspace(-1, 1, width, dtype=np.float32)
        y = np.linspace(-1, 1, height, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)
        angle = rng.uniform(0, np.pi * 2)
        gradient = (np.cos(angle) * xx + np.sin(angle) * yy + 1) / 2
        shadow = 1 - strength * np.clip(gradient, 0, 1)
        adjusted *= shadow[..., None]
    return np.clip(adjusted, 0, 255).astype(np.uint8)


def generate_synthetic_capture(
    reference: np.ndarray,
    config: SyntheticTransformConfig | None = None,
    *,
    seed: int,
) -> tuple[np.ndarray, dict]:
    if reference is None or reference.size == 0:
        raise ValueError("reference image is required")
    if reference.ndim not in (2, 3):
        raise ValueError("reference image must be grayscale or color")

    config = config or SyntheticTransformConfig()
    rng = np.random.default_rng(seed)
    source_hash = hashlib.sha256(reference.tobytes()).hexdigest()
    prepared = _resize_for_limit(reference, config.max_dimension)
    if prepared.ndim == 2:
        prepared = cv2.cvtColor(prepared, cv2.COLOR_GRAY2BGR)

    height, width = prepared.shape[:2]
    source_corners = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    destination_corners = _target_corners(width, height, config, rng)
    pixel_matrix = cv2.getPerspectiveTransform(source_corners, destination_corners)
    border = tuple(int(value) for value in np.median(prepared.reshape(-1, 3), axis=0))
    warped = cv2.warpPerspective(
        prepared,
        pixel_matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )
    capture = _apply_lighting(warped, config, rng)
    normalized_matrix = _pixel_to_normalized_homography(
        pixel_matrix,
        (width, height),
        (width, height),
    )

    manifest = {
        "schema_version": "VISUAL-QC-SYNTHETIC-PROXY-V1",
        "evidence_role": "synthetic_proxy",
        "seed": seed,
        "source_sha256": source_hash,
        "source_size": {"width": int(reference.shape[1]), "height": int(reference.shape[0])},
        "output_size": {"width": width, "height": height},
        "parameters": asdict(config),
        "expected_board_to_image_matrix": normalized_matrix.reshape(-1).tolist(),
        "destination_corners": [
            {"x": float(x / (width - 1)), "y": float(y / (height - 1))}
            for x, y in destination_corners
        ],
    }
    return capture, manifest
