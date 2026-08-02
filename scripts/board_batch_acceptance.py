import json
import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_cross_source_registration import validate_dataset


CATALOG_BASE = Path("assets/cross-source-registration")


def _catalog_path(root, value):
    return (root / CATALOG_BASE / value).resolve()


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalized_outline(outline):
    return len(outline) >= 4 and all(
        isinstance(point, dict)
        and all(
            isinstance(point.get(axis), (int, float)) and 0 <= point[axis] <= 1
            for axis in ("x", "y")
        )
        for point in outline
    )


def _profile_source_layout(root, profile_id):
    registry = _load_json(root / "knowledge-base/board-compiler-profiles.json")
    profile = next(
        (candidate for candidate in registry.get("profiles", []) if candidate.get("profile_id") == profile_id),
        None,
    )
    if profile is None:
        return None
    sources = {
        side.get("point_map_source") or profile.get("point_map_source")
        for side in profile.get("sides", [])
    }
    sources.discard(None)
    if not sources:
        return None
    return "independent_per_side" if len(sources) > 1 else "shared_multi_page"


def audit_board(root, board_key, entry):
    root = Path(root).resolve()
    errors = []
    documents = {}

    for name in ("data", "schematic", "side_manifest"):
        value = entry.get(name)
        path = _catalog_path(root, value) if isinstance(value, str) else None
        if path is None or not path.is_file():
            errors.append(f"{name} does not resolve")
            continue
        try:
            documents[name] = _load_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{name} is not valid UTF-8 JSON: {exc}")

    geometry_by_side = entry.get("geometry_by_side", {})
    geometry_documents = {}
    if not isinstance(geometry_by_side, dict) or not geometry_by_side:
        errors.append("geometry_by_side is required")
    else:
        for side_id, value in geometry_by_side.items():
            path = _catalog_path(root, value) if isinstance(value, str) else None
            if path is None or not path.is_file():
                errors.append(f"geometry {side_id} does not resolve")
                continue
            try:
                geometry_documents[side_id] = _load_json(path)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"geometry {side_id} is not valid UTF-8 JSON: {exc}")

    data = documents.get("data", {})
    schematic = documents.get("schematic", {})
    manifest = documents.get("side_manifest", {})
    board_id = data.get("board_id")
    if not board_id:
        errors.append("registration board_id is required")
    for name, document in (("schematic", schematic), ("side manifest", manifest)):
        if document and document.get("board_id") != board_id:
            errors.append(f"{name} board_id does not match registration")

    manifest_side_ids = [side.get("side_id") for side in manifest.get("sides", [])]
    geometry_side_ids = list(geometry_by_side)
    if manifest and manifest_side_ids != geometry_side_ids:
        errors.append("catalog geometry sides do not match the ordered side manifest")

    accepted_designators = 0
    geometry_components = {}
    for side_id, geometry in geometry_documents.items():
        if geometry.get("board_id") != board_id:
            errors.append(f"geometry {side_id} board_id does not match registration")
        if geometry.get("side_id") != side_id:
            errors.append(f"geometry {side_id} declares a different side_id")
        if not _normalized_outline(geometry.get("board_outline", [])):
            errors.append(f"geometry {side_id} requires a normalized board outline")
        components = geometry.get("components", [])
        if not components:
            errors.append(f"geometry {side_id} requires accepted components")
        accepted_designators += len(components)
        geometry_components[side_id] = {
            component.get("designator") for component in components if component.get("designator")
        }

    for entity in data.get("entities", []):
        entity_id = entity.get("component_id")
        designator = entity.get("designator")
        side_id = entity.get("side_id") or data.get("side_id") or manifest.get("default_side_id")
        if side_id not in geometry_components:
            errors.append(f"{entity_id} declares an unknown side")
        elif designator not in geometry_components[side_id]:
            errors.append(f"{entity_id} does not resolve in its declared side geometry")

    if data:
        errors.extend(validate_dataset(data, root))

    flows = data.get("repair_flows", [])
    flow_source_statuses = {flow.get("source_status") for flow in flows}
    repair_coverage = (
        "reviewed_flows"
        if flows and flow_source_statuses == {"reviewed"}
        else data.get("repair_coverage", {}).get("status")
    )
    reference_mode = data.get("registration", {}).get("reference_mode", "photo_proxy")
    profile_id = manifest.get("profile_id") or board_key
    point_map_source_layout = _profile_source_layout(root, profile_id) if manifest else None
    if manifest and point_map_source_layout is None:
        errors.append("board compiler profile does not resolve point-map sources")
    schematic_audit = schematic.get("audit", {})
    entities = data.get("entities", [])

    return {
        "board_key": board_key,
        "board_id": board_id,
        "title": entry.get("title"),
        "compatible_models": entry.get("compatible_models") or [entry.get("model")],
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "side_ids": manifest_side_ids,
        "accepted_designators": accepted_designators,
        "schematic_linked_designators": schematic_audit.get("linked_designators", 0),
        "schematic_occurrences": schematic_audit.get("schematic_occurrences", 0),
        "reviewed_entities": len(entities),
        "repair_flows": len(flows),
        "repair_coverage": repair_coverage,
        "reference_mode": reference_mode,
        "point_map_source_layout": point_map_source_layout,
        "source_named_sides": any(
            side_id not in ("main_page_1", "main_page_2") for side_id in manifest_side_ids
        ),
        "location_only_entities": sum(1 for entity in entities if not entity.get("inspection_profile")),
    }


