import copy
import math
import unittest

from scripts.build_xk67j_physical_registration import build_manifest
from scripts.visual_qc.reviewed_registration import build_review, project_point, solve_homography


class Xk67jPhysicalRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = build_manifest()

    def test_builds_three_reviewed_full_board_records(self):
        self.assertEqual(
            self.manifest["schema_version"],
            "XK67J-PHYSICAL-REGISTRATION-REVIEW-V1",
        )
        self.assertEqual(len(self.manifest["images"]), 3)
        self.assertTrue(
            all(item["view_scope"] == "full_board_repair_case" for item in self.manifest["images"])
        )
        self.assertTrue(all("source_path" not in item for item in self.manifest["images"]))
        self.assertTrue(all(item["automatic_registration"]["status"] == "failed" for item in self.manifest["images"]))
        page_one = next(item for item in self.manifest["images"] if item["side_id"] == "main_page_1")
        self.assertEqual(page_one["source_dimensions"], {"width": 3024, "height": 4032})
        self.assertEqual(page_one["registration_transform"], "rotate_90_counterclockwise")
        self.assertEqual(page_one["registration_dimensions"], {"width": 4032, "height": 3024})
        page_two = next(item for item in self.manifest["images"] if item["side_id"] == "main_page_2")
        outline_anchor = next(
            pair for pair in page_two["registration_review"]["solve_anchors"]
            if pair["landmark_id"] == "outline_upper_right"
        )
        self.assertEqual(outline_anchor["selection_basis"], "outline_assisted_estimate")

    def test_reviews_are_auditable_and_reproject_solve_anchors(self):
        for item in self.manifest["images"]:
            review = item["registration_review"]
            self.assertEqual(review["method"], "reviewed_manual_four_point")
            self.assertEqual(review["review_status"], "reviewed")
            self.assertEqual(review["review_scope"], "board_coordinate_alignment")
            self.assertEqual(len(review["board_to_image_matrix"]), 9)
            self.assertEqual(len(review["solve_anchors"]), 4)
            self.assertGreaterEqual(len(review["independent_check_points"]), 3)
            self.assertFalse(review["field_accuracy_claim_allowed"])
            for pair in review["solve_anchors"]:
                projected = project_point(review["board_to_image_matrix"], pair["board"])
                self.assertLess(
                    math.hypot(
                        projected["x"] - pair["image"]["x"],
                        projected["y"] - pair["image"]["y"],
                    ),
                    1e-5,
                )

    def test_independent_error_is_recomputed_and_bounded_only_for_this_review(self):
        maxima = {}
        for item in self.manifest["images"]:
            review = item["registration_review"]
            errors = []
            for pair in review["independent_check_points"]:
                projected = project_point(review["board_to_image_matrix"], pair["board"])
                errors.append(
                    math.hypot(
                        projected["x"] - pair["image"]["x"],
                        projected["y"] - pair["image"]["y"],
                    )
                )
            self.assertAlmostEqual(review["error"]["rms"], math.sqrt(sum(value * value for value in errors) / len(errors)), places=6)
            self.assertAlmostEqual(review["error"]["maximum"], max(errors), places=6)
            maxima[item["side_id"]] = max(maxima.get(item["side_id"], 0), max(errors))
        self.assertLess(maxima["main_page_1"], 0.03)
        self.assertLess(maxima["main_page_2"], 0.05)
        self.assertEqual(self.manifest["threshold_policy"], "no_industrial_pass_threshold_declared")

    def test_same_page_two_capture_geometry_reuses_the_reviewed_matrix(self):
        page_two = [item for item in self.manifest["images"] if item["side_id"] == "main_page_2"]
        self.assertEqual(len(page_two), 2)
        self.assertEqual(page_two[0]["capture_geometry_id"], page_two[1]["capture_geometry_id"])
        self.assertEqual(
            page_two[0]["registration_review"]["board_to_image_matrix"],
            page_two[1]["registration_review"]["board_to_image_matrix"],
        )

    def test_review_never_admits_downstream_labels_or_accuracy_claims(self):
        self.assertEqual(
            self.manifest["downstream_admission"],
            {
                "golden_sample": False,
                "defect_label": False,
                "training_data": False,
                "repair_causality": False,
            },
        )
        self.assertFalse(self.manifest["field_accuracy_claim_allowed"])

    def test_solver_rejects_duplicate_degenerate_and_misordered_anchors(self):
        square = [
            {"board": {"x": 0.1, "y": 0.1}, "image": {"x": 0.2, "y": 0.2}},
            {"board": {"x": 0.1, "y": 0.9}, "image": {"x": 0.2, "y": 0.8}},
            {"board": {"x": 0.9, "y": 0.9}, "image": {"x": 0.8, "y": 0.8}},
            {"board": {"x": 0.9, "y": 0.1}, "image": {"x": 0.8, "y": 0.2}},
        ]
        duplicate = [dict(pair) for pair in square]
        duplicate[3] = duplicate[0]
        with self.assertRaisesRegex(ValueError, "distinct"):
            solve_homography(duplicate)

        collinear = [
            {"board": {"x": value, "y": value}, "image": {"x": value, "y": value}}
            for value in (0.1, 0.3, 0.6, 0.9)
        ]
        with self.assertRaisesRegex(ValueError, "degenerate"):
            solve_homography(collinear)

        reversed_target = copy.deepcopy(square)
        reversed_target[1]["image"], reversed_target[3]["image"] = (
            reversed_target[3]["image"],
            reversed_target[1]["image"],
        )
        with self.assertRaisesRegex(ValueError, "winding"):
            solve_homography(reversed_target)

        concave_target = copy.deepcopy(square)
        concave_target[2]["image"] = {"x": 0.3, "y": 0.5}
        with self.assertRaisesRegex(ValueError, "convex"):
            solve_homography(concave_target)

    def test_review_rejects_error_above_the_board_coordinate_guardrail(self):
        anchors = [
            {
                "landmark_id": f"corner_{index}",
                "label": f"Corner {index}",
                "board": {"x": x, "y": y},
                "image": {"x": x, "y": y},
            }
            for index, (x, y) in enumerate(((0.1, 0.1), (0.1, 0.9), (0.9, 0.9), (0.9, 0.1)))
        ]
        checks = [
            {
                "landmark_id": "bad_check",
                "label": "Bad check",
                "board": {"x": 0.5, "y": 0.5},
                "image": {"x": 0.7, "y": 0.7},
            }
        ]
        with self.assertRaisesRegex(ValueError, "guardrail"):
            build_review(
                solve_anchors=anchors,
                independent_check_points=checks,
                selection_basis="test",
                review_note="test",
            )


if __name__ == "__main__":
    unittest.main()
