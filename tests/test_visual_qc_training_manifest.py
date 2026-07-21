import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import jsonschema
import numpy as np
from fastapi.testclient import TestClient

from scripts.visual_qc.server.api import create_app
from scripts.visual_qc.server.config import VisualQcServerSettings


ROOT = Path(__file__).resolve().parents[1]


class VisualQcTrainingManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=Path(self.temp_dir.name),
            maximum_upload_bytes=20 * 1024 * 1024,
            minimum_image_dimension=64,
            worker_count=0,
        )
        self.app = create_app(settings)
        self.client = TestClient(self.app)
        reference = cv2.imread(
            str(ROOT / "assets/board-atlas/km4-f151/main-point-map-page-2.png"),
            cv2.IMREAD_COLOR,
        )
        reference = np.clip(reference.astype(np.float32) * 0.65, 0, 255).astype(
            np.uint8
        )
        ok, encoded = cv2.imencode(
            ".jpg",
            reference,
            [cv2.IMWRITE_JPEG_QUALITY, 95],
        )
        self.assertTrue(ok)
        self.image_bytes = encoded.tobytes()

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def create_processed_case(
        self,
        request_id,
        evidence_role="physical_capture",
    ):
        checklist = {
            "status": "confirmed",
            "items": {
                "board_and_side_confirmed": True,
                "focus_and_lens_confirmed": True,
                "lighting_and_occlusion_confirmed": True,
            },
            "confirmed_at": "2026-07-20T10:00:00.000Z",
        }
        response = self.client.post(
            "/api/v1/visual-qc/cases",
            data={
                "board_key": "km4-f151",
                "side_id": "main_page_2",
                "capture_stage": "before_repair",
                "evidence_role": evidence_role,
                "capture_session_id": f"capture-{request_id}",
                "capture_setup_id": "bench-a",
                "capture_checklist": json.dumps(checklist),
                "sha256": hashlib.sha256(self.image_bytes).hexdigest(),
            },
            files={"file": ("reference.jpg", self.image_bytes, "image/jpeg")},
            headers={
                "X-Actor-Id": "technician-001",
                "Idempotency-Key": request_id,
            },
        )
        self.assertEqual(response.status_code, 202)
        processed = self.app.state.visual_qc_service.process_next_job()
        self.assertEqual(processed["status"], "succeeded")
        return response.json()

    def accept_registration(self, case_id):
        response = self.client.post(
            f"/api/v1/visual-qc/cases/{case_id}/registration-reviews",
            json={
                "decision": "accept_automatic",
                "notes": "Overlay checked.",
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def submit_no_anomaly(self, case_id, notes=""):
        return self.client.post(
            f"/api/v1/visual-qc/cases/{case_id}/qc-reviews",
            json={
                "qc_result": "no_visible_anomaly",
                "annotations": [],
                "notes": notes,
            },
            headers={"X-Actor-Id": "technician-001"},
        )

    def test_final_review_is_versioned_and_exposed_in_reviewer_training_manifest(self):
        case = self.create_processed_case("training-case-001")
        self.accept_registration(case["case_id"])

        first = self.submit_no_anomaly(case["case_id"], "First review.")
        second = self.submit_no_anomaly(case["case_id"], "Second review.")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["version"], 1)
        self.assertEqual(first.json()["training_status"], "eligible")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["version"], 2)
        restored_case = self.client.get(
            f"/api/v1/visual-qc/cases/{case['case_id']}",
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(restored_case.status_code, 200)
        self.assertEqual(restored_case.json()["server_qc_review"]["version"], 2)

        forbidden = self.client.get(
            "/api/v1/visual-qc/datasets/training-manifest",
            headers={"X-Actor-Id": "technician-001"},
        )
        coco_forbidden = self.client.get(
            "/api/v1/visual-qc/datasets/coco",
            headers={"X-Actor-Id": "technician-001"},
        )
        manifest = self.client.get(
            "/api/v1/visual-qc/datasets/training-manifest",
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(coco_forbidden.status_code, 403)
        self.assertEqual(
            coco_forbidden.json()["detail"]["code"],
            "reviewer_role_required",
        )
        self.assertEqual(manifest.status_code, 200)
        payload = manifest.json()
        schema = json.loads(
            (
                ROOT
                / "knowledge-base"
                / "visual-qc-training-manifest-v1-schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.validate(payload, schema)
        self.assertEqual(payload["schema_version"], "VISUAL-QC-TRAINING-MANIFEST-V1")
        self.assertEqual(payload["case_count"], 1)
        self.assertEqual(payload["annotation_count"], 0)
        self.assertEqual(payload["cases"][0]["case_id"], case["case_id"])
        self.assertEqual(payload["cases"][0]["qc_review"]["version"], 2)
        self.assertEqual(payload["cases"][0]["image"]["sha256"], hashlib.sha256(self.image_bytes).hexdigest())

        image_id = payload["cases"][0]["image"]["image_id"]
        image_forbidden = self.client.get(
            f"/api/v1/visual-qc/datasets/images/{image_id}",
            headers={"X-Actor-Id": "technician-001"},
        )
        image_download = self.client.get(
            f"/api/v1/visual-qc/datasets/images/{image_id}",
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )
        self.assertEqual(image_forbidden.status_code, 403)
        self.assertEqual(image_download.status_code, 200)
        self.assertEqual(
            hashlib.sha256(image_download.content).hexdigest(),
            hashlib.sha256(self.image_bytes).hexdigest(),
        )

    def test_final_review_rejects_missing_registration_proxy_and_contradictory_result(self):
        unreviewed = self.create_processed_case("training-unreviewed")
        missing_registration = self.submit_no_anomaly(unreviewed["case_id"])
        self.assertEqual(missing_registration.status_code, 409)
        self.assertEqual(
            missing_registration.json()["detail"]["code"],
            "registration_review_required",
        )

        self.accept_registration(unreviewed["case_id"])
        contradictory = self.client.post(
            f"/api/v1/visual-qc/cases/{unreviewed['case_id']}/qc-reviews",
            json={
                "qc_result": "confirmed_anomaly",
                "annotations": [],
                "notes": "",
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(contradictory.status_code, 422)
        self.assertEqual(
            contradictory.json()["detail"]["code"],
            "confirmed_anomaly_requires_annotation",
        )

        proxy = self.create_processed_case(
            "training-proxy",
            evidence_role="service_manual_proxy",
        )
        self.accept_registration(proxy["case_id"])
        proxy_review = self.submit_no_anomaly(proxy["case_id"])
        self.assertEqual(proxy_review.status_code, 409)
        self.assertEqual(
            proxy_review.json()["detail"]["code"],
            "physical_capture_required",
        )

    def test_manual_registration_preserves_independent_check_evidence_for_training(self):
        case = self.create_processed_case("training-manual")
        review = self.client.post(
            f"/api/v1/visual-qc/cases/{case['case_id']}/registration-reviews",
            json={
                "decision": "accept_manual",
                "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                "anchors": [
                    {"board": [0, 0], "image": [0, 0]},
                    {"board": [1, 0], "image": [1, 0]},
                    {"board": [1, 1], "image": [1, 1]},
                    {"board": [0, 1], "image": [0, 1]},
                ],
                "check_points": [
                    {"board": [0.5, 0.5], "image": [0.5, 0.5]},
                ],
                "error": {"count": 1, "rms": 0, "maximum": 0},
                "notes": "Manual overlay and independent check reviewed.",
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        final = self.client.post(
            f"/api/v1/visual-qc/cases/{case['case_id']}/qc-reviews",
            json={
                "qc_result": "confirmed_anomaly",
                "annotations": [
                    {
                        "annotation_id": "annotation-001",
                        "category": "burn_or_heat_damage",
                        "source": "human_annotation",
                        "review_status": "confirmed",
                        "component": None,
                        "image_geometry": {
                            "type": "rectangle",
                            "points": [
                                {"x": 0.1, "y": 0.2},
                                {"x": 0.3, "y": 0.5},
                            ],
                        },
                        "board_geometry": {
                            "type": "polygon",
                            "points": [
                                {"x": 0.1, "y": 0.2},
                                {"x": 0.3, "y": 0.2},
                                {"x": 0.3, "y": 0.5},
                                {"x": 0.1, "y": 0.5},
                            ],
                        },
                        "note": "Reviewed visible damage.",
                    }
                ],
                "notes": "Training export integration sample.",
            },
            headers={"X-Actor-Id": "technician-001"},
        )

        self.assertEqual(review.status_code, 201)
        self.assertEqual(len(review.json()["check_points"]), 1)
        self.assertEqual(final.status_code, 201)
        self.assertEqual(final.json()["training_status"], "eligible")

        headers = {
            "X-Actor-Id": "reviewer-001",
            "X-Actor-Role": "reviewer",
        }
        first = self.client.get(
            "/api/v1/visual-qc/datasets/coco",
            headers=headers,
        )
        second = self.client.get(
            "/api/v1/visual-qc/datasets/coco",
            headers=headers,
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), second.json())
        payload = first.json()
        self.assertEqual(payload["info"]["version"], "VISUAL-QC-COCO-V1")
        self.assertEqual(len(payload["images"]), 1)
        self.assertEqual(len(payload["annotations"]), 1)
        self.assertEqual(payload["images"][0]["case_id"], case["case_id"])
        self.assertEqual(payload["annotations"][0]["category_id"], 1)
        self.assertEqual(
            payload["annotations"][0]["bbox"],
            [
                round(0.1 * payload["images"][0]["width"], 6),
                round(0.2 * payload["images"][0]["height"], 6),
                round(0.2 * payload["images"][0]["width"], 6),
                round(0.3 * payload["images"][0]["height"], 6),
            ],
        )
        schema = json.loads(
            (
                ROOT
                / "knowledge-base"
                / "visual-qc-coco-v1-schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.validate(payload, schema)

    def test_reviewer_dataset_audit_explains_the_current_training_gate(self):
        proxy = self.create_processed_case(
            "audit-proxy",
            evidence_role="service_manual_proxy",
        )
        waiting_registration = self.create_processed_case("audit-registration")
        eligible = self.create_processed_case("audit-eligible")
        self.accept_registration(eligible["case_id"])
        self.assertEqual(self.submit_no_anomaly(eligible["case_id"]).status_code, 201)

        forbidden = self.client.get(
            "/api/v1/visual-qc/datasets/audit",
            headers={"X-Actor-Id": "technician-001"},
        )
        first = self.client.get(
            "/api/v1/visual-qc/datasets/audit",
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )
        second = self.client.get(
            "/api/v1/visual-qc/datasets/audit",
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(first.status_code, 200)
        first_stable = {
            key: value for key, value in first.json().items() if key != "generated_at"
        }
        second_stable = {
            key: value for key, value in second.json().items() if key != "generated_at"
        }
        self.assertEqual(first_stable, second_stable)
        payload = first.json()
        jsonschema.validate(
            payload,
            json.loads(
                (
                    ROOT
                    / "knowledge-base"
                    / "visual-qc-dataset-audit-v1-schema.json"
                ).read_text(encoding="utf-8")
            ),
        )
        self.assertEqual(payload["schema_version"], "VISUAL-QC-DATASET-AUDIT-V1")
        self.assertEqual(payload["total_case_count"], 3)
        self.assertEqual(payload["eligible_case_count"], 1)
        self.assertEqual(payload["excluded_case_count"], 2)
        self.assertEqual(payload["reason_counts"], {
            "non_physical_evidence": 1,
            "registration_review_required": 1,
        })
        cases = {case["case_id"]: case for case in payload["cases"]}
        self.assertEqual(cases[proxy["case_id"]]["status"], "excluded")
        self.assertEqual(
            cases[proxy["case_id"]]["blocking_reason"],
            "non_physical_evidence",
        )
        self.assertEqual(
            cases[waiting_registration["case_id"]]["blocking_reason"],
            "registration_review_required",
        )
        self.assertEqual(cases[eligible["case_id"]]["status"], "eligible")
        self.assertIsNone(cases[eligible["case_id"]]["blocking_reason"])