def _coverage_gate(covered, evidence):
    return {"covered": bool(covered), "evidence": evidence}


def evaluate_coverage(boards):
    shared_platforms = [
        board["board_key"] for board in boards if len(set(board.get("compatible_models", []))) > 1
    ]
    reference_modes = sorted({board.get("reference_mode") for board in boards if board.get("reference_mode")})
    repair_modes = sorted({board.get("repair_coverage") for board in boards if board.get("repair_coverage")})
    source_layouts = sorted(
        {board.get("point_map_source_layout") for board in boards if board.get("point_map_source_layout")}
    )
    source_named = [board["board_key"] for board in boards if board.get("source_named_sides")]
    location_limited = [
        board["board_key"] for board in boards if board.get("location_only_entities", 0) > 0
    ]
    return {
        "minimum_board_count": _coverage_gate(len(boards) >= 5, [board["board_key"] for board in boards]),
        "shared_platform_models": _coverage_gate(bool(shared_platforms), shared_platforms),
        "reference_modes": _coverage_gate(
            {"photo_proxy", "point_map_only"}.issubset(reference_modes), reference_modes
        ),
        "repair_coverage_modes": _coverage_gate(
            {"reviewed_flows", "source_unavailable"}.issubset(repair_modes), repair_modes
        ),
        "point_map_source_layouts": _coverage_gate(
            {"shared_multi_page", "independent_per_side"}.issubset(source_layouts), source_layouts
        ),
        "source_named_sides": _coverage_gate(bool(source_named), source_named),
        "confidence_limited_locations": _coverage_gate(bool(location_limited), location_limited),
    }


def audit_catalog(root, catalog_path="knowledge-base/repair-workbench-boards.json"):
    root = Path(root).resolve()
    catalog = _load_json(root / catalog_path)
    boards = [
        audit_board(root, board_key, entry)
        for board_key, entry in catalog.get("boards", {}).items()
    ]
    coverage = evaluate_coverage(boards)
    return {
        "audit_id": "BOARD-CATALOG-BATCH-ACCEPTANCE-V2",
        "catalog_id": catalog.get("catalog_id"),
        "boards": boards,
        "coverage": coverage,
        "sufficient_for_current_pipeline": (
            bool(boards)
            and all(board["status"] == "pass" for board in boards)
            and all(gate["covered"] for gate in coverage.values())
        ),
        "scope_boundaries": [
            "visual_defect_recognition",
            "physical_photo_registration_accuracy",
            "cad_geometry",
            "electrical_connectivity_inference",
            "field_repair_effectiveness",
        ],
    }


