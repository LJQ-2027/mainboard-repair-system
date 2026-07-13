import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.board_compiler.compiler import compile_designators
from scripts.board_compiler.outline import extract_board_outline
from scripts.board_compiler.pdf_primitives import extract_form_primitives


REQUIRED_DESIGNATORS = {"U2001", "U4000", "X2100", "U0600", "J6101", "VBAT1", "VBUS1"}


def main():
    root = ROOT
    source = root / "source-materials/manufacturing-center/top20-model-board-assets/2026-07-02-inhouse-top20/packages/KM4-F151/F151_MAIN_PCB_V1.2_位号图.pdf"
    output = root / "knowledge-base/km4-board-compiled.json"
    point_map_image = root / "assets/board-atlas/km4-f151/main-point-map-page-2.png"
    primitives = extract_form_primitives(source, 2)
    outline = extract_board_outline(point_map_image)
    components = compile_designators(primitives["labels"], primitives["rectangles"], primitives["visible_bounds"])
    recovered = {item["designator"] for item in components} & REQUIRED_DESIGNATORS
    footprint_count = sum("footprint" in item for item in components)
    confidence_counts = Counter(item["footprint"]["confidence"] for item in components if "footprint" in item)
    payload = {
        "compiler_id": "BOARD-COMPILER-PYPDF-V1",
        "board_id": "BOARD-KM4-F151-MAIN-V1.2",
        "side_id": "main_page_2",
        "coordinate_system": "normalized_form_xobject",
        "source": {
            "path": str(source.relative_to(root)).replace("\\", "/"),
            "page": 2,
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
            "required_designators": sorted(REQUIRED_DESIGNATORS),
            "recovered_required_designators": sorted(recovered),
            "required_recovery_complete": recovered == REQUIRED_DESIGNATORS,
            "outline_points": len(outline["outline"]),
            "outline_mask_area_ratio": outline["mask_area_ratio"],
        },
        "board_outline": outline["outline"],
        "board_outline_source": {
            "image": str(point_map_image.relative_to(root)).replace("\\", "/"),
            "method": "engineering-mark closing, largest component, hole fill, contour simplification",
            "image_size": outline["image_size"],
        },
        "accuracy_boundary": "Designators are decoded from the embedded PDF CMap. Footprints are provisional nearest-vector candidates until geometry pairing is reviewed.",
        "components": components,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["audit"], indent=2, ensure_ascii=False))
    if recovered != REQUIRED_DESIGNATORS:
        print(f"Missing required designators: {sorted(REQUIRED_DESIGNATORS - recovered)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
