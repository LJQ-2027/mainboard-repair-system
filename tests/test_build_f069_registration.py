import unittest

from scripts.build_f069_registration import build_dataset


class BuildF069RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = build_dataset()
        cls.entities = {item["designator"]: item for item in cls.dataset["entities"]}

    def test_builds_exact_bg6h_f069_v12_reference_platform(self):
        self.assertEqual(self.dataset["board_id"], "BOARD-F069-MAIN-V1.2")
        self.assertEqual(self.dataset["model"], "BG6H")
        self.assertEqual(self.dataset["compatible_models"], ["BG6H", "BG6h"])
        self.assertNotIn("BG6", self.dataset["compatible_models"])
        self.assertEqual(len(self.entities), 12)
        self.assertEqual(self.entities["U1001"]["side_id"], "main_page_1")
        self.assertEqual(self.entities["U2001"]["side_id"], "main_page_2")

    def test_available_manual_remains_pending_review_without_fake_flows(self):
        self.assertEqual(self.dataset["repair_flows"], [])
        self.assertEqual(
            self.dataset["repair_coverage"]["status"],
            "source_available_pending_review",
        )
        self.assertIn("维修指导书", self.dataset["repair_coverage"]["note"])
        self.assertTrue(all(
            not entity["repair_links"]
            for designator, entity in self.entities.items()
            if designator != "VBAT1"
        ))

    def test_components_keep_exact_schematic_links_and_vbat_stays_point_map_only(self):
        linked = {key for key, entity in self.entities.items() if entity["schematic_links"]}
        self.assertEqual(linked, set(self.entities) - {"VBAT1"})
        self.assertEqual(self.entities["U4000"]["schematic_links"][0]["page"], "13")
        self.assertEqual(self.entities["J6250"]["schematic_links"][0]["page"], "18")
        self.assertEqual(self.entities["VBAT1"]["schematic_links"], [])
        self.assertEqual(
            self.entities["VBAT1"]["source_boundary"],
            "point_map_and_unreviewed_guide",
        )
        self.assertEqual(
            self.entities["VBAT1"]["repair_links"][0]["page"],
            "不开机章节（DOCX，无固定页码）",
        )

    def test_low_confidence_locations_do_not_claim_component_inspection(self):
        self.assertNotIn("inspection_profile", self.entities["U1001"])
        self.assertNotIn("inspection_profile", self.entities["U4001"])
        self.assertNotIn("inspection_profile", self.entities["U4000"])
        self.assertNotIn("inspection_profile", self.entities["VBUS1"])
        self.assertIn("inspection_profile", self.entities["U2001"])

    def test_reference_dataset_does_not_invent_measurement_ranges(self):
        self.assertTrue(
            all("measurement_profile" not in entity for entity in self.entities.values())
        )


if __name__ == "__main__":
    unittest.main()
