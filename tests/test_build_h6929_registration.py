import unittest

from scripts.build_h6929_registration import build_dataset


class BuildH6929RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = build_dataset()
        cls.entities = {item["designator"]: item for item in cls.dataset["entities"]}
        cls.flows = {item["flow_id"]: item for item in cls.dataset["repair_flows"]}

    def test_builds_ck6n_h6929_dual_side_platform(self):
        self.assertEqual(self.dataset["board_id"], "BOARD-H6929-MAIN-V1.1")
        self.assertEqual(self.dataset["model"], "CK6N")
        self.assertEqual(len(self.entities), 10)
        self.assertEqual(self.entities["U1001"]["side_id"], "main_top")
        self.assertEqual(self.entities["U2001"]["side_id"], "main_bot")

    def test_source_truth_uses_point_map_only_reference_mode(self):
        registration = self.dataset["registration"]
        self.assertEqual(registration["reference_mode"], "point_map_only")
        self.assertNotIn("proxy_image", registration)
        self.assertNotIn("anchors", registration)

    def test_measurements_preserve_manual_values(self):
        self.assertEqual(self.entities["VBAT1"]["measurement_profile"]["reference"], {"kind": "range", "min": 3.4, "max": 4.35})
        self.assertEqual(self.entities["X2101"]["measurement_profile"]["reference"], {"kind": "nominal", "value": 26})

    def test_builds_four_source_bounded_repair_flows(self):
        self.assertEqual(len(self.flows), 4)
        self.assertIn("h6929-no-power-zero-current-page-12", self.flows)
        self.assertIn("h6929-no-power-small-current-page-13", self.flows)
        self.assertIn("h6929-no-charge-page-17", self.flows)
        self.assertIn("h6929-display-page-31", self.flows)

    def test_package_entities_offer_inspection_but_test_point_does_not(self):
        self.assertIn("inspection_profile", self.entities["U2001"])
        self.assertIn("inspection_profile", self.entities["J6101"])
        self.assertNotIn("inspection_profile", self.entities["VBAT1"])


if __name__ == "__main__":
    unittest.main()
