import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "H897-PHOTO-NAVIGATION-V1"
SOURCE_SCOPE = "owner_authorized_feishu_case_library"
SUPPORTED_TRANSFORMS = {"none", "rotate_90_counterclockwise"}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dimensions(image):
    return {"width": image.width, "height": image.height}


def _discover_sources(source_root, hashes):
    remaining = set(hashes)
    matches = {}
    for path in sorted(Path(source_root).rglob("*")):
        if not path.is_file():
            continue
        digest = _sha256(path)
        if digest in remaining:
            matches[digest] = path
            remaining.remove(digest)
            if not remaining:
                break
    if remaining:
        raise ValueError(f"source hash not found: {', '.join(sorted(remaining))}")
    return matches


def _validate_reviewed_images(images):
    hashes = [item.get("sha256") for item in images]
    sides = [item.get("side_id") for item in images]
    if len(images) != 2 or len(set(hashes)) != 2 or any(not value for value in hashes):
        raise ValueError("H897 photo navigation requires two unique source hashes")
    if sorted(sides) != ["main_page_1", "main_page_2"]:
        raise ValueError("H897 photo navigation requires one photo per board side")
    for item in images:
        review = item.get("registration_review", {})
        matrix = review.get("board_to_image_matrix", [])
        if (
            item.get("registration_status") != "reviewed_manual_registration"
            or review.get("review_status") != "reviewed"
            or len(matrix) != 9
            or any(not isinstance(value, (int, float)) for value in matrix)
        ):
            raise ValueError(f"reviewed registration required for {item.get('sha256')}")
        if item.get("registration_transform") not in SUPPORTED_TRANSFORMS:
            raise ValueError(f"unsupported registration transform for {item.get('sha256')}")


def _normalized_image(path, reviewed):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        if _dimensions(image) != reviewed["source_dimensions"]:
            raise ValueError(
                f"source dimensions do not match reviewed registration for {reviewed['sha256']}"
            )
        image = image.convert("RGB")
        if reviewed["registration_transform"] == "rotate_90_counterclockwise":
            image = image.transpose(Image.Transpose.ROTATE_90)
        if _dimensions(image) != reviewed["registration_dimensions"]:
            raise ValueError(
                f"registration dimensions do not match reviewed registration for {reviewed['sha256']}"
            )
        return Image.frombytes("RGB", image.size, image.tobytes())


def build_navigation_manifest(
    source_root,
    derivative_root,
    reviewed_manifest,
    *,
    asset_prefix="assets/board-atlas/h897/physical",
    max_dimension=2000,
):
    images = list(reviewed_manifest.get("images", []))
    _validate_reviewed_images(images)
    source_matches = _discover_sources(source_root, [item["sha256"] for item in images])
    derivative_root = Path(derivative_root)
    derivative_root.mkdir(parents=True, exist_ok=True)
    photos = []

    for reviewed in sorted(images, key=lambda item: item["side_id"]):
        source_hash = reviewed["sha256"]
        image = _normalized_image(source_matches[source_hash], reviewed)
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        filename = f"{reviewed['side_id'].replace('_', '-')}-{source_hash[:12]}.webp"
        output = derivative_root / filename
        image.save(output, format="WEBP", quality=88, method=6)
        side_number = "1" if reviewed["side_id"] == "main_page_1" else "2"
        photos.append(
            {
                "photo_id": f"H897-{reviewed['side_id'].upper()}-{source_hash[:12].upper()}",
                "label": f"第{side_number}面实拍",
                "side_id": reviewed["side_id"],
                "source_sha256": source_hash,
                "derivative_sha256": _sha256(output),
                "asset_path": f"{asset_prefix.rstrip('/')}/{filename}",
                "source_scope": SOURCE_SCOPE,
                "source_annotation_present": reviewed["source_annotation_present"],
                "source_annotation_role": reviewed["source_annotation_role"],
                "capture_geometry_id": reviewed.get("capture_geometry_id"),
                "registration_dimensions": reviewed["registration_dimensions"],
                "derivative_dimensions": _dimensions(image),
                "board_to_image_matrix": reviewed["registration_review"]["board_to_image_matrix"],
                "registration_review_status": "reviewed",
                "field_accuracy_claim_allowed": False,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "board_key": reviewed_manifest["board_key"],
        "board_id": reviewed_manifest["board_id"],
        "physical_board_revision": reviewed_manifest["physical_board_revision"],
        "engineering_board_revision": reviewed_manifest["engineering_board_revision"],
        "reference_mode": "reviewed_physical_photo_navigation",
        "photos": photos,
        "accuracy_boundary": (
            "这些与原始 SHA-256 精确绑定的派生图仅支持经审核的板级坐标导航；"
            "不能作为 Golden Sample、缺陷标签或维修因果证据。"
        ),
    }


def validate_navigation_manifest(manifest, site_root):
    errors = []
    photos = manifest.get("photos", [])
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("photo navigation schema version is unsupported")
    hashes = [item.get("source_sha256") for item in photos]
    if len(photos) != 2 or len(set(hashes)) != 2:
        errors.append("H897 photo navigation requires two unique source hashes")
    if sorted(item.get("side_id") for item in photos) != ["main_page_1", "main_page_2"]:
        errors.append("H897 photo navigation side coverage is invalid")
    for item in photos:
        asset_path = item.get("asset_path")
        asset = Path(site_root) / asset_path if asset_path else None
        if not asset or not asset.is_file():
            errors.append(f"photo navigation asset does not resolve: {item.get('photo_id')}")
            continue
        if _sha256(asset) != item.get("derivative_sha256"):
            errors.append(f"photo navigation asset hash mismatch: {item.get('photo_id')}")
        if len(item.get("board_to_image_matrix", [])) != 9:
            errors.append(f"photo navigation matrix is invalid: {item.get('photo_id')}")
        if item.get("registration_review_status") != "reviewed":
            errors.append(f"photo navigation review is invalid: {item.get('photo_id')}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument(
        "--output-root", type=Path, default=ROOT / "assets/board-atlas/h897/physical"
    )
    parser.add_argument(
        "--manifest", type=Path, default=ROOT / "knowledge-base/h897-photo-navigation.json"
    )
    args = parser.parse_args()
    reviewed = json.loads(
        (ROOT / "knowledge-base/h897-physical-registration-reviewed.json").read_text(
            encoding="utf-8"
        )
    )
    payload = build_navigation_manifest(args.source_root, args.output_root, reviewed)
    args.manifest.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"photos": len(payload["photos"]), "manifest": str(args.manifest)}))


if __name__ == "__main__":
    main()
