import hashlib
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.visual_qc.upgrade_preflight import (
    create_read_only_snapshot,
    database_projection,
)


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


if __name__ == "__main__":
    unittest.main()
