import json
import os
from collections import Counter
from pathlib import Path

from PIL import Image

from scripts.board_compiler.compiler import compile_designators
from scripts.board_compiler.outline import extract_board_outline
from scripts.board_compiler.pdf_primitives import extract_form_primitives
from scripts.board_compiler.schematic import extract_schematic_pages, index_component_pages
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


def build_schematic_payload(profile, board_designators, pages, page_sizes):
    reviewed = set(profile.get("reviewed_designators", []))
    indexed = index_component_pages(pages, set(board_designators) | reviewed)
    components = {}
    for designator, occurrences in indexed.items():
        if not occurrences:
            continue
        normalized = []
        for occurrence in occurrences:
            size = page_sizes[occurrence["page"]]
            normalized.append({
                **occurrence,
                "text_origin": {
                    "x": round(occurrence["x"] / size["width"], 6),
                    "y": round(1 - occurrence["y"] / size["height"], 6),
                },
                "source_status": "decoded_pdf_text_run",
            })
        components[designator] = normalized

    page_counts = Counter(
        occurrence["page"]
        for occurrences in components.values()
        for occurrence in occurrences
    )
    recovered = set(components) & reviewed
    missing = sorted(reviewed - recovered)
    linked_board_designators = set(components) & set(board_designators)
    return {
        "compiler_id": "SCHEMATIC-COMPILER-PYPDF-V2",
        "profile_id": profile["profile_id"],
        "board_id": profile["board_id"],
        "source": {
            "path": profile["schematic_source"],
            "pages": len(pages),
        },
        "audit": {
            "board_designators": len(board_designators),
            "linked_designators": len(linked_board_designators),
            "unlinked_designators": len(set(board_designators) - linked_board_designators),
            "schematic_occurrences": sum(len(occurrences) for occurrences in components.values()),
            "page_occurrences": {str(page): count for page, count in sorted(page_counts.items())},
            "reviewed_designators": sorted(reviewed),
            "recovered_reviewed_designators": sorted(recovered),
            "missing_reviewed_designators": missing,
            "reviewed_recovery_complete": not missing,
            "standalone_match_only": True,
            "quality_gate_complete": not missing,
        },
        "accuracy_boundary": "Only standalone exact designator text runs are linked. Coordinates are normalized PDF text origins, not symbol centers. Embedded note references and merged runs are excluded, and electrical net connectivity is not inferred.",
        "components": components,
    }


def compile_schematic(
    root,
    profile,
    *,
    pages=None,
    page_sizes=None,
    board_designators=None,
    preview_builder=None,
    publish=True,
):
    if board_designators is None:
        board_designators = set()
        schematic_side_id = profile.get("schematic_geometry_side_id", profile["default_side_id"])
        side = next(item for item in profile["sides"] if item["side_id"] == schematic_side_id)
        path = root / side["compiled_data"]
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("board_id") != profile["board_id"]:
            raise ValueError(f"{side['side_id']} geometry board_id does not match the profile")
        board_designators.update(component["designator"] for component in data["components"])
    if pages is None or page_sizes is None:
        pages, page_sizes = extract_schematic_pages(root / profile["schematic_source"])

    payload = build_schematic_payload(profile, board_designators, pages, page_sizes)
    if not payload["audit"]["reviewed_recovery_complete"]:
        missing = ", ".join(payload["audit"]["missing_reviewed_designators"])
        raise ValueError(f"schematic is missing reviewed designators: {missing}")
    if preview_builder:
        preview_builder(payload["components"])
    if publish:
        _stage_json_outputs(root, {profile["schematic_output"]: payload})
    return payload
