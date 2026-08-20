import unittest
from pathlib import Path

import cv2
import numpy as np

from scripts.visual_qc.registration import (
    RegistrationConfig,
    locate_board_contour,
    register_board_image,
)
from scripts.visual_qc.synthetic import (
    SyntheticTransformConfig,
    generate_synthetic_capture,
)


ROOT = Path(__file__).resolve().parents[1]


def project_points(matrix, points):
    homography = np.asarray(matrix, dtype=np.float64).reshape(3, 3)
    source = np.asarray(points, dtype=np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(source, homography).reshape(-1, 2)


class VisualQcSyntheticTransformTests(unittest.TestCase):
    def test_synthetic_capture_is_deterministic_and_records_ground_truth(self):
        reference = np.full((360, 520, 3), 245, dtype=np.uint8)
        cv2.rectangle(reference, (45, 40), (470, 315), (35, 90, 70), 8)
        cv2.putText(reference, "KM4 U2001", (90, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (10, 10, 10), 3)
        config = SyntheticTransformConfig(
            rotation_degrees=7,
            perspective_jitter=0.08,
            crop_fraction=0.04,
            brightness_delta=-12,
            contrast=1.08,
            shadow_strength=0.16,
        )

        first_image, first_manifest = generate_synthetic_capture(reference, config, seed=20260720)
        second_image, second_manifest = generate_synthetic_capture(reference, config, seed=20260720)

        self.assertTrue(np.array_equal(first_image, second_image))
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first_manifest["evidence_role"], "synthetic_proxy")
        self.assertEqual(first_manifest["seed"], 20260720)
        self.assertEqual(len(first_manifest["expected_board_to_image_matrix"]), 9)
        self.assertEqual(first_image.shape, reference.shape)

    def test_contour_locator_reports_a_plausible_board_region(self):
        image = np.full((500, 700, 3), 244, dtype=np.uint8)
        board = np.array([[110, 75], [610, 95], [570, 425], [85, 390]], dtype=np.int32)
        cv2.fillConvexPoly(image, board, (28, 79, 64))
        cv2.circle(image, (200, 180), 25, (180, 180, 180), -1)

        contour = locate_board_contour(image)

        self.assertEqual(contour["status"], "candidate")
        self.assertGreater(contour["area_fraction"], 0.35)
        self.assertEqual(len(contour["polygon"]), 4)
        self.assertTrue(all(0 <= value <= 1 for point in contour["polygon"] for value in point))


class VisualQcAutomaticRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source_path = ROOT / "assets/board-atlas/km4-f151/main-point-map-page-2.png"
        cls.reference = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
        if cls.reference is None:
            raise RuntimeError(f"Unable to load registration reference: {source_path}")

    def test_feature_registration_recovers_a_synthetic_km4_transform(self):
        config = SyntheticTransformConfig(
            rotation_degrees=-6,
            perspective_jitter=0.055,
            crop_fraction=0.025,
            brightness_delta=-18,
            contrast=0.96,
            shadow_strength=0.12,
            max_dimension=1500,
        )
        capture, manifest = generate_synthetic_capture(self.reference, config, seed=41)

        result = register_board_image(
            self.reference,
            capture,
            RegistrationConfig(max_dimension=1500),
        )

        self.assertEqual(result["status"], "candidate", result)
        self.assertEqual(result["schema_version"], "VISUAL-QC-REGISTRATION-CANDIDATE-V1")
        self.assertEqual(result["method"], "automatic_feature_homography")
        self.assertEqual(result["review_status"], "draft")
        self.assertTrue(result["requires_human_review"])
        self.assertEqual(result["fallback"]["method"], "reviewed_manual_four_point")
        self.assertGreaterEqual(result["evidence"]["inlier_count"], 10)
        self.assertGreater(result["evidence"]["reference_coverage"], 0.08)

        corners = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float64)
        expected = project_points(manifest["expected_board_to_image_matrix"], corners)
        actual = project_points(result["board_to_image_matrix"], corners)
        mean_corner_error = np.linalg.norm(expected - actual, axis=1).mean()
        self.assertLess(mean_corner_error, 0.025)

    def test_blank_capture_returns_a_structured_manual_fallback(self):
        blank = np.full((900, 1200, 3), 255, dtype=np.uint8)

        result = register_board_image(
            self.reference,
            blank,
            RegistrationConfig(max_dimension=1200),
        )

        self.assertEqual(result["status"], "manual_required")
        self.assertIn(
            result["failure"]["code"],
            {"insufficient_keypoints", "insufficient_matches", "homography_not_found"},
        )
        self.assertEqual(result["fallback"]["method"], "reviewed_manual_four_point")
        self.assertIsNone(result["board_to_image_matrix"])
        self.assertFalse(result["requires_human_review"])


if __name__ == "__main__":
    unittest.main()
