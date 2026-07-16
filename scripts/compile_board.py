import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.board_compiler.pipeline import compile_geometry, compile_schematic
from scripts.board_compiler.profiles import load_profile


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile a source-driven board profile")
    parser.add_argument("--profile", required=True, help="Profile id from board-compiler-profiles.json")
    parser.add_argument("--side", help="Compile one declared side")
    parser.add_argument("--geometry-only", action="store_true", help="Compile point-map geometry only")
    parser.add_argument("--schematic-only", action="store_true", help="Compile schematic links only")
    args = parser.parse_args(argv)
    if args.geometry_only and args.schematic_only:
        parser.error("--geometry-only and --schematic-only are mutually exclusive")
    profile = load_profile(ROOT, args.profile)
    result = {"profile_id": args.profile}
    if not args.schematic_only:
        payloads = compile_geometry(ROOT, profile, side_id=args.side)
        result["sides"] = [item["audit"] for item in payloads]
    if not args.geometry_only:
        schematic = compile_schematic(ROOT, profile)
        result["schematic"] = schematic["audit"]
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
