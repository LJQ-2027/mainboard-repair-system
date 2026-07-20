from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class VisualQcStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.recover_interrupted_jobs()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self):
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL,
                    board_key TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    side_id TEXT NOT NULL,
                    capture_stage TEXT NOT NULL,
                    evidence_role TEXT NOT NULL,
                    reference_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(actor_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS images (
                    image_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id),
                    original_filename TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    byte_size INTEGER NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id),
                    image_id TEXT NOT NULL REFERENCES images(image_id),
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    input_json TEXT NOT NULL DEFAULT '{}',
                    dedupe_key TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL REFERENCES cases(case_id),
                    actor_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS registration_reviews (
                    review_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id),
                    job_id TEXT NOT NULL REFERENCES jobs(job_id),
                    reviewer_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    method TEXT NOT NULL,
                    matrix_json TEXT NOT NULL,
                    anchors_json TEXT NOT NULL DEFAULT '[]',
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS golden_samples (
                    golden_sample_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id),
                    registration_review_id TEXT NOT NULL REFERENCES registration_reviews(review_id),
                    board_key TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    side_id TEXT NOT NULL,
                    capture_setup_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    retired_at TEXT,
                    UNIQUE(board_key, side_id, capture_setup_id, version)
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id),
                    job_id TEXT NOT NULL REFERENCES jobs(job_id),
                    kind TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    byte_size INTEGER NOT NULL,
                    storage_path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS candidate_reviews (
                    candidate_review_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id),
                    job_id TEXT NOT NULL REFERENCES jobs(job_id),
                    candidate_id TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    defect_category TEXT,
                    label_source TEXT NOT NULL,
                    candidate_json TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_status_created
                    ON jobs(status, created_at);
                CREATE INDEX IF NOT EXISTS registration_reviews_case_created
                    ON registration_reviews(case_id, created_at);
                CREATE INDEX IF NOT EXISTS golden_samples_scope_status
                    ON golden_samples(board_key, side_id, capture_setup_id, status);
                CREATE INDEX IF NOT EXISTS candidate_reviews_job_candidate
                    ON candidate_reviews(job_id, candidate_id, created_at);
                """
            )
            review_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(registration_reviews)"
                ).fetchall()
            }
            if "anchors_json" not in review_columns:
                connection.execute(
                    "ALTER TABLE registration_reviews "
                    "ADD COLUMN anchors_json TEXT NOT NULL DEFAULT '[]'"
                )
            job_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "input_json" not in job_columns:
                connection.execute(
                    "ALTER TABLE jobs ADD COLUMN input_json TEXT NOT NULL DEFAULT '{}'"
                )
            if "dedupe_key" not in job_columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN dedupe_key TEXT")
                connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS jobs_dedupe_key "
                    "ON jobs(dedupe_key) WHERE dedupe_key IS NOT NULL"
                )
            connection.commit()

    def recover_interrupted_jobs(self):
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = 'queued',
                    error_code = 'worker_interrupted',
                    error_message = 'Recovered after an interrupted worker process.',
                    updated_at = ?
                WHERE status = 'running'
                """,
                (timestamp,),
            )
            connection.commit()

    def get_case_for_idempotency(self, actor_id: str, idempotency_key: str):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT case_id, request_fingerprint FROM cases WHERE actor_id = ? AND idempotency_key = ?",
                (actor_id, idempotency_key),
            ).fetchone()
        return dict(row) if row else None

    def create_case(self, case_record: dict, image_record: dict, job_record: dict):
        timestamp = case_record["created_at"]
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO cases (
                    case_id, actor_id, idempotency_key, request_fingerprint,
                    board_key, board_id, side_id, capture_stage, evidence_role,
                    reference_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(
                    case_record[key]
                    for key in (
                        "case_id", "actor_id", "idempotency_key", "request_fingerprint",
                        "board_key", "board_id", "side_id", "capture_stage", "evidence_role",
                        "reference_path", "created_at",
                    )
                ),
            )
            connection.execute(
                """
                INSERT INTO images (
                    image_id, case_id, original_filename, mime_type, byte_size,
                    width, height, sha256, storage_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(
                    image_record[key]
                    for key in (
                        "image_id", "case_id", "original_filename", "mime_type",
                        "byte_size", "width", "height", "sha256", "storage_path", "created_at",
                    )
                ),
            )
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, case_id, image_id, job_type, status, attempt_count,
                    input_json, dedupe_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(
                    job_record[key]
                    for key in (
                        "job_id", "case_id", "image_id", "job_type", "status",
                        "attempt_count", "input_json", "dedupe_key", "created_at", "updated_at",
                    )
                ),
            )
            connection.execute(
                """
                INSERT INTO audit_events (
                    case_id, actor_id, event_type, payload_json, created_at
                ) VALUES (?, ?, 'case_created', ?, ?)
                """,
                (
                    case_record["case_id"],
                    case_record["actor_id"],
                    json.dumps(
                        {"image_id": image_record["image_id"], "job_id": job_record["job_id"]},
                        separators=(",", ":"),
                    ),
                    timestamp,
                ),
            )
            connection.commit()

    def get_case(self, case_id: str):
        with self.connect() as connection:
            case = connection.execute(
                "SELECT * FROM cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
            if not case:
                return None
            image = connection.execute(
                "SELECT * FROM images WHERE case_id = ? ORDER BY created_at LIMIT 1",
                (case_id,),
            ).fetchone()
            job = connection.execute(
                "SELECT * FROM jobs WHERE case_id = ? ORDER BY created_at LIMIT 1",
                (case_id,),
            ).fetchone()
        return {
            "case": dict(case),
            "image": dict(image),
            "job": self._job_dict(job),
        }

    def get_job(self, job_id: str):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT jobs.*, cases.actor_id, cases.board_key, cases.board_id,
                       cases.side_id, cases.reference_path, images.storage_path
                FROM jobs
                JOIN cases USING(case_id)
                JOIN images USING(image_id)
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        return self._job_dict(row) if row else None

    def create_job(self, record: dict):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT job_id FROM jobs WHERE dedupe_key = ?",
                (record["dedupe_key"],),
            ).fetchone()
            if existing:
                connection.commit()
                return self.get_job(existing["job_id"])
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, case_id, image_id, job_type, status, attempt_count,
                    input_json, dedupe_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'queued', 0, ?, ?, ?, ?)
                """,
                (
                    record["job_id"],
                    record["case_id"],
                    record["image_id"],
                    record["job_type"],
                    json.dumps(record["input"], separators=(",", ":")),
                    record["dedupe_key"],
                    record["created_at"],
                    record["created_at"],
                ),
            )
            connection.commit()
        return self.get_job(record["job_id"])

    def get_latest_registration_review(self, case_id: str):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM registration_reviews
                WHERE case_id = ?
                ORDER BY created_at DESC, review_id DESC
                LIMIT 1
                """,
                (case_id,),
            ).fetchone()
        return self._registration_review_dict(row) if row else None

    def create_registration_review(self, record: dict):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO registration_reviews (
                    review_id, case_id, job_id, reviewer_id, decision,
                    method, matrix_json, anchors_json, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["review_id"],
                    record["case_id"],
                    record["job_id"],
                    record["reviewer_id"],
                    record["decision"],
                    record["method"],
                    json.dumps(record["board_to_image_matrix"], separators=(",", ":")),
                    json.dumps(record["anchors"], separators=(",", ":")),
                    record["notes"],
                    record["created_at"],
                ),
            )
            connection.execute(
                """
                INSERT INTO audit_events (
                    case_id, actor_id, event_type, payload_json, created_at
                ) VALUES (?, ?, 'registration_reviewed', ?, ?)
                """,
                (
                    record["case_id"],
                    record["reviewer_id"],
                    json.dumps(
                        {
                            "review_id": record["review_id"],
                            "decision": record["decision"],
                            "method": record["method"],
                        },
                        separators=(",", ":"),
                    ),
                    record["created_at"],
                ),
            )
            connection.commit()
        return self.get_latest_registration_review(record["case_id"])

    def create_golden_sample(self, record: dict):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            next_version = connection.execute(
                """
                SELECT COALESCE(MAX(version), 0) + 1 AS next_version
                FROM golden_samples
                WHERE board_key = ? AND side_id = ? AND capture_setup_id = ?
                """,
                (
                    record["board_key"],
                    record["side_id"],
                    record["capture_setup_id"],
                ),
            ).fetchone()["next_version"]
            connection.execute(
                """
                UPDATE golden_samples
                SET status = 'retired', retired_at = ?
                WHERE board_key = ? AND side_id = ? AND capture_setup_id = ?
                  AND status = 'active'
                """,
                (
                    record["created_at"],
                    record["board_key"],
                    record["side_id"],
                    record["capture_setup_id"],
                ),
            )
            connection.execute(
                """
                INSERT INTO golden_samples (
                    golden_sample_id, case_id, registration_review_id,
                    board_key, board_id, side_id, capture_setup_id, version,
                    status, source_sha256, reviewer_id, created_at, retired_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, NULL)
                """,
                (
                    record["golden_sample_id"],
                    record["case_id"],
                    record["registration_review_id"],
                    record["board_key"],
                    record["board_id"],
                    record["side_id"],
                    record["capture_setup_id"],
                    next_version,
                    record["source_sha256"],
                    record["reviewer_id"],
                    record["created_at"],
                ),
            )
            connection.execute(
                """
                INSERT INTO audit_events (
                    case_id, actor_id, event_type, payload_json, created_at
                ) VALUES (?, ?, 'golden_sample_activated', ?, ?)
                """,
                (
                    record["case_id"],
                    record["reviewer_id"],
                    json.dumps(
                        {
                            "golden_sample_id": record["golden_sample_id"],
                            "capture_setup_id": record["capture_setup_id"],
                            "version": next_version,
                        },
                        separators=(",", ":"),
                    ),
                    record["created_at"],
                ),
            )
            connection.commit()
        return self.get_active_golden_sample(
            record["board_key"],
            record["side_id"],
            record["capture_setup_id"],
        )

    def get_active_golden_sample(
        self,
        board_key: str,
        side_id: str,
        capture_setup_id: str,
    ):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT golden_samples.*, registration_reviews.matrix_json
                FROM golden_samples
                JOIN registration_reviews
                  ON registration_reviews.review_id = golden_samples.registration_review_id
                WHERE golden_samples.board_key = ?
                  AND golden_samples.side_id = ?
                  AND golden_samples.capture_setup_id = ?
                  AND golden_samples.status = 'active'
                ORDER BY golden_samples.version DESC
                LIMIT 1
                """,
                (board_key, side_id, capture_setup_id),
            ).fetchone()
        return self._golden_sample_dict(row) if row else None

    def get_golden_sample_material(self, golden_sample_id: str):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT golden_samples.*, registration_reviews.matrix_json,
                       images.storage_path
                FROM golden_samples
                JOIN registration_reviews
                  ON registration_reviews.review_id = golden_samples.registration_review_id
                JOIN images ON images.case_id = golden_samples.case_id
                WHERE golden_samples.golden_sample_id = ?
                """,
                (golden_sample_id,),
            ).fetchone()
        return self._golden_sample_dict(row) if row else None

    def create_artifact(self, record: dict):
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, case_id, job_id, kind, mime_type, sha256,
                    byte_size, storage_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(
                    record[key]
                    for key in (
                        "artifact_id", "case_id", "job_id", "kind", "mime_type",
                        "sha256", "byte_size", "storage_path", "created_at",
                    )
                ),
            )
            connection.commit()
        return self.get_artifact(record["artifact_id"])

    def get_artifact(self, artifact_id: str):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT artifacts.*, cases.actor_id
                FROM artifacts
                JOIN cases USING(case_id)
                WHERE artifact_id = ?
                """,
                (artifact_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_candidate_review(self, record: dict):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO candidate_reviews (
                    candidate_review_id, case_id, job_id, candidate_id,
                    reviewer_id, decision, defect_category, label_source,
                    candidate_json, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["candidate_review_id"],
                    record["case_id"],
                    record["job_id"],
                    record["candidate_id"],
                    record["reviewer_id"],
                    record["decision"],
                    record["defect_category"],
                    record["label_source"],
                    json.dumps(record["candidate"], separators=(",", ":")),
                    record["notes"],
                    record["created_at"],
                ),
            )
            connection.execute(
                """
                INSERT INTO audit_events (
                    case_id, actor_id, event_type, payload_json, created_at
                ) VALUES (?, ?, 'difference_candidate_reviewed', ?, ?)
                """,
                (
                    record["case_id"],
                    record["reviewer_id"],
                    json.dumps(
                        {
                            "candidate_review_id": record["candidate_review_id"],
                            "job_id": record["job_id"],
                            "candidate_id": record["candidate_id"],
                            "decision": record["decision"],
                            "defect_category": record["defect_category"],
                        },
                        separators=(",", ":"),
                    ),
                    record["created_at"],
                ),
            )
            connection.commit()
        return self.get_candidate_review(record["candidate_review_id"])

    def get_candidate_review(self, candidate_review_id: str):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM candidate_reviews WHERE candidate_review_id = ?",
                (candidate_review_id,),
            ).fetchone()
        return self._candidate_review_dict(row) if row else None

    def list_candidate_reviews(self, job_id: str):
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM candidate_reviews
                WHERE job_id = ?
                ORDER BY created_at DESC, candidate_review_id DESC
                """,
                (job_id,),
            ).fetchall()
        latest = {}
        for row in rows:
            review = self._candidate_review_dict(row)
            latest.setdefault(review["candidate_id"], review)
        return sorted(latest.values(), key=lambda review: review["candidate_id"])

    def claim_next_job(self):
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT job_id FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at, job_id
                LIMIT 1
                """
            ).fetchone()
            if not row:
                connection.commit()
                return None
            connection.execute(
                """
                UPDATE jobs
                SET status = 'running',
                    attempt_count = attempt_count + 1,
                    updated_at = ?,
                    error_code = NULL,
                    error_message = NULL
                WHERE job_id = ? AND status = 'queued'
                """,
                (timestamp, row["job_id"]),
            )
            connection.commit()
        return self.get_job(row["job_id"])

    def complete_job(self, job_id: str, result: dict):
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = 'succeeded', result_json = ?, updated_at = ?,
                    error_code = NULL, error_message = NULL
                WHERE job_id = ? AND status = 'running'
                """,
                (json.dumps(result, separators=(",", ":")), timestamp, job_id),
            )
            connection.commit()
        return self.get_job(job_id)

    def fail_job(self, job_id: str, error_code: str, error_message: str):
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = 'failed', error_code = ?, error_message = ?, updated_at = ?
                WHERE job_id = ? AND status = 'running'
                """,
                (error_code, error_message[:1000], timestamp, job_id),
            )
            connection.commit()
        return self.get_job(job_id)

    def retry_failed_job(self, job_id: str):
        timestamp = utc_now()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = 'queued', result_json = NULL, error_code = NULL,
                    error_message = NULL, updated_at = ?
                WHERE job_id = ? AND status = 'failed'
                """,
                (timestamp, job_id),
            )
            connection.commit()
        return self.get_job(job_id) if cursor.rowcount else None

    @staticmethod
    def _job_dict(row):
        if not row:
            return None
        result = dict(row)
        result["result"] = json.loads(result.pop("result_json")) if result.get("result_json") else None
        result.pop("result_json", None)
        result["input"] = json.loads(result.pop("input_json")) if result.get("input_json") else {}
        result.pop("input_json", None)
        return result

    @staticmethod
    def _registration_review_dict(row):
        result = dict(row)
        result["board_to_image_matrix"] = json.loads(result.pop("matrix_json"))
        result["anchors"] = json.loads(result.pop("anchors_json"))
        result["status"] = "reviewed"
        return result

    @staticmethod
    def _golden_sample_dict(row):
        result = dict(row)
        if "matrix_json" in result:
            result["board_to_image_matrix"] = json.loads(result.pop("matrix_json"))
        return result

    @staticmethod
    def _candidate_review_dict(row):
        result = dict(row)
        result["candidate"] = json.loads(result.pop("candidate_json"))
        return result
