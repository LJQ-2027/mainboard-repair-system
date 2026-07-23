import hashlib
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
import json
import subprocess
import sys
from unittest.mock import patch

import jsonschema
from scripts.visual_qc.upgrade_preflight import (
    audit_visual_qc_upgrade,
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
        (data_root / ".storage-reference.lock").write_bytes(b"\0")

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

    def test_read_only_snapshot_rejects_live_wal_database(self):
        source = self.root / "live.sqlite3"
        connection = sqlite3.connect(source)
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("CREATE TABLE cases (case_id TEXT PRIMARY KEY)")
            connection.execute("INSERT INTO cases VALUES ('live-case')")
            connection.commit()
            self.assertTrue(Path(f"{source}-wal").is_file())

            with self.assertRaisesRegex(ValueError, "consistent SQLite backup"):
                create_read_only_snapshot(
                    source,
                    self.root / "working" / "snapshot.sqlite3",
                )
        finally:
            connection.close()

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

    def test_candidate_schema_comparison_detects_dropped_index(self):
        source = self.create_f278061_database()
        working = self.root / "working" / "candidate.sqlite3"
        create_read_only_snapshot(source, working)
        before = database_projection(source)
        rehearse_candidate_migration(working, "f278061")
        expected = database_projection(working)
        with closing(sqlite3.connect(working)) as connection:
            connection.execute("DROP INDEX cases_actor_intake_entry")
            connection.commit()

        comparison = compare_database_projections(
            before,
            database_projection(working),
            source_version="f278061",
            expected_projection=expected,
        )

        self.assertEqual(comparison["status"], "failed")
        self.assertIn(
            "candidate_schema_contract_changed",
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

    def test_object_validation_hashes_from_one_open_file_handle(self):
        source = self.create_f278061_database()
        data_root = self.root / "visual-qc-data"
        self.attach_managed_objects(source, data_root)

        with patch.object(
            Path,
            "read_bytes",
            side_effect=AssertionError("path reopened during object hashing"),
        ):
            result = validate_managed_objects(source, data_root)

        self.assertEqual(result["status"], "passed")

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

    def snapshot_paths(self, database: Path, data_root: Path) -> dict:
        paths = [database]
        paths.extend(
            path for path in sorted(data_root.rglob("*")) if path.is_file()
        )
        return {
            (
                "database"
                if path == database
                else f"data/{path.relative_to(data_root).as_posix()}"
            ): sha256_file(path)
            for path in paths
        }

    def test_full_upgrade_audit_passes_without_mutating_source(self):
        source = self.create_f278061_database()
        source_data_root = self.root / "source-data"
        self.attach_managed_objects(source, source_data_root)
        source_app_root = self.create_rollback_app()
        before = self.snapshot_paths(source, source_data_root)

        report = audit_visual_qc_upgrade(
            project_root=ROOT,
            source_database=source,
            source_data_root=source_data_root,
            source_app_root=source_app_root,
            target_version="abcdef1",
            clock=lambda: "2026-07-23T12:00:00.000Z",
        )

        self.assertEqual(report["schema_version"], "VISUAL-QC-UPGRADE-PREFLIGHT-V1")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["generated_at"], "2026-07-23T12:00:00.000Z")
        self.assertEqual(report["source"]["version"], "f278061")
        self.assertEqual(report["source"]["snapshot_sha256"], sha256_file(source))
        self.assertEqual(report["target"]["version"], "abcdef1")
        self.assertEqual(
            [check["check_id"] for check in report["checks"]],
            [
                "source_version_supported",
                "source_database_integrity",
                "managed_objects_integrity",
                "candidate_migration_integrity",
                "candidate_schema_additive",
                "candidate_rows_preserved",
                "candidate_runtime_contract",
                "candidate_dataset_gates",
                "rollback_runtime_compatible",
                "source_immutable",
            ],
        )
        self.assertTrue(all(check["status"] == "passed" for check in report["checks"]))
        self.assertEqual(
            report["migration"]["added_columns"],
            [{"table": "cases", "columns": ["qualified_handoff_json"]}],
        )
        self.assertEqual(report["candidate_runtime"]["counts"]["database_cases"], 1)
        self.assertEqual(report["rollback_runtime"]["cases_read"], 1)
        self.assertEqual(self.snapshot_paths(source, source_data_root), before)
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_full_upgrade_audit_requires_existing_storage_reference_lock(self):
        source = self.create_f278061_database()
        source_data_root = self.root / "source-data"
        self.attach_managed_objects(source, source_data_root)
        (source_data_root / ".storage-reference.lock").unlink()

        with self.assertRaisesRegex(ValueError, "storage reference lock"):
            audit_visual_qc_upgrade(
                project_root=ROOT,
                source_database=source,
                source_data_root=source_data_root,
                source_app_root=self.create_rollback_app(),
                target_version="abcdef1",
            )

    def test_top_level_fails_when_candidate_smoke_has_non_dataset_issue(self):
        source = self.create_f278061_database()
        source_data_root = self.root / "source-data"
        self.attach_managed_objects(source, source_data_root)
        candidate_failure = {
            "status": "failed",
            "api_schemas": {
                "health": "VISUAL-QC-SERVER-HEALTH-V2",
                "admin_list": "VISUAL-QC-ADMIN-CASE-LIST-V2",
                "admin_detail": "VISUAL-QC-SERVER-CASE-V3",
                "dataset_audit": "VISUAL-QC-DATASET-AUDIT-V1",
            },
            "counts": {
                "database_cases": 1,
                "listed_cases": 1,
                "detailed_cases": 1,
            },
            "dataset": {
                "eligible_case_count": 0,
                "excluded_case_count": 1,
                "reason_counts": {"non_physical_evidence": 1},
            },
            "issues": [
                {
                    "error_code": "candidate_admin_list_count_mismatch",
                    "message": "Candidate list returned the wrong case identity.",
                }
            ],
        }

        with patch(
            "scripts.visual_qc.upgrade_preflight.smoke_candidate_runtime",
            return_value=candidate_failure,
        ):
            report = audit_visual_qc_upgrade(
                project_root=ROOT,
                source_database=source,
                source_data_root=source_data_root,
                source_app_root=self.create_rollback_app(),
                target_version="abcdef1",
            )

        self.assertEqual(report["status"], "failed")
        self.assertEqual(
            {
                check["check_id"]: check["status"]
                for check in report["checks"]
            }["candidate_runtime_contract"],
            "failed",
        )


class VisualQcUpgradePreflightCliTests(unittest.TestCase):
    def setUp(self):
        self.fixture = VisualQcUpgradePreflightTests()
        self.fixture.setUp()
        self.root = self.fixture.root
        self.source = self.fixture.create_f278061_database()
        self.data_root = self.root / "source-data"
        self.fixture.attach_managed_objects(self.source, self.data_root)
        self.directory_links = []

    def tearDown(self):
        for link in reversed(self.directory_links):
            if link.exists():
                os.rmdir(link)
        self.fixture.tearDown()

    def create_directory_link(self, link: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if result.returncode != 0:
                self.skipTest(f"Unable to create test junction: {result.stderr}")
        else:
            link.symlink_to(target, target_is_directory=True)
        self.directory_links.append(link)

    def run_cli(self, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_visual_qc_upgrade.py"),
                "--source-database",
                str(self.source),
                "--source-data-root",
                str(self.data_root),
                "--source-app-root",
                str(self.fixture.create_rollback_app()),
                "--target-version",
                "abcdef1",
                "--output",
                str(self.root / "reports" / "upgrade-preflight.json"),
                *map(str, extra),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_cli_publishes_schema_valid_passed_report(self):
        output = self.root / "reports" / "upgrade-preflight.json"
        before = self.fixture.snapshot_paths(self.source, self.data_root)

        completed = self.run_cli()

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(output.is_file())
        report = json.loads(output.read_text(encoding="utf-8"))
        schema = json.loads(
            (
                ROOT
                / "knowledge-base"
                / "visual-qc-upgrade-preflight-v1-schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(report)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(
            json.loads(completed.stdout)["schema_version"],
            "VISUAL-QC-UPGRADE-PREFLIGHT-V1",
        )
        self.assertEqual(
            self.fixture.snapshot_paths(self.source, self.data_root),
            before,
        )

    def test_report_schema_rejects_duplicate_or_reordered_checks(self):
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(
            (self.root / "reports" / "upgrade-preflight.json").read_text(
                encoding="utf-8"
            )
        )
        report["checks"][1] = dict(report["checks"][0])
        schema = json.loads(
            (
                ROOT
                / "knowledge-base"
                / "visual-qc-upgrade-preflight-v1-schema.json"
            ).read_text(encoding="utf-8")
        )

        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(report)

    def test_report_schema_rejects_status_that_disagrees_with_checks(self):
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(
            (self.root / "reports" / "upgrade-preflight.json").read_text(
                encoding="utf-8"
            )
        )
        report["checks"][0]["status"] = "failed"
        report["checks"][0]["error_code"] = "synthetic_failure"
        schema = json.loads(
            (
                ROOT
                / "knowledge-base"
                / "visual-qc-upgrade-preflight-v1-schema.json"
            ).read_text(encoding="utf-8")
        )

        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(report)

    def test_cli_does_not_overwrite_existing_report(self):
        output = self.root / "reports" / "upgrade-preflight.json"
        output.parent.mkdir(parents=True)
        output.write_bytes(b"keep-existing")

        completed = self.run_cli()

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(output.read_bytes(), b"keep-existing")
        self.assertEqual(json.loads(completed.stdout)["status"], "validation_failed")

    def test_cli_publishes_failed_report_with_exit_one(self):
        output = self.root / "reports" / "upgrade-preflight.json"
        incompatible_app = self.fixture.create_rollback_app(compatible=False)

        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_visual_qc_upgrade.py"),
                "--source-database",
                str(self.source),
                "--source-data-root",
                str(self.data_root),
                "--source-app-root",
                str(incompatible_app),
                "--target-version",
                "abcdef1",
                "--output",
                str(output),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "failed")
        rollback_check = {
            check["check_id"]: check for check in report["checks"]
        }["rollback_runtime_compatible"]
        self.assertEqual(rollback_check["status"], "failed")

    def test_cli_rejects_output_inside_source_data_root(self):
        output = self.data_root / "upgrade-preflight.json"

        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_visual_qc_upgrade.py"),
                "--source-database",
                str(self.source),
                "--source-data-root",
                str(self.data_root),
                "--source-app-root",
                str(self.fixture.create_rollback_app()),
                "--target-version",
                "abcdef1",
                "--output",
                str(output),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertFalse(output.exists())
        self.assertEqual(json.loads(completed.stdout)["status"], "validation_failed")

    def test_cli_rejects_reparse_point_in_output_parent_chain(self):
        target = self.root / "junction-target"
        (target / "existing-child").mkdir(parents=True)
        link = self.root / "junction-output"
        self.create_directory_link(link, target)
        output = link / "existing-child" / "upgrade-preflight.json"

        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_visual_qc_upgrade.py"),
                "--source-database",
                str(self.source),
                "--source-data-root",
                str(self.data_root),
                "--source-app-root",
                str(self.fixture.create_rollback_app()),
                "--target-version",
                "abcdef1",
                "--output",
                str(output),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