COVERAGE_LABELS = {
    "minimum_board_count": "Five or more board platforms",
    "shared_platform_models": "Shared platform across sales models",
    "reference_modes": "Photo-proxy and point-map-only references",
    "repair_coverage_modes": "Reviewed-flow and reference-only repair coverage",
    "point_map_source_layouts": "Shared and independent point-map source layouts",
    "source_named_sides": "Source-named board sides",
    "confidence_limited_locations": "Confidence-limited location-only entities",
}


SCOPE_LABELS = {
    "visual_defect_recognition": "Visual defect recognition",
    "physical_photo_registration_accuracy": "Physical photo registration accuracy",
    "cad_geometry": "CAD geometry",
    "electrical_connectivity_inference": "Electrical connectivity inference",
    "field_repair_effectiveness": "Field repair effectiveness",
}


def render_markdown(audit):
    lines = [
        "# Board Catalog Batch Acceptance",
        "",
        f"Catalog: `{audit.get('catalog_id')}`",
        "",
        "## Board Results",
        "",
        "| Board | Status | Designators | SCH linked | Reviewed entities | Repair flows | Reference | Repair coverage |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for board in audit.get("boards", []):
        row = {**board, "status": board.get("status", "fail").upper()}
        lines.append(
            "| `{board_key}` | {status} | {accepted_designators:,} | "
            "{schematic_linked_designators:,} | {reviewed_entities:,} | {repair_flows:,} | "
            "`{reference_mode}` | `{repair_coverage}` |".format(
                **row,
            )
        )
    lines.extend([
        "",
        "## Coverage Gates",
        "",
        "| Gate | Result | Evidence |",
        "| --- | --- | --- |",
    ])
    for key, gate in audit.get("coverage", {}).items():
        evidence = ", ".join(str(value) for value in gate.get("evidence", [])) or "None"
        lines.append(
            f"| {COVERAGE_LABELS.get(key, key)} | {'PASS' if gate.get('covered') else 'FAIL'} | {evidence} |"
        )
    lines.extend([
        "",
        "## Scope Boundaries",
        "",
    ])
    lines.extend(
        f"- {SCOPE_LABELS.get(boundary, boundary)}"
        for boundary in audit.get("scope_boundaries", [])
    )
    lines.extend([
        "",
        "**Sufficient for current source-to-2.5D pipeline: "
        f"{'YES' if audit.get('sufficient_for_current_pipeline') else 'NO'}**",
        "",
    ])
    return "\n".join(lines)


def _write_atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(content, encoding="utf-8", newline="\n")
    temporary_path.replace(path)


def publish_reports(audit, json_path, markdown_path):
    if (
        not audit.get("sufficient_for_current_pipeline")
        or any(board.get("status") != "pass" for board in audit.get("boards", []))
        or any(not gate.get("covered") for gate in audit.get("coverage", {}).values())
    ):
        raise ValueError("acceptance audit failed; reports were not published")
    _write_atomic(json_path, json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    _write_atomic(markdown_path, render_markdown(audit))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit every source-driven repair board")
    parser.add_argument("--catalog", default="knowledge-base/repair-workbench-boards.json")
    parser.add_argument("--json-output", default="reports/board-catalog-batch-acceptance.json")
    parser.add_argument("--markdown-output", default="reports/board-catalog-batch-acceptance.md")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    audit = audit_catalog(root, args.catalog)
    try:
        publish_reports(audit, root / args.json_output, root / args.markdown_output)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        for board in audit.get("boards", []):
            for error in board.get("errors", []):
                print(f"  {board['board_key']}: {error}", file=sys.stderr)
        return 1
    print(
        f"Batch acceptance passed: {len(audit['boards'])} boards, "
        f"{len(audit['coverage'])} coverage gates"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
