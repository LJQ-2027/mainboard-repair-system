import copy
import json
import unittest
from pathlib import Path

import jsonschema

from scripts.export_visual_qc_coco import build_coco_dataset
from scripts.validate_visual_qc_dataset import validate_visual_qc_case


ROOT = Path(__file__).resolve().parents[1]


def sample_case():
    return {
        "schema_version": "VISUAL-QC-CASE-V1",
        "case_id": "case-km4-001",
        "board_key": "km4-f151",
        "board_id": "BOARD-KM4-F151-MAIN-V1.2",
        "side_id": "main_page_2",
        "storage_scope": "local_only",
        "capture_stage": "before_repair",
        "image": {
            "file_name": "km4-before.jpg",
            "mime_type": "image/jpeg",
            "width": 2400,
            "height": 1800,
            "sha256": "a" * 64,
            "evidence_role": "physical_capture",
        },
        "quality": {
            "status": "good",
            "score": 91,
            "metrics": {"sharpness": 18.2},
        },
        "registration": {
            "method": "reviewed_manual_homography",
            "status": "reviewed",
            "matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
            "solve_anchors": [
                {"board": {"x": 0.1, "y": 0.1}, "image": {"x": 0.1, "y": 0.1}},
                {"board": {"x": 0.9, "y": 0.1}, "image": {"x": 0.9, "y": 0.1}},
                {"board": {"x": 0.9, "y": 0.9}, "image": {"x": 0.9, "y": 0.9}},
                {"board": {"x": 0.1, "y": 0.9}, "image": {"x": 0.1, "y": 0.9}},
            ],
            "check_points": [
                {"board": {"x": 0.5, "y": 0.5}, "image": {"x": 0.501, "y": 0.499}},
            ],
            "error": {"count": 1, "rms": 0.001414, "maximum": 0.001414},
        },
        "annotations": [
            {
                "annotation_id": "annotation-001",
                "category": "burn_or_heat_damage",
                "source": "human_annotation",
                "review_status": "confirmed",
                "component": {"component_id": "KM4-F151-P2-U4000", "designator": "U4000"},
                "image_geometry": {
                    "type": "rectangle",
                    "points": [{"x": 0.2, "y": 0.3}, {"x": 0.4, "y": 0.6}],
                },
                "board_geometry": {
                    "type": "polygon",
                    "points": [
                        {"x": 0.2, "y": 0.3},
                        {"x": 0.4, "y": 0.3},
                        {"x": 0.4, "y": 0.6},
                        {"x": 0.2, "y": 0.6},
                    ],
                },
                "note": "",
            }
        ],
        "qc_result": {"status": "confirmed_anomaly", "reviewed_at": "2026-07-17T12:00:00Z"},
    }


