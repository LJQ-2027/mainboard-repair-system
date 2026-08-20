import hashlib
import io
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from fastapi.testclient import TestClient

from scripts.visual_qc.server.api import create_app
from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.storage import LocalObjectStorage, StorageCleanupError
from scripts.visual_qc.repair_evidence_link_contract import canonical_sha256
from tests.test_visual_qc_repair_evidence_link_contract import link_manifest
from scripts.maintain_visual_qc_server import (
    main as maintenance_main,
    validate_execution_confirmation,
)


ROOT = Path(__file__).resolve().parents[1]
OLD_TIMESTAMP = "2026-05-01T00:00:00.000Z"
NOW = datetime(2026, 7, 20, tzinfo=timezone.utc)


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


def encode_jpeg(value: int) -> bytes:
    image = np.full((120, 180, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Unable to encode test image")
    return encoded.tobytes()


class VisualQcMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=Path(self.temp_dir.name),
            minimum_image_dimension=64,
            minimum_free_bytes=100,
            warning_free_bytes=200,
            retention_days=30,
            retention_batch_limit=100,
            worker_count=0,
        )
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)
        self.service = self.app.state.visual_qc_service

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def _create_case(self, key: str, content: bytes):
        return self.service.create_case(
            actor_id="maintenance-test",
            idempotency_key=key,
            board_key="km4-f151",
            side_id="main_page_2",
            capture_stage="before_repair",
            evidence_role="physical_capture",
            intake_batch_id=f"batch-{key}",
            intake_entry_id=f"entry-{key}",
            qualified_handoff=json.dumps(
                qualified_handoff(), separators=(",", ":")
            ),
            claimed_sha256=hashlib.sha256(content).hexdigest(),
            original_filename=f"{key}.jpg",
            mime_type="image/jpeg",
            content=content,
        )

    def _make_old_terminal(self, case_id: str):
        with self.service.store.connect() as connection:
            connection.execute(
                "UPDATE cases SET created_at = ? WHERE case_id = ?",
                (OLD_TIMESTAMP, case_id),
            )
            connection.execute(
                "UPDATE images SET created_at = ? WHERE case_id = ?",
                (OLD_TIMESTAMP, case_id),
            )
            connection.execute(
                """
                UPDATE jobs
                SET status = 'failed', created_at = ?, updated_at = ?
                WHERE case_id = ?
                """,
                (OLD_TIMESTAMP, OLD_TIMESTAMP, case_id),
            )
            connection.commit()

    def _review_registration(self, case):
        return self.service.store.create_registration_review(
            {
                "review_id": f"review-{case['case_id']}",
                "case_id": case["case_id"],
                "job_id": case["job"]["job_id"],
                "reviewer_id": "maintenance-reviewer",
                "decision": "accept_manual",
                "method": "reviewed_manual_four_point",
                "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                "anchors": [],
                "notes": "",
                "created_at": OLD_TIMESTAMP,
            }
        )

    def _insert_retention_projection(self, case_id: str):
        manifest = link_manifest()
        evidence = manifest["physical_evidence"][0]
        evidence["server_case_id"] = case_id
        evidence["physical_evidence_snapshot_sha256"] = canonical_sha256(
            {
                key: value
                for key, value in evidence.items()
                if key != "physical_evidence_snapshot_sha256"
            }
        )
        manifest_sha256 = canonical_sha256(manifest)
        repair_case_id = manifest["repair_case_references"][0][
            "repair_case_id"
        ]
        with self.service.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO repair_evidence_link_revisions (
                    link_set_id, revision, manifest_sha256, repair_case_id,
                    board_key, board_id, manifest_json, import_actor_id,
                    imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest["link_set_id"],
                    manifest["revision"],
                    manifest_sha256,
                    repair_case_id,
                    manifest["board"]["board_key"],
                    manifest["board"]["board_id"],
                    json.dumps(
                        manifest,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "maintenance-reviewer",
                    OLD_TIMESTAMP,
                ),
            )
            connection.execute(
                """
                INSERT INTO repair_evidence_link_cases (
                    link_set_id, revision, server_case_id,
                    physical_evidence_snapshot_sha256
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    manifest["link_set_id"],
                    manifest["revision"],
                    case_id,
                    evidence["physical_evidence_snapshot_sha256"],
                ),
            )
            connection.commit()
        return manifest

    def test_health_reports_disk_pressure_and_operational_counts(self):
        self._create_case("queued-case", encode_jpeg(140))

        with patch(
            "scripts.visual_qc.server.storage.shutil.disk_usage",
            return_value=SimpleNamespace(total=1000, used=850, free=150),
        ):
            response = self.client.get("/api/v1/visual-qc/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], "VISUAL-QC-SERVER-HEALTH-V2")
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["storage"]["pressure"], "warning")
        self.assertEqual(payload["storage"]["free_bytes"], 150)
        self.assertEqual(payload["storage"]["minimum_free_bytes"], 100)
        self.assertEqual(payload["jobs"]["queued"], 1)
        self.assertEqual(payload["cases"]["total"], 1)

    def test_retention_execution_requires_the_exact_confirmation_phrase(self):
        self.assertFalse(validate_execution_confirmation(False, None))
        with self.assertRaisesRegex(ValueError, "DELETE-EXPIRED-DRAFTS"):
            validate_execution_confirmation(True, None)
        with self.assertRaisesRegex(ValueError, "DELETE-EXPIRED-DRAFTS"):
            validate_execution_confirmation(True, "delete")
        self.assertTrue(
            validate_execution_confirmation(True, "DELETE-EXPIRED-DRAFTS")
        )

    def test_cli_dry_run_does_not_requeue_a_running_job(self):
        case = self._create_case("running-dry-run", encode_jpeg(145))
        claimed = self.service.store.claim_next_job()
        self.assertEqual(claimed["job_id"], case["job"]["job_id"])
        self.assertEqual(claimed["status"], "running")

        with redirect_stdout(io.StringIO()):
            exit_code = maintenance_main(
                ["--data-root", str(self.settings.data_root)]
            )

        self.assertEqual(exit_code, 0)
        restored = self.service.store.get_job(case["job"]["job_id"])
        self.assertEqual(restored["status"], "running")

    def test_retention_deletes_only_unreviewed_terminal_drafts_and_keeps_shared_objects(self):
        shared_content = encode_jpeg(110)
        stale = self._create_case("stale", shared_content)
        recent_shared = self._create_case("recent-shared", shared_content)
        reviewed = self._create_case("reviewed", encode_jpeg(120))
        golden = self._create_case("golden", encode_jpeg(130))
        candidate_reviewed = self._create_case("candidate-reviewed", encode_jpeg(150))

        for case in (stale, reviewed, golden, candidate_reviewed):
            self._make_old_terminal(case["case_id"])

        self._review_registration(reviewed)
        golden_review = self._review_registration(golden)
        self.service.store.create_golden_sample(
            {
                "golden_sample_id": "gold-maintenance-test",
                "case_id": golden["case_id"],
                "registration_review_id": golden_review["review_id"],
                "board_key": "km4-f151",
                "board_id": "F151 MAIN PCB",
                "side_id": "main_page_2",
                "capture_setup_id": "maintenance-rig",
                "source_sha256": golden["image"]["sha256"],
                "reviewer_id": "maintenance-reviewer",
                "created_at": OLD_TIMESTAMP,
            }
        )
        self.service.store.create_candidate_review(
            {
                "candidate_review_id": "candidate-review-maintenance-test",
                "case_id": candidate_reviewed["case_id"],
                "job_id": candidate_reviewed["job"]["job_id"],
                "candidate_id": "candidate-1",
                "reviewer_id": "maintenance-reviewer",
                "decision": "rejected",
                "defect_category": None,
                "label_source": "human_review",
                "candidate": {"candidate_id": "candidate-1"},
                "notes": "",
                "created_at": OLD_TIMESTAMP,
            }
        )

        dry_run = self.service.run_retention(dry_run=True, now=NOW)

        self.assertEqual(dry_run["schema_version"], "VISUAL-QC-RETENTION-RUN-V1")
        self.assertTrue(dry_run["dry_run"])
        self.assertEqual(dry_run["candidate_case_ids"], [stale["case_id"]])
        self.assertIsNotNone(self.service.store.get_case(stale["case_id"]))

        shared_path = Path(
            self.service.store.get_case(stale["case_id"])["image"]["storage_path"]
        )
        executed = self.service.run_retention(dry_run=False, now=NOW)

        self.assertEqual(executed["deleted_cases"], 1)
        self.assertEqual(executed["deleted_objects"], 0)
        self.assertIsNone(self.service.store.get_case(stale["case_id"]))
        self.assertIsNotNone(self.service.store.get_case(recent_shared["case_id"]))
        self.assertIsNotNone(self.service.store.get_case(reviewed["case_id"]))
        self.assertIsNotNone(self.service.store.get_case(golden["case_id"]))
        self.assertIsNotNone(self.service.store.get_case(candidate_reviewed["case_id"]))
        self.assertTrue(shared_path.is_file())

        with self.service.store.connect() as connection:
            run = connection.execute(
                "SELECT * FROM retention_runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        self.assertEqual(run["status"], "completed")

    def test_retention_requires_at_least_one_job_and_only_known_terminal_states(self):
        missing_job = self._create_case("missing-job", encode_jpeg(151))
        unknown_state = self._create_case("unknown-state", encode_jpeg(152))
        eligible = self._create_case("known-terminal", encode_jpeg(153))
        for case in (missing_job, unknown_state, eligible):
            self._make_old_terminal(case["case_id"])

        with self.service.store.connect() as connection:
            connection.execute(
                "DELETE FROM jobs WHERE case_id = ?",
                (missing_job["case_id"],),
            )
            connection.execute(
                "UPDATE jobs SET status = 'paused' WHERE case_id = ?",
                (unknown_state["case_id"],),
            )
            connection.commit()

        plan = self.service.run_retention(dry_run=True, now=NOW)

        self.assertEqual(plan["candidate_case_ids"], [eligible["case_id"]])

    def test_retention_excludes_linked_cases_and_reports_exact_audit_reason(self):
        linked = self._create_case("linked-retention", encode_jpeg(154))
        self._make_old_terminal(linked["case_id"])
        self._insert_retention_projection(linked["case_id"])

        plan = self.service.run_retention(dry_run=True, now=NOW)

        self.assertNotIn(linked["case_id"], plan["candidate_case_ids"])
        self.assertIn(
            {
                "case_id": linked["case_id"],
                "reason": "repair_evidence_link_present",
            },
            plan["excluded_cases"],
        )
        self.assertIsNotNone(self.service.store.get_case(linked["case_id"]))

    def test_retention_uses_manifest_when_child_projection_is_missing(self):
        linked = self._create_case("linked-child-missing", encode_jpeg(155))
        self._make_old_terminal(linked["case_id"])
        manifest = self._insert_retention_projection(linked["case_id"])
        with self.service.store.connect() as connection:
            connection.execute(
                "DELETE FROM repair_evidence_link_cases "
                "WHERE link_set_id = ? AND revision = ?",
                (manifest["link_set_id"], manifest["revision"]),
            )
            connection.commit()

        plan = self.service.run_retention(dry_run=True, now=NOW)

        self.assertEqual(plan["candidate_case_ids"], [])
        self.assertIn(
            {
                "case_id": linked["case_id"],
                "reason": "repair_evidence_link_present",
            },
            plan["excluded_cases"],
        )
        with self.assertRaisesRegex(
            Exception, "repair_evidence_link_projection_corrupt"
        ):
            self.service.store.get_repair_evidence_link_revision(
                manifest["link_set_id"], manifest["revision"]
            )

    def test_retention_fails_closed_when_link_case_child_is_orphaned(self):
        linked = self._create_case("linked-orphaned", encode_jpeg(156))
        unrelated = self._create_case("unrelated-orphaned", encode_jpeg(157))
        for case in (linked, unrelated):
            self._make_old_terminal(case["case_id"])
        manifest = self._insert_retention_projection(linked["case_id"])

        connection = sqlite3.connect(self.service.store.database_path)
        try:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                "DELETE FROM repair_evidence_link_revisions "
                "WHERE link_set_id = ? AND revision = ?",
                (manifest["link_set_id"], manifest["revision"]),
            )
            connection.commit()
        finally:
            connection.close()

        plan = self.service.run_retention(dry_run=True, now=NOW)

        self.assertEqual(plan["candidate_case_ids"], [])
        self.assertEqual(
            plan["excluded_cases"],
            [
                {
                    "case_id": case_id,
                    "reason": "repair_evidence_link_authority_unavailable",
                }
                for case_id in sorted(
                    (linked["case_id"], unrelated["case_id"])
                )
            ],
        )

        executed = self.service.run_retention(dry_run=False, now=NOW)

        self.assertEqual(executed["deleted_cases"], 0)
        self.assertIsNotNone(self.service.store.get_case(linked["case_id"]))
        self.assertIsNotNone(self.service.store.get_case(unrelated["case_id"]))

    def test_retention_records_final_protection_when_orphan_appears_before_delete(self):
        stale = self._create_case("stale-race-orphan", encode_jpeg(158))
        unrelated = self._create_case("unrelated-race-orphan", encode_jpeg(159))
        for case in (stale, unrelated):
            self._make_old_terminal(case["case_id"])

        original_delete = self.service.store.delete_retention_candidates

        def introduce_orphan_before_delete(candidates, cutoff_at):
            connection = sqlite3.connect(self.service.store.database_path)
            try:
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.execute(
                    """
                    INSERT INTO repair_evidence_link_cases (
                        link_set_id, revision, server_case_id,
                        physical_evidence_snapshot_sha256
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        "race-orphan-link-set",
                        1,
                        stale["case_id"],
                        "f" * 64,
                    ),
                )
                connection.commit()
            finally:
                connection.close()
            return original_delete(candidates, cutoff_at)

        with patch.object(
            self.service.store,
            "delete_retention_candidates",
            side_effect=introduce_orphan_before_delete,
        ):
            executed = self.service.run_retention(dry_run=False, now=NOW)

        expected_exclusions = [
            {
                "case_id": case_id,
                "reason": "repair_evidence_link_authority_unavailable",
            }
            for case_id in sorted((stale["case_id"], unrelated["case_id"]))
        ]
        self.assertEqual(executed["deleted_cases"], 0)
        self.assertEqual(executed["candidate_case_ids"], [])
        self.assertEqual(executed["candidate_count"], 0)
        self.assertEqual(executed["excluded_cases"], expected_exclusions)
        self.assertIsNotNone(self.service.store.get_case(stale["case_id"]))
        self.assertIsNotNone(self.service.store.get_case(unrelated["case_id"]))

        with self.service.store.connect() as connection:
            run = connection.execute(
                "SELECT * FROM retention_runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        payload = json.loads(run["payload_json"])
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["candidate_count"], 0)
        self.assertEqual(payload["candidate_case_ids"], [])
        self.assertEqual(payload["excluded_cases"], expected_exclusions)

    def test_retention_fails_closed_when_canonical_manifest_is_corrupt(self):
        linked = self._create_case("linked-corrupt", encode_jpeg(156))
        unrelated = self._create_case("unrelated-corrupt", encode_jpeg(157))
        for case in (linked, unrelated):
            self._make_old_terminal(case["case_id"])
        manifest = self._insert_retention_projection(linked["case_id"])
        with self.service.store.connect() as connection:
            connection.execute(
                """
                UPDATE repair_evidence_link_revisions
                SET manifest_json = '{}'
                WHERE link_set_id = ? AND revision = ?
                """,
                (manifest["link_set_id"], manifest["revision"]),
            )
            connection.commit()

        plan = self.service.run_retention(dry_run=True, now=NOW)

        self.assertEqual(plan["candidate_case_ids"], [])
        self.assertEqual(
            plan["excluded_cases"],
            [
                {
                    "case_id": case_id,
                    "reason": "repair_evidence_link_authority_unavailable",
                }
                for case_id in sorted(
                    (linked["case_id"], unrelated["case_id"])
                )
            ],
        )

    def test_upload_reference_commit_and_retention_object_deletion_are_serialized(self):
        shared_content = encode_jpeg(160)
        stale = self._create_case("stale-concurrent", shared_content)
        self._make_old_terminal(stale["case_id"])
        shared_path = Path(
            self.service.store.get_case(stale["case_id"])["image"]["storage_path"]
        )

        original_create_case = self.service.store.create_case
        upload_at_commit = threading.Event()
        allow_upload_commit = threading.Event()
        upload_result = {}
        retention_result = {}

        def blocked_create_case(*args, **kwargs):
            upload_at_commit.set()
            self.assertTrue(allow_upload_commit.wait(timeout=5))
            return original_create_case(*args, **kwargs)

        def upload():
            upload_result["case"] = self._create_case(
                "new-concurrent",
                shared_content,
            )

        def retain():
            retention_result["run"] = self.service.run_retention(
                dry_run=False,
                now=NOW,
            )

        with patch.object(self.service.store, "create_case", blocked_create_case):
            upload_thread = threading.Thread(target=upload)
            upload_thread.start()
            self.assertTrue(upload_at_commit.wait(timeout=5))

            retention_thread = threading.Thread(target=retain)
            retention_thread.start()
            retention_thread.join(timeout=0.25)
            allow_upload_commit.set()
            upload_thread.join(timeout=5)
            retention_thread.join(timeout=5)

        self.assertFalse(upload_thread.is_alive())
        self.assertFalse(retention_thread.is_alive())
        self.assertEqual(retention_result["run"]["deleted_cases"], 1)
        self.assertTrue(shared_path.is_file())
        new_case = self.service.store.get_case(upload_result["case"]["case_id"])
        self.assertEqual(Path(new_case["image"]["storage_path"]), shared_path)

    def test_retention_records_a_failed_run_when_object_cleanup_raises(self):
        stale = self._create_case("stale-cleanup-error", encode_jpeg(170))
        self._make_old_terminal(stale["case_id"])

        with patch.object(
            self.service.storage,
            "delete_unreferenced",
            side_effect=StorageCleanupError(
                "simulated object cleanup failure",
                deleted_objects=2,
                deleted_bytes=42,
            ),
        ):
            with self.assertRaisesRegex(
                StorageCleanupError,
                "simulated object cleanup failure",
            ):
                self.service.run_retention(dry_run=False, now=NOW)

        with self.service.store.connect() as connection:
            run = connection.execute(
                "SELECT * FROM retention_runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["deleted_cases"], 1)
        self.assertEqual(run["deleted_objects"], 2)
        self.assertEqual(run["deleted_bytes"], 42)
        self.assertIn("simulated object cleanup failure", run["error_message"])

    def test_retention_keeps_cleanup_totals_when_completion_recording_fails(self):
        stale = self._create_case("stale-completion-error", encode_jpeg(171))
        self._make_old_terminal(stale["case_id"])

        with patch.object(
            self.service.store,
            "complete_retention_run",
            side_effect=RuntimeError("simulated completion write failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "simulated completion write failure",
            ):
                self.service.run_retention(dry_run=False, now=NOW)

        with self.service.store.connect() as connection:
            run = connection.execute(
                "SELECT * FROM retention_runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["deleted_cases"], 1)
        self.assertEqual(run["deleted_objects"], 1)
        self.assertGreater(run["deleted_bytes"], 0)

    def test_storage_reference_transaction_serializes_independent_adapters(self):
        first = LocalObjectStorage(self.settings.data_root, minimum_free_bytes=0)
        second = LocalObjectStorage(self.settings.data_root, minimum_free_bytes=0)
        first_acquired = threading.Event()
        release_first = threading.Event()
        second_acquired = threading.Event()

        def hold_first():
            with first.reference_transaction():
                first_acquired.set()
                self.assertTrue(release_first.wait(timeout=5))

        def take_second():
            with second.reference_transaction():
                second_acquired.set()

        first_thread = threading.Thread(target=hold_first)
        second_thread = threading.Thread(target=take_second)
        first_thread.start()
        self.assertTrue(first_acquired.wait(timeout=5))
        second_thread.start()
        self.assertFalse(second_acquired.wait(timeout=0.2))
        release_first.set()
        first_thread.join(timeout=5)
        second_thread.join(timeout=5)

        self.assertTrue(second_acquired.is_set())


if __name__ == "__main__":
    unittest.main()
