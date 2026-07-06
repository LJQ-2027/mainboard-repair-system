from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD_ATLAS_JSON = ROOT / "knowledge-base" / "board-atlas-mvp.json"
POPPLER_PDFTOPPM = Path(
    "C:/Users/Mercurluto/.cache/codex-runtimes/codex-primary-runtime/"
    "dependencies/native/poppler/Library/bin/pdftoppm.exe"
)


def find_pdftoppm() -> str:
    if POPPLER_PDFTOPPM.exists():
        return str(POPPLER_PDFTOPPM)
    found = shutil.which("pdftoppm")
    if found:
        return found
    raise RuntimeError("pdftoppm was not found. Install Poppler or use bundled workspace dependencies.")


def render_pdf_pages(pdf_path: Path, output_dir: Path, output_stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        find_pdftoppm(),
        "-png",
        "-r",
        "180",
        str(pdf_path),
        str(output_dir / output_stem),
    ]
    subprocess.run(command, check=True)
    return sorted(output_dir.glob(f"{output_stem}-*.png"))


def normalize_page_names(rendered_pages: list[Path], board: dict) -> list[Path]:
    renamed: list[Path] = []
    for side in board["sides"]:
        page = int(side["source_pdf_page"])
        source = rendered_pages[page - 1]
        target = ROOT / side["image"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        source.replace(target)
        renamed.append(target)
    return renamed


def main() -> None:
    atlas = json.loads(BOARD_ATLAS_JSON.read_text(encoding="utf-8"))
    board = atlas["boards"][0]
    pdf_path = ROOT / board["source_materials"]["main_point_map"]
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    temp_dir = ROOT / ".local" / "board-atlas-build" / board["board_id"].lower()
    rendered = render_pdf_pages(pdf_path, temp_dir, "main-point-map")
    renamed = normalize_page_names(rendered, board)

    print(f"Rendered {len(renamed)} board atlas page(s):")
    for path in renamed:
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()

