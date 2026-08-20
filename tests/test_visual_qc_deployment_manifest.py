from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import jsonschema

from scripts.visual_qc.deployment_manifest import (
    build_deployment_manifest,
    validate_deployment_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "knowledge-base" / "visual-qc-deployment-manifest-v1-schema.json"
)


class VisualQcDeploymentManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="visual-qc-deployment-manifest-"
        )
        self.root = Path(self.temporary.name)
        self.archive = self.root / "app.tar.gz"
        self.runtime_manifest = self.root / "visual-qc-runtime-files.txt"
        self.local_runtime_content = (
            b"# bounded runtime\r\n"
            b"deploy/visual-qc-runtime-files.txt\r\n"
            b"scripts/a.py\r\n"
        )
        self.archived_runtime_content = self.local_runtime_content.replace(
            b"\r\n", b"\n"
        )
        self.runtime_manifest.write_bytes(self.local_runtime_content)
        self.write_archive()

    def tearDown(self):
        self.temporary.cleanup()

    def build(self, **overrides):
        arguments = {
            "archive": self.archive,
            "runtime_manifest": self.runtime_manifest,
            "commit_sha": "a" * 40,
        }
        arguments.update(overrides)
        return build_deployment_manifest(**arguments)

    def write_archive(self, runtime_content=None):
        content = runtime_content or self.archived_runtime_content
        with tarfile.open(self.archive, "w:gz") as archive:
            runtime = tarfile.TarInfo(
                "deploy/visual-qc-runtime-files.txt"
            )
            runtime.size = len(content)
            archive.addfile(runtime, io.BytesIO(content))
            script_content = b"print('ok')\n"
            script = tarfile.TarInfo("scripts/a.py")
            script.size = len(script_content)
            archive.addfile(script, io.BytesIO(script_content))

    def test_manifest_binds_archive_commit_and_runtime_boundary(self):
        manifest = self.build()

        self.assertEqual(
            manifest,
            {
                "schema_version": "VISUAL-QC-DEPLOYMENT-MANIFEST-V1",
                "commit_sha": "a" * 40,
                "archive_sha256": hashlib.sha256(
                    self.archive.read_bytes()
                ).hexdigest(),
                "archive_bytes": self.archive.stat().st_size,
                "runtime_manifest_sha256": hashlib.sha256(
                    self.archived_runtime_content
                ).hexdigest(),
                "runtime_path_count": 2,
            },
        )
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(manifest)
        self.assertEqual(validate_deployment_manifest(manifest), manifest)

    def test_manifest_rejects_short_or_uppercase_commit(self):
        for commit in ("abcdef1", "A" * 40):
            with self.subTest(commit=commit):
                with self.assertRaisesRegex(ValueError, "40-character"):
                    self.build(commit_sha=commit)

    def test_manifest_rejects_empty_archive(self):
        self.archive.write_bytes(b"")

        with self.assertRaisesRegex(ValueError, "must not be empty"):
            self.build()

    def test_runtime_manifest_is_parsed_from_the_hashed_file_handle(self):
        with patch.object(
            Path,
            "read_text",
            side_effect=AssertionError("runtime manifest was reopened"),
        ):
            manifest = self.build()

        self.assertEqual(manifest["runtime_path_count"], 2)

    def test_manifest_rejects_archive_runtime_path_drift(self):
        self.write_archive(
            b"# bounded runtime\n"
            b"deploy/visual-qc-runtime-files.txt\n"
            b"scripts/other.py\n"
        )

        with self.assertRaisesRegex(ValueError, "path list"):
            self.build()

    def test_manifest_rejects_duplicate_or_unsafe_runtime_paths(self):
        invalid_values = (
            "scripts/a.py\nscripts/a.py\n",
            "../secrets.txt\n",
            "/etc/passwd\n",
            "scripts\\a.py\n",
        )
        for value in invalid_values:
            with self.subTest(value=value):
                self.runtime_manifest.write_text(value, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.build()

    def test_validation_rejects_extra_properties_and_bad_scalars(self):
        manifest = self.build()
        invalid_manifests = [
            {**manifest, "unexpected": True},
            {**manifest, "archive_sha256": "A" * 64},
            {**manifest, "archive_bytes": 0},
            {**manifest, "runtime_path_count": 0},
        ]

        for invalid in invalid_manifests:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_deployment_manifest(invalid)

    def run_cli(self, output: Path):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_visual_qc_deployment_manifest.py"),
                "--archive",
                str(self.archive),
                "--runtime-manifest",
                str(self.runtime_manifest),
                "--commit-sha",
                "a" * 40,
                "--output",
                str(output),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_cli_publishes_utf8_manifest_without_overwrite(self):
        output = self.root / "deployment-manifest.json"

        completed = self.run_cli(output)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        published = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(published, self.build())
        self.assertEqual(json.loads(completed.stdout), published)

        repeated = self.run_cli(output)
        self.assertEqual(repeated.returncode, 2)
        self.assertEqual(
            json.loads(repeated.stdout)["status"],
            "validation_failed",
        )
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), published)


if __name__ == "__main__":
    unittest.main()
