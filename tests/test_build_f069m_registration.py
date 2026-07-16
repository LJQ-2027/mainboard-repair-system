import unittest

from scripts.build_f069m_registration import build_dataset


class BuildF069mRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = build_dataset()
        cls.entities = {item["designator"]: item for item in cls.dataset["entities"]}

    def test_builds_bg6m_reference_platform_from_point_map_and_schematic(self):
        self.assertEqual(self.dataset["board_id"], "BOARD-F069M-MAIN-V1.0")
        self.assertEqual(self.dataset["model"], "BG6M")
        self.assertEqual(len(self.entities), 10)
        self.assertEqual(self.entities["U1001"]["side_id"], "main_page_1")
        self.assertEqual(self.entities["U2001"]["side_id"], "main_page_2")

    def test_missing_manual_is_explicit_and_does_not_generate_fake_flows(self):
        self.assertEqual(self.dataset["repair_flows"], [])
        self.assertEqual(self.dataset["repair_coverage"]["status"], "source_unavailable")
        self.assertIn("维修手册", self.dataset["repair_coverage"]["note"])
        self.assertTrue(all(not entity["repair_links"] for entity in self.entities.values()))

    def test_every_entity_keeps_an_exact_schematic_link(self):
        self.assertTrue(all(entity["schematic_links"] for entity in self.entities.values()))
        self.assertEqual(self.entities["U4000"]["schematic_links"][0]["page"], "12")
        self.assertEqual(self.entities["J6250"]["schematic_links"][0]["page"], "17")

    def test_low_confidence_locations_do_not_claim_component_inspection(self):
        self.assertNotIn("inspection_profile", self.entities["U4001"])
        self.assertNotIn("inspection_profile", self.entities["VBUS1"])
        self.assertIn("inspection_profile", self.entities["U4000"])

    def test_reference_only_dataset_does_not_invent_measurement_ranges(self):
        self.assertTrue(all("measurement_profile" not in entity for entity in self.entities.values()))


if __name__ == "__main__":
    unittest.main()
