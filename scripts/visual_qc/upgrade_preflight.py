from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

from scripts.visual_qc.source_library import (
    _absolute_lexical_path,
    _is_reparse_or_symlink,
)
from scripts.visual_qc.server.store import VisualQcStore


UPGRADE_PREFLIGHT_SCHEMA_VERSION = "VISUAL-QC-UPGRADE-PREFLIGHT-V1"
SUPPORTED_SOURCE_VERSIONS = frozenset({"f278061"})
ALLOWED_ADDITIVE_COLUMNS = {
    "f278061": {
        "cases": {"qualified_handoff_json"},
    }
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
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True, timeout=30)
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
                f"PRAGMA table_info({quoted_table})"
            ).fetchall()
            columns = [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key_position": row["pk"],
                }
                for row in column_rows
            ]
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
                    "rows": rows,
                    "row_count": len(rows),
                }
            )

    payload = {"tables": projected_tables}
    return {
        **payload,
        "table_counts": {
            table["name"]: table["row_count"] for table in projected_tables
        },
        "digest": hashlib.sha256(_canonical_json_bytes(payload)).hexdigest(),
    }


def create_read_only_snapshot(source_database: Path, destination: Path) -> dict:
    source_database = Path(source_database).resolve()
    destination = Path(destination).resolve()
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
) -> dict:
    allowed = ALLOWED_ADDITIVE_COLUMNS.get(source_version)
    if allowed is None:
        raise ValueError(f"Unsupported source version: {source_version}")

    before_tables = _table_map(before)
    after_tables = _table_map(after)
    issues = []

    missing_tables = sorted(set(before_tables) - set(after_tables))
    unexpected_tables = sorted(set(after_tables) - set(before_tables))
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

    shared_payload = {"tables": shared_tables}
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

    VisualQcStore(snapshot_database, recover_interrupted_jobs=False)

    with closing(_read_only_connection(snapshot_database)) as connection:
        integrity = _integrity_result(connection)
    after = database_projection(snapshot_database)
    comparison = compare_database_projections(
        before,
        after,
        source_version=source_version,
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


def validate_managed_objects(database: Path, data_root: Path) -> dict:
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
        if not expected.is_file():
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_missing",
                    "Managed object file is missing.",
                )
            )
            continue
        content = expected.read_bytes()
        if len(content) != record["byte_size"]:
            issues.append(
                _object_issue(
                    object_kind,
                    object_id,
                    "managed_object_size_mismatch",
                    "Managed object byte size does not match the database.",
                )
            )
        if hashlib.sha256(content).hexdigest() != sha256:
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
