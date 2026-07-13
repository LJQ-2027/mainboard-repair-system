import json
import sys
from pathlib import Path


def _normalized(point):
    return isinstance(point, dict) and all(
        isinstance(point.get(axis), (int, float)) and 0 <= point[axis] <= 1 for axis in ("x", "y")
    )


def validate_dataset(data, root):
    errors = []
    outline = data.get("board_outline", [])
    if len(outline) < 4 or any(not _normalized(point) for point in outline):
        errors.append("board outline requires at least four normalized points")
    registration = data.get("registration", {})
    for key in ("proxy_image", "point_map_image"):
        path = registration.get(key)
        if not path or not (root / path).is_file():
            errors.append(f"registration {key} does not resolve")

    anchors = registration.get("anchors", [])
    if len(anchors) < 4:
        errors.append("registration requires at least four anchors")
    for anchor in anchors:
        if not _normalized(anchor.get("board")) or not _normalized(anchor.get("image")):
            errors.append(f"anchor {anchor.get('anchor_id', 'unknown')} must use normalized coordinates")

    identities = set()
    for entity in data.get("entities", []):
        entity_id = entity.get("component_id")
        if not entity_id or entity_id in identities:
            errors.append(f"duplicate or missing component identity: {entity_id}")
        identities.add(entity_id)
        geometry = entity.get("geometry", {})
        if not _normalized(geometry.get("center")):
            errors.append(f"{entity_id} center must use normalized coordinates")
        size = geometry.get("size", {})
        if not _normalized(size) or size.get("x", 0) <= 0 or size.get("y", 0) <= 0:
            errors.append(f"{entity_id} size must use positive normalized coordinates")
        if not entity.get("schematic_links") and not entity.get("repair_links"):
            errors.append(f"{entity_id} requires at least one source link")
        for group in ("schematic_links", "repair_links"):
            for link in entity.get(group, []):
                if not link.get("source") or not link.get("page"):
                    errors.append(f"{entity_id} contains an unsupported source link")
    if not data.get("entities"):
        errors.append("dataset requires entities")
    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "knowledge-base/km4-cross-source-registration.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_dataset(data, root)
    if errors:
        print("Cross-source registration validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Cross-source registration validation passed: {len(data['entities'])} entities, {len(data['registration']['anchors'])} anchors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
