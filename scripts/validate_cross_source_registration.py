import json
import sys
from pathlib import Path


def _normalized(point):
    return isinstance(point, dict) and all(
        isinstance(point.get(axis), (int, float)) and 0 <= point[axis] <= 1 for axis in ("x", "y")
    )


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_dataset(data, root):
    errors = []
    outline = data.get("board_outline", [])
    if len(outline) < 4 or any(not _normalized(point) for point in outline):
        errors.append("board outline requires at least four normalized points")
    registration = data.get("registration", {})
    reference_mode = registration.get("reference_mode", "photo_proxy")
    if reference_mode not in ("photo_proxy", "point_map_only"):
        errors.append("registration reference_mode is unsupported")
    point_map_path = registration.get("point_map_image")
    if not point_map_path or not (root / point_map_path).is_file():
        errors.append("registration point_map_image does not resolve")
    if not isinstance(registration.get("point_map_note"), str) or not registration["point_map_note"].strip():
        errors.append("registration point_map_note is required")

    anchors = registration.get("anchors", [])
    if reference_mode != "point_map_only":
        proxy_path = registration.get("proxy_image")
        if not proxy_path or not (root / proxy_path).is_file():
            errors.append("registration proxy_image does not resolve")
        if not isinstance(registration.get("proxy_note"), str) or not registration["proxy_note"].strip():
            errors.append("registration proxy_note is required")
        if len(anchors) < 4:
            errors.append("registration requires at least four anchors")
        for anchor in anchors:
            if not _normalized(anchor.get("board")) or not _normalized(anchor.get("image")):
                errors.append(f"anchor {anchor.get('anchor_id', 'unknown')} must use normalized coordinates")

    identities = set()
    entities_by_id = {}
    measurement_ids = set()
    for entity in data.get("entities", []):
        entity_id = entity.get("component_id")
        if not entity_id or entity_id in identities:
            errors.append(f"duplicate or missing component identity: {entity_id}")
        identities.add(entity_id)
        entities_by_id[entity_id] = entity
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
        inspection_profile = entity.get("inspection_profile")
        if inspection_profile:
            if entity.get("category") == "test_point":
                errors.append(f"{entity_id} test point cannot expose component inspection")
            for key in ("profile_id", "fidelity", "source_status", "visual_note"):
                if not inspection_profile.get(key):
                    errors.append(f"{entity_id} inspection profile requires {key}")
        profile = entity.get("measurement_profile")
        if profile:
            measurement_id = profile.get("measurement_id")
            if not measurement_id or measurement_id in measurement_ids:
                errors.append(f"{entity_id} has a duplicate or missing measurement identity")
            measurement_ids.add(measurement_id)
            if not profile.get("label") or not profile.get("quantity") or not profile.get("unit"):
                errors.append(f"{entity_id} measurement requires label, quantity, and unit")
            if not _number(profile.get("input_step")) or profile["input_step"] <= 0:
                errors.append(f"{entity_id} measurement input step must be positive")
            source_index = profile.get("source_link_index")
            repair_links = entity.get("repair_links", [])
            if not isinstance(source_index, int) or isinstance(source_index, bool) or not 0 <= source_index < len(repair_links):
                errors.append(f"{entity_id} measurement source must reference a repair link")
            reference = profile.get("reference", {})
            reference_kind = reference.get("kind")
            if reference_kind == "range":
                minimum = reference.get("min")
                maximum = reference.get("max")
                if not _number(minimum) or not _number(maximum) or minimum > maximum:
                    errors.append(f"{entity_id} measurement range requires ordered numeric bounds")
            elif reference_kind == "nominal":
                if not _number(reference.get("value")):
                    errors.append(f"{entity_id} nominal measurement requires a numeric value")
            elif reference_kind != "record_only":
                errors.append(f"{entity_id} measurement reference kind is unsupported")
    repair_flows = data.get("repair_flows", [])
    declared_flow_ids = {flow.get("flow_id") for flow in repair_flows if flow.get("flow_id")}
    flow_ids = set()
    for flow in repair_flows:
        flow_id = flow.get("flow_id")
        if not flow_id or flow_id in flow_ids:
            errors.append(f"duplicate or missing repair flow identity: {flow_id}")
        flow_ids.add(flow_id)
        if not flow.get("entry_label") or flow.get("entry_type") not in ("known_fault", "precheck"):
            errors.append(f"{flow_id} flow entry requires a label and supported type")
        if not isinstance(flow.get("entry_order"), int) or isinstance(flow.get("entry_order"), bool):
            errors.append(f"{flow_id} flow entry order must be an integer")
        entry_component_id = flow.get("entry_component_id")
        if entry_component_id not in identities:
            errors.append(f"{flow_id} flow component must resolve to a reviewed entity")
        source = flow.get("source", {})
        if not source.get("source") or not source.get("page"):
            errors.append(f"{flow_id} flow source must include a document and page")
        steps = flow.get("steps", [])
        step_ids = [step.get("step_id") for step in steps]
        if not steps or any(not step_id for step_id in step_ids) or len(step_ids) != len(set(step_ids)):
            errors.append(f"{flow_id} flow steps require unique identities")
        step_id_set = set(step_ids)
        if flow.get("entry_step_id") not in step_id_set:
            errors.append(f"{flow_id} flow entry step must resolve inside the graph")
        has_boundary = False
        for step in steps:
            step_id = step.get("step_id")
            if not step.get("label") or not step.get("prompt") or not step.get("choices"):
                errors.append(f"{flow_id}/{step_id} flow step requires a label, prompt, and choices")
            if step.get("target_component_id") and step["target_component_id"] not in identities:
                errors.append(f"{flow_id}/{step_id} flow component target is unresolved")
            measurements = step.get("measurements", [])
            measurement_ids = [measurement.get("measurement_id") for measurement in measurements]
            if any(not measurement_id for measurement_id in measurement_ids) or len(measurement_ids) != len(set(measurement_ids)):
                errors.append(f"{flow_id}/{step_id} flow measurement identities must be unique")
            for measurement in measurements:
                if not measurement.get("label") or not measurement.get("unit"):
                    errors.append(f"{flow_id}/{step_id} flow measurement requires a label and unit")
                if not _number(measurement.get("input_step")) or measurement["input_step"] <= 0:
                    errors.append(f"{flow_id}/{step_id} flow measurement input step must be positive")
                reference = measurement.get("reference", {})
                reference_kind = reference.get("kind")
                if reference_kind == "range":
                    minimum = reference.get("min")
                    maximum = reference.get("max")
                    if not _number(minimum) or not _number(maximum) or minimum > maximum:
                        errors.append(f"{flow_id}/{step_id} flow measurement range requires ordered numeric bounds")
                elif reference_kind == "nominal":
                    if not _number(reference.get("value")):
                        errors.append(f"{flow_id}/{step_id} flow measurement nominal reference requires a numeric value")
                elif reference_kind != "record_only":
                    errors.append(f"{flow_id}/{step_id} flow measurement reference kind is unsupported")
            choice_values = [choice.get("value") for choice in step.get("choices", [])]
            if any(not value for value in choice_values) or len(choice_values) != len(set(choice_values)):
                errors.append(f"{flow_id}/{step_id} flow choices require unique values")
            for choice in step.get("choices", []):
                outcome = choice.get("outcome", {})
                kind = outcome.get("kind")
                if kind == "next":
                    if outcome.get("step_id") not in step_id_set:
                        errors.append(f"{flow_id}/{step_id} flow destination is outside the graph")
                elif kind == "handoff":
                    if outcome.get("flow_id") not in declared_flow_ids or not outcome.get("label"):
                        errors.append(f"{flow_id}/{step_id} flow handoff must resolve to a reviewed flow")
                elif kind in ("action", "boundary"):
                    if not outcome.get("label"):
                        errors.append(f"{flow_id}/{step_id} flow terminal requires a label")
                    if kind == "boundary":
                        has_boundary = True
                    target = outcome.get("target_component_id")
                    if target and target not in identities:
                        errors.append(f"{flow_id}/{step_id} flow component target is unresolved")
                else:
                    errors.append(f"{flow_id}/{step_id} flow outcome kind is unsupported")
        if has_boundary and (flow.get("source_status") != "reviewed_partial" or not flow.get("boundary_note")):
            errors.append(f"{flow_id} flow boundary requires reviewed-partial status and a note")
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
    anchor_count = len(data["registration"].get("anchors", []))
    print(f"Cross-source registration validation passed: {len(data['entities'])} entities, {anchor_count} anchors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
