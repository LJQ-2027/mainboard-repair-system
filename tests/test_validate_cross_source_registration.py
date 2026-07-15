import json
import unittest
from pathlib import Path

from scripts.validate_cross_source_registration import validate_dataset


ROOT = Path(__file__).resolve().parents[1]


class CrossSourceRegistrationTests(unittest.TestCase):
    def test_committed_dataset_is_valid(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_dataset(data, ROOT), [])

    def test_registration_requires_view_specific_source_notes(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        data["registration"].pop("point_map_note", None)

        self.assertTrue(any(
            "registration point_map_note" in error
            for error in validate_dataset(data, ROOT)
        ))

    def test_repair_visual_inspection_is_explicitly_limited_to_package_entities(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        inspectable = {
            entity["designator"]
            for entity in data["entities"]
            if entity.get("inspection_profile", {}).get("fidelity") == "repair_visual"
        }

        self.assertEqual(inspectable, {"U2001", "U4000", "X2100", "U0600", "J6101"})
        self.assertTrue(all(
            "inspection_profile" not in entity
            for entity in data["entities"]
            if entity["category"] == "test_point"
        ))

    def test_rejects_component_inspection_profile_on_a_test_point(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        test_point = next(entity for entity in data["entities"] if entity["category"] == "test_point")
        test_point["inspection_profile"] = {
            "profile_id": "invalid-test-point-v1",
            "fidelity": "repair_visual",
            "source_status": "category_based",
            "visual_note": "invalid",
        }

        self.assertTrue(any(
            "test point cannot expose component inspection" in error
            for error in validate_dataset(data, ROOT)
        ))

    def test_committed_measurement_profiles_preserve_source_boundaries(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        profiles = {
            entity["designator"]: entity["measurement_profile"]
            for entity in data["entities"]
            if "measurement_profile" in entity
        }
        self.assertEqual(set(profiles), {"U4000", "X2100", "VBAT1", "VBUS1"})
        self.assertEqual(profiles["U4000"]["reference"], {"kind": "nominal", "value": 3.3})
        self.assertEqual(profiles["X2100"]["reference"], {"kind": "nominal", "value": 26})
        self.assertEqual(profiles["VBAT1"]["reference"], {"kind": "range", "min": 3.4, "max": 4.35})
        self.assertEqual(profiles["VBUS1"]["reference"], {"kind": "nominal", "value": 5})

    def test_committed_repair_flows_preserve_reviewed_entries(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        flows = {flow["flow_id"]: flow for flow in data["repair_flows"]}
        self.assertEqual(set(flows), {"not-charging-page-14-reviewed", "no-power-small-current-page-10"})
        small_current = flows["no-power-small-current-page-10"]
        self.assertEqual(small_current["entry_component_id"], "KM4-MAIN-U4000")
        self.assertEqual([item["reference"]["value"] for item in small_current["steps"][0]["measurements"]], [1.15, 3.3])

    def test_rejects_out_of_range_geometry(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        data["entities"][0]["geometry"]["center"]["x"] = 1.2
        self.assertTrue(any("normalized" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_missing_source_links(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        data["entities"][0]["schematic_links"] = []
        data["entities"][0]["repair_links"] = []
        self.assertTrue(any("source link" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_measurement_without_a_valid_repair_source(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        profile = data["entities"][1]["measurement_profile"]
        profile["source_link_index"] = 99
        self.assertTrue(any("measurement source" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_invalid_measurement_reference_bounds(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        profile = data["entities"][5]["measurement_profile"]
        profile["reference"] = {"kind": "range", "min": 4.35, "max": 3.4}
        self.assertTrue(any("measurement range" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_nominal_reference_without_a_value(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        profile = data["entities"][2]["measurement_profile"]
        profile["reference"] = {"kind": "nominal"}
        self.assertTrue(any("nominal measurement" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_repair_flow_edges_outside_the_declared_graph(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        flow = data["repair_flows"][0]
        flow["steps"][0]["choices"][0]["outcome"]["step_id"] = "missing"
        self.assertTrue(any("flow destination" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_repair_flow_targets_outside_reviewed_entities(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        flow = data["repair_flows"][0]
        flow["entry_component_id"] = "KM4-MAIN-MISSING"
        self.assertTrue(any("flow component" in error for error in validate_dataset(data, ROOT)))

    def test_boundary_outcomes_require_an_explicit_source_note(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        flow = data["repair_flows"][0]
        flow["boundary_note"] = ""
        self.assertTrue(any("flow boundary" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_invalid_flow_measurement_reference(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        flow = data["repair_flows"][1]
        flow["steps"][0]["measurements"][0]["reference"] = {"kind": "nominal"}
        self.assertTrue(any("flow measurement" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_repair_flow_step_without_a_short_label(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        data["repair_flows"][0]["steps"][0].pop("label")
        self.assertTrue(any("flow step" in error for error in validate_dataset(data, ROOT)))


if __name__ == "__main__":
    unittest.main()
