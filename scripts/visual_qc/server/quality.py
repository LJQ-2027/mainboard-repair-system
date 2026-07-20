from __future__ import annotations

import numpy as np


def analyze_image_quality(image: np.ndarray) -> dict:
    if image is None or image.size == 0:
        raise ValueError("image is required")
    if image.ndim == 2:
        gray = image.astype(np.float32)
    elif image.ndim == 3 and image.shape[2] in {3, 4}:
        color = image[:, :, :3].astype(np.float32)
        gray = 0.0722 * color[:, :, 0] + 0.7152 * color[:, :, 1] + 0.2126 * color[:, :, 2]
    else:
        raise ValueError("image must be grayscale, BGR, or BGRA")

    height, width = gray.shape
    mean_luminance = float(np.mean(gray))
    contrast = float(np.std(gray))
    shadow_clipping = float(np.mean(gray <= 8))
    highlight_clipping = float(np.mean(gray >= 247))
    horizontal = np.abs(np.diff(gray, axis=1))
    vertical = np.abs(np.diff(gray, axis=0))
    gradient_count = horizontal.size + vertical.size
    sharpness = float(
        (float(np.sum(horizontal)) + float(np.sum(vertical))) / gradient_count
        if gradient_count
        else 0
    )
    metrics = {
        "width": width,
        "height": height,
        "megapixels": width * height / 1_000_000,
        "mean_luminance": mean_luminance,
        "contrast": contrast,
        "shadow_clipping": shadow_clipping,
        "highlight_clipping": highlight_clipping,
        "sharpness": sharpness,
    }

    score = 100
    guidance = []
    if min(width, height) < 600 or metrics["megapixels"] < 0.5:
        score -= 30
        guidance.append(
            {
                "code": "low_resolution",
                "message": "Move closer and keep the complete board in frame.",
            }
        )
    if mean_luminance > 225 or highlight_clipping > 0.18:
        score -= 25
        guidance.append(
            {
                "code": "overexposed",
                "message": "Reduce direct light or change the angle to remove glare.",
            }
        )
    if mean_luminance < 35 or shadow_clipping > 0.22:
        score -= 25
        guidance.append(
            {
                "code": "underexposed",
                "message": "Add diffuse light so dark board regions remain visible.",
            }
        )
    if contrast < 22:
        score -= 20
        guidance.append(
            {
                "code": "low_contrast",
                "message": "Use a plain contrasting background and more even light.",
            }
        )
    if sharpness < 7:
        score -= 30
        guidance.append(
            {
                "code": "blurred",
                "message": "Hold the camera steady and tap the board to focus.",
            }
        )
    elif sharpness < 14:
        score -= 12
        guidance.append(
            {
                "code": "soft_focus",
                "message": "Retake closer with firmer focus for better matching.",
            }
        )

    score = max(0, min(100, round(score)))
    status = "good" if score >= 80 else "usable" if score >= 55 else "retake"
    if not guidance:
        guidance.append(
            {
                "code": "ready",
                "message": "Image quality is suitable for internal reference matching.",
            }
        )
    return {
        "schema_version": "VISUAL-QC-IMAGE-QUALITY-V1",
        "score": score,
        "status": status,
        "metrics": metrics,
        "guidance": guidance,
    }
