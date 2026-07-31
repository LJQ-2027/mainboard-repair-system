import unittest
from pathlib import Path

from scripts.build_xk67j_registration import build_dataset
from scripts.validate_cross_source_registration import validate_dataset


ROOT = Path(__file__).resolve().parents[1]


class Xk67jRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = build_dataset(ROOT)

    def test_exposes_five_aliases_with_distinct_evidence_levels(self):
        self.assertEqual(
            self.dataset["compatible_models"],
            ["KM4n", "KM4k", "KM5", "KM5n", "KM5s"],
        )
        self.assertEqual(
            self.dataset["model_evidence"],
            {
                "KM4n": "photo_verified_shared_platform",
                "KM4k": "owner_confirmed_alias",
                "KM5": "engineering_source",
                "KM5n": "owner_confirmed_alias",
                "KM5s": "owner_confirmed_alias",
            },
        )

    def test_builds_twelve_source_linked_location_only_entities(self):
        entities = self.dataset["entities"]
        self.assertEqual(len(entities), 12)
        self.assertEqual(
            {entity["designator"] for entity in entities},
            {
                "U1001",
                "U2001",
                "U3001",
                "U3101",
                "U4001",
                "U4002",
                "U5007",
                "J2810",
                "J6102",
                "J6402",
                "J6501",
                "X2101",
            },
        )
        self.assertTrue(
            all(entity["geometry"]["source_status"] == "location_only" for entity in entities)
        )
        self.assertTrue(all(entity["schematic_links"] for entity in entities))
        self.assertTrue(all("inspection_profile" not in entity for entity in entities))

    def test_links_reviewed_board_coordinate_registrations_without_downstream_claims(self):
        evidence = self.dataset["physical_evidence"]
        self.assertEqual(evidence["status"], "reviewed_board_coordinate_registration")
        self.assertEqual(evidence["board_revision"], "XK67J_MAIN V1.0")
        self.assertEqual(len(evidence["unique_image_sha256"]), 3)
        self.assertEqual(self.dataset["registration"]["reference_mode"], "point_map_only")

        images = {item["sha256"]: item for item in evidence["images"]}
        self.assertEqual(
            images["1a3e4bdb3f5019656cd0910544e4f825b0eb94c3f85bf6668c956cd6a757687d"][
                "registration_status"
            ],
            "reviewed_manual_registration",
        )
        self.assertEqual(
            images["57a9b1d36326cd0a0b1cee3a0bc622290728cbb1b4775cfab5182b9b84138fa6"][
                "side_id"
            ],
            "main_page_1",
        )
        self.assertEqual(
            images["28a193f9bbd0750240fb20477f5ec0497de7f279868b408eab7c872dcd0273d6"][
                "registration_status"
            ],
            "reviewed_manual_registration",
        )
        self.assertEqual(
            images["28a193f9bbd0750240fb20477f5ec0497de7f279868b408eab7c872dcd0273d6"][
                "view_scope"
            ],
            "full_board_repair_case",
        )
        self.assertTrue(all(item["view_scope"] == "full_board_repair_case" for item in images.values()))
        self.assertTrue(all(item["registration_review"]["review_status"] == "reviewed" for item in images.values()))
        self.assertTrue(all(item["registration_review"]["field_accuracy_claim_allowed"] is False for item in images.values()))
        self.assertEqual(evidence["downstream_admission"], {
            "golden_sample": False,
            "defect_label": False,
            "training_data": False,
            "repair_causality": False,
        })

    def test_dataset_passes_the_shared_registration_contract(self):
        self.assertEqual(validate_dataset(self.dataset, ROOT), [])


if __name__ == "__main__":
    unittest.main()
