import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from fastapi.testclient import TestClient

from scripts.visual_qc.server.api import create_app
from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.quality import analyze_image_quality
from scripts.visual_qc.server.storage import LocalObjectStorage, StorageError
from scripts.visual_qc.synthetic import SyntheticTransformConfig, generate_synthetic_capture


ROOT = Path(__file__).resolve().parents[1]


def encode_jpeg(image):
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("Unable to encode test image")
    return encoded.tobytes()


class VisualQcServerApiTests(unittest.TestCase):
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
        self.headers = {
            "X-Actor-Id": "technician-001",
            "Idempotency-Key": "capture-request-001",
        }

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def upload(self, image_bytes, **overrides):
        fields = {
            "board_key": "km4-f151",
            "side_id": "main_page_2",
            "capture_stage": "before_repair",
            "evidence_role": "physical_capture",
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
        }
        fields.update(overrides)
        return self.client.post(
            "/api/v1/visual-qc/cases",
            data=fields,
            files={"file": ("board.jpg", image_bytes, "image/jpeg")},
            headers=self.headers,
        )

    def test_upload_is_persisted_and_idempotent(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))

        first = self.upload(image_bytes)
        second = self.upload(image_bytes)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json(), second.json())
        payload = first.json()
        self.assertEqual(payload["schema_version"], "VISUAL-QC-SERVER-CASE-V1")
        self.assertEqual(payload["job"]["status"], "queued")

        restored = self.client.get(
            f"/api/v1/visual-qc/cases/{payload['case_id']}",
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["image"]["sha256"], fields_sha256(image_bytes))
        self.assertTrue((Path(self.temp_dir.name) / "visual-qc.sqlite3").exists())
        originals = list((Path(self.temp_dir.name) / "objects" / "originals").rglob("*.jpg"))
        self.assertEqual(len(originals), 1)

    def test_upload_rejects_unknown_side_and_hash_mismatch(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))

        unknown_side = self.upload(image_bytes, side_id="not_a_side")
        hash_mismatch = self.upload(image_bytes, sha256="0" * 64)

        self.assertEqual(unknown_side.status_code, 422)
        self.assertEqual(unknown_side.json()["detail"]["code"], "unknown_board_side")
        self.assertEqual(hash_mismatch.status_code, 422)
        self.assertEqual(hash_mismatch.json()["detail"]["code"], "sha256_mismatch")

    def test_worker_persists_registration_candidate_across_app_restart(self):
        reference_path = ROOT / "assets/board-atlas/km4-f151/main-point-map-page-2.png"
        reference = cv2.imread(str(reference_path), cv2.IMREAD_COLOR)
        capture, _ = generate_synthetic_capture(
            reference,
            SyntheticTransformConfig(
                rotation_degrees=4,
                perspective_jitter=0.035,
                crop_fraction=0.02,
                brightness_delta=-10,
                max_dimension=1400,
            ),
            seed=20260721,
        )
        response = self.upload(encode_jpeg(capture))
        job_id = response.json()["job"]["job_id"]

        processed = self.app.state.visual_qc_service.process_next_job()

        self.assertEqual(processed["job_id"], job_id)
        self.assertEqual(processed["status"], "succeeded")
        self.assertEqual(
            processed["result"]["schema_version"],
            "VISUAL-QC-SERVER-JOB-RESULT-V1",
        )
        self.assertEqual(processed["result"]["registration"]["status"], "candidate")
        self.assertIn(processed["result"]["quality"]["status"], {"good", "usable", "retake"})
        self.client.close()

        restored_app = create_app(self.settings)
        restored_client = TestClient(restored_app)
        restored = restored_client.get(
            f"/api/v1/visual-qc/jobs/{job_id}",
            headers={"X-Actor-Id": "technician-001"},
        )
        restored_client.close()
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["status"], "succeeded")
        self.assertEqual(
            restored.json()["result"]["registration"]["review_status"],
            "draft",
        )

    def test_worker_persists_manual_fallback_as_a_successful_business_result(self):
        image_bytes = encode_jpeg(np.full((180, 260, 3), 255, dtype=np.uint8))
        response = self.upload(image_bytes)

        processed = self.app.state.visual_qc_service.process_next_job()

        self.assertEqual(processed["status"], "succeeded")
        self.assertEqual(
            processed["result"]["registration"]["status"],
            "manual_required",
        )
        self.assertTrue(
            processed["result"]["registration"]["requires_manual_registration"]
        )

    def test_running_job_is_requeued_when_the_service_restarts(self):
        image_bytes = encode_jpeg(np.full((180, 260, 3), 190, dtype=np.uint8))
        response = self.upload(image_bytes)
        job_id = response.json()["job"]["job_id"]
        claimed = self.app.state.visual_qc_service.store.claim_next_job()
        self.assertEqual(claimed["status"], "running")

        restarted_app = create_app(self.settings)
        restarted_client = TestClient(restarted_app)
        restored = restarted_client.get(
            f"/api/v1/visual-qc/jobs/{job_id}",
            headers={"X-Actor-Id": "technician-001"},
        )
        restarted_client.close()

        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["status"], "queued")
        self.assertEqual(restored.json()["error"]["code"], "worker_interrupted")

    def test_failed_job_can_be_requeued_explicitly(self):
        image_bytes = encode_jpeg(np.full((180, 260, 3), 190, dtype=np.uint8))
        response = self.upload(image_bytes)
        job_id = response.json()["job"]["job_id"]
        stored = self.app.state.visual_qc_service.store.get_job(job_id)
        Path(stored["storage_path"]).unlink()
        failed = self.app.state.visual_qc_service.process_next_job()
        self.assertEqual(failed["status"], "failed")

        retried = self.client.post(
            f"/api/v1/visual-qc/jobs/{job_id}/retry",
            headers={"X-Actor-Id": "technician-001"},
        )

        self.assertEqual(retried.status_code, 202)
        self.assertEqual(retried.json()["status"], "queued")
        self.assertEqual(retried.json()["attempt_count"], 1)

    def test_actor_boundary_and_idempotency_conflict_are_enforced(self):
        image_bytes = encode_jpeg(np.full((180, 260, 3), 190, dtype=np.uint8))
        response = self.upload(image_bytes)
        case_id = response.json()["case_id"]

        missing_actor = self.client.get(f"/api/v1/visual-qc/cases/{case_id}")
        different_actor = self.client.get(
            f"/api/v1/visual-qc/cases/{case_id}",
            headers={"X-Actor-Id": "technician-002"},
        )
        conflict = self.upload(
            encode_jpeg(np.full((180, 260, 3), 80, dtype=np.uint8)),
        )

        self.assertEqual(missing_actor.status_code, 401)
        self.assertEqual(different_actor.status_code, 404)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["detail"]["code"], "idempotency_conflict")

    def test_upload_limit_is_enforced_before_storage(self):
        limited_settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=Path(self.temp_dir.name) / "limited",
            maximum_upload_bytes=100,
            minimum_image_dimension=64,
            worker_count=0,
        )
        limited_app = create_app(limited_settings)
        limited_client = TestClient(limited_app)
        image_bytes = encode_jpeg(np.full((180, 260, 3), 190, dtype=np.uint8))
        response = limited_client.post(
            "/api/v1/visual-qc/cases",
            data={
                "board_key": "km4-f151",
                "side_id": "main_page_2",
                "capture_stage": "before_repair",
                "evidence_role": "physical_capture",
                "sha256": fields_sha256(image_bytes),
            },
            files={"file": ("board.jpg", image_bytes, "image/jpeg")},
            headers=self.headers,
        )
        limited_client.close()

        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            list((Path(self.temp_dir.name) / "limited" / "objects" / "originals").rglob("*.jpg")),
            [],
        )

    def test_development_cors_allows_only_configured_workbench_origin(self):
        cors_settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=Path(self.temp_dir.name) / "cors",
            minimum_image_dimension=64,
            worker_count=0,
            allowed_origins=("http://127.0.0.1:8899",),
        )
        cors_client = TestClient(create_app(cors_settings))

        allowed = cors_client.options(
            "/api/v1/visual-qc/cases",
            headers={
                "Origin": "http://127.0.0.1:8899",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-actor-id,idempotency-key",
            },
        )
        denied = cors_client.options(
            "/api/v1/visual-qc/cases",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        cors_client.close()

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(
            allowed.headers["access-control-allow-origin"],
            "http://127.0.0.1:8899",
        )
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_declared_mime_type_must_match_image_bytes(self):
        ok, encoded = cv2.imencode(".png", np.full((180, 260, 3), 190, dtype=np.uint8))
        self.assertTrue(ok)
        image_bytes = encoded.tobytes()

        response = self.upload(image_bytes)

        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["detail"]["code"], "mime_content_mismatch")


