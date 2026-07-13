import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.board_compiler.schematic import extract_schematic_pages, index_component_pages
from scripts.board_compiler.schematic import crop_box_from_origin

from PIL import Image


REVIEWED_DESIGNATORS = {"U2001", "U4000", "X2100", "U0600", "J6101", "VBAT1", "VBUS1"}
POPPLER_PDFTOPPM = Path(
    "C:/Users/Mercurluto/.cache/codex-runtimes/codex-primary-runtime/"
    "dependencies/native/poppler/Library/bin/pdftoppm.exe"
)


def find_pdftoppm():
    if POPPLER_PDFTOPPM.exists():
        return str(POPPLER_PDFTOPPM)
    discovered = shutil.which("pdftoppm")
    if discovered:
        return discovered
    raise RuntimeError("pdftoppm is required to render schematic evidence previews.")


def build_reviewed_previews(source, components):
    output_dir = ROOT / "assets/schematic-evidence/km4-f151"
    output_dir.mkdir(parents=True, exist_ok=True)
    for previous in output_dir.glob("*.png"):
        previous.unlink()
    pages = sorted({item["page"] for designator in REVIEWED_DESIGNATORS for item in components.get(designator, [])})
    with tempfile.TemporaryDirectory(prefix="km4-schematic-pages-") as temporary:
        render_dir = Path(temporary)
        rendered_pages = {}
        for page in pages:
            stem = render_dir / f"page-{page}"
            rendered = stem.with_suffix(".png")
            subprocess.run([
                find_pdftoppm(), "-f", str(page), "-l", str(page), "-png", "-singlefile", "-r", "180",
                str(source), str(stem),
            ], check=True)
            rendered_pages[page] = rendered

        for designator in sorted(REVIEWED_DESIGNATORS):
            for index, occurrence in enumerate(components.get(designator, []), 1):
                source_image = Image.open(rendered_pages[occurrence["page"]]).convert("RGB")
                crop_options = {"height_ratio": 0.08, "y_offset_ratio": 0} if designator == "VBUS1" else {}
                crop = source_image.crop(crop_box_from_origin(
                    occurrence["text_origin"], source_image.width, source_image.height, **crop_options,
                ))
                filename = f"{designator.lower()}-p{occurrence['page']}-{index}.png"
                target = output_dir / filename
                crop.save(target, format="PNG", optimize=True)
                occurrence["preview_image"] = target.relative_to(ROOT).as_posix()


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
    build_reviewed_previews(source, components)
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
