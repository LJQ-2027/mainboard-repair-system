from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


UPGRADE_PREFLIGHT_SCHEMA_VERSION = "VISUAL-QC-UPGRADE-PREFLIGHT-V1"
SUPPORTED_SOURCE_VERSIONS = frozenset({"f278061"})


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
