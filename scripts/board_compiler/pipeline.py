import json
import os
from collections import Counter
from pathlib import Path

from PIL import Image

from scripts.board_compiler.compiler import compile_designators
from scripts.board_compiler.outline import extract_board_outline
from scripts.board_compiler.pdf_primitives import extract_form_primitives
from scripts.build_board_atlas_assets import (
    remove_connected_page_background,
    render_pdf_pages,
    source_crop_box,
)


def compile_side(root, profile, side, *, primitives=None, outline=None):
    source = root / profile["point_map_source"]
    texture = root / side["engineering_texture"]
    primitives = primitives or extract_form_primitives(source, side["source_pdf_page"])
    outline = outline or extract_board_outline(texture)
    components = compile_designators(
        primitives["labels"],
        primitives["rectangles"],
        primitives["visible_bounds"],
        component_prefix=f"{profile['component_prefix']}-P{side['source_pdf_page']}",
    )
    required = set(side.get("required_designators", []))
    recovered = {item["designator"] for item in components} & required
    missing = sorted(required - recovered)
    confidence_counts = Counter(
        item["footprint"]["confidence"] for item in components if "footprint" in item
    )
    return {
        "compiler_id": "BOARD-COMPILER-PYPDF-V2",
        "profile_id": profile["profile_id"],
        "board_id": profile["board_id"],
        "side_id": side["side_id"],
        "coordinate_system": "normalized_form_xobject",
        "source": {
            "path": profile["point_map_source"],
            "page": side["source_pdf_page"],
            "form_xobject": primitives["form_name"],
            "bounds": primitives["bounds"],
            "visible_bounds": primitives["visible_bounds"],
        },
        "audit": {
            "decoded_text_objects": len(primitives["labels"]),
            "vector_rectangles": len(primitives["rectangles"]),
            "accepted_designators": len(components),
            "candidate_footprints": sum("footprint" in item for item in components),
            "footprint_confidence": dict(sorted(confidence_counts.items())),
            "required_designators": sorted(required),
            "recovered_required_designators": sorted(recovered),
            "missing_required_designators": missing,
            "required_recovery_complete": not missing,
            "outline_points": len(outline["outline"]),
            "outline_mask_area_ratio": outline["mask_area_ratio"],
        },
        "board_outline": outline["outline"],
        "board_outline_source": {
            "image": side["engineering_texture"],
            "method": "engineering-mark closing, largest component, hole fill, contour simplification",
            "image_size": outline["image_size"],
        },
        "accuracy_boundary": "Designators are decoded from the embedded PDF CMap. Footprints are provisional nearest-vector candidates until geometry pairing is reviewed.",
        "components": components,
    }


def build_side_manifest(profile):
    return {
        "manifest_id": f"{profile['component_prefix']}-BOARD-SIDES-V1",
        "profile_id": profile["profile_id"],
        "board_id": profile["board_id"],
        "default_side_id": profile["default_side_id"],
        "sides": [
            {
                "side_id": side["side_id"],
                "label": side["label"],
                "source_pdf_page": side["source_pdf_page"],
                "engineering_texture": side["engineering_texture"],
                "compiled_data": side["compiled_data"],
            }
            for side in profile["sides"]
        ],
    }


def render_profile_textures(root, profile, sides=None):
    selected = sides or profile["sides"]
    source = root / profile["point_map_source"]
    temporary = root / ".local" / "board-atlas-build" / profile["profile_id"]
    rendered = render_pdf_pages(source, temporary, "main-point-map")
    built = []
    for side in selected:
        page_index = side["source_pdf_page"] - 1
        if page_index >= len(rendered):
            raise ValueError(f"{side['side_id']} source page is outside the point-map PDF")
        target = root / side["engineering_texture"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(rendered[page_index]).convert("RGBA") as image:
            cropped = image.crop(source_crop_box(image, side))
            cutout = remove_connected_page_background(cropped)
            cutout.save(target, format="PNG", optimize=True)
        built.append(target)
    return built


def _stage_json_outputs(root, payloads):
    staged = []
    try:
        for relative_path, payload in payloads.items():
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            staged.append((temporary, target))
        for temporary, target in staged:
            os.replace(temporary, target)
    finally:
        for temporary, _target in staged:
            if temporary.exists():
                temporary.unlink()


def compile_geometry(
    root,
    profile,
    *,
    side_id=None,
    render_textures=True,
    primitive_extractor=extract_form_primitives,
    outline_extractor=extract_board_outline,
):
    selected = [side for side in profile["sides"] if side_id is None or side["side_id"] == side_id]
    if not selected:
        raise ValueError(f"Unknown side_id for {profile['profile_id']}: {side_id}")
    if render_textures:
        render_profile_textures(root, profile, selected)

    payloads = {}
    compiled = []
    source = root / profile["point_map_source"]
    for side in selected:
        primitives = primitive_extractor(source, side["source_pdf_page"])
        outline = outline_extractor(root / side["engineering_texture"])
        result = compile_side(root, profile, side, primitives=primitives, outline=outline)
        if not result["audit"]["required_recovery_complete"]:
            missing = ", ".join(result["audit"]["missing_required_designators"])
            raise ValueError(f"{side['side_id']} is missing required designators: {missing}")
        payloads[side["compiled_data"]] = result
        compiled.append(result)
    payloads[profile["side_manifest_output"]] = build_side_manifest(profile)
    _stage_json_outputs(root, payloads)
    return compiled
