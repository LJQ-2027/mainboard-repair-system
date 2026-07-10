from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


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


def source_crop_box(image: Image.Image, side: dict) -> tuple[int, int, int, int]:
    crop = side["source_crop"]
    left = round(image.width * crop["x"])
    top = round(image.height * crop["y"])
    right = round(image.width * (crop["x"] + crop["width"]))
    bottom = round(image.height * (crop["y"] + crop["height"]))
    return left, top, right, bottom


def remove_connected_page_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    difference = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white")).convert("L")

    # Thicken the source outline before flood filling so the page background
    # cannot leak into the closed board silhouette through anti-aliased pixels.
    barrier = difference.point(lambda value: 255 if value > 8 else 0)
    barrier = barrier.filter(ImageFilter.MaxFilter(5))
    ImageDraw.floodfill(barrier, (0, 0), 128, thresh=0)

    external_background = barrier.point(lambda value: 255 if value == 128 else 0)
    alpha = ImageChops.invert(external_background).filter(ImageFilter.GaussianBlur(0.6))
    rgba.putalpha(alpha)
    return rgba


def build_web_assets(rendered_pages: list[Path], board: dict) -> list[Path]:
    built: list[Path] = []
    for side in board["sides"]:
        page = int(side["source_pdf_page"])
        source = rendered_pages[page - 1]
        target = ROOT / side["image"]
        target.parent.mkdir(parents=True, exist_ok=True)
        rendered = Image.open(source).convert("RGBA")
        cropped = rendered.crop(source_crop_box(rendered, side))
        cutout = remove_connected_page_background(cropped)
        cutout.save(target, format="PNG", optimize=True)
        built.append(target)
    return built


def main() -> None:
    atlas = json.loads(BOARD_ATLAS_JSON.read_text(encoding="utf-8"))
    board = atlas["boards"][0]
    pdf_path = ROOT / board["source_materials"]["main_point_map"]
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    temp_dir = ROOT / ".local" / "board-atlas-build" / board["board_id"].lower()
    rendered = render_pdf_pages(pdf_path, temp_dir, "main-point-map")
    built = build_web_assets(rendered, board)

    print(f"Rendered {len(built)} board atlas page(s):")
    for path in built:
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
