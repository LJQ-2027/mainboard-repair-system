from __future__ import annotations

from contextlib import closing, contextmanager
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
from datetime import datetime, timezone

from scripts.visual_qc.source_library import (
    _absolute_lexical_path,
    _is_reparse_or_symlink,
)
from scripts.visual_qc.deployment_manifest import (
    FULL_COMMIT_PATTERN,
    SHA256_PATTERN as DEPLOYMENT_SHA256_PATTERN,
)
from scripts.visual_qc.server.store import VisualQcStore
from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.service import VisualQcService
from scripts.visual_qc.server.storage import LocalObjectStorage


UPGRADE_PREFLIGHT_SCHEMA_VERSION = "VISUAL-QC-UPGRADE-PREFLIGHT-V1"
EARLIEST_PRODUCTION_SOURCE = "08d08cd38aaffc9b01d901dfe9ef7684a614abac"
PREVIOUS_PRODUCTION_SOURCE = "7ed316c07130ef1488037f537c5968c832e16668"
CURRENT_PRODUCTION_SOURCE = "0594b06581ec41085b6e281159ee52b65ac80081"
NO_SCHEMA_CHANGE_SOURCES = frozenset(
    {
        EARLIEST_PRODUCTION_SOURCE,
        PREVIOUS_PRODUCTION_SOURCE,
        CURRENT_PRODUCTION_SOURCE,
    }
)
SUPPORTED_SOURCE_VERSIONS = frozenset({"f278061", *NO_SCHEMA_CHANGE_SOURCES})
ALLOWED_ADDITIVE_COLUMNS = {
    "f278061": {
        "cases": {"qualified_handoff_json"},
    },
    **{source: {} for source in NO_SCHEMA_CHANGE_SOURCES},
}
ALLOWED_ADDITIVE_TABLES = {
    "f278061": {
        "repair_evidence_link_revisions",
        "repair_evidence_link_cases",
    },
    **{source: set() for source in NO_SCHEMA_CHANGE_SOURCES},
}
ALLOWED_ADDITIVE_DEFINITIONS = {
    "f278061": {
        "cases": {
            "qualified_handoff_json": "TEXT",
        },
    },
    **{source: {} for source in NO_SCHEMA_CHANGE_SOURCES},
}
ALLOWED_ADDITIVE_SCHEMA_SQL = {
    "f278061": """
                CREATE TABLE IF NOT EXISTS repair_evidence_link_revisions (
                    link_set_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    manifest_sha256 TEXT NOT NULL,
                    repair_case_id TEXT NOT NULL,
                    board_key TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    import_actor_id TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    PRIMARY KEY (link_set_id, revision),
                    UNIQUE (manifest_sha256)
                );
                CREATE TABLE IF NOT EXISTS repair_evidence_link_cases (
                    link_set_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    server_case_id TEXT NOT NULL,
                    physical_evidence_snapshot_sha256 TEXT NOT NULL,
                    PRIMARY KEY (link_set_id, revision, server_case_id),
                    FOREIGN KEY (link_set_id, revision)
                        REFERENCES repair_evidence_link_revisions(link_set_id, revision),
                    FOREIGN KEY (server_case_id) REFERENCES cases(case_id)
                );
                CREATE INDEX IF NOT EXISTS repair_evidence_link_cases_server_case
                    ON repair_evidence_link_cases(server_case_id, link_set_id, revision);
    """,
    **{source: "" for source in NO_SCHEMA_CHANGE_SOURCES},
}
EXPECTED_ADDED_COLUMNS = {
    "f278061": [{"table": "cases", "columns": ["qualified_handoff_json"]}],
    **{source: [] for source in NO_SCHEMA_CHANGE_SOURCES},
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MANAGED_MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/json": ".json",
}


def _read_only_connection(database: Path) -> sqlite3.Connection:
    database = Path(database).resolve()
    if not database.is_file():
        raise ValueError("Source database does not exist.")
    connection = sqlite3.connect(
        f"{database.as_uri()}?mode=ro&immutable=1",
        uri=True,
        timeout=30,
    )
    connection.row_factory = sqlite3.Row
    return connection


def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _canonical_value(value):
    if isinstance(value, bytes):
        return {"type": "bytes", "hex": value.hex()}
    if isinstance(value, float):
        return {"type": "float", "value": value.hex()}
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    return {"type": "text", "value": str(value)}


def _canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _integrity_result(connection: sqlite3.Connection) -> str:
    rows = connection.execute("PRAGMA integrity_check").fetchall()
    values = [str(row[0]) for row in rows]
    return "ok" if values == ["ok"] else "\n".join(values)