class VisualQcServerQualityTests(unittest.TestCase):
    def test_flat_overexposed_image_requires_retake_with_raw_metrics(self):
        image = np.full((700, 900, 3), 255, dtype=np.uint8)

        quality = analyze_image_quality(image)

        self.assertEqual(quality["schema_version"], "VISUAL-QC-IMAGE-QUALITY-V1")
        self.assertEqual(quality["status"], "retake")
        self.assertEqual(quality["metrics"]["width"], 900)
        self.assertEqual(quality["metrics"]["height"], 700)
        self.assertGreater(quality["metrics"]["highlight_clipping"], 0.99)
        self.assertIn(
            "overexposed",
            {item["code"] for item in quality["guidance"]},
        )

    def test_artifact_write_preserves_the_configured_free_space_reserve(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            storage = LocalObjectStorage(
                root,
                minimum_free_bytes=100,
            )

            with patch(
                "scripts.visual_qc.server.storage.shutil.disk_usage",
                return_value=SimpleNamespace(free=100),
            ):
                with self.assertRaises(StorageError) as raised:
                    storage.put_artifact(
                        b"artifact",
                        hashlib.sha256(b"artifact").hexdigest(),
                        ".png",
                    )

        self.assertEqual(raised.exception.code, "insufficient_storage")


def fields_sha256(value):
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    unittest.main()
