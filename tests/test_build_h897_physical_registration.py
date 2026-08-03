import unittest

from scripts.build_h897_physical_registration import build_manifest


class H897PhysicalRegistrationTests(unittest.TestCase):
    def test_builds_one_reviewed_hash_bound_registration_per_side(self):
        manifest = build_manifest()

        self.assertEqual(
            manifest["schema_version"], "H897-PHYSICAL-REGISTRATION-REVIEW-V1"
        )
        self.assertEqual(manifest["board_key"], "kj6-h897")
        self.assertEqual(manifest["board_id"], "BOARD-H897-MAIN-V1.2")
        self.assertEqual(len(manifest["images"]), 2)
        self.assertEqual(
            {item["side_id"] for item in manifest["images"]},
            {"main_page_1", "main_page_2"},
        )
        self.assertEqual(
            {item["sha256"] for item in manifest["images"]},
            {
                "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48",
                "a862ecee11e683562ccfdc9a7743d813accfd37235e0267665bf32b44d9fe491",
            },
        )

        for item in manifest["images"]:
            review = item["registration_review"]
            self.assertEqual(item["registration_status"], "reviewed_manual_registration")
            self.assertEqual(review["review_status"], "reviewed")
            self.assertEqual(len(review["solve_anchors"]), 4)
            self.assertGreaterEqual(len(review["independent_check_points"]), 3)
            self.assertEqual(len(review["board_to_image_matrix"]), 9)
            self.assertLessEqual(review["error"]["maximum"], 0.05)
            self.assertFalse(review["field_accuracy_claim_allowed"])

    def test_preserves_evidence_boundaries(self):
        manifest = build_manifest()

        self.assertEqual(
            manifest["threshold_policy"], "no_industrial_pass_threshold_declared"
        )
        self.assertFalse(manifest["field_accuracy_claim_allowed"])
        self.assertEqual(
            manifest["downstream_admission"],
            {
                "golden_sample": False,
                "defect_label": False,
                "training_data": False,
                "repair_causality": False,
            },
        )
        self.assertTrue(
            all(not item["source_annotation_present"] for item in manifest["images"])
        )


if __name__ == "__main__":
    unittest.main()