def database_projection(database: Path) -> dict:
    with closing(_read_only_connection(database)) as connection:
        schema_objects = [
            {
                "type": row["type"],
                "name": row["name"],
                "table": row["tbl_name"],
                "sql": row["sql"],
            }
            for row in connection.execute(
                """
                SELECT type, name, tbl_name, sql
                FROM sqlite_schema
                WHERE type IN ('table', 'index', 'trigger', 'view')
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY type, name
                """
            ).fetchall()
        ]
        tables = [
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_schema
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        ]
        projected_tables = []
        for table in tables:
            quoted_table = _quoted_identifier(table)
            column_rows = connection.execute(
                f"PRAGMA table_xinfo({quoted_table})"
            ).fetchall()
            columns = [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key_position": row["pk"],
                    "hidden": row["hidden"],
                }
                for row in column_rows
            ]
            foreign_keys = [
                dict(row)
                for row in connection.execute(
                    f"PRAGMA foreign_key_list({quoted_table})"
                ).fetchall()
            ]
            indexes = []
            for index_row in connection.execute(
                f"PRAGMA index_list({quoted_table})"
            ).fetchall():
                index = dict(index_row)
                quoted_index = _quoted_identifier(index["name"])
                index["columns"] = [
                    dict(row)
                    for row in connection.execute(
                        f"PRAGMA index_xinfo({quoted_index})"
                    ).fetchall()
                ]
                indexes.append(index)
            indexes.sort(key=lambda item: item["name"])
            names = [column["name"] for column in columns]
            select_columns = ", ".join(_quoted_identifier(name) for name in names)
            rows = [
                [_canonical_value(value) for value in row]
                for row in connection.execute(
                    f"SELECT {select_columns} FROM {quoted_table}"
                ).fetchall()
            ]
            rows.sort(key=_canonical_json_bytes)
            projected_tables.append(
                {
                    "name": table,
                    "columns": columns,
                    "foreign_keys": foreign_keys,
                    "indexes": indexes,
                    "rows": rows,
                    "row_count": len(rows),
                }
            )

    payload = {
        "tables": projected_tables,
        "schema_objects": schema_objects,
    }
    schema_payload = {
        "schema_objects": schema_objects,
        "tables": [
            {
                "name": table["name"],
                "columns": table["columns"],
                "foreign_keys": table["foreign_keys"],
                "indexes": table["indexes"],
            }
            for table in projected_tables
        ],
    }
    return {
        **payload,
        "table_counts": {
            table["name"]: table["row_count"] for table in projected_tables
        },
        "digest": hashlib.sha256(_canonical_json_bytes(payload)).hexdigest(),
        "schema_digest": hashlib.sha256(
            _canonical_json_bytes(schema_payload)
        ).hexdigest(),
    }


def create_read_only_snapshot(source_database: Path, destination: Path) -> dict:
    source_database = Path(source_database).resolve()
    destination = Path(destination).resolve()
    if any(
        Path(f"{source_database}{suffix}").exists()
        for suffix in ("-wal", "-shm")
    ):
        raise ValueError(
            "Source database must be a consistent SQLite backup without WAL or SHM."
        )
    if destination.exists():
        raise ValueError("Snapshot destination already exists.")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with closing(_read_only_connection(source_database)) as source:
        source_integrity = _integrity_result(source)
        if source_integrity != "ok":
            raise ValueError("Source database integrity check failed.")
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            target.commit()

    projection = database_projection(destination)
    return {
        "integrity": source_integrity,
        "snapshot_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "logical_digest": projection["digest"],
        "table_counts": projection["table_counts"],
    }


def _table_map(projection: dict) -> dict[str, dict]:
    return {table["name"]: table for table in projection["tables"]}


def _projected_rows(table: dict, column_names: list[str]) -> list[list[dict]]:
    indexes = {
        column["name"]: index for index, column in enumerate(table["columns"])
    }
    rows = [
        [row[indexes[column_name]] for column_name in column_names]
        for row in table["rows"]
    ]
    rows.sort(key=_canonical_json_bytes)
    return rows


def _finding(error_code: str, message: str) -> dict:
    return {"error_code": error_code, "message": message}


