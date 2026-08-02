import copy
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

    def test_builds_thirteen_source_linked_location_only_entities(self):
        entities = self.dataset["entities"]
        self.assertEqual(len(entities), 13)
        self.assertEqual(
            {entity["designator"] for entity in entities},
            {
                "U1001",
                "U2001",
                "U3001",
                "U3101",
                "U4001",
                "U4002",
                "U2411",
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

    def test_exposes_u2411_no_display_evidence_without_repair_causality(self):
        entity = next(
            item for item in self.dataset["entities"]
            if item["component_id"] == "XK67J-MAIN-U2411"
        )

        self.assertEqual(entity["side_id"], "main_page_2")
        self.assertEqual(entity["name"], "OCP2130WPAD-G LCM bias IC")
        self.assertEqual(entity["schematic_links"][0]["page"], "9")
        self.assertEqual(
            entity["schematic_links"][0]["facts"],
            [
                "Exact schematic designator U2411",
                "Part marking OCP2130WPAD-G",
                "LCM BIAS circuit includes AVDD_LCM and AVEE_LCM",
            ],
        )
        self.assertEqual(entity["repair_links"][0]["evidence_role"], "field_case_context_only")
        self.assertFalse(entity["repair_links"][0]["repair_causality_claim_allowed"])

    def test_no_display_case_evidence_is_privacy_reduced_and_hash_bound(self):
        evidence = self.dataset["repair_case_evidence"]

        self.assertEqual(evidence["fault"], "No display")
        self.assertEqual(evidence["source_symptom"], "无显示")
        self.assertEqual(evidence["source_finding"], "显示IC坏")
        self.assertEqual(
            [case["case_id"] for case in evidence["cases"]],
            ["CASE-0022", "CASE-0025"],
        )
        self.assertTrue(all(case["board_state"] == "维修后已修复" for case in evidence["cases"]))
        self.assertEqual(
            evidence["source_photo_sha256"],
            "28a193f9bbd0750240fb20477f5ec0497de7f279868b408eab7c872dcd0273d6",
        )
        self.assertEqual(evidence["reviewed_target_component_id"], "XK67J-MAIN-U2411")
        self.assertEqual(evidence["reviewed_target_method"], "annotation_center_inverse_projection")
        self.assertFalse(evidence["repair_causality_claim_allowed"])
        serialized = str(evidence).lower()
        for forbidden in ("imei", "350314", "country", "operator", "罗涛"):
            self.assertNotIn(forbidden, serialized)

    def test_no_display_flow_records_location_check_and_stops_at_source_boundary(self):
        self.assertEqual(self.dataset["repair_coverage"]["status"], "source_boundary_only")
        self.assertEqual(len(self.dataset["repair_flows"]), 1)
        flow = self.dataset["repair_flows"][0]

        self.assertEqual(flow["flow_id"], "xk67j-no-display-u2411-location-check")
        self.assertEqual(flow["entry_label"], "无显示")
        self.assertEqual(flow["entry_component_id"], "XK67J-MAIN-U2411")
        self.assertEqual(flow["source_status"], "reviewed_partial")
        self.assertEqual(flow["source"]["label"], "案例 CASE-0022 / CASE-0025 · SCH 第 9 页")
        self.assertEqual(flow["source_photo_sha256"], self.dataset["repair_case_evidence"]["source_photo_sha256"])
        self.assertEqual(len(flow["steps"]), 1)
        step = flow["steps"][0]
        self.assertEqual(step["target_component_id"], "XK67J-MAIN-U2411")
        self.assertEqual(
            {choice["value"] for choice in step["choices"]},
            {"location_match", "location_unconfirmed"},
        )
        self.assertTrue(all(choice["outcome"]["kind"] == "boundary" for choice in step["choices"]))
        flow_text = str(flow)
        for unsupported in ("更换", "补焊", "重焊", "电压正常", "阻值正常"):
            self.assertNotIn(unsupported, flow_text)

    def test_source_boundary_only_coverage_rejects_action_outcomes(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["repair_flows"][0]["steps"][0]["choices"][0]["outcome"]["kind"] = "action"

        self.assertTrue(any(
            "source-boundary-only coverage cannot expose action outcomes" in error
            for error in validate_dataset(dataset, ROOT)
        ))

    def test_existing_flows_reject_a_tampered_no_source_coverage_status(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["repair_coverage"]["status"] = "source_unavailable"
        dataset["repair_flows"][0]["steps"][0]["choices"][0]["outcome"]["kind"] = "action"

        self.assertTrue(any(
            "repair coverage status is incompatible with existing flows" in error
            for error in validate_dataset(dataset, ROOT)
        ))

    def test_repair_case_evidence_requires_the_exact_reviewed_photo(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["repair_case_evidence"]["source_photo_sha256"] = "0" * 64

        self.assertTrue(any(
            "repair case evidence photo must resolve" in error
            for error in validate_dataset(dataset, ROOT)
        ))

    def test_repair_case_evidence_cross_references_flow_target_and_hash(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["repair_case_evidence"]["reviewed_target_component_id"] = "XK67J-MAIN-U4002"
        dataset["repair_flows"][0]["source_photo_sha256"] = "1" * 64

        errors = validate_dataset(dataset, ROOT)
        self.assertTrue(any("repair case evidence target must match" in error for error in errors))
        self.assertTrue(any("repair flow evidence photo must match" in error for error in errors))

    def test_repair_case_evidence_rejects_terminal_target_drift(self):
        dataset = copy.deepcopy(self.dataset)
        for choice in dataset["repair_flows"][0]["steps"][0]["choices"]:
            choice["outcome"]["target_component_id"] = "XK67J-MAIN-U4002"

        self.assertTrue(any(
            "repair case evidence target must match every repair flow target" in error
            for error in validate_dataset(dataset, ROOT)
        ))

    def test_repair_case_evidence_requires_nonempty_case_identities(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["repair_case_evidence"]["cases"] = []
        dataset["repair_flows"][0]["source_case_ids"] = []

        self.assertTrue(any(
            "repair case evidence requires source case identities" in error
            for error in validate_dataset(dataset, ROOT)
        ))

    def test_repair_case_evidence_rejects_private_fields_and_causality_claims(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["repair_case_evidence"]["imei"] = "350314000000000"
        dataset["repair_case_evidence"]["repair_causality_claim_allowed"] = True

        errors = validate_dataset(dataset, ROOT)
        self.assertTrue(any("repair case evidence contains prohibited private fields" in error for error in errors))
        self.assertTrue(any("repair case evidence cannot allow repair causality" in error for error in errors))

    def test_links_reviewed_board_coordinate_registrations_without_downstream_claims(self):
        evidence = self.dataset["physical_evidence"]
        self.assertEqual(evidence["status"], "reviewed_board_coordinate_registration")
        self.assertEqual(evidence["board_revision"], "XK67J_MAIN V1.0")
        self.assertEqual(len(evidence["unique_image_sha256"]), 3)
        self.assertEqual(
            self.dataset["registration"]["reference_mode"],
            "reviewed_physical_photo_navigation",
        )

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

    def test_embeds_hash_bound_reviewed_photo_navigation(self):
        registration = self.dataset["registration"]

        self.assertEqual(
            registration["reference_mode"],
            "reviewed_physical_photo_navigation",
        )
        navigation = registration["photo_navigation"]
        self.assertEqual(navigation["schema_version"], "XK67J-PHOTO-NAVIGATION-V1")
        self.assertEqual(len(navigation["photos"]), 3)
        self.assertEqual(
            [item["side_id"] for item in navigation["photos"]],
            ["main_page_1", "main_page_2", "main_page_2"],
        )
        self.assertTrue(
            all(len(item["board_to_image_matrix"]) == 9 for item in navigation["photos"])
        )
        self.assertTrue(
            all((ROOT / item["asset_path"]).is_file() for item in navigation["photos"])
        )

    def test_dataset_passes_the_shared_registration_contract(self):
        self.assertEqual(validate_dataset(self.dataset, ROOT), [])

    def test_shared_contract_rejects_photo_asset_hash_mismatch(self):
        dataset = copy.deepcopy(self.dataset)
        photos = dataset["registration"]["photo_navigation"]["photos"]
        photos[0]["asset_path"] = photos[1]["asset_path"]

        self.assertTrue(any(
            "derivative hash does not match" in error
            for error in validate_dataset(dataset, ROOT)
        ))


if __name__ == "__main__":
    unittest.main()
