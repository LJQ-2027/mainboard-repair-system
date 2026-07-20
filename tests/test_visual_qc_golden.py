import hashlib
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from scripts.visual_qc.server.api import create_app
from scripts.visual_qc.server.config import VisualQcServerSettings


ROOT = Path(__file__).resolve().parents[1]


class VisualQcGoldenSampleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=Path(self.temp_dir.name),
            maximum_upload_bytes=20 * 1024 * 1024,
            minimum_image_dimension=64,
            worker_count=0,
        )
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)
        reference = cv2.imread(
            str(ROOT / "assets/board-atlas/km4-f151/main-point-map-page-2.png"),
            cv2.IMREAD_COLOR,
        )
        reference = np.clip(reference.astype(np.float32) * 0.65, 0, 255).astype(np.uint8)
        self.reference = reference
        ok, encoded = cv2.imencode(".jpg", reference, [cv2.IMWRITE_JPEG_QUALITY, 95])
        self.assertTrue(ok)
        self.image_bytes = encoded.tobytes()

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def create_processed_case(
        self,
        *,
        idempotency_key,
        capture_stage="golden_reference",
        evidence_role="physical_capture",
        image_bytes=None,
    ):
        image_bytes = image_bytes or self.image_bytes
        response = self.client.post(
            "/api/v1/visual-qc/cases",
            data={
                "board_key": "km4-f151",
                "side_id": "main_page_2",
                "capture_stage": capture_stage,
                "evidence_role": evidence_role,
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
            },
            files={"file": ("reference.jpg", image_bytes, "image/jpeg")},
            headers={
                "X-Actor-Id": "technician-001",
                "Idempotency-Key": idempotency_key,
            },
        )
        self.assertEqual(response.status_code, 202)
        case = response.json()
        processed = self.app.state.visual_qc_service.process_next_job()
        self.assertEqual(processed["status"], "succeeded")
        return case

    def accept_automatic_registration(self, case_id):
        response = self.client.post(
            f"/api/v1/visual-qc/cases/{case_id}/registration-reviews",
            json={"decision": "accept_automatic", "notes": "Reference alignment checked."},
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "reviewed")
        self.assertEqual(response.json()["method"], "automatic_feature_homography")
        self.assertEqual(len(response.json()["board_to_image_matrix"]), 9)
        return response.json()

    def test_reviewed_physical_capture_can_become_versioned_golden_sample(self):
        first_case = self.create_processed_case(idempotency_key="golden-001")
        self.accept_automatic_registration(first_case["case_id"])
        conflicting_review = self.client.post(
            f"/api/v1/visual-qc/cases/{first_case['case_id']}/registration-reviews",
            json={
                "decision": "accept_manual",
                "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                "anchors": [
                    {"board": [0, 0], "image": [0, 0]},
                    {"board": [1, 0], "image": [1, 0]},
                    {"board": [1, 1], "image": [1, 1]},
                    {"board": [0, 1], "image": [0, 1]},
                ],
            },
            headers={"X-Actor-Id": "technician-001"},
        )

        forbidden = self.client.post(
            "/api/v1/visual-qc/golden-samples",
            json={
                "case_id": first_case["case_id"],
                "capture_setup_id": "bench-a",
                "confirmed_normal": True,
            },
            headers={"X-Actor-Id": "reviewer-001"},
        )
        created = self.client.post(
            "/api/v1/visual-qc/golden-samples",
            json={
                "case_id": first_case["case_id"],
                "capture_setup_id": "bench-a",
                "confirmed_normal": True,
            },
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(conflicting_review.status_code, 409)
        self.assertEqual(
            conflicting_review.json()["detail"]["code"],
            "registration_already_reviewed",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["status"], "active")
        self.assertEqual(created.json()["version"], 1)
        self.assertEqual(created.json()["source_sha256"], hashlib.sha256(self.image_bytes).hexdigest())

        second_case = self.create_processed_case(idempotency_key="golden-002")
        self.accept_automatic_registration(second_case["case_id"])
        replacement = self.client.post(
            "/api/v1/visual-qc/golden-samples",
            json={
                "case_id": second_case["case_id"],
                "capture_setup_id": "bench-a",
                "confirmed_normal": True,
            },
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )
        active = self.client.get(
            "/api/v1/visual-qc/golden-samples/active",
            params={
                "board_key": "km4-f151",
                "side_id": "main_page_2",
                "capture_setup_id": "bench-a",
            },
            headers={"X-Actor-Id": "technician-001"},
        )

        self.assertEqual(replacement.status_code, 201)
        self.assertEqual(replacement.json()["version"], 2)
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.json()["golden_sample_id"], replacement.json()["golden_sample_id"])

    def test_optional_golden_lookup_returns_a_clean_missing_state(self):
        response = self.client.get(
            "/api/v1/visual-qc/golden-samples/active",
            params={
                "board_key": "km4-f151",
                "side_id": "main_page_2",
                "capture_setup_id": "bench-without-golden",
                "allow_missing": "true",
            },
            headers={"X-Actor-Id": "technician-001"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["schema_version"], "VISUAL-QC-GOLDEN-LOOKUP-V1")
        self.assertEqual(response.json()["status"], "missing")

    def test_proxy_and_unreviewed_cases_cannot_become_golden_samples(self):
        proxy_case = self.create_processed_case(
            idempotency_key="proxy-001",
            evidence_role="synthetic_proxy",
        )
        self.accept_automatic_registration(proxy_case["case_id"])
        proxy_response = self.client.post(
            "/api/v1/visual-qc/golden-samples",
            json={
                "case_id": proxy_case["case_id"],
                "capture_setup_id": "bench-a",
                "confirmed_normal": True,
            },
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )

        unreviewed_case = self.create_processed_case(idempotency_key="unreviewed-001")
        unreviewed_response = self.client.post(
            "/api/v1/visual-qc/golden-samples",
            json={
                "case_id": unreviewed_case["case_id"],
                "capture_setup_id": "bench-a",
                "confirmed_normal": True,
            },
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )

        self.assertEqual(proxy_response.status_code, 409)
        self.assertEqual(proxy_response.json()["detail"]["code"], "physical_capture_required")
        self.assertEqual(unreviewed_response.status_code, 409)
        self.assertEqual(
            unreviewed_response.json()["detail"]["code"],
            "reviewed_registration_required",
        )

    def test_manual_four_point_fallback_requires_valid_normalized_geometry(self):
        blank = np.full((720, 960, 3), 180, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", blank)
        self.assertTrue(ok)
        blank_bytes = encoded.tobytes()
        response = self.client.post(
            "/api/v1/visual-qc/cases",
            data={
                "board_key": "km4-f151",
                "side_id": "main_page_2",
                "capture_stage": "before_repair",
                "evidence_role": "physical_capture",
                "sha256": hashlib.sha256(blank_bytes).hexdigest(),
            },
            files={"file": ("blank.jpg", blank_bytes, "image/jpeg")},
            headers={
                "X-Actor-Id": "technician-001",
                "Idempotency-Key": "manual-001",
            },
        )
        self.assertEqual(response.status_code, 202)
        case_id = response.json()["case_id"]
        result = self.app.state.visual_qc_service.process_next_job()
        self.assertEqual(result["result"]["registration"]["status"], "manual_required")

        invalid = self.client.post(
            f"/api/v1/visual-qc/cases/{case_id}/registration-reviews",
            json={
                "decision": "accept_manual",
                "board_to_image_matrix": [0] * 9,
                "anchors": [
                    {"board": [0, 0], "image": [0, 0]},
                    {"board": [1, 0], "image": [1, 0]},
                    {"board": [1, 1], "image": [1, 1]},
                    {"board": [0, 1], "image": [0, 1]},
                ],
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        inconsistent = self.client.post(
            f"/api/v1/visual-qc/cases/{case_id}/registration-reviews",
            json={
                "decision": "accept_manual",
                "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                "anchors": [
                    {"board": [0, 0], "image": [0.2, 0.2]},
                    {"board": [1, 0], "image": [0.8, 0.2]},
                    {"board": [1, 1], "image": [0.8, 0.8]},
                    {"board": [0, 1], "image": [0.2, 0.8]},
                ],
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        accepted = self.client.post(
            f"/api/v1/visual-qc/cases/{case_id}/registration-reviews",
            json={
                "decision": "accept_manual",
                "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                "anchors": [
                    {"board": [0, 0], "image": [0, 0]},
                    {"board": [1, 0], "image": [1, 0]},
                    {"board": [1, 1], "image": [1, 1]},
                    {"board": [0, 1], "image": [0, 1]},
                ],
            },
            headers={"X-Actor-Id": "technician-001"},
        )

        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["detail"]["code"], "degenerate_homography")
        self.assertEqual(inconsistent.status_code, 422)
        self.assertEqual(
            inconsistent.json()["detail"]["code"],
            "manual_anchor_matrix_mismatch",
        )
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(accepted.json()["method"], "reviewed_manual_four_point")
        self.assertEqual(accepted.json()["decision"], "accept_manual")

    def test_reviewed_case_produces_human_reviewable_difference_candidates(self):
        golden_case = self.create_processed_case(idempotency_key="diff-golden-001")
        self.accept_automatic_registration(golden_case["case_id"])
        golden = self.client.post(
            "/api/v1/visual-qc/golden-samples",
            json={
                "case_id": golden_case["case_id"],
                "capture_setup_id": "bench-a",
                "confirmed_normal": True,
            },
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )
        self.assertEqual(golden.status_code, 201)

        changed = self.reference.copy()
        height, width = changed.shape[:2]
        cv2.rectangle(
            changed,
            (round(width * 0.42), round(height * 0.35)),
            (round(width * 0.56), round(height * 0.52)),
            (0, 0, 220),
            -1,
        )
        ok, encoded = cv2.imencode(".jpg", changed, [cv2.IMWRITE_JPEG_QUALITY, 95])
        self.assertTrue(ok)
        current_case = self.create_processed_case(
            idempotency_key="diff-current-001",
            capture_stage="before_repair",
            image_bytes=encoded.tobytes(),
        )
        self.accept_automatic_registration(current_case["case_id"])

        queued = self.client.post(
            f"/api/v1/visual-qc/cases/{current_case['case_id']}/difference-jobs",
            json={"capture_setup_id": "bench-a"},
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(queued.status_code, 202)
        processed = self.app.state.visual_qc_service.process_next_job()
        self.assertEqual(processed["job_id"], queued.json()["job_id"])
        self.assertEqual(processed["status"], "succeeded")
        self.assertEqual(
            processed["result"]["schema_version"],
            "VISUAL-QC-DIFFERENCE-CANDIDATES-V1",
        )
        self.assertTrue(processed["result"]["requires_human_review"])
        self.assertGreaterEqual(len(processed["result"]["candidates"]), 1)
        self.assertTrue(
            all(
                candidate["source"] == "model_candidate"
                for candidate in processed["result"]["candidates"]
            )
        )

        heatmap = self.client.get(
            f"/api/v1/visual-qc/artifacts/{processed['result']['heatmap']['artifact_id']}",
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(heatmap.status_code, 200)
        self.assertEqual(heatmap.headers["content-type"], "image/png")
        self.assertGreater(len(heatmap.content), 1000)

        candidate_id = processed["result"]["candidates"][0]["candidate_id"]
        missing_category = self.client.post(
            f"/api/v1/visual-qc/jobs/{processed['job_id']}/candidate-reviews",
            json={
                "candidate_id": candidate_id,
                "decision": "confirmed",
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        confirmed = self.client.post(
            f"/api/v1/visual-qc/jobs/{processed['job_id']}/candidate-reviews",
            json={
                "candidate_id": candidate_id,
                "decision": "confirmed",
                "defect_category": "burn_or_thermal_damage",
                "notes": "Visible darkened region checked on the board.",
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        refreshed = self.client.get(
            f"/api/v1/visual-qc/jobs/{processed['job_id']}",
            headers={"X-Actor-Id": "technician-001"},
        )

        self.assertEqual(missing_category.status_code, 422)
        self.assertEqual(
            missing_category.json()["detail"]["code"],
            "defect_category_required",
        )
        self.assertEqual(confirmed.status_code, 201)
        self.assertEqual(confirmed.json()["label_source"], "human_annotation")
        self.assertEqual(confirmed.json()["decision"], "confirmed")
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(
            refreshed.json()["candidate_reviews"][0]["candidate_id"],
            candidate_id,
        )


if __name__ == "__main__":
    unittest.main()
