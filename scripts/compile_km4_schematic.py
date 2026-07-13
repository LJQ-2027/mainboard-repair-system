import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.board_compiler.schematic import extract_schematic_pages, index_component_pages


REVIEWED_DESIGNATORS = {"U2001", "U4000", "X2100", "U0600", "J6101", "VBAT1", "VBUS1"}


def main():
    source = ROOT / "source-materials/manufacturing-center/top20-model-board-assets/2026-07-02-inhouse-top20/packages/KM4-F151/F151_MAIN_PCB_1_维修原理图_V1.2_20250310.pdf"
    board_path = ROOT / "knowledge-base/km4-board-compiled.json"
    output = ROOT / "knowledge-base/km4-schematic-compiled.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    designators = {component["designator"] for component in board["components"]}
    pages, page_sizes = extract_schematic_pages(source)
    indexed = index_component_pages(pages, designators)

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

    page_counts = Counter(occurrence["page"] for occurrences in components.values() for occurrence in occurrences)
    recovered = set(components) & REVIEWED_DESIGNATORS
    quality_gate_complete = recovered == REVIEWED_DESIGNATORS and len(components) >= 650
    payload = {
        "compiler_id": "SCHEMATIC-COMPILER-PYPDF-V1",
        "board_id": board["board_id"],
        "source": {
            "path": source.relative_to(ROOT).as_posix(),
            "pages": len(pages),
        },
        "audit": {
            "board_designators": len(designators),
            "linked_designators": len(components),
            "unlinked_designators": len(designators - set(components)),
            "schematic_occurrences": sum(len(occurrences) for occurrences in components.values()),
            "page_occurrences": {str(page): count for page, count in sorted(page_counts.items())},
            "reviewed_designators": sorted(REVIEWED_DESIGNATORS),
            "recovered_reviewed_designators": sorted(recovered),
            "reviewed_recovery_complete": recovered == REVIEWED_DESIGNATORS,
            "standalone_match_only": True,
            "quality_gate_complete": quality_gate_complete,
        },
        "accuracy_boundary": "Only standalone exact designator text runs are linked. Coordinates are normalized PDF text origins, not symbol centers. Embedded note references and merged runs are excluded, and electrical net connectivity is not inferred.",
        "components": components,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["audit"], indent=2, ensure_ascii=False))
    return 0 if quality_gate_complete else 1


if __name__ == "__main__":
    sys.exit(main())
