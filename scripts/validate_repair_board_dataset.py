import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.board_compiler.profiles import load_registry, validate_profile
from scripts.validate_cross_source_registration import validate_dataset


def _matching_profile(root, dataset_path):
    relative = dataset_path.resolve().relative_to(root.resolve()).as_posix()
    registry = load_registry(root)
    profile = next((item for item in registry["profiles"] if item["cross_source_output"] == relative), None)
    return validate_profile(root, profile) if profile else None


def validate_dataset_package(data, root, profile):
    errors = list(validate_dataset(data, root))
    if data.get("board_id") != profile["board_id"]:
        errors.append("dataset board_id does not match board profile")

    manifest = json.loads((root / profile["side_manifest_output"]).read_text(encoding="utf-8"))
    schematic = json.loads((root / profile["schematic_output"]).read_text(encoding="utf-8"))
    if manifest.get("board_id") != profile["board_id"]:
        errors.append("side manifest board_id does not match board profile")
    if schematic.get("board_id") != profile["board_id"]:
        errors.append("schematic board_id does not match board profile")

    declared_sides = {side["side_id"]: side for side in profile["sides"]}
    geometry_by_side = {
        side_id: json.loads((root / side["compiled_data"]).read_text(encoding="utf-8"))
        for side_id, side in declared_sides.items()
    }
    for entity in data.get("entities", []):
        entity_id = entity.get("component_id", "unknown")
        side_id = entity.get("side_id", data.get("side_id"))
        if side_id not in declared_sides:
            errors.append(f"{entity_id} references an undeclared side")
            continue
        geometry = geometry_by_side[side_id]
        if geometry.get("board_id") != profile["board_id"]:
            errors.append(f"{side_id} geometry board_id does not match board profile")
        designators = {component["designator"] for component in geometry.get("components", [])}
        if entity.get("designator") not in designators:
            errors.append(f"{entity_id} does not resolve in declared-side geometry")
        if entity.get("designator") not in schematic.get("components", {}):
            errors.append(f"{entity_id} does not resolve in exact schematic links")
    return errors


def validate_dataset_path(path, root=ROOT):
    path = path.resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    profile = _matching_profile(root, path)
    if profile is None:
        return ["dataset path is not declared by a board compiler profile"]
    return validate_dataset_package(data, root, profile)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a compiled repair-board dataset")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args(argv)
    path = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    errors = validate_dataset_path(path, ROOT)
    if errors:
        print("Repair-board dataset validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"Repair-board dataset validation passed: {data['model']} / {len(data['entities'])} entities / {len(data.get('repair_flows', []))} flow(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
