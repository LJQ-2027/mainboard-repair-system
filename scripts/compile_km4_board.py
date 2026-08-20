import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.board_compiler.pipeline import (
    build_side_manifest as build_profile_side_manifest,
    compile_geometry,
    compile_side as compile_profile_side,
)
from scripts.board_compiler.profiles import load_profile


PROFILE = load_profile(ROOT, "km4-f151")
BOARD_ID = PROFILE["board_id"]
SOURCE_PATH = PROFILE["point_map_source"]
REQUIRED_DESIGNATORS = set(PROFILE["reviewed_designators"])
SIDE_CONFIGS = {
    side["side_id"]: {
        "page": side["source_pdf_page"],
        "label": side["label"],
        "image": side["engineering_texture"],
        "output": side["compiled_data"],
        "required_designators": set(side["required_designators"]),
    }
    for side in PROFILE["sides"]
}


def _profile_side(side_id):
    return next(side for side in PROFILE["sides"] if side["side_id"] == side_id)


def compile_side(root, side_id, config):
    del config
    return compile_profile_side(root, PROFILE, _profile_side(side_id))


def build_side_manifest(root=ROOT):
    del root
    return build_profile_side_manifest(PROFILE)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile KM4/F151 point-map sides")
    parser.add_argument("--side", choices=SIDE_CONFIGS, help="Compile only one side while refreshing the side manifest")
    args = parser.parse_args(argv)
    try:
        payloads = compile_geometry(ROOT, PROFILE, side_id=args.side, render_textures=False)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    for payload in payloads:
        print(json.dumps({"side_id": payload["side_id"], **payload["audit"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
