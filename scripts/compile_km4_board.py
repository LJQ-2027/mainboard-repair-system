import json
import sys
import argparse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.board_compiler.compiler import compile_designators
from scripts.board_compiler.outline import extract_board_outline
from scripts.board_compiler.pdf_primitives import extract_form_primitives


BOARD_ID = "BOARD-KM4-F151-MAIN-V1.2"
SOURCE_PATH = "source-materials/manufacturing-center/top20-model-board-assets/2026-07-02-inhouse-top20/packages/KM4-F151/F151_MAIN_PCB_V1.2_位号图.pdf"
REQUIRED_DESIGNATORS = {"U2001", "U4000", "X2100", "U0600", "J6101", "VBAT1", "VBUS1"}
SIDE_CONFIGS = {
    "main_page_1": {
        "page": 1,
        "label": "第1面",
        "image": "assets/board-atlas/km4-f151/main-point-map-page-1.png",
        "output": "knowledge-base/km4-board-compiled-page-1.json",
        "required_designators": set(),
    },
    "main_page_2": {
        "page": 2,
        "label": "第2面",
        "image": "assets/board-atlas/km4-f151/main-point-map-page-2.png",
        "output": "knowledge-base/km4-board-compiled.json",
        "required_designators": REQUIRED_DESIGNATORS,
    },
}


def compile_side(root, side_id, config):
    source = root / SOURCE_PATH
    point_map_image = root / config["image"]
    primitives = extract_form_primitives(source, config["page"])
    outline = extract_board_outline(point_map_image)
    components = compile_designators(
        primitives["labels"],
        primitives["rectangles"],
        primitives["visible_bounds"],
        component_prefix=f"KM4-F151-P{config['page']}",
    )
    required = config["required_designators"]
    recovered = {item["designator"] for item in components} & required
    footprint_count = sum("footprint" in item for item in components)
    confidence_counts = Counter(item["footprint"]["confidence"] for item in components if "footprint" in item)
    return {
        "compiler_id": "BOARD-COMPILER-PYPDF-V1",
        "board_id": BOARD_ID,
        "side_id": side_id,
        "coordinate_system": "normalized_form_xobject",
        "source": {
            "path": SOURCE_PATH,
            "page": config["page"],
            "form_xobject": primitives["form_name"],
            "bounds": primitives["bounds"],
            "visible_bounds": primitives["visible_bounds"],
        },
        "audit": {
            "decoded_text_objects": len(primitives["labels"]),
            "vector_rectangles": len(primitives["rectangles"]),
            "accepted_designators": len(components),
            "candidate_footprints": footprint_count,
            "footprint_confidence": dict(sorted(confidence_counts.items())),
            "required_designators": sorted(required),
            "recovered_required_designators": sorted(recovered),
            "required_recovery_complete": recovered == required,
            "outline_points": len(outline["outline"]),
            "outline_mask_area_ratio": outline["mask_area_ratio"],
        },
        "board_outline": outline["outline"],
        "board_outline_source": {
            "image": config["image"],
            "method": "engineering-mark closing, largest component, hole fill, contour simplification",
            "image_size": outline["image_size"],
        },
        "accuracy_boundary": "Designators are decoded from the embedded PDF CMap. Footprints are provisional nearest-vector candidates until geometry pairing is reviewed.",
        "components": components,
    }


def build_side_manifest(root=ROOT):
    del root
    return {
        "manifest_id": "KM4-F151-BOARD-SIDES-V1",
        "board_id": BOARD_ID,
        "default_side_id": "main_page_2",
        "sides": [
            {
                "side_id": side_id,
                "label": config["label"],
                "source_pdf_page": config["page"],
                "engineering_texture": config["image"],
                "compiled_data": config["output"],
            }
            for side_id, config in SIDE_CONFIGS.items()
        ],
    }


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile KM4/F151 point-map sides")
    parser.add_argument("--side", choices=SIDE_CONFIGS, help="Compile only one side while refreshing the side manifest")
    args = parser.parse_args(argv)
    failed = False
    selected_sides = [args.side] if args.side else list(SIDE_CONFIGS)
    for side_id in selected_sides:
        config = SIDE_CONFIGS[side_id]
        payload = compile_side(ROOT, side_id, config)
        write_json(ROOT / config["output"], payload)
        print(json.dumps({"side_id": side_id, **payload["audit"]}, indent=2, ensure_ascii=False))
        if not payload["audit"]["required_recovery_complete"]:
            missing = set(config["required_designators"]) - set(payload["audit"]["recovered_required_designators"])
            print(f"Missing required designators on {side_id}: {sorted(missing)}", file=sys.stderr)
            failed = True
    write_json(ROOT / "knowledge-base/km4-board-sides.json", build_side_manifest(ROOT))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
