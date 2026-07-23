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
from scripts.visual_qc.server.store import utc_now


ROOT = Path(__file__).resolve().parents[1]


def qualified_handoff():
    return {
        "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
        "handoff_schema_version": "VISUAL-QC-PHYSICAL-HANDOFF-V1",
        "source_package_manifest_sha256": "a" * 64,
        "archived_intake_manifest_sha256": "b" * 64,
        "acceptance_report_sha256": "c" * 64,
        "acceptance_action": "automatic_candidate_review_required",
        "registration_review_required": True,
        "field_accuracy_claim_allowed": False,
    }


def encode_jpeg(value=170):
    image = np.full((120, 180, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("Unable to encode test JPEG")
    return encoded.tobytes()


class VisualQcAdminCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=Path(self.temp_dir.name),
            minimum_image_dimension=64,
            worker_count=0,
        )
        self.app = create_app(settings)
        self.client = TestClient(self.app)
        self.service = self.app.state.visual_qc_service
        self.admin_headers = {"X-Actor-Id": "owner-001", "X-Actor-Role": "reviewer"}

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def upload(self, token, *, actor_id="owner-001", value=170):
        image = encode_jpeg(value)
        response = self.client.post(
            "/api/v1/visual-qc/cases",
            data={
                "board_key": "km4-f151",
                "side_id": "main_page_2",
                "capture_stage": "golden_reference",
                "evidence_role": "physical_capture",
                "capture_session_id": f"session-{token}",
                "capture_setup_id": "standard-bench",
                "capture_checklist": json.dumps(
                    {
                        "status": "confirmed",
                        "items": {
                            "board_and_side_confirmed": True,
                            "focus_and_lens_confirmed": True,
                            "lighting_and_occlusion_confirmed": True,
                        },
                        "confirmed_at": "2026-07-21T00:00:00.000Z",
                    }
                ),
                "intake_batch_id": "test-batch",
                "intake_entry_id": token,
                "qualified_handoff": json.dumps(
                    qualified_handoff(), separators=(",", ":")
                ),
                "sha256": hashlib.sha256(image).hexdigest(),
            },
            files={"file": (f"{token}.jpg", image, "image/jpeg")},
            headers={
                "X-Actor-Id": actor_id,
                "X-Actor-Role": "reviewer",
                "Idempotency-Key": f"upload-{token}",
            },
        )
        self.assertEqual(response.status_code, 202, response.text)
        return response.json(), image

    def set_job(self, case_id, status, result=None):
        with self.service.store.connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = ?, result_json = ?, updated_at = ? WHERE case_id = ?",
                (
                    status,
                    json.dumps(result, separators=(",", ":")) if result else None,
                    utc_now(),
                    case_id,
                ),
            )
            connection.commit()

    def add_registration_review(self, case_payload):
        review = {
            "review_id": f"review-{case_payload['case_id']}",
            "case_id": case_payload["case_id"],
            "job_id": case_payload["job"]["job_id"],
            "reviewer_id": "owner-001",
            "decision": "accept_automatic",
            "method": "orb_homography",
            "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
            "anchors": [],
            "check_points": [],
            "error": {"count": 0, "rms": None, "maximum": None},
            "notes": "",
            "created_at": utc_now(),
        }
        return self.service.store.create_registration_review(review)

    def test_admin_catalog_derives_all_states_and_is_actor_scoped(self):
        queued, _ = self.upload("queued", value=171)
        failed, _ = self.upload("failed", value=172)
        manual, _ = self.upload("manual", value=173)
        candidate, _ = self.upload("candidate", value=174)
        reviewed, _ = self.upload("reviewed", value=175)
        completed, _ = self.upload("completed", value=176)
        foreign, _ = self.upload("foreign", actor_id="owner-002", value=177)

        self.set_job(failed["case_id"], "failed")
        self.set_job(
            manual["case_id"],
            "succeeded",
            {"registration": {"status": "manual_required"}},
        )
        candidate_result = {
            "quality": {"status": "good"},
            "registration": {"status": "candidate", "review_status": "draft"},
        }
        for payload in (candidate, reviewed, completed):
            self.set_job(payload["case_id"], "succeeded", candidate_result)
        reviewed_registration = self.add_registration_review(reviewed)
        completed_registration = self.add_registration_review(completed)
        self.service.store.create_case_qc_review(
            {
                "qc_review_id": "qc-completed",
                "case_id": completed["case_id"],
                "registration_review_id": completed_registration["review_id"],
                "reviewer_id": "owner-001",
                "qc_result": "no_visible_anomaly",
                "annotations": [],
                "notes": "",
                "created_at": utc_now(),
            }
        )

        response = self.client.get(
            "/api/v1/visual-qc/admin/cases?page=1&page_size=100",
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["schema_version"], "VISUAL-QC-ADMIN-CASE-LIST-V2")
        jsonschema.validate(
            payload,
            json.loads(
                (
                    ROOT
                    / "knowledge-base"
                    / "visual-qc-admin-case-list-v2-schema.json"
                ).read_text(encoding="utf-8")
            ),
        )
        self.assertEqual(payload["total"], 6)
        self.assertTrue(
            all(
                item["qualified_handoff"] == qualified_handoff()
                for item in payload["cases"]
            )
        )
        self.assertEqual(
            {item["state"] for item in payload["cases"]},
            {
                "processing",
                "processing_failed",
                "manual_registration_required",
                "registration_review_required",
                "ready_for_human_qc",
                "completed",
            },
        )
        self.assertNotIn(foreign["case_id"], {item["case_id"] for item in payload["cases"]})
        self.assertNotIn("actor_id", json.dumps(payload))
        order = [(item["created_at"], item["case_id"]) for item in payload["cases"]]
        self.assertEqual(order, sorted(order, reverse=True))

        filtered = self.client.get(
            "/api/v1/visual-qc/admin/cases?page=1&page_size=2&state=ready_for_human_qc",
            headers=self.admin_headers,
        ).json()
        self.assertEqual(filtered["total"], 1)
        self.assertTrue(all(item["state"] == "ready_for_human_qc" for item in filtered["cases"]))

    def test_catalog_validates_role_pagination_and_filters(self):
        technician = self.client.get(
            "/api/v1/visual-qc/admin/cases",
            headers={"X-Actor-Id": "tech-001", "X-Actor-Role": "technician"},
        )
        bad_page = self.client.get(
            "/api/v1/visual-qc/admin/cases?page_size=101", headers=self.admin_headers
        )
        bad_state = self.client.get(
            "/api/v1/visual-qc/admin/cases?state=unknown", headers=self.admin_headers
        )

        self.assertEqual(technician.status_code, 403)
        self.assertEqual(technician.json()["detail"]["code"], "data_admin_role_required")
        self.assertEqual(bad_page.status_code, 422)
        self.assertEqual(bad_state.status_code, 422)
        self.assertEqual(bad_state.json()["detail"]["code"], "invalid_admin_case_state")

    def test_admin_detail_and_original_are_owner_scoped_and_byte_exact(self):
        case, image = self.upload("detail", value=182)
        result = {
            "quality": {"status": "good", "score": 0.9},
            "registration": {"status": "candidate", "review_status": "draft"},
        }
        self.set_job(case["case_id"], "succeeded", result)
        registration = self.add_registration_review(case)
        self.service.store.create_case_qc_review(
            {
                "qc_review_id": "qc-detail",
                "case_id": case["case_id"],
                "registration_review_id": registration["review_id"],
                "reviewer_id": "owner-001",
                "qc_result": "no_visible_anomaly",
                "annotations": [],
                "notes": "confirmed",
                "created_at": utc_now(),
            }
        )

        detail = self.client.get(
            f"/api/v1/visual-qc/admin/cases/{case['case_id']}",
            headers=self.admin_headers,
        )
        original = self.client.get(
            f"/api/v1/visual-qc/admin/cases/{case['case_id']}/image",
            headers=self.admin_headers,
        )
        foreign = self.client.get(
            f"/api/v1/visual-qc/admin/cases/{case['case_id']}",
            headers={"X-Actor-Id": "owner-002", "X-Actor-Role": "reviewer"},
        )
        technician = self.client.get(
            f"/api/v1/visual-qc/admin/cases/{case['case_id']}/image",
            headers={"X-Actor-Id": "tech-001", "X-Actor-Role": "technician"},
        )

        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["schema_version"], "VISUAL-QC-SERVER-CASE-V3")
        jsonschema.validate(
            detail.json(),
            json.loads(
                (
                    ROOT
                    / "knowledge-base"
                    / "visual-qc-server-case-v3-schema.json"
                ).read_text(encoding="utf-8")
            ),
        )
        self.assertEqual(detail.json()["qualified_handoff"], qualified_handoff())
        self.assertEqual(detail.json()["server_registration_review"]["review_id"], registration["review_id"])
        self.assertEqual(detail.json()["server_qc_review"]["qc_review_id"], "qc-detail")
        self.assertEqual(original.status_code, 200)
        self.assertEqual(original.content, image)
        self.assertEqual(original.headers["content-type"], "image/jpeg")
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(technician.status_code, 403)


if __name__ == "__main__":
    unittest.main()
