import hashlib
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.visual_qc.upgrade_preflight import (
    compare_database_projections,
    create_read_only_snapshot,
    database_projection,
    rehearse_candidate_migration,
    smoke_candidate_runtime,
    smoke_rollback_runtime,
    validate_managed_objects,
)
from scripts.visual_qc.server.store import VisualQcStore


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VisualQcUpgradePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_source_database(self) -> Path:
        database = self.root / "source.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            connection.executescript(
                """
                CREATE TABLE cases (
                    case_id TEXT PRIMARY KEY,
                    evidence_role TEXT NOT NULL
                );
                INSERT INTO cases VALUES
                    ('proxy-case', 'service_manual_proxy'),
                    ('physical-case', 'physical_capture');
                """
            )
            connection.commit()
        return database

    def create_f278061_database(self) -> Path:
        database = self.root / "f278061.sqlite3"
        VisualQcStore(database, recover_interrupted_jobs=False)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "ALTER TABLE cases DROP COLUMN qualified_handoff_json"
            )
            connection.execute(
                """
                INSERT INTO cases (
                    case_id, actor_id, idempotency_key, request_fingerprint,
                    board_key, board_id, side_id, capture_stage, evidence_role,
                    capture_session_id, capture_setup_id, capture_checklist_json,
                    intake_batch_id, intake_entry_id, reference_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-proxy",
                    "owner-001",
                    "legacy-key",
                    "legacy-fingerprint",
                    "km4-f151",
                    "BOARD-KM4-F151-MAIN-V1.2",
                    "main_page_2",
                    "golden_reference",
                    "service_manual_proxy",
                    "legacy-session",
                    "standard-bench",
                    '{"status":"not_applicable","items":{}}',
                    None,
                    None,
                    "reference.png",
                    "2026-07-20T00:00:00.000Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO capture_sessions (
                    actor_id, capture_session_id, board_key, board_id,
                    capture_stage, evidence_role, capture_setup_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "owner-001",
                    "legacy-session",
                    "km4-f151",
                    "BOARD-KM4-F151-MAIN-V1.2",
                    "golden_reference",
                    "service_manual_proxy",
                    "standard-bench",
                    "2026-07-20T00:00:00.000Z",
                ),
            )
            connection.commit()
        return database

    def attach_managed_objects(self, database: Path, data_root: Path) -> dict:
        original_bytes = b"\xff\xd8\xffvisual-qc-upgrade-original"
        original_sha256 = hashlib.sha256(original_bytes).hexdigest()
        original_path = (
            data_root
            / "objects"
            / "originals"
            / original_sha256[:2]
            / f"{original_sha256}.jpg"
        )
        original_path.parent.mkdir(parents=True)
        original_path.write_bytes(original_bytes)

        artifact_bytes = b'{"kind":"registration-evidence"}'
        artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
        artifact_path = (
            data_root
            / "objects"
            / "artifacts"
            / artifact_sha256[:2]
            / f"{artifact_sha256}.json"
        )
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_bytes(artifact_bytes)

        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                """
                INSERT INTO images (
                    image_id, case_id, original_filename, mime_type, byte_size,
                    width, height, sha256, storage_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-image",
                    "legacy-proxy",
                    "proxy.jpg",
                    "image/jpeg",
                    len(original_bytes),
                    1200,
                    800,
                    original_sha256,
                    str(original_path.resolve()),
                    "2026-07-20T00:00:00.000Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, case_id, image_id, job_type, status, attempt_count,
                    result_json, error_code, error_message, input_json,
                    dedupe_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-job",
                    "legacy-proxy",
                    "legacy-image",
                    "automatic_registration",
                    "succeeded",
                    1,
                    '{"quality":{"status":"usable"}}',
                    None,
                    None,
                    "{}",
                    "legacy-job-dedupe",
                    "2026-07-20T00:00:00.000Z",
                    "2026-07-20T00:00:00.000Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, case_id, job_id, kind, mime_type, sha256,
                    byte_size, storage_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-artifact",
                    "legacy-proxy",
                    "legacy-job",
                    "registration_candidate",
                    "application/json",
                    artifact_sha256,
                    len(artifact_bytes),
                    str(artifact_path.resolve()),
                    "2026-07-20T00:00:00.000Z",
                ),
            )
            connection.commit()
        return {
            "original_path": original_path,
            "original_sha256": original_sha256,
            "artifact_path": artifact_path,
            "artifact_sha256": artifact_sha256,
        }

    def test_read_only_snapshot_binds_source_without_changing_it(self):
        source = self.create_source_database()
        destination = self.root / "working" / "snapshot.sqlite3"
        before_bytes = source.read_bytes()
        before_sha256 = sha256_file(source)

        evidence = create_read_only_snapshot(source, destination)

        self.assertEqual(source.read_bytes(), before_bytes)
        self.assertEqual(sha256_file(source), before_sha256)
        self.assertTrue(destination.is_file())
        self.assertEqual(evidence["integrity"], "ok")
        self.assertEqual(evidence["snapshot_sha256"], sha256_file(destination))
        self.assertEqual(evidence["logical_digest"], database_projection(source)["digest"])
        self.assertEqual(evidence["table_counts"], {"cases": 2})
        self.assertEqual(
            database_projection(destination),
            database_projection(source),
        )

    def test_candidate_migration_is_additive_and_preserves_legacy_rows(self):
        source = self.create_f278061_database()
        working = self.root / "working" / "candidate.sqlite3"
        create_read_only_snapshot(source, working)
        before = database_projection(source)

        result = rehearse_candidate_migration(working, "f278061")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["integrity"], "ok")
        self.assertEqual(
            result["added_columns"],
            [{"table": "cases", "columns": ["qualified_handoff_json"]}],
        )
        self.assertEqual(result["before_digest"], before["digest"])
        self.assertEqual(result["shared_digest"], before["digest"])
        self.assertEqual(result["table_counts"], before["table_counts"])
        with closing(sqlite3.connect(working)) as connection:
            row = connection.execute(
                "SELECT case_id, qualified_handoff_json FROM cases"
            ).fetchone()
        self.assertEqual(row, ("legacy-proxy", None))

    def test_unexpected_schema_drift_fails_closed(self):
        source = self.create_f278061_database()
        working = self.root / "working" / "candidate.sqlite3"
        create_read_only_snapshot(source, working)
        before = database_projection(source)
        rehearse_candidate_migration(working, "f278061")
        with closing(sqlite3.connect(working)) as connection:
            connection.execute("ALTER TABLE cases ADD COLUMN unreviewed_data TEXT")
            connection.commit()

        comparison = compare_database_projections(
            before,
            database_projection(working),
            source_version="f278061",
        )

        self.assertEqual(comparison["status"], "failed")
        self.assertIn(
            "unexpected_additive_schema",
            [issue["error_code"] for issue in comparison["issues"]],
        )

    def test_managed_objects_match_canonical_paths_and_hashes(self):
        source = self.create_f278061_database()
        data_root = self.root / "visual-qc-data"
        objects = self.attach_managed_objects(source, data_root)
        before = {
            path.name: sha256_file(path)
            for path in (objects["original_path"], objects["artifact_path"])
        }

        result = validate_managed_objects(source, data_root)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(
            result["counts"],
            {"originals": 1, "artifacts": 1, "total": 2},
        )
        self.assertEqual(result["issues"], [])
        self.assertEqual(
            {
                path.name: sha256_file(path)
                for path in (objects["original_path"], objects["artifact_path"])
            },
            before,
        )

    def test_missing_or_changed_managed_object_fails_closed(self):
        source = self.create_f278061_database()
        data_root = self.root / "visual-qc-data"
        objects = self.attach_managed_objects(source, data_root)
        objects["original_path"].unlink()
        objects["artifact_path"].write_bytes(b"changed")

        result = validate_managed_objects(source, data_root)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            [issue["error_code"] for issue in result["issues"]],
            [
                "managed_object_hash_mismatch",
                "managed_object_missing",
                "managed_object_size_mismatch",
            ],
        )

    def test_database_storage_path_must_match_canonical_object_path(self):
        source = self.create_f278061_database()
        data_root = self.root / "visual-qc-data"
        self.attach_managed_objects(source, data_root)
        escaped = self.root / "outside.jpg"
        escaped.write_bytes(b"outside")
        with closing(sqlite3.connect(source)) as connection:
            connection.execute(
                "UPDATE images SET storage_path = ? WHERE image_id = ?",
                (str(escaped.resolve()), "legacy-image"),
            )
            connection.commit()

        result = validate_managed_objects(source, data_root)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "managed_object_path_mismatch",
            [issue["error_code"] for issue in result["issues"]],
        )

    def prepare_candidate_data_root(self, *, physical=False) -> Path:
        source = self.create_f278061_database()
        source_data_root = self.root / "source-data"
        self.attach_managed_objects(source, source_data_root)
        if physical:
            with closing(sqlite3.connect(source)) as connection:
                connection.execute(
                    """
                    UPDATE cases
                    SET evidence_role = 'physical_capture',
                        capture_stage = 'before_repair',
                        capture_checklist_json =
                            '{"status":"confirmed","items":{"board_identity":true}}'
                    """
                )
                connection.execute(
                    """
                    UPDATE capture_sessions
                    SET evidence_role = 'physical_capture',
                        capture_stage = 'before_repair'
                    """
                )
                connection.commit()
        candidate_root = self.root / (
            "candidate-physical" if physical else "candidate-proxy"
        )
        candidate_database = candidate_root / "visual-qc.sqlite3"
        create_read_only_snapshot(source, candidate_database)
        result = rehearse_candidate_migration(candidate_database, "f278061")
        self.assertEqual(result["status"], "passed")
        return candidate_root

    def test_candidate_runtime_exposes_new_contract_and_excludes_proxy(self):
        candidate_root = self.prepare_candidate_data_root()

        result = smoke_candidate_runtime(ROOT, candidate_root)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(
            result["api_schemas"],
            {
                "health": "VISUAL-QC-SERVER-HEALTH-V2",
                "admin_list": "VISUAL-QC-ADMIN-CASE-LIST-V2",
                "admin_detail": "VISUAL-QC-SERVER-CASE-V3",
                "dataset_audit": "VISUAL-QC-DATASET-AUDIT-V1",
            },
        )
        self.assertEqual(
            result["counts"],
            {"database_cases": 1, "listed_cases": 1, "detailed_cases": 1},
        )
        self.assertEqual(result["dataset"]["eligible_case_count"], 0)
        self.assertEqual(
            result["dataset"]["reason_counts"],
            {"non_physical_evidence": 1},
        )

    def test_candidate_runtime_excludes_legacy_physical_without_handoff(self):
        candidate_root = self.prepare_candidate_data_root(physical=True)

        result = smoke_candidate_runtime(ROOT, candidate_root)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["dataset"]["eligible_case_count"], 0)
        self.assertEqual(
            result["dataset"]["reason_counts"],
            {"qualified_handoff_provenance_required": 1},
        )

    def create_rollback_app(self, *, compatible=True) -> Path:
        app_root = self.root / (
            "rollback-compatible" if compatible else "rollback-incompatible"
        )
        store_path = app_root / "scripts" / "visual_qc" / "server" / "store.py"
        store_path.parent.mkdir(parents=True)
        (app_root / "VERSION").write_text("f278061\n", encoding="ascii")
        rejection = """
            columns = {
                row[1]
                for row in self.connection.execute("PRAGMA table_info(cases)")
            }
            if "qualified_handoff_json" in columns:
                raise RuntimeError("new column rejected")
""" if not compatible else ""
        store_path.write_text(
            f"""
import sqlite3


class VisualQcStore:
    def __init__(self, database_path, recover_interrupted_jobs=True):
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
{rejection}

    def operational_counts(self):
        count = self.connection.execute(
            "SELECT COUNT(*) FROM cases"
        ).fetchone()[0]
        return {{"cases": {{"total": count}}}}

    def get_case(self, case_id):
        row = self.connection.execute(
            "SELECT case_id FROM cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()
        return {{"case": dict(row)}} if row else None
""".lstrip(),
            encoding="utf-8",
        )
        return app_root

    def test_rollback_runtime_reads_candidate_migrated_database(self):
        candidate_root = self.prepare_candidate_data_root()
        rollback_database = self.root / "rollback.sqlite3"
        create_read_only_snapshot(
            candidate_root / "visual-qc.sqlite3",
            rollback_database,
        )

        result = smoke_rollback_runtime(
            self.create_rollback_app(),
            rollback_database,
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["source_version"], "f278061")
        self.assertEqual(result["case_count"], 1)
        self.assertEqual(result["cases_read"], 1)
        self.assertEqual(result["issues"], [])

    def test_rollback_runtime_incompatibility_fails_closed(self):
        candidate_root = self.prepare_candidate_data_root()
        rollback_database = self.root / "rollback.sqlite3"
        create_read_only_snapshot(
            candidate_root / "visual-qc.sqlite3",
            rollback_database,
        )

        result = smoke_rollback_runtime(
            self.create_rollback_app(compatible=False),
            rollback_database,
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            result["issues"][0]["error_code"],
            "rollback_runtime_incompatible",
        )


if __name__ == "__main__":
    unittest.main()
