import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import jsonschema
import numpy as np
from fastapi.testclient import TestClient

from scripts.visual_qc.server.api import create_app
from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.provenance import (
    QualifiedHandoffError,
    normalize_qualified_handoff,
)
from scripts.visual_qc.server.quality import analyze_image_quality
from scripts.visual_qc.server.storage import LocalObjectStorage, StorageError
from scripts.visual_qc.server.store import VisualQcStore
from scripts.visual_qc.synthetic import SyntheticTransformConfig, generate_synthetic_capture
from visual_qc_server import runtime_options


ROOT = Path(__file__).resolve().parents[1]


def qualified_handoff(action="automatic_candidate_review_required", **overrides):
    payload = {
        "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
        "handoff_schema_version": "VISUAL-QC-PHYSICAL-HANDOFF-V1",
        "source_package_manifest_sha256": "a" * 64,
        "archived_intake_manifest_sha256": "b" * 64,
        "acceptance_report_sha256": "c" * 64,
        "acceptance_action": action,
        "registration_review_required": True,
        "field_accuracy_claim_allowed": False,
    }
    payload.update(overrides)
    return payload


def encode_jpeg(image):
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("Unable to encode test image")
    return encoded.tobytes()


class VisualQcServerApiTests(unittest.TestCase):
    def test_qualified_handoff_contract_is_closed_and_schema_valid(self):
        normalized = normalize_qualified_handoff(
            json.dumps(qualified_handoff(), separators=(",", ":"))
        )

        self.assertEqual(normalized, qualified_handoff())
        schema = json.loads(
            (
                ROOT
                / "knowledge-base"
                / "visual-qc-qualified-handoff-provenance-v1-schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.validate(normalized, schema)

    def test_qualified_handoff_rejects_unknown_fields_and_semantic_drift(self):
        invalid = qualified_handoff(extra="pollution")
        with self.assertRaises(QualifiedHandoffError):
            normalize_qualified_handoff(json.dumps(invalid))

        for key, value in (
            ("registration_review_required", False),
            ("field_accuracy_claim_allowed", True),
            ("source_package_manifest_sha256", "A" * 64),
            ("acceptance_action", "reviewed"),
        ):
            invalid = qualified_handoff(**{key: value})
            with self.subTest(key=key), self.assertRaises(QualifiedHandoffError):
                normalize_qualified_handoff(json.dumps(invalid))

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
            "X-Actor-Role": "reviewer",
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
            "capture_session_id": "capture-session-001",
            "capture_setup_id": "standard-bench",
            "capture_checklist": (
                '{"status":"confirmed","items":{'
                '"board_and_side_confirmed":true,'
                '"focus_and_lens_confirmed":true,'
                '"lighting_and_occlusion_confirmed":true},'
                '"confirmed_at":"2026-07-20T10:00:00.000Z"}'
            ),
            "qualified_handoff": json.dumps(
                qualified_handoff(), separators=(",", ":")
            ),
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
        }
        fields.update(overrides)
        fields.setdefault(
            "intake_batch_id",
            f"{fields['capture_session_id']}-batch",
        )
        fields.setdefault(
            "intake_entry_id",
            f"{fields['capture_session_id']}-{fields['side_id']}",
        )
        fields = {key: value for key, value in fields.items() if value is not None}
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
        self.assertEqual(payload["schema_version"], "VISUAL-QC-SERVER-CASE-V2")
        jsonschema.validate(
            payload,
            json.loads(
                (
                    ROOT
                    / "knowledge-base"
                    / "visual-qc-server-case-v2-schema.json"
                ).read_text(encoding="utf-8")
            ),
        )
        self.assertEqual(payload["qualified_handoff"], qualified_handoff())
        self.assertEqual(payload["job"]["status"], "queued")
        self.assertEqual(payload["capture_session"]["session_id"], "capture-session-001")
        self.assertEqual(payload["capture_session"]["pair_status"], "pair_in_progress")

        restored = self.client.get(
            f"/api/v1/visual-qc/cases/{payload['case_id']}",
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["image"]["sha256"], fields_sha256(image_bytes))
        self.assertTrue((Path(self.temp_dir.name) / "visual-qc.sqlite3").exists())
        originals = list((Path(self.temp_dir.name) / "objects" / "originals").rglob("*.jpg"))
        self.assertEqual(len(originals), 1)

    def test_new_physical_case_requires_intake_and_qualified_handoff(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))

        missing = self.upload(image_bytes, qualified_handoff=None)

        self.assertEqual(missing.status_code, 422)
        self.assertEqual(
            missing.json()["detail"]["code"],
            "physical_handoff_provenance_required",
        )

    def test_nonphysical_case_rejects_qualified_handoff(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))

        response = self.upload(
            image_bytes,
            evidence_role="service_manual_proxy",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "qualified_handoff_not_allowed",
        )

    def test_qualified_handoff_round_trips_to_case_store_and_audit(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))

        response = self.upload(image_bytes)

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["qualified_handoff"], qualified_handoff())
        database = Path(self.temp_dir.name) / "visual-qc.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            stored = connection.execute(
                "SELECT qualified_handoff_json FROM cases WHERE case_id = ?",
                (payload["case_id"],),
            ).fetchone()[0]
            audit = connection.execute(
                "SELECT payload_json FROM audit_events "
                "WHERE case_id = ? AND event_type = 'case_created'",
                (payload["case_id"],),
            ).fetchone()[0]

        self.assertEqual(
            stored,
            json.dumps(qualified_handoff(), sort_keys=True, separators=(",", ":")),
        )
        self.assertEqual(
            json.loads(audit)["qualified_handoff"],
            qualified_handoff(),
        )
        self.assertNotIn("overlay", stored + audit)
        self.assertNotIn("report_body", stored + audit)

    def test_idempotency_rejects_qualified_handoff_hash_drift(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))
        first = self.upload(image_bytes)
        drifted = qualified_handoff(acceptance_report_sha256="d" * 64)

        second = self.upload(
            image_bytes,
            qualified_handoff=json.dumps(drifted, separators=(",", ":")),
        )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["detail"]["code"], "idempotency_conflict")

    def test_intake_identity_deduplicates_only_an_identical_request(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))
        first = self.upload(image_bytes)
        self.headers["Idempotency-Key"] = "capture-request-retry"

        identical = self.upload(image_bytes)
        drifted = self.upload(
            image_bytes,
            qualified_handoff=json.dumps(
                qualified_handoff(acceptance_report_sha256="d" * 64),
                separators=(",", ":"),
            ),
        )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(identical.status_code, 202)
        self.assertEqual(identical.json()["case_id"], first.json()["case_id"])
        self.assertEqual(drifted.status_code, 409)
        self.assertEqual(
            drifted.json()["detail"]["code"],
            "intake_provenance_conflict",
        )

    def test_technician_cannot_upload_visual_qc_case_before_route_handling(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))
        service = self.app.state.visual_qc_service
        with patch.object(service, "create_case") as create_case:
            response = self.client.post(
                "/api/v1/visual-qc/cases",
                data={
                    "board_key": "km4-f151",
                    "side_id": "main_page_2",
                    "capture_stage": "golden_reference",
                    "evidence_role": "physical_capture",
                    "sha256": fields_sha256(image_bytes),
                },
                files={"file": ("board.jpg", image_bytes, "image/jpeg")},
                headers={
                    "X-Actor-Id": "technician-001",
                    "X-Actor-Role": "technician",
                    "Idempotency-Key": "forbidden-upload",
                },
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "data_admin_role_required")
        create_case.assert_not_called()

    def test_intake_provenance_round_trips_on_created_case(self):
        image_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))

        response = self.upload(
            image_bytes,
            intake_batch_id="km4-first-physical-batch",
            intake_entry_id="km4-board-01-side-2",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json()["intake"],
            {
                "batch_id": "km4-first-physical-batch",
                "entry_id": "km4-board-01-side-2",
            },
        )

    def test_legacy_database_migrates_intake_columns_without_data_loss(self):
        database_path = Path(self.temp_dir.name) / "legacy.sqlite3"
        connection = sqlite3.connect(database_path)
        try:
            connection.executescript(
                """
                CREATE TABLE cases (
                    case_id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL,
                    board_key TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    side_id TEXT NOT NULL,
                    capture_stage TEXT NOT NULL,
                    evidence_role TEXT NOT NULL,
                    capture_session_id TEXT NOT NULL DEFAULT '',
                    capture_setup_id TEXT NOT NULL DEFAULT 'standard-bench',
                    capture_checklist_json TEXT NOT NULL DEFAULT '{}',
                    reference_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(actor_id, idempotency_key)
                );
                INSERT INTO cases VALUES (
                    'legacy-case', 'owner-001', 'legacy-key', 'fingerprint',
                    'km4-f151', 'BOARD-KM4-F151-MAIN-V1.2', 'main_page_2',
                    'golden_reference', 'service_manual_proxy', 'legacy-session',
                    'standard-bench', '{}', 'reference.png', '2026-07-20T00:00:00.000Z'
                );
                """
            )
            connection.commit()
        finally:
            connection.close()

        store = VisualQcStore(database_path, recover_interrupted_jobs=False)
        with store.connect() as connection:
            row = connection.execute(
                "SELECT case_id, intake_batch_id, intake_entry_id, "
                "qualified_handoff_json FROM cases"
            ).fetchone()

        self.assertEqual(row["case_id"], "legacy-case")
        self.assertIsNone(row["intake_batch_id"])
        self.assertIsNone(row["intake_entry_id"])
        self.assertIsNone(row["qualified_handoff_json"])

    def test_capture_session_pairs_board_sides_and_rejects_identity_pollution(self):
        first_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))
        first = self.upload(first_bytes)
        self.assertEqual(first.status_code, 202)

        self.headers["Idempotency-Key"] = "capture-request-002"
        second_bytes = encode_jpeg(np.full((120, 180, 3), 150, dtype=np.uint8))
        second = self.upload(second_bytes, side_id="main_page_1")

        self.assertEqual(second.status_code, 202)
        self.assertEqual(
            set(second.json()["capture_session"]["captured_side_ids"]),
            {"main_page_1", "main_page_2"},
        )
        self.assertEqual(second.json()["capture_session"]["pair_status"], "pair_complete")

        restored = self.client.get(
            "/api/v1/visual-qc/capture-sessions/capture-session-001",
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["pair_status"], "pair_complete")
        self.assertEqual(len(restored.json()["cases"]), 2)

        self.headers["Idempotency-Key"] = "capture-request-003"
        polluted = self.upload(
            encode_jpeg(np.full((120, 180, 3), 130, dtype=np.uint8)),
            capture_stage="after_repair",
        )
        self.assertEqual(polluted.status_code, 409)
        self.assertEqual(
            polluted.json()["detail"]["code"],
            "capture_session_identity_conflict",
        )

    def test_capture_session_identity_is_enforced_inside_the_write_transaction(self):
        first_bytes = encode_jpeg(np.full((120, 180, 3), 170, dtype=np.uint8))
        first = self.upload(first_bytes)
        self.assertEqual(first.status_code, 202)

        self.headers["Idempotency-Key"] = "capture-request-race"
        original_list_capture_session = (
            self.app.state.visual_qc_service.store.list_capture_session
        )
        calls = iter(
            [
                [],
                original_list_capture_session(
                    "technician-001",
                    "capture-session-001",
                ),
            ]
        )
        with patch.object(
            self.app.state.visual_qc_service.store,
            "list_capture_session",
            side_effect=lambda *_args, **_kwargs: next(calls),
        ):
            polluted = self.upload(
                encode_jpeg(np.full((120, 180, 3), 140, dtype=np.uint8)),
                capture_stage="after_repair",
                intake_entry_id="capture-session-001-race",
            )

        self.assertEqual(polluted.status_code, 409)
        self.assertEqual(
            polluted.json()["detail"]["code"],
            "capture_session_identity_conflict",
        )

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

    def test_identity_comes_from_gateway_headers_and_unknown_roles_fail_closed(self):
        reviewer = self.client.get(
            "/api/v1/visual-qc/identity",
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )
        unknown_role = self.client.get(
            "/api/v1/visual-qc/identity",
            headers={
                "X-Actor-Id": "technician-001",
                "X-Actor-Role": "administrator",
            },
        )
        missing_actor = self.client.get("/api/v1/visual-qc/identity")

        self.assertEqual(reviewer.status_code, 200)
        self.assertEqual(
            reviewer.json(),
            {
                "schema_version": "VISUAL-QC-IDENTITY-V1",
                "actor_id": "reviewer-001",
                "role": "reviewer",
            },
        )
        self.assertEqual(unknown_role.status_code, 200)
        self.assertEqual(unknown_role.json()["role"], "technician")
        self.assertEqual(missing_actor.status_code, 401)

    def test_runtime_binds_qc_api_to_loopback_by_default(self):
        with patch.dict("os.environ", {}, clear=True):
            options = runtime_options()

        self.assertEqual(options["host"], "127.0.0.1")
        self.assertEqual(options["port"], 3020)


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
