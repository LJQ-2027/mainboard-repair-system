import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.board_compiler.pipeline import compile_schematic
from scripts.board_compiler.profiles import load_profile
from scripts.board_compiler.schematic import crop_box_from_origin


PROFILE = load_profile(ROOT, "km4-f151")
REVIEWED_DESIGNATORS = set(PROFILE["reviewed_designators"])
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
    pages = sorted({
        item["page"]
        for designator in REVIEWED_DESIGNATORS
        for item in components.get(designator, [])
    })
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

        staged = []
        for designator in sorted(REVIEWED_DESIGNATORS):
            for index, occurrence in enumerate(components.get(designator, []), 1):
                with Image.open(rendered_pages[occurrence["page"]]).convert("RGB") as source_image:
                    crop_options = {"height_ratio": 0.08, "y_offset_ratio": 0} if designator == "VBUS1" else {}
                    crop = source_image.crop(crop_box_from_origin(
                        occurrence["text_origin"], source_image.width, source_image.height, **crop_options,
                    ))
                    filename = f"{designator.lower()}-p{occurrence['page']}-{index}.png"
                    target = output_dir / filename
                    temporary_target = target.with_suffix(".png.tmp")
                    crop.save(temporary_target, format="PNG", optimize=True)
                    staged.append((temporary_target, target))
                    occurrence["preview_image"] = target.relative_to(ROOT).as_posix()
        for temporary_target, target in staged:
            temporary_target.replace(target)
        expected = {target for _temporary, target in staged}
        for previous in output_dir.glob("*.png"):
            if previous not in expected:
                previous.unlink()


def main():
    source = ROOT / PROFILE["schematic_source"]
    try:
        payload = compile_schematic(
            ROOT,
            PROFILE,
            preview_builder=lambda components: build_reviewed_previews(source, components),
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(payload["audit"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
