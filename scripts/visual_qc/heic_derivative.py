from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import hashlib
from pathlib import Path
import tempfile
from typing import Any

from scripts.visual_qc.intake import (
    IntakeValidationError,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MIN_IMAGE_DIMENSION,
    _image_evidence,
)


HEIC_EXTENSIONS = frozenset({".heic", ".heif"})
HEIC_MIME_TYPE = "image/heic"
JPEG_QUALITY = 95
JPEG_SUBSAMPLING = 0


@dataclass(frozen=True)
class PreparedHeicDerivative:
    working_path: Path
    source_original: dict
    derivation: dict


def is_heic_path(path: Path) -> bool:
    return Path(path).suffix.lower() in HEIC_EXTENSIONS


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _decoder_modules():
    try:
        from PIL import Image, ImageOps, __version__ as pillow_version
        import pillow_heif
    except ImportError as exc:
        raise IntakeValidationError(
            "HEIC decoder dependency unavailable; install "
            "requirements-visual-qc-admin.txt"
        ) from exc
    return Image, ImageOps, pillow_version, pillow_heif


def _source_evidence(path: Path) -> tuple[dict, Any, dict]:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise IntakeValidationError(f"image file does not exist: {path}")
    if not is_heic_path(path):
        raise IntakeValidationError("HEIC source must use .heic or .heif extension")
    _, _, _, pillow_heif = _decoder_modules()
    try:
        content = path.read_bytes()
        if not content or len(content) > MAX_IMAGE_BYTES:
            raise IntakeValidationError(
                "HEIC byte size is outside supported limits"
            )
        if not pillow_heif.is_supported(content):
            raise IntakeValidationError("unsupported or invalid HEIC container")
        heif_file = pillow_heif.open_heif(content, convert_hdr_to_8bit=True)
        image = heif_file.to_pillow()
    except IntakeValidationError:
        raise
    except Exception as exc:
        raise IntakeValidationError(f"unable to decode HEIC primary image: {exc}") from exc
    if heif_file.info.get("primary") is not True:
        raise IntakeValidationError("HEIC source does not expose a primary image")
    if image.width < 1 or image.height < 1:
        raise IntakeValidationError("HEIC primary image has invalid dimensions")
    if (
        min(image.width, image.height) < MIN_IMAGE_DIMENSION
        or max(image.width, image.height) > MAX_IMAGE_DIMENSION
    ):
        raise IntakeValidationError(
            "HEIC dimensions are outside supported limits"
        )
    evidence = {
        "original_filename": path.name,
        "mime_type": HEIC_MIME_TYPE,
        "byte_size": len(content),
        "sha256": _sha256(content),
    }
    return evidence, image, heif_file.info


def inspect_heic_source(path: Path) -> dict:
    evidence, _, _ = _source_evidence(path)
    return evidence


def prepare_heic_derivative(
    source_path: Path,
    output_directory: Path,
    *,
    output_name: str,
) -> PreparedHeicDerivative:
    source_path = Path(source_path).expanduser().resolve()
    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    Image, ImageOps, pillow_version, pillow_heif = _decoder_modules()
    source, image, heif_info = _source_evidence(source_path)
    orientation = image.getexif().get(274, 1)
    oriented = ImageOps.exif_transpose(image)
    if oriented.mode in {"RGBA", "LA"}:
        rgba = oriented.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        working = background.convert("RGB")
    else:
        working = oriented.convert("RGB")
    icc_profile = heif_info.get("icc_profile")
    output = BytesIO()
    save_options = {
        "quality": JPEG_QUALITY,
        "subsampling": JPEG_SUBSAMPLING,
        "optimize": False,
        "progressive": False,
        "exif": b"",
    }
    if isinstance(icc_profile, bytes) and icc_profile:
        save_options["icc_profile"] = icc_profile
    working.save(output, format="JPEG", **save_options)
    output_path = output_directory / f"{output_name}.jpg"
    output_path.write_bytes(output.getvalue())
    working_evidence = _image_evidence(output_path)
    if working_evidence["mime_type"] != "image/jpeg":
        raise IntakeValidationError("HEIC derivative is not a valid JPEG")
    derivation = {
        "operation": "heic_primary_image_to_oriented_rgb_jpeg",
        "input_sha256": source["sha256"],
        "output_sha256": working_evidence["sha256"],
        "decoder": {
            "name": "pillow-heif",
            "version": pillow_heif.__version__,
            "libheif_version": pillow_heif.libheif_version(),
        },
        "pillow_version": pillow_version,
        "primary_image_selected": True,
        "source_bit_depth": heif_info.get("bit_depth"),
        "exif_orientation": int(orientation or 1),
        "exif_orientation_applied": int(orientation or 1) not in {0, 1},
        "metadata": {
            "exif": "removed",
            "icc_profile_preserved": bool(icc_profile),
        },
        "output": {
            "mime_type": "image/jpeg",
            "quality": JPEG_QUALITY,
            "subsampling": JPEG_SUBSAMPLING,
            "optimize": False,
            "progressive": False,
            "color_mode": "RGB",
        },
    }
    return PreparedHeicDerivative(
        working_path=output_path,
        source_original=source,
        derivation=derivation,
    )


def temporary_heic_derivative(
    source_path: Path, *, output_name: str
) -> tuple[tempfile.TemporaryDirectory, PreparedHeicDerivative]:
    temporary = tempfile.TemporaryDirectory()
    try:
        prepared = prepare_heic_derivative(
            source_path, Path(temporary.name), output_name=output_name
        )
    except Exception:
        temporary.cleanup()
        raise
    return temporary, prepared
