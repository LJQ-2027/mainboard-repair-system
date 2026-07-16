import unittest
from pathlib import Path

from scripts.build_kl4_registration import build_dataset


ROOT = Path(__file__).resolve().parents[1]


class BuildKl4RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = build_dataset(ROOT)
        cls.entities = {entity["designator"]: entity for entity in cls.dataset["entities"]}

    def test_uses_compiled_geometry_and_source_sides(self):
        self.assertEqual(self.dataset["board_id"], "BOARD-KL4-F201-MAIN-V1.2")
        self.assertEqual(set(self.entities), {"U1001", "U2001", "X2100"})
        self.assertEqual(self.entities["U1001"]["side_id"], "main_page_1")
        self.assertEqual(self.entities["U2001"]["side_id"], "main_page_2")
        self.assertEqual(self.entities["X2100"]["side_id"], "main_page_2")

    def test_low_confidence_u1001_stays_a_location_without_inspection(self):
        self.assertEqual(self.entities["U1001"]["geometry"]["source_status"], "low")
        self.assertNotIn("inspection_profile", self.entities["U1001"])

    def test_small_current_flow_keeps_nominal_values_technician_judged(self):
        flow = self.dataset["repair_flows"][0]
        self.assertEqual(flow["entry_label"], "不开机")
        self.assertEqual(flow["entry_step_id"], "rail_check")
        rail_step = next(step for step in flow["steps"] if step["step_id"] == "rail_check")
        self.assertEqual([item["reference"] for item in rail_step["measurements"]], [
            {"kind": "nominal", "value": 1.15},
            {"kind": "nominal", "value": 3.3},
        ])
        self.assertEqual(rail_step["choices"][0]["outcome"], {"kind": "next", "step_id": "crystal_check"})

    def test_crystal_step_targets_x2100_and_preserves_source_actions(self):
        flow = self.dataset["repair_flows"][0]
        crystal = next(step for step in flow["steps"] if step["step_id"] == "crystal_check")
        self.assertEqual(crystal["target_component_id"], "KL4-MAIN-X2100")
        self.assertEqual(crystal["measurements"][0]["reference"], {"kind": "nominal", "value": 26})
        self.assertEqual(
            {choice["outcome"]["label"] for choice in crystal["choices"]},
            {"重焊或更换 U1001", "重焊或更换 X2100"},
        )


if __name__ == "__main__":
    unittest.main()
