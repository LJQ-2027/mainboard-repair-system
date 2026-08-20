import unittest
from pathlib import Path

from scripts.build_h897_registration import build_dataset


ROOT = Path(__file__).resolve().parents[1]


class BuildH897RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = build_dataset(ROOT)

    def test_builds_exact_kj6_h897_identity(self):
        self.assertEqual(self.dataset["board_id"], "BOARD-H897-MAIN-V1.2")
        self.assertEqual(self.dataset["model"], "KJ6")
        self.assertEqual(self.dataset["compatible_models"], ["KJ6"])
        self.assertEqual(self.dataset["board_version"], "H897_MAIN_PCB_V1.2")

    def test_exposes_fifteen_source_linked_entities(self):
        entities = {item["designator"]: item for item in self.dataset["entities"]}

        self.assertEqual(len(entities), 15)
        self.assertEqual(entities["U1001"]["module"], "Main processor")
        self.assertEqual(entities["U2001"]["module"], "Power management")
        self.assertEqual(entities["U5003"]["module"], "Wireless connectivity")
        self.assertEqual(entities["U6000"]["module"], "Audio amplifier")
        self.assertEqual(entities["U6601"]["module"], "NFC")
        self.assertTrue(all(item["schematic_links"] for item in entities.values()))

    def test_starts_at_a_truthful_case_registration_boundary(self):
        self.assertEqual(
            self.dataset["repair_coverage"]["status"],
            "source_available_pending_review",
        )
        self.assertEqual(self.dataset["repair_flows"], [])
        self.assertFalse(self.dataset["boundaries"]["repair_instruction_allowed"])
        self.assertFalse(self.dataset["boundaries"]["visual_defect_confirmed"])

    def test_embeds_reviewed_photos_and_physical_registration(self):
        registration = self.dataset["registration"]
        self.assertEqual(
            registration["reference_mode"], "reviewed_physical_photo_navigation"
        )
        navigation = registration["photo_navigation"]
        self.assertEqual(navigation["schema_version"], "H897-PHOTO-NAVIGATION-V1")
        self.assertEqual(len(navigation["photos"]), 2)
        self.assertEqual(
            {item["side_id"] for item in navigation["photos"]},
            {"main_page_1", "main_page_2"},
        )
        self.assertTrue(
            all((ROOT / item["asset_path"]).is_file() for item in navigation["photos"])
        )
        physical = self.dataset["physical_evidence"]
        self.assertEqual(physical["status"], "reviewed_board_coordinate_registration")
        self.assertEqual(len(physical["images"]), 2)
        self.assertFalse(physical["downstream_admission"]["golden_sample"])

    def test_exposes_source_bounded_case_navigation_and_gap_audit(self):
        navigation = self.dataset["case_navigation"]
        self.assertEqual(navigation["schema_version"], "H897-CASE-NAVIGATION-V1")
        self.assertEqual(navigation["case_count"], 13)
        self.assertEqual(navigation["unique_photo_count"], 14)
        self.assertEqual(len(navigation["cases"]), 13)
        self.assertTrue(all(case["repair_causality_claim_allowed"] is False for case in navigation["cases"]))
        self.assertTrue(all(case["defect_label_allowed"] is False for case in navigation["cases"]))
        self.assertTrue(all("reported_action" not in case for case in navigation["cases"]))
        self.assertTrue(
            all(
                key not in str(navigation).lower()
                for key in ("imei", "technician", "country", "operator")
            )
        )
        by_id = {case["case_id"]: case for case in navigation["cases"]}
        self.assertEqual(by_id["CASE-0011-KJ6"]["candidate_component_ids"], ["H897-MAIN-U1001"])
        self.assertEqual(
            by_id["CASE-0017"]["candidate_component_ids"],
            ["H897-MAIN-U4101", "H897-MAIN-U4102"],
        )
        self.assertEqual(by_id["CASE-0013"]["navigation_scope"], "board_only")
        self.assertEqual(
            {item["field_id"] for item in navigation["missing_fields"]},
            {
                "probe_location",
                "tool_and_mode",
                "measured_value",
                "reference_or_tolerance",
                "branch_logic",
                "repair_action_detail",
                "post_repair_recheck",
            },
        )


if __name__ == "__main__":
    unittest.main()