def compare_database_projections(
    before: dict,
    after: dict,
    *,
    source_version: str,
    expected_projection: dict | None = None,
) -> dict:
    allowed = ALLOWED_ADDITIVE_COLUMNS.get(source_version)
    if allowed is None:
        raise ValueError(f"Unsupported source version: {source_version}")

    before_tables = _table_map(before)
    after_tables = _table_map(after)
    issues = []

    missing_tables = sorted(set(before_tables) - set(after_tables))
    added_tables = set(after_tables) - set(before_tables)
    reviewed_tables = ALLOWED_ADDITIVE_TABLES[source_version]
    unexpected_tables = sorted(added_tables - reviewed_tables)
    missing_reviewed_tables = sorted(reviewed_tables - added_tables)
    if missing_tables:
        issues.append(
            _finding(
                "source_table_removed",
                "Candidate migration removed source tables: "
                + ", ".join(missing_tables),
            )
        )
    if unexpected_tables:
        issues.append(
            _finding(
                "unexpected_additive_schema",
                "Candidate migration added unreviewed tables: "
                + ", ".join(unexpected_tables),
            )
        )
    if missing_reviewed_tables:
        issues.append(
            _finding(
                "unexpected_additive_schema",
                "Candidate migration omitted reviewed tables: "
                + ", ".join(missing_reviewed_tables),
            )
        )

    added_columns = []
    shared_tables = []
    for table_name in sorted(set(before_tables) & set(after_tables)):
        before_table = before_tables[table_name]
        after_table = after_tables[table_name]
        before_columns = {
            column["name"]: column for column in before_table["columns"]
        }
        after_columns = {
            column["name"]: column for column in after_table["columns"]
        }
        removed = sorted(set(before_columns) - set(after_columns))
        added = sorted(set(after_columns) - set(before_columns))
        if removed:
            issues.append(
                _finding(
                    "source_column_removed",
                    f"Candidate migration removed {table_name} columns: "
                    + ", ".join(removed),
                )
            )
        if added:
            added_columns.append({"table": table_name, "columns": added})

        expected_added = allowed.get(table_name, set())
        unreviewed_added = sorted(set(added) - expected_added)
        missing_additions = sorted(expected_added - set(added))
        if unreviewed_added or missing_additions:
            detail = []
            if unreviewed_added:
                detail.append("unreviewed " + ", ".join(unreviewed_added))
            if missing_additions:
                detail.append("missing " + ", ".join(missing_additions))
            issues.append(
                _finding(
                    "unexpected_additive_schema",
                    f"Candidate migration additions for {table_name} are invalid: "
                    + "; ".join(detail),
                )
            )

        shared_names = [
            column["name"] for column in before_table["columns"]
            if column["name"] in after_columns
        ]
        for column_name in shared_names:
            if before_columns[column_name] != after_columns[column_name]:
                issues.append(
                    _finding(
                        "source_column_contract_changed",
                        f"Candidate migration changed {table_name}.{column_name}.",
                    )
                )

        after_shared_rows = _projected_rows(after_table, shared_names)
        before_shared_rows = _projected_rows(before_table, shared_names)
        if before_shared_rows != after_shared_rows:
            issues.append(
                _finding(
                    "source_row_data_changed",
                    f"Candidate migration changed legacy data in {table_name}.",
                )
            )
        shared_tables.append(
            {
                "name": table_name,
                "columns": [
                    before_columns[column_name] for column_name in shared_names
                ],
                "foreign_keys": before_table["foreign_keys"],
                "indexes": before_table["indexes"],
                "rows": after_shared_rows,
                "row_count": len(after_shared_rows),
            }
        )

        for column_name in added:
            column = after_columns[column_name]
            if column["not_null"]:
                issues.append(
                    _finding(
                        "additive_column_not_nullable",
                        f"Candidate column {table_name}.{column_name} is not nullable.",
                    )
                )
            column_index = [
                item["name"] for item in after_table["columns"]
            ].index(column_name)
            if any(
                row[column_index] != {"type": "null"}
                for row in after_table["rows"]
            ):
                issues.append(
                    _finding(
                        "legacy_additive_value_not_null",
                        f"Legacy rows contain values in {table_name}.{column_name}.",
                    )
                )

    for table_name, expected_columns in sorted(allowed.items()):
        if table_name not in before_tables:
            issues.append(
                _finding(
                    "expected_source_table_missing",
                    f"Expected source table is missing: {table_name}.",
                )
            )
        elif table_name not in after_tables:
            continue
        elif not expected_columns:
            continue

    shared_payload = {
        "tables": shared_tables,
        "schema_objects": before["schema_objects"],
    }
    shared_digest = hashlib.sha256(
        _canonical_json_bytes(shared_payload)
    ).hexdigest()
    if shared_digest != before["digest"] and not any(
        issue["error_code"] in {
            "source_table_removed",
            "source_column_removed",
            "source_column_contract_changed",
            "source_row_data_changed",
        }
        for issue in issues
    ):
        issues.append(
            _finding(
                "source_projection_changed",
                "Candidate migration changed the legacy database projection.",
            )
        )
    if (
        expected_projection is not None
        and after["schema_digest"] != expected_projection["schema_digest"]
    ):
        issues.append(
            _finding(
                "candidate_schema_contract_changed",
                "Candidate schema differs from the reviewed additive migration.",
            )
        )

    return {
        "status": "passed" if not issues else "failed",
        "added_columns": added_columns,
        "before_digest": before["digest"],
        "shared_digest": shared_digest,
        "table_counts": before["table_counts"],
        "issues": issues,
    }


