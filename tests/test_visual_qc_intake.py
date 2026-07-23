import copy
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from scripts.visual_qc.intake import (
    IntakeValidationError,
    create_intake_receipt,
    intake_idempotency_key,
    merge_receipt,
    validate_intake_batch,
    write_json_atomic,
)
from scripts.import_visual_qc_batch import (
    VisualQcIntakeTransport,
    VisualQcIntakeTransportError,
    run_intake,
)


ROOT = Path(__file__).resolve().parents[1]


def encode_jpeg(width=180, height=120, value=170):
    image = np.full((height, width, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("Unable to encode test JPEG")
    return encoded.tobytes()


class FakeTransport:
    def __init__(self, *, fail_entries=None, job_states=None):
        self.uploads = []
        self.job_requests = []
        self.fail_entries = set(fail_entries or [])
        self.job_states = list(job_states or ["succeeded"])

    def upload(self, entry, *, idempotency_key):
        self.uploads.append((entry["entry_id"], idempotency_key))
        if entry["entry_id"] in self.fail_entries:
            raise RuntimeError(f"upload failed for {entry['entry_id']}")
        return {
            "case_id": f"case-{entry['entry_id']}",
            "job": {"job_id": f"job-{entry['entry_id']}", "status": "queued"},
        }

    def get_job(self, job_id):
        self.job_requests.append(job_id)
        state = self.job_states.pop(0) if len(self.job_states) > 1 else self.job_states[0]
        payload = {
            "job_id": job_id,
            "case_id": job_id.replace("job-", "case-", 1),
            "status": state,
        }
        if state == "failed":
            payload["error"] = {"code": "processing_failed", "message": "worker failed"}
        return payload


class VisualQcIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.image = encode_jpeg()
        (self.root / "board.jpg").write_bytes(self.image)
        self.manifest_path = self.root / "batch.json"
        self.receipt_path = self.root / "batch.receipt.json"
        self.write_manifest()

    def tearDown(self):
        self.temp_dir.cleanup()

    def entry(self, entry_id="km4-board-01-side-2", **overrides):
        payload = {
            "entry_id": entry_id,
            "file_path": "board.jpg",
            "board_key": "km4-f151",
            "side_id": "main_page_2",
            "capture_stage": "golden_reference",
            "capture_session_id": "km4-board-01",
            "capture_setup_id": "standard-bench",
            "capture_checklist": {
                "board_and_side_confirmed": True,
                "focus_and_lens_confirmed": True,
                "lighting_and_occlusion_confirmed": True,
            },
            "expected_sha256": None,
        }
        payload.update(overrides)
        return payload

    def write_manifest(self, entries=None, **overrides):
        payload = {
            "schema_version": "VISUAL-QC-INTAKE-BATCH-V1",
            "batch_id": "km4-first-physical-batch",
            "entries": entries or [self.entry()],
        }
        payload.update(overrides)
        self.manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def validate(self):
        return validate_intake_batch(self.manifest_path, ROOT)

    def assert_invalid(self, pattern, *, entries=None, **manifest_overrides):
        self.write_manifest(entries=entries, **manifest_overrides)
        with self.assertRaisesRegex(IntakeValidationError, pattern):
            self.validate()

    def test_valid_batch_binds_known_board_side_and_computed_evidence(self):
        result = self.validate()

        self.assertEqual(result["schema_version"], "VISUAL-QC-INTAKE-BATCH-V1")
        entry = result["entries"][0]
        self.assertEqual(entry["board_key"], "km4-f151")
        self.assertEqual(entry["side_id"], "main_page_2")
        self.assertEqual(entry["mime_type"], "image/jpeg")
        self.assertEqual(entry["width"], 180)
        self.assertEqual(entry["height"], 120)
        self.assertEqual(entry["byte_size"], len(self.image))
        self.assertEqual(entry["sha256"], hashlib.sha256(self.image).hexdigest())
        self.assertEqual(entry["file_path"], (self.root / "board.jpg").resolve())

    def test_duplicate_session_side_fails_before_upload(self):
        second = self.entry("front-b", file_path="board-b.jpg")
        (self.root / "board-b.jpg").write_bytes(encode_jpeg(value=120))
        self.assert_invalid(
            "duplicate capture session side",
            entries=[self.entry("front-a"), second],
        )

    def test_duplicate_entry_id_and_resolved_path_are_rejected(self):
        other = self.entry("same", file_path="board-b.jpg", capture_session_id="session-b")
        (self.root / "board-b.jpg").write_bytes(encode_jpeg(value=120))
        self.assert_invalid(
            "duplicate entry_id", entries=[self.entry("same"), other]
        )

        same_path = self.entry("other", capture_session_id="session-b")
        self.assert_invalid(
            "duplicate resolved file path", entries=[self.entry(), same_path]
        )

    def test_unsafe_identifiers_and_unknown_board_side_are_rejected(self):
        self.assert_invalid("unsafe batch_id", batch_id="../batch")
        self.assert_invalid("unsafe entry_id", entries=[self.entry("bad/id")])
        self.assert_invalid(
            "Unknown board_key", entries=[self.entry(board_key="unknown-board")]
        )
        self.assert_invalid(
            "does not belong", entries=[self.entry(side_id="main_page_999")]
        )

    def test_mixed_session_identity_and_incomplete_checklist_are_rejected(self):
        (self.root / "board-b.jpg").write_bytes(encode_jpeg(value=120))
        mixed = self.entry(
            "side-one",
            file_path="board-b.jpg",
            side_id="main_page_1",
            board_key="kl4-f201",
        )
        self.assert_invalid("mixed capture session identity", entries=[self.entry(), mixed])

        checklist = copy.deepcopy(self.entry()["capture_checklist"])
        checklist["focus_and_lens_confirmed"] = False
        self.assert_invalid(
            "incomplete capture checklist",
            entries=[self.entry(capture_checklist=checklist)],
        )

    def test_mime_decode_dimensions_and_expected_hash_are_verified(self):
        png_path = self.root / "wrong.jpg"
        png = cv2.imencode(".png", np.full((120, 180, 3), 100, dtype=np.uint8))[1].tobytes()
        png_path.write_bytes(png)
        self.assert_invalid(
            "extension does not match detected MIME",
            entries=[self.entry(file_path="wrong.jpg")],
        )

        (self.root / "broken.jpg").write_bytes(b"not-an-image")
        self.assert_invalid(
            "unsupported or invalid image signature",
            entries=[self.entry(file_path="broken.jpg")],
        )

        (self.root / "tiny.jpg").write_bytes(encode_jpeg(width=31, height=31))
        self.assert_invalid(
            "image dimensions",
            entries=[self.entry(file_path="tiny.jpg")],
        )

        self.assert_invalid(
            "expected SHA-256 does not match",
            entries=[self.entry(expected_sha256="0" * 64)],
        )

    def test_receipt_is_stable_resumable_and_contains_no_credentials(self):
        validated = self.validate()
        receipt = create_intake_receipt(validated)
        row = receipt["entries"][0]

        self.assertEqual(receipt["schema_version"], "VISUAL-QC-INTAKE-RECEIPT-V1")
        self.assertEqual(row["state"], "validated")
        self.assertEqual(row["server_case_id"], None)
        self.assertEqual(row["server_job_id"], None)
        self.assertEqual(row["error"], None)
        self.assertEqual(
            row["idempotency_key"],
            intake_idempotency_key(receipt["batch_id"], row["entry_id"], row["sha256"]),
        )
        self.assertNotIn("authorization", json.dumps(receipt).lower())
        self.assertNotIn("credential", json.dumps(receipt).lower())

        completed = copy.deepcopy(receipt)
        completed["entries"][0].update(
            {"state": "completed", "server_case_id": "case-1", "server_job_id": "job-1"}
        )
        self.assertEqual(
            merge_receipt(completed, validated)["entries"][0]["server_case_id"], "case-1"
        )

        changed = copy.deepcopy(validated)
        changed["entries"][0]["sha256"] = "f" * 64
        self.assertIsNone(merge_receipt(completed, changed)["entries"][0]["server_case_id"])

    def test_atomic_writer_uses_utf8_lf_and_round_trips(self):
        output = self.root / "receipt.json"
        payload = {"message": "视觉数据", "value": 1}

        write_json_atomic(output, payload)

        raw = output.read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertEqual(json.loads(raw.decode("utf-8")), payload)

    def test_dry_run_writes_validated_receipt_without_transport_calls(self):
        transport = FakeTransport()

        result = run_intake(
            self.manifest_path,
            self.receipt_path,
            transport,
            dry_run=True,
            project_root=ROOT,
        )

        self.assertEqual(transport.uploads, [])
        self.assertEqual(result["entries"][0]["state"], "validated")
        self.assertEqual(json.loads(self.receipt_path.read_text(encoding="utf-8")), result)

    def test_resume_reconciles_existing_job_without_duplicate_upload(self):
        transport = FakeTransport()

        first = run_intake(
            self.manifest_path, self.receipt_path, transport, project_root=ROOT
        )
        resumed = run_intake(
            self.manifest_path, self.receipt_path, transport, project_root=ROOT
        )

        self.assertEqual(len(transport.uploads), 1)
        self.assertEqual(first["entries"][0]["state"], "uploaded")
        self.assertEqual(resumed["entries"][0]["state"], "completed")
        self.assertEqual(len(transport.job_requests), 1)

    def test_changed_sha_invalidates_prior_server_ids_and_uploads_again(self):
        transport = FakeTransport()
        first = run_intake(
            self.manifest_path, self.receipt_path, transport, project_root=ROOT
        )
        self.assertIsNotNone(first["entries"][0]["server_case_id"])
        (self.root / "board.jpg").write_bytes(encode_jpeg(value=90))

        changed = run_intake(
            self.manifest_path, self.receipt_path, transport, project_root=ROOT
        )

        self.assertEqual(len(transport.uploads), 2)
        self.assertNotEqual(first["entries"][0]["sha256"], changed["entries"][0]["sha256"])

    def test_stop_on_error_and_explicit_continue_on_error_are_sequential(self):
        (self.root / "board-b.jpg").write_bytes(encode_jpeg(value=120))
        entries = [
            self.entry("first"),
            self.entry(
                "second",
                file_path="board-b.jpg",
                side_id="main_page_1",
            ),
        ]
        self.write_manifest(entries=entries)
        stopped = FakeTransport(fail_entries={"first"})

        result = run_intake(
            self.manifest_path, self.receipt_path, stopped, project_root=ROOT
        )

        self.assertEqual([entry for entry, _key in stopped.uploads], ["first"])
        self.assertEqual(result["entries"][0]["state"], "failed")
        self.assertEqual(result["entries"][1]["state"], "validated")

        self.receipt_path.unlink()
        continued = FakeTransport(fail_entries={"first"})
        result = run_intake(
            self.manifest_path,
            self.receipt_path,
            continued,
            continue_on_error=True,
            project_root=ROOT,
        )
        self.assertEqual([entry for entry, _key in continued.uploads], ["first", "second"])
        self.assertEqual([row["state"] for row in result["entries"]], ["failed", "uploaded"])

    def test_wait_for_jobs_records_terminal_state_and_typed_error(self):
        succeeded = FakeTransport(job_states=["running", "succeeded"])
        result = run_intake(
            self.manifest_path,
            self.receipt_path,
            succeeded,
            wait_for_jobs=True,
            poll_interval_seconds=0,
            project_root=ROOT,
        )
        self.assertEqual(result["entries"][0]["state"], "completed")
        self.assertEqual(len(succeeded.job_requests), 2)

        self.receipt_path.unlink()
        failed = FakeTransport(job_states=["failed"])
        result = run_intake(
            self.manifest_path,
            self.receipt_path,
            failed,
            wait_for_jobs=True,
            poll_interval_seconds=0,
            project_root=ROOT,
        )
        self.assertEqual(result["entries"][0]["state"], "failed")
        self.assertEqual(result["entries"][0]["error"]["code"], "processing_failed")

    def test_resume_polls_existing_job_without_duplicate_upload(self):
        uploaded = run_intake(
            self.manifest_path,
            self.receipt_path,
            FakeTransport(),
            project_root=ROOT,
        )
        self.assertEqual(uploaded["entries"][0]["state"], "uploaded")

        resumed_transport = FakeTransport(job_states=["succeeded"])
        resumed = run_intake(
            self.manifest_path,
            self.receipt_path,
            resumed_transport,
            wait_for_jobs=True,
            poll_interval_seconds=0,
            project_root=ROOT,
        )

        self.assertEqual(resumed["entries"][0]["state"], "completed")
        self.assertEqual(resumed_transport.uploads, [])
        self.assertEqual(len(resumed_transport.job_requests), 1)

    def test_local_completed_receipt_requires_server_identity_reconciliation(self):
        validated = self.validate()
        forged = create_intake_receipt(validated)
        forged["entries"][0].update(
            {
                "state": "completed",
                "server_case_id": "forged-case",
                "server_job_id": "job-other",
            }
        )
        write_json_atomic(self.receipt_path, forged)
        transport = FakeTransport(job_states=["succeeded"])

        result = run_intake(
            self.manifest_path,
            self.receipt_path,
            transport,
            wait_for_jobs=True,
            poll_interval_seconds=0,
            project_root=ROOT,
        )

        self.assertEqual(transport.uploads, [])
        self.assertEqual(transport.job_requests, ["job-other"])
        self.assertEqual(result["entries"][0]["state"], "failed")
        self.assertEqual(result["entries"][0]["error"]["code"], "job_identity_mismatch")

    def test_prior_receipt_rejects_unknown_fields_before_transport(self):
        receipt = create_intake_receipt(self.validate())
        receipt["entries"][0]["trusted"] = True
        write_json_atomic(self.receipt_path, receipt)
        transport = FakeTransport()

        with self.assertRaisesRegex(IntakeValidationError, "prior intake receipt"):
            run_intake(
                self.manifest_path,
                self.receipt_path,
                transport,
                project_root=ROOT,
            )

        self.assertEqual(transport.uploads, [])

    def test_expected_manifest_hash_is_checked_before_receipt_or_transport(self):
        transport = FakeTransport()

        with self.assertRaisesRegex(IntakeValidationError, "manifest.*changed"):
            run_intake(
                self.manifest_path,
                self.receipt_path,
                transport,
                expected_manifest_sha256="0" * 64,
                project_root=ROOT,
            )

        self.assertFalse(self.receipt_path.exists())
        self.assertEqual(transport.uploads, [])

    def test_orchestrator_never_prints_or_persists_transport_credentials(self):
        output = StringIO()
        with redirect_stdout(output):
            run_intake(
                self.manifest_path,
                self.receipt_path,
                FakeTransport(),
                project_root=ROOT,
            )

        self.assertEqual(output.getvalue(), "")
        serialized = self.receipt_path.read_text(encoding="utf-8").lower()
        self.assertNotIn("authorization", serialized)
        self.assertNotIn("password", serialized)

    def test_http_transport_requires_explicit_localhost_override(self):
        with self.assertRaisesRegex(ValueError, "requires HTTPS"):
            VisualQcIntakeTransport(
                "http://example.test/api/v1/visual-qc",
                actor_id="owner-001",
                username="user",
                password="secret",
            )
        with self.assertRaisesRegex(ValueError, "requires HTTPS"):
            VisualQcIntakeTransport(
                "http://127.0.0.1:3020/api/v1/visual-qc",
                actor_id="owner-001",
                username="user",
                password="secret",
            )

        transport = VisualQcIntakeTransport(
            "http://127.0.0.1:3020/api/v1/visual-qc",
            actor_id="owner-001",
            username="user",
            password="secret",
            allow_http_localhost=True,
        )
        self.assertEqual(transport.api_base, "http://127.0.0.1:3020/api/v1/visual-qc")

    def test_transport_rejects_source_changed_after_validation_before_request(self):
        entry = self.validate()["entries"][0]
        entry["intake_batch_id"] = "km4-first-physical-batch"
        (self.root / "board.jpg").write_bytes(encode_jpeg(value=80))
        transport = VisualQcIntakeTransport(
            "https://example.test/api/v1/visual-qc",
            actor_id="owner-001",
            username="user",
            password="secret",
        )

        with patch.object(transport, "_request_json") as request_json:
            with self.assertRaisesRegex(
                VisualQcIntakeTransportError, "changed after validation"
            ):
                transport.upload(entry, idempotency_key="intake:test")

        request_json.assert_not_called()

    def test_multipart_contains_the_same_bytes_verified_by_hash_and_length(self):
        entry = self.validate()["entries"][0]
        transport = VisualQcIntakeTransport(
            "https://example.test/api/v1/visual-qc",
            actor_id="owner-001",
            username="user",
            password="secret",
        )

        body, content_type = transport._multipart_body(entry, {"board_key": "km4-f151"})

        self.assertIn(self.image, body)
        self.assertIn("multipart/form-data; boundary=", content_type)
        self.assertEqual(hashlib.sha256(self.image).hexdigest(), entry["sha256"])
        self.assertEqual(len(self.image), entry["byte_size"])

    def test_script_help_runs_directly_from_repository_root(self):
        result = subprocess.run(
            [sys.executable, "scripts/import_visual_qc_batch.py", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("owner-managed Visual-QC photo batch", result.stdout)


if __name__ == "__main__":
    unittest.main()
