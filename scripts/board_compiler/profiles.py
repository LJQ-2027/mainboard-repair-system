import json
import re
from pathlib import Path


REGISTRY_PATH = Path("knowledge-base/board-compiler-profiles.json")
DESIGNATOR_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _repository_path(root, value, field, *, must_exist=False):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a repository-relative path")
    root = root.resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{field} must stay inside the repository")
    if must_exist and not path.is_file():
        raise ValueError(f"{field} does not exist: {value}")
    return path


def _validate_crop(crop, side_id):
    if not isinstance(crop, dict) or set(crop) != {"x", "y", "width", "height"}:
        raise ValueError(f"{side_id} source_crop requires x, y, width, and height")
    values = [crop[key] for key in ("x", "y", "width", "height")]
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in values):
        raise ValueError(f"{side_id} source_crop values must be numeric")
    x, y, width, height = values
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValueError(f"{side_id} source_crop must be a positive normalized rectangle")


def validate_profile(root, profile):
    required_text = ("profile_id", "model", "board_id", "board_version", "component_prefix", "default_side_id")
    for field in required_text:
        if not isinstance(profile.get(field), str) or not profile[field].strip():
            raise ValueError(f"{field} is required")

    _repository_path(root, profile.get("point_map_source"), "point_map_source", must_exist=True)
    _repository_path(root, profile.get("schematic_source"), "schematic_source", must_exist=True)

    sides = profile.get("sides")
    if not isinstance(sides, list) or not sides:
        raise ValueError("sides must contain at least one board side")
    side_ids = [side.get("side_id") for side in sides]
    if any(not side_id for side_id in side_ids) or len(side_ids) != len(set(side_ids)):
        raise ValueError("profile contains a missing or duplicate side_id")
    if profile["default_side_id"] not in side_ids:
        raise ValueError("default_side_id must resolve to a declared side")

    outputs = []
    for side in sides:
        side_id = side["side_id"]
        if not isinstance(side.get("source_pdf_page"), int) or isinstance(side["source_pdf_page"], bool) or side["source_pdf_page"] < 1:
            raise ValueError(f"{side_id} source_pdf_page must be a positive integer")
        _validate_crop(side.get("source_crop"), side_id)
        for field in ("engineering_texture", "compiled_data"):
            _repository_path(root, side.get(field), f"{side_id}.{field}")
            outputs.append(side[field])

    if len({side["source_pdf_page"] for side in sides}) != len(sides):
        raise ValueError("profile contains duplicate source_pdf_page values")

    for field in ("side_manifest_output", "schematic_output", "cross_source_output"):
        _repository_path(root, profile.get(field), field)
        outputs.append(profile[field])
    if len(outputs) != len(set(outputs)):
        raise ValueError("profile output paths must be unique")

    reviewed = profile.get("reviewed_designators", [])
    if not isinstance(reviewed, list) or any(not isinstance(item, str) or not DESIGNATOR_PATTERN.fullmatch(item) for item in reviewed):
        raise ValueError("reviewed_designators must contain uppercase standalone identities")
    for side in sides:
        required = side.get("required_designators", [])
        if not isinstance(required, list) or any(not isinstance(item, str) or not DESIGNATOR_PATTERN.fullmatch(item) for item in required):
            raise ValueError(f"{side['side_id']} required_designators must contain uppercase standalone identities")
    return profile


def load_registry(root):
    path = root / REGISTRY_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles")
    if not isinstance(profiles, list):
        raise ValueError("board compiler registry requires a profiles list")
    profile_ids = [profile.get("profile_id") for profile in profiles]
    if any(not profile_id for profile_id in profile_ids) or len(profile_ids) != len(set(profile_ids)):
        raise ValueError("board compiler registry contains duplicate or missing profile_id")
    return payload


def load_profile(root, profile_id):
    registry = load_registry(root)
    profile = next((item for item in registry["profiles"] if item["profile_id"] == profile_id), None)
    if profile is None:
        raise ValueError(f"Unknown board profile: {profile_id}")
    return validate_profile(root, profile)