def rehearse_candidate_migration(
    snapshot_database: Path,
    source_version: str,
) -> dict:
    if source_version not in SUPPORTED_SOURCE_VERSIONS:
        raise ValueError(f"Unsupported source version: {source_version}")
    snapshot_database = Path(snapshot_database).resolve()
    before = database_projection(snapshot_database)

    definitions = ALLOWED_ADDITIVE_DEFINITIONS[source_version]
    with tempfile.TemporaryDirectory(
        prefix=".visual-qc-expected-schema-",
        dir=snapshot_database.parent,
    ) as expected_directory:
        expected_database = Path(expected_directory) / "expected.sqlite3"
        create_read_only_snapshot(snapshot_database, expected_database)
        with closing(sqlite3.connect(expected_database)) as connection:
            for table_name, columns in sorted(definitions.items()):
                for column_name, declaration in sorted(columns.items()):
                    if not table_name.isidentifier() or not column_name.isidentifier():
                        raise ValueError("Reviewed schema identifiers are invalid.")
                    connection.execute(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column_name} {declaration}"
                    )
            connection.executescript(ALLOWED_ADDITIVE_SCHEMA_SQL[source_version])
            connection.commit()
        expected_projection = database_projection(expected_database)

    VisualQcStore(snapshot_database, recover_interrupted_jobs=False)

    with closing(_read_only_connection(snapshot_database)) as connection:
        integrity = _integrity_result(connection)
    after = database_projection(snapshot_database)
    comparison = compare_database_projections(
        before,
        after,
        source_version=source_version,
        expected_projection=expected_projection,
    )
    issues = list(comparison["issues"])
    if integrity != "ok":
        issues.append(
            _finding(
                "candidate_database_integrity_failed",
                "Candidate database integrity check failed.",
            )
        )
    return {
        **comparison,
        "status": "passed" if not issues else "failed",
        "integrity": integrity,
        "issues": issues,
    }


def _same_lexical_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(_absolute_lexical_path(left))) == os.path.normcase(
        str(_absolute_lexical_path(right))
    )


def _contains_reparse_path(root: Path, target: Path) -> bool:
    current = Path(os.path.abspath(root))
    target = Path(os.path.abspath(target))
    try:
        relative = target.relative_to(current)
    except ValueError:
        return True
    if _is_reparse_or_symlink(current):
        return True
    for part in relative.parts:
        current = current / part
        if _is_reparse_or_symlink(current):
            return True
    return False


def _object_issue(
    object_kind: str,
    object_id: str,
    error_code: str,
    message: str,
) -> dict:
    return {
        "object_kind": object_kind,
        "object_id": object_id,
        "error_code": error_code,
        "message": message,
    }


@contextmanager
def _storage_reference_lock(data_root: Path):
    data_root = _absolute_lexical_path(data_root)
    lock_path = data_root / ".storage-reference.lock"
    if not lock_path.is_file() or _is_reparse_or_symlink(lock_path):
        raise ValueError(
            "Existing regular storage reference lock is required."
        )
    with lock_path.open("r+b", buffering=0) as handle:
        if os.fstat(handle.fileno()).st_size < 1:
            raise ValueError("Existing storage reference lock is invalid.")
        handle.seek(0)
        LocalObjectStorage._lock_reference_file(handle)
        try:
            yield
        finally:
            handle.seek(0)
            LocalObjectStorage._unlock_reference_file(handle)


def _hash_regular_file(path: Path) -> dict:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Managed path is not a regular file.")
        digest = hashlib.sha256()
        byte_size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            byte_size += len(chunk)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            getattr(before, "st_mtime_ns", None),
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            getattr(after, "st_mtime_ns", None),
        )
        if identity_before != identity_after or byte_size != after.st_size:
            raise ValueError("Managed file changed while it was being hashed.")
        return {
            "byte_size": byte_size,
            "sha256": digest.hexdigest(),
        }
    finally:
        os.close(descriptor)