class VisualQcDatasetTests(unittest.TestCase):
    def test_reviewed_case_passes_board_and_training_contract(self):
        self.assertEqual(validate_visual_qc_case(sample_case(), ROOT), [])

    def test_server_authoritative_v2_case_accepts_reviewed_automatic_registration(self):
        visual_case = sample_case()
        visual_case["schema_version"] = "VISUAL-QC-CASE-V2"
        visual_case["storage_scope"] = "server_authoritative_with_local_draft"
        visual_case["capture_session"] = {
            "schema_version": "VISUAL-QC-CAPTURE-SESSION-V1",
            "session_id": "capture-session-001",
            "setup_id": "standard-bench",
            "expected_side_ids": ["main_page_1", "main_page_2"],
            "captured_side_ids": ["main_page_2"],
            "pair_status": "pair_in_progress",
            "checklist": {
                "status": "confirmed",
                "items": {
                    "board_and_side_confirmed": True,
                    "focus_and_lens_confirmed": True,
                    "lighting_and_occlusion_confirmed": True,
                },
                "confirmed_at": "2026-07-20T10:00:00Z",
            },
        }
        visual_case["registration"] = {
            "method": "automatic_feature_homography",
            "status": "reviewed",
            "matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
            "solve_anchors": [],
            "check_points": [],
            "error": {"count": 240, "rms": 0.001, "maximum": 0.003},
            "server_review_id": "regrev-001",
        }
        visual_case["server_sync"] = {
            "schema_version": "VISUAL-QC-SERVER-SYNC-V1",
            "status": "reviewed",
            "idempotency_key": "visual-qc:case-km4-001:aaaaaaaaaaaaaaaa",
            "server_case_id": "server-case-001",
            "server_image_id": "server-image-001",
            "job_id": "job-001",
            "job_status": "succeeded",
        }
        visual_case["visual_comparison"] = {
            "capture_setup_id": "standard-bench",
            "golden_sample": None,
            "difference": None,
        }
        visual_case["server_qc_review"] = {
            "qc_review_id": "qcrev-001",
            "case_id": "case-km4-001",
            "registration_review_id": "regrev-001",
            "reviewer_id": "technician-001",
            "version": 1,
            "qc_result": "confirmed_anomaly",
            "annotations": visual_case["annotations"],
            "notes": "",
            "created_at": "2026-07-20T12:00:00Z",
            "training_status": "eligible",
        }

        self.assertEqual(validate_visual_qc_case(visual_case, ROOT), [])
        schema = json.loads(
            (ROOT / "knowledge-base/visual-qc-case-v2-schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.validate(visual_case, schema)

    def test_server_authoritative_training_case_requires_matching_server_qc_review(self):
        visual_case = sample_case()
        visual_case["schema_version"] = "VISUAL-QC-CASE-V2"
        visual_case["storage_scope"] = "server_authoritative_with_local_draft"

        errors = validate_visual_qc_case(visual_case, ROOT, training_ready=True)

        self.assertIn(
            "training server-authoritative V2 cases require an eligible server QC review",
            errors,
        )

    def test_training_ready_v2_case_requires_confirmed_capture_checklist(self):
        visual_case = sample_case()
        visual_case["schema_version"] = "VISUAL-QC-CASE-V2"
        visual_case["storage_scope"] = "server_authoritative_with_local_draft"
        visual_case["capture_session"] = {
            "schema_version": "VISUAL-QC-CAPTURE-SESSION-V1",
            "session_id": "capture-session-002",
            "setup_id": "standard-bench",
            "expected_side_ids": ["main_page_1", "main_page_2"],
            "captured_side_ids": ["main_page_2"],
            "pair_status": "pair_in_progress",
            "checklist": {
                "status": "pending",
                "items": {
                    "board_and_side_confirmed": True,
                    "focus_and_lens_confirmed": False,
                    "lighting_and_occlusion_confirmed": True,
                },
                "confirmed_at": None,
            },
        }

        errors = validate_visual_qc_case(visual_case, ROOT, training_ready=True)

        self.assertIn(
            "training V2 cases require a confirmed physical capture checklist",
            errors,
        )

    def test_malformed_capture_session_returns_validation_errors_instead_of_crashing(self):
        visual_case = sample_case()
        visual_case["schema_version"] = "VISUAL-QC-CASE-V2"
        visual_case["storage_scope"] = "server_authoritative_with_local_draft"
        visual_case["capture_session"] = {
            "schema_version": "VISUAL-QC-CAPTURE-SESSION-V1",
            "session_id": "capture-session-malformed",
            "setup_id": "standard-bench",
            "expected_side_ids": [["main_page_1"], "main_page_2"],
            "captured_side_ids": [{"side_id": "main_page_2"}],
            "pair_status": "pair_in_progress",
            "checklist": [],
        }

        errors = validate_visual_qc_case(visual_case, ROOT)

        self.assertIn(
            "capture_session expected_side_ids must match the board manifest",
            errors,
        )
        self.assertIn("capture_session captured_side_ids are invalid", errors)
        self.assertIn("capture_session checklist must be an object", errors)

    def test_invalid_hash_and_cross_board_identity_are_rejected(self):
        visual_case = sample_case()
        visual_case["image"]["sha256"] = "bad"
        visual_case["board_id"] = "BOARD-WRONG"

        errors = validate_visual_qc_case(visual_case, ROOT)

        self.assertIn("image sha256 must contain 64 lowercase hexadecimal characters", errors)
        self.assertIn("board_id does not match the board catalog dataset", errors)

    def test_draft_registration_and_suspected_labels_are_not_training_ready(self):
        visual_case = sample_case()
        visual_case["registration"]["status"] = "draft"
        visual_case["annotations"][0]["review_status"] = "suspected"
        visual_case["qc_result"]["status"] = "needs_review"

        errors = validate_visual_qc_case(visual_case, ROOT, training_ready=True)

        self.assertIn("training cases require reviewed registration", errors)
        self.assertIn("training annotations must be confirmed human annotations or rejected non-defects", errors)

    def test_proxy_sample_is_valid_for_workbench_review_but_not_training(self):
        visual_case = sample_case()
        visual_case["image"]["evidence_role"] = "proxy_sample"

        self.assertEqual(validate_visual_qc_case(visual_case, ROOT), [])
        self.assertIn(
            "training cases require physical capture images",
            validate_visual_qc_case(visual_case, ROOT, training_ready=True),
        )

    def test_partial_anchor_draft_is_valid_but_not_training_ready(self):
        visual_case = sample_case()
        visual_case["registration"]["status"] = "draft"
        visual_case["registration"]["matrix"] = None
        visual_case["registration"]["solve_anchors"] = visual_case["registration"]["solve_anchors"][:2]
        visual_case["registration"]["check_points"] = []
        visual_case["registration"]["error"] = {
            "count": 0,
            "rms": None,
            "maximum": None,
        }
        visual_case["annotations"] = []
        visual_case["qc_result"] = {"status": "needs_review", "reviewed_at": None}

        self.assertEqual(validate_visual_qc_case(visual_case, ROOT), [])
        self.assertIn(
            "training cases require reviewed registration",
            validate_visual_qc_case(visual_case, ROOT, training_ready=True),
        )

    def test_reviewed_registration_matrix_must_match_anchors_and_recorded_error(self):
        visual_case = sample_case()
        visual_case["registration"]["matrix"] = [1, 0, 0.2, 0, 1, 0, 0, 0, 1]
        visual_case["registration"]["error"]["count"] = 9

        errors = validate_visual_qc_case(visual_case, ROOT)

        self.assertIn("registration matrix does not project the declared solve anchors", errors)
        self.assertIn("registration error count does not match check_points", errors)

    def test_compiled_geometry_designator_is_a_valid_component_link(self):
        self.assertEqual(validate_visual_qc_case(sample_case(), ROOT), [])

    def test_component_from_another_board_side_and_stale_board_geometry_are_rejected(self):
        visual_case = sample_case()
        visual_case["annotations"][0]["component"] = {
            "component_id": "KM4-F151-P1-U4000",
            "designator": "U4000",
        }
        visual_case["annotations"][0]["board_geometry"]["points"][0]["x"] += 0.02

        errors = validate_visual_qc_case(visual_case, ROOT)

        self.assertIn("annotation-001 component does not resolve on the selected board side", errors)
        self.assertIn("annotation-001 board_geometry does not match the registration matrix", errors)

    def test_training_qc_result_must_agree_with_confirmed_annotations(self):
        no_anomaly = sample_case()
        no_anomaly["qc_result"]["status"] = "no_visible_anomaly"
        self.assertIn(
            "no_visible_anomaly cannot contain confirmed annotations",
            validate_visual_qc_case(no_anomaly, ROOT, training_ready=True),
        )

        confirmed = sample_case()
        confirmed["annotations"][0]["review_status"] = "not_defect"
        self.assertIn(
            "confirmed_anomaly requires at least one confirmed annotation",
            validate_visual_qc_case(confirmed, ROOT, training_ready=True),
        )

    def test_coco_export_is_deterministic_and_uses_source_photo_geometry(self):
        first = sample_case()
        second = copy.deepcopy(first)
        second["case_id"] = "case-km4-002"
        second["image"]["file_name"] = "km4-after.jpg"
        second["image"]["sha256"] = "b" * 64
        second["annotations"] = []
        second["qc_result"] = {
            "status": "no_visible_anomaly",
            "reviewed_at": "2026-07-17T13:00:00Z",
        }

        coco = build_coco_dataset([second, first], ROOT)

        self.assertEqual([image["file_name"] for image in coco["images"]], [
            "km4-before.jpg",
            "km4-after.jpg",
        ])
        self.assertEqual(len(coco["annotations"]), 1)
        self.assertEqual(coco["annotations"][0]["bbox"], [480.0, 540.0, 480.0, 540.0])
        self.assertEqual(coco["annotations"][0]["area"], 259200.0)
        self.assertEqual(coco["annotations"][0]["attributes"]["designator"], "U4000")
        self.assertEqual(coco, build_coco_dataset([first, second], ROOT))

    def test_coco_polygon_area_uses_the_polygon_instead_of_its_bounding_box(self):
        visual_case = sample_case()
        visual_case["image"]["width"] = 100
        visual_case["image"]["height"] = 100
        visual_case["annotations"][0]["image_geometry"] = {
            "type": "polygon",
            "points": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.5, "y": 0.1},
                {"x": 0.1, "y": 0.5},
            ],
        }
        visual_case["annotations"][0]["board_geometry"] = copy.deepcopy(
            visual_case["annotations"][0]["image_geometry"]
        )

        annotation = build_coco_dataset([visual_case], ROOT)["annotations"][0]

        self.assertEqual(annotation["bbox"], [10.0, 10.0, 40.0, 40.0])
        self.assertEqual(annotation["area"], 800.0)

    def test_coco_export_rejects_duplicate_case_ids(self):
        first = sample_case()
        second = copy.deepcopy(first)

        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            build_coco_dataset([first, second], ROOT)


if __name__ == "__main__":
    unittest.main()
