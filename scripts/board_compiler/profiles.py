import json
import re
from pathlib import Path


REGISTRY_PATH = Path("knowledge-base/board-compiler-profiles.json")
DESIGNATOR_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
MODEL_EVIDENCE_LEVELS = {
    "engineering_source",
    "photo_verified_shared_platform",
    "owner_confirmed_alias",
}


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


def _validate_coordinate_bounds(bounds, side_id):
    if bounds is None:
        return
    if (
        not isinstance(bounds, list)
        or len(bounds) != 4
        or any(
            not isinstance(value, (int, float)) or isinstance(value, bool)
            for value in bounds
        )
        or bounds[2] <= bounds[0]
        or bounds[3] <= bounds[1]
    ):
        raise ValueError(f"{side_id} coordinate_bounds must be [x0, y0, x1, y1]")


def validate_profile(root, profile):
    required_text = ("profile_id", "model", "board_id", "board_version", "component_prefix", "default_side_id")
    for field in required_text:
        if not isinstance(profile.get(field), str) or not profile[field].strip():
            raise ValueError(f"{field} is required")

    models = profile.get("models", [profile["model"]])
    if (
        not isinstance(models, list)
        or not models
        or any(not isinstance(model, str) or not model.strip() for model in models)
        or len(models) != len(set(models))
        or profile["model"] not in models
    ):
        raise ValueError("models must be unique nonempty sales models including model")
    model_evidence = profile.get("model_evidence")
    if model_evidence is not None and (
        not isinstance(model_evidence, dict)
        or set(model_evidence) != set(models)
        or any(level not in MODEL_EVIDENCE_LEVELS for level in model_evidence.values())
    ):
        raise ValueError("model_evidence must assign one supported level to every model")
    if profile.get("outline_method", "engineering_marks") not in ("engineering_marks", "alpha_silhouette"):
        raise ValueError("outline_method must be engineering_marks or alpha_silhouette")

    _repository_path(root, profile.get("point_map_source"), "point_map_source", must_exist=True)
    _repository_path(root, profile.get("schematic_source"), "schematic_source", must_exist=True)
    if profile.get("repair_guide_source") is not None:
        _repository_path(root, profile["repair_guide_source"], "repair_guide_source", must_exist=True)

    sides = profile.get("sides")
    if not isinstance(sides, list) or not sides:
        raise ValueError("sides must contain at least one board side")
    side_ids = [side.get("side_id") for side in sides]
    if any(not side_id for side_id in side_ids) or len(side_ids) != len(set(side_ids)):
        raise ValueError("profile contains a missing or duplicate side_id")
    if profile["default_side_id"] not in side_ids:
        raise ValueError("default_side_id must resolve to a declared side")
    schematic_side_id = profile.get("schematic_geometry_side_id", profile["default_side_id"])
    if schematic_side_id not in side_ids:
        raise ValueError("schematic_geometry_side_id must resolve to a declared side")

    outputs = []
    source_pages = []
    component_pages = []
    for side in sides:
        side_id = side["side_id"]
        if not isinstance(side.get("source_pdf_page"), int) or isinstance(side["source_pdf_page"], bool) or side["source_pdf_page"] < 1:
            raise ValueError(f"{side_id} source_pdf_page must be a positive integer")
        source_path = side.get("point_map_source", profile["point_map_source"])
        _repository_path(root, source_path, f"{side_id}.point_map_source", must_exist=True)
        source_pages.append((source_path, side["source_pdf_page"]))
        component_page = side.get("component_page", side["source_pdf_page"])
        if not isinstance(component_page, int) or isinstance(component_page, bool) or component_page < 1:
            raise ValueError(f"{side_id} component_page must be a positive integer")
        component_pages.append(component_page)
        _validate_crop(side.get("source_crop"), side_id)
        _validate_coordinate_bounds(side.get("coordinate_bounds"), side_id)
        for field in ("engineering_texture", "compiled_data"):
            _repository_path(root, side.get(field), f"{side_id}.{field}")
            outputs.append(side[field])

    if len(set(source_pages)) != len(source_pages):
        raise ValueError("profile contains a duplicate point-map source page")
    if len(set(component_pages)) != len(component_pages):
        raise ValueError("profile contains duplicate component_page values")

    for field in ("side_manifest_output", "schematic_output", "cross_source_output"):
        _repository_path(root, profile.get(field), field)
        outputs.append(profile[field])
    if len(outputs) != len(set(outputs)):
        raise ValueError("profile output paths must be unique")

    reviewed = profile.get("reviewed_designators", [])
    if not isinstance(reviewed, list) or any(not isinstance(item, str) or not DESIGNATOR_PATTERN.fullmatch(item) for item in reviewed):
        raise ValueError("reviewed_designators must contain uppercase standalone identities")
    schematic_reviewed = profile.get("schematic_reviewed_designators", reviewed)
    if not isinstance(schematic_reviewed, list) or any(not isinstance(item, str) or not DESIGNATOR_PATTERN.fullmatch(item) for item in schematic_reviewed):
        raise ValueError("schematic_reviewed_designators must contain uppercase standalone identities")
    if not set(schematic_reviewed).issubset(reviewed):
        raise ValueError("schematic_reviewed_designators must be a subset of reviewed_designators")
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