def _validate_managed_objects_locked(database: Path, data_root: Path) -> dict:
    data_root = _absolute_lexical_path(data_root)
    issues = []
    records = []
    with closing(_read_only_connection(database)) as connection:
        for row in connection.execute(
            """
            SELECT image_id AS object_id, 'original' AS object_kind,
                   mime_type, sha256, byte_size, storage_path
            FROM images
            ORDER BY image_id
            """
        ).fetchall():
            records.append(dict(row))
        for row in connection.execute(
            """
            SELECT artifact_id AS object_id, 'artifact' AS object_kind,
                   mime_type, sha256, byte_size, storage_path
            FROM artifacts
            ORDER BY artifact_id
            """
        ).fetchall():
            records.append(dict(row))

    for record in records:
        object_kind = record["object_kind"]
        object_id = record["object_id"]
        sha256 = record["sha256"]
        extension = MANAGED_MIME_EXTENSIONS.get(record["mime_type"])
        if not isinstance(sha256, str) or SHA256_PATTERN.fullmatch(sha256) is None:
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_invalid_sha256",
                    "Managed object has an invalid SHA-256.",
                )
            )
            continue
        if extension is None:
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_invalid_mime_type",
                    "Managed object has an unsupported MIME type.",
                )
            )
            continue
        category = "originals" if object_kind == "original" else "artifacts"
        expected = (
            data_root
            / "objects"
            / category
            / sha256[:2]
            / f"{sha256}{extension}"
        )
        stored = Path(record["storage_path"])
        if not _same_lexical_path(stored, expected):
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_path_mismatch",
                    "Stored path does not match the canonical content-addressed path.",
                )
            )
        if _contains_reparse_path(data_root, expected):
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_unsafe_path",
                    "Managed object path contains a symlink or reparse point.",
                )
            )
            continue
        try:
            evidence = _hash_regular_file(expected)
        except FileNotFoundError:
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_missing",
                    "Managed object file is missing.",
                )
            )
            continue
        except (OSError, ValueError):
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_unstable",
                    "Managed object could not be read as one stable regular file.",
                )
            )
            continue
        if evidence["byte_size"] != record["byte_size"]:
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_size_mismatch",
                    "Managed object byte size does not match the database.",
                )
            )
        if evidence["sha256"] != sha256:
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_hash_mismatch",
                    "Managed object SHA-256 does not match the database.",
                )
            )

    issues.sort(
        key=lambda issue: (
            issue["error_code"],
            issue["object_kind"],
            issue["object_id"],
        )
    )
    originals = sum(record["object_kind"] == "original" for record in records)
    artifacts = sum(record["object_kind"] == "artifact" for record in records)
    return {
        "status": "passed" if not issues else "failed",
        "counts": {
            "originals": originals,
            "artifacts": artifacts,
            "total": len(records),
        },
        "issues": issues,
    }


def validate_managed_objects(database: Path, data_root: Path) -> dict:
    with _storage_reference_lock(data_root):
        return _validate_managed_objects_locked(database, data_root)


