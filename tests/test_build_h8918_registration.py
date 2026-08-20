import unittest

from scripts.build_h8918_registration import build_dataset


class BuildH8918RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = build_dataset()
        cls.entities = {item["designator"]: item for item in cls.dataset["entities"]}
        cls.flows = {item["flow_id"]: item for item in cls.dataset["repair_flows"]}

    def test_builds_shared_h8918_platform_for_cm6_and_cm5(self):
        self.assertEqual(self.dataset["board_id"], "BOARD-H8918-MAIN-V1.2")
        self.assertEqual(self.dataset["model"], "CM6")
        self.assertEqual(self.dataset["compatible_models"], ["CM6", "CM5"])
        self.assertEqual(set(self.entities), {"U1001", "U2001", "X2101", "J6102", "U5007", "VBAT1"})

    def test_reviewed_entities_keep_real_side_and_geometry_confidence(self):
        self.assertEqual(self.entities["U1001"]["side_id"], "main_page_1")
        self.assertEqual(self.entities["U2001"]["side_id"], "main_page_2")
        self.assertEqual(self.entities["J6102"]["geometry"]["source_status"], "low")
        self.assertNotIn("inspection_profile", self.entities["J6102"])
        self.assertNotIn("inspection_profile", self.entities["U1001"])
        self.assertIn("inspection_profile", self.entities["U2001"])
        self.assertIn("inspection_profile", self.entities["X2101"])

    def test_source_measurements_preserve_range_and_nominal_semantics(self):
        self.assertEqual(
            self.entities["VBAT1"]["measurement_profile"]["reference"],
            {"kind": "range", "min": 3.4, "max": 4.35},
        )
        self.assertEqual(
            self.entities["X2101"]["measurement_profile"]["reference"],
            {"kind": "nominal", "value": 26},
        )

    def test_builds_three_source_bounded_repair_flows(self):
        self.assertEqual(len(self.flows), 3)
        self.assertIn("h8918-no-power-small-current-page-11", self.flows)
        self.assertIn("h8918-wifi-page-23", self.flows)
        self.assertIn("h8918-display-page-25", self.flows)
        self.assertEqual(self.flows["h8918-no-power-small-current-page-11"]["entry_component_id"], "H8918-MAIN-X2101")
        self.assertEqual(self.flows["h8918-wifi-page-23"]["entry_component_id"], "H8918-MAIN-U5007")
        self.assertEqual(self.flows["h8918-display-page-25"]["entry_component_id"], "H8918-MAIN-J6102")

    def test_choices_do_not_invent_automatic_tolerance(self):
        no_power = self.flows["h8918-no-power-small-current-page-11"]
        clock_step = next(item for item in no_power["steps"] if item["step_id"] == "dcxo_check")
        self.assertEqual(clock_step["measurements"][0]["reference"], {"kind": "nominal", "value": 26})
        self.assertEqual([item["value"] for item in clock_step["choices"]], ["normal", "abnormal"])


if __name__ == "__main__":
    unittest.main()