def smoke_candidate_runtime(project_root: Path, candidate_data_root: Path) -> dict:
    project_root = Path(project_root).resolve()
    candidate_data_root = Path(candidate_data_root).resolve()
    database = candidate_data_root / "visual-qc.sqlite3"
    issues = []
    api_schemas = {
        "health": None,
        "admin_list": None,
        "admin_detail": None,
        "dataset_audit": None,
    }
    counts = {
        "database_cases": 0,
        "listed_cases": 0,
        "detailed_cases": 0,
    }
    dataset = {
        "eligible_case_count": 0,
        "excluded_case_count": 0,
        "reason_counts": {},
    }
    try:
        with closing(_read_only_connection(database)) as connection:
            case_rows = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT case_id, actor_id, evidence_role,
                           qualified_handoff_json
                    FROM cases
                    ORDER BY actor_id, case_id
                    """
                ).fetchall()
            ]
        counts["database_cases"] = len(case_rows)
        settings = VisualQcServerSettings.from_environment()
        settings = replace(
            settings,
            project_root=project_root,
            data_root=candidate_data_root,
            minimum_free_bytes=0,
            warning_free_bytes=0,
            worker_count=0,
        )
        service = VisualQcService(settings, recover_interrupted_jobs=False)

        health = service.health()
        api_schemas["health"] = health.get("schema_version")
        if api_schemas["health"] != "VISUAL-QC-SERVER-HEALTH-V2":
            issues.append(
                _finding(
                    "candidate_health_schema_mismatch",
                    "Candidate health schema is incompatible.",
                )
            )
        if health.get("cases", {}).get("total") != len(case_rows):
            issues.append(
                _finding(
                    "candidate_health_count_mismatch",
                    "Candidate health case count does not match the database.",
                )
            )

        case_by_actor: dict[str, list[str]] = {}
        for row in case_rows:
            case_by_actor.setdefault(row["actor_id"], []).append(row["case_id"])
        for actor_id, expected_case_ids in sorted(case_by_actor.items()):
            page = service.list_admin_cases(
                actor_id,
                board_key=None,
                side_id=None,
                capture_stage=None,
                state=None,
                page=1,
                page_size=max(1, len(expected_case_ids)),
            )
            api_schemas["admin_list"] = page.get("schema_version")
            if api_schemas["admin_list"] != "VISUAL-QC-ADMIN-CASE-LIST-V2":
                issues.append(
                    _finding(
                        "candidate_admin_list_schema_mismatch",
                        "Candidate admin list schema is incompatible.",
                    )
                )
            listed_ids = [item["case_id"] for item in page.get("cases", [])]
            counts["listed_cases"] += len(listed_ids)
            if sorted(listed_ids) != sorted(expected_case_ids):
                issues.append(
                    _finding(
                        "candidate_admin_list_count_mismatch",
                        f"Candidate admin list is incomplete for actor {actor_id}.",
                    )
                )
            for case_id in expected_case_ids:
                detail = service.get_admin_case(case_id, actor_id)
                api_schemas["admin_detail"] = detail.get("schema_version")
                if api_schemas["admin_detail"] != "VISUAL-QC-SERVER-CASE-V3":
                    issues.append(
                        _finding(
                            "candidate_admin_detail_schema_mismatch",
                            "Candidate admin detail schema is incompatible.",
                        )
                    )
                counts["detailed_cases"] += 1

        audit = service.training_audit()
        api_schemas["dataset_audit"] = audit.get("schema_version")
        if api_schemas["dataset_audit"] != "VISUAL-QC-DATASET-AUDIT-V1":
            issues.append(
                _finding(
                    "candidate_dataset_audit_schema_mismatch",
                    "Candidate dataset audit schema is incompatible.",
                )
            )
        if audit.get("total_case_count") != len(case_rows):
            issues.append(
                _finding(
                    "candidate_dataset_count_mismatch",
                    "Candidate dataset audit case count does not match the database.",
                )
            )
        dataset = {
            "eligible_case_count": audit.get("eligible_case_count", 0),
            "excluded_case_count": audit.get("excluded_case_count", 0),
            "reason_counts": audit.get("reason_counts", {}),
        }
        audit_cases = {
            item["case_id"]: item for item in audit.get("cases", [])
        }
        for row in case_rows:
            item = audit_cases.get(row["case_id"])
            if item is None:
                issues.append(
                    _finding(
                        "candidate_dataset_case_missing",
                        f"Candidate dataset audit omitted case {row['case_id']}.",
                    )
                )
                continue
            if row["evidence_role"] != "physical_capture":
                expected_reason = "non_physical_evidence"
            elif row["qualified_handoff_json"] is None:
                expected_reason = "qualified_handoff_provenance_required"
            else:
                expected_reason = None
            if expected_reason and item.get("blocking_reason") != expected_reason:
                issues.append(
                    _finding(
                        "candidate_dataset_gate_mismatch",
                        f"Candidate dataset gate changed for case {row['case_id']}.",
                    )
                )
    except Exception:
        issues.append(
            _finding(
                "candidate_runtime_incompatible",
                "Candidate runtime could not read the migrated database.",
            )
        )

    return {
        "status": "passed" if not issues else "failed",
        "api_schemas": api_schemas,
        "counts": counts,
        "dataset": dataset,
        "issues": issues,
    }


def smoke_rollback_runtime(
    source_app_root: Path,
    migrated_database: Path,
) -> dict:
    source_app_root = Path(source_app_root).resolve()
    migrated_database = Path(migrated_database).resolve()
    version_path = source_app_root / "VERSION"
    store_path = (
        source_app_root / "scripts" / "visual_qc" / "server" / "store.py"
    )
    source_version = (
        version_path.read_text(encoding="ascii").strip()
        if version_path.is_file()
        else ""
    )
    issues = []
    case_count = 0
    cases_read = 0
    try:
        if source_version not in SUPPORTED_SOURCE_VERSIONS:
            raise ValueError("Rollback source version is unsupported.")
        if not store_path.is_file():
            raise ValueError("Rollback store module is missing.")
        with closing(_read_only_connection(migrated_database)) as connection:
            case_ids = [
                row["case_id"]
                for row in connection.execute(
                    "SELECT case_id FROM cases ORDER BY case_id"
                ).fetchall()
            ]
        case_count = len(case_ids)
        module_name = (
            "_visual_qc_rollback_store_"
            + hashlib.sha256(str(store_path).encode("utf-8")).hexdigest()[:16]
        )
        specification = importlib.util.spec_from_file_location(
            module_name,
            store_path,
        )
        if specification is None or specification.loader is None:
            raise RuntimeError("Rollback store module cannot be loaded.")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        rollback_store = module.VisualQcStore(
            migrated_database,
            recover_interrupted_jobs=False,
        )
        operational = rollback_store.operational_counts()
        if operational.get("cases", {}).get("total") != case_count:
            raise RuntimeError("Rollback store case count changed.")
        for case_id in case_ids:
            if rollback_store.get_case(case_id) is None:
                raise RuntimeError("Rollback store omitted a case.")
            cases_read += 1
        connection = getattr(rollback_store, "connection", None)
        if connection is not None:
            connection.close()
    except Exception:
        issues.append(
            _finding(
                "rollback_runtime_incompatible",
                "Rollback runtime could not read the candidate-migrated database.",
            )
        )

    return {
        "status": "passed" if not issues else "failed",
        "source_version": source_version,
        "case_count": case_count,
        "cases_read": cases_read,
        "issues": issues,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00",
        "Z",
    )


def _source_fingerprint(database: Path, data_root: Path) -> dict:
    database = Path(database).resolve()
    data_root = _absolute_lexical_path(data_root)
    paths = []
    for label, path in (
        ("database", database),
        ("database-wal", Path(f"{database}-wal")),
        ("database-shm", Path(f"{database}-shm")),
    ):
        if path.is_file():
            paths.append((label, path))
    objects_root = data_root / "objects"
    if objects_root.exists():
        if _is_reparse_or_symlink(objects_root):
            raise ValueError("Managed objects root contains a reparse point.")
        for path in sorted(objects_root.rglob("*")):
            if _is_reparse_or_symlink(path):
                raise ValueError("Managed objects contain a reparse point.")
            if path.is_file():
                paths.append(
                    (
                        "objects/" + path.relative_to(objects_root).as_posix(),
                        path,
                    )
                )
    records = []
    for label, path in paths:
        evidence = _hash_regular_file(path)
        records.append({"label": label, **evidence})
    return {
        "digest": hashlib.sha256(_canonical_json_bytes(records)).hexdigest(),
        "file_count": len(records),
        "records": records,
    }


def _check(
    check_id: str,
    passed: bool,
    error_code: str,
    passed_message: str,
    failed_message: str,
) -> dict:
    return {
        "check_id": check_id,
        "status": "passed" if passed else "failed",
        "error_code": None if passed else error_code,
        "message": passed_message if passed else failed_message,
    }


def audit_visual_qc_upgrade(
    *,
    project_root: Path,
    source_database: Path,
    source_data_root: Path,
    source_app_root: Path,
    target_version: str,
    target_archive_sha256: str,
    target_archive_bytes: int,
    target_runtime_manifest_sha256: str,
    clock=utc_now,
) -> dict:
    project_root = Path(project_root).resolve()
    source_database = Path(source_database).resolve()
    source_data_root = _absolute_lexical_path(source_data_root)
    source_app_root = Path(source_app_root).resolve()
    if not source_database.is_file():
        raise ValueError("Source database does not exist.")
    if not source_data_root.is_dir():
        raise ValueError("Source data root does not exist.")
    version_path = source_app_root / "VERSION"
    if not version_path.is_file():
        raise ValueError("Source application VERSION is missing.")
    source_version = version_path.read_text(encoding="ascii").strip()
    if (
        not isinstance(target_version, str)
        or FULL_COMMIT_PATTERN.fullmatch(target_version) is None
    ):
        raise ValueError(
            "Target version must be a full 40-character lowercase Git commit."
        )
    for field_name, value in (
        ("target archive SHA-256", target_archive_sha256),
        ("target runtime manifest SHA-256", target_runtime_manifest_sha256),
    ):
        if (
            not isinstance(value, str)
            or DEPLOYMENT_SHA256_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(f"{field_name} must be lowercase SHA-256.")
    if (
        isinstance(target_archive_bytes, bool)
        or not isinstance(target_archive_bytes, int)
        or target_archive_bytes < 1
    ):
        raise ValueError("Target archive byte size must be a positive integer.")

    with _storage_reference_lock(source_data_root):
        before_fingerprint = _source_fingerprint(
            source_database,
            source_data_root,
        )
        with tempfile.TemporaryDirectory(
            prefix="visual-qc-upgrade-preflight-"
        ) as temporary:
            temporary_root = Path(temporary)
            candidate_root = temporary_root / "candidate-data"
            candidate_database = candidate_root / "visual-qc.sqlite3"
            snapshot = create_read_only_snapshot(
                source_database,
                candidate_database,
            )
            managed_objects = _validate_managed_objects_locked(
                source_database,
                source_data_root,
            )
            migration = rehearse_candidate_migration(
                candidate_database,
                source_version,
            )
            candidate_runtime = smoke_candidate_runtime(
                project_root,
                candidate_root,
            )
            rollback_database = temporary_root / "rollback.sqlite3"
            create_read_only_snapshot(candidate_database, rollback_database)
            rollback_runtime = smoke_rollback_runtime(
                source_app_root,
                rollback_database,
            )

        after_fingerprint = _source_fingerprint(
            source_database,
            source_data_root,
        )
        source_snapshot_sha256 = _hash_regular_file(
            source_database
        )["sha256"]
    source_immutable = before_fingerprint == after_fingerprint
    source_supported = source_version in SUPPORTED_SOURCE_VERSIONS
    migration_schema_passed = (
        migration["status"] == "passed"
        and migration["added_columns"]
        == EXPECTED_ADDED_COLUMNS[source_version]
    )
    migration_rows_passed = (
        migration["before_digest"] == migration["shared_digest"]
    )
    expected_schemas = {
        "health": "VISUAL-QC-SERVER-HEALTH-V2",
        "admin_list": "VISUAL-QC-ADMIN-CASE-LIST-V2",
        "admin_detail": "VISUAL-QC-SERVER-CASE-V3",
        "dataset_audit": "VISUAL-QC-DATASET-AUDIT-V1",
    }
    candidate_contract_passed = (
        candidate_runtime["status"] == "passed"
        and not candidate_runtime["issues"]
        and candidate_runtime["api_schemas"] == expected_schemas
        and candidate_runtime["counts"]["database_cases"]
        == candidate_runtime["counts"]["listed_cases"]
        == candidate_runtime["counts"]["detailed_cases"]
    )
    candidate_dataset_passed = not any(
        issue["error_code"].startswith("candidate_dataset_")
        for issue in candidate_runtime["issues"]
    )
    checks = [
        _check(
            "source_version_supported",
            source_supported,
            "unsupported_source_version",
            "Source application version is supported.",
            "Source application version is not supported.",
        ),
        _check(
            "source_database_integrity",
            snapshot["integrity"] == "ok",
            "source_database_integrity_failed",
            "Source database integrity check passed.",
            "Source database integrity check failed.",
        ),
        _check(
            "managed_objects_integrity",
            managed_objects["status"] == "passed",
            "managed_objects_integrity_failed",
            "Managed object integrity checks passed.",
            "Managed object integrity checks failed.",
        ),
        _check(
            "candidate_migration_integrity",
            migration["integrity"] == "ok",
            "candidate_database_integrity_failed",
            "Candidate-migrated database integrity check passed.",
            "Candidate-migrated database integrity check failed.",
        ),
        _check(
            "candidate_schema_additive",
            migration_schema_passed,
            "candidate_schema_incompatible",
            "Candidate migration is limited to reviewed additive schema.",
            "Candidate migration changed unreviewed schema.",
        ),
        _check(
            "candidate_rows_preserved",
            migration_rows_passed,
            "candidate_rows_changed",
            "Candidate migration preserved every legacy row value.",
            "Candidate migration changed legacy row values.",
        ),
        _check(
            "candidate_runtime_contract",
            candidate_contract_passed,
            "candidate_runtime_incompatible",
            "Candidate runtime schemas and case counts are compatible.",
            "Candidate runtime schemas or case counts are incompatible.",
        ),
        _check(
            "candidate_dataset_gates",
            candidate_dataset_passed,
            "candidate_dataset_gate_incompatible",
            "Candidate runtime preserved legacy dataset exclusions.",
            "Candidate runtime changed legacy dataset exclusions.",
        ),
        _check(
            "rollback_runtime_compatible",
            rollback_runtime["status"] == "passed",
            "rollback_runtime_incompatible",
            "Rollback runtime can read the candidate-migrated database.",
            "Rollback runtime cannot read the candidate-migrated database.",
        ),
        _check(
            "source_immutable",
            source_immutable,
            "source_mutated",
            "Source database and managed objects remained byte-identical.",
            "Source database or managed objects changed during preflight.",
        ),
    ]
    status = (
        "passed"
        if all(check["status"] == "passed" for check in checks)
        else "failed"
    )
    return {
        "schema_version": UPGRADE_PREFLIGHT_SCHEMA_VERSION,
        "status": status,
        "generated_at": clock(),
        "source": {
            "version": source_version,
            "snapshot_sha256": source_snapshot_sha256,
            "logical_digest": snapshot["logical_digest"],
            "table_counts": snapshot["table_counts"],
            "managed_object_counts": managed_objects["counts"],
            "fingerprint_digest": before_fingerprint["digest"],
            "fingerprint_file_count": before_fingerprint["file_count"],
        },
        "target": {
            "version": target_version,
            "archive_sha256": target_archive_sha256,
            "archive_bytes": target_archive_bytes,
            "runtime_manifest_sha256": target_runtime_manifest_sha256,
        },
        "checks": checks,
        "managed_objects": managed_objects,
        "migration": migration,
        "candidate_runtime": candidate_runtime,
        "rollback_runtime": rollback_runtime,
    }
