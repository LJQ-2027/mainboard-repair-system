from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from scripts.visual_qc.deployment_verifier import (
    verify_extracted_runtime,
    verify_input_bundle,
    verify_upgrade_report,
)


ROOT = Path(__file__).resolve().parents[1]


class VisualQcDeploymentVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="visual-qc-deployment-verifier-"
        )
        self.root = Path(self.temporary.name)
        self.runtime_content = (
            b"deploy/visual-qc-runtime-files.txt\nscripts/a.py\n"
        )
        self.archive = self.root / "app.tar.gz"
        self.write_archive()
        self.manifest = {
            "schema_version": "VISUAL-QC-DEPLOYMENT-MANIFEST-V1",
            "commit_sha": "a" * 40,
            "archive_sha256": self.sha256(self.archive),
            "archive_bytes": self.archive.stat().st_size,
            "runtime_manifest_sha256": hashlib.sha256(
                self.runtime_content
            ).hexdigest(),
            "runtime_path_count": 2,
        }
        self.manifest_path = self.root / "deployment-manifest.json"
        self.write_manifest(self.manifest)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def add_bytes(self, archive, name: str, content: bytes):
        member = tarfile.TarInfo(name)
        member.size = len(content)
        member.mode = 0o644
        archive.addfile(member, io.BytesIO(content))

    def write_archive(self, extra_member=None):
        with tarfile.open(self.archive, "w:gz") as archive:
            self.add_bytes(
                archive,
                "deploy/visual-qc-runtime-files.txt",
                self.runtime_content,
            )
            self.add_bytes(archive, "scripts/a.py", b"print('ok')\n")
            if extra_member is not None:
                archive.addfile(extra_member)

    def write_manifest(self, manifest):
        self.manifest_path.write_text(
            json.dumps(manifest, sort_keys=True),
            encoding="utf-8",
        )

    def refresh_archive_evidence(self):
        self.manifest["archive_sha256"] = self.sha256(self.archive)
        self.manifest["archive_bytes"] = self.archive.stat().st_size
        self.write_manifest(self.manifest)

    def test_input_bundle_accepts_exact_manifest_and_safe_tar(self):
        result = verify_input_bundle(
            manifest_path=self.manifest_path,
            archive_path=self.archive,
            expected_manifest=self.manifest,
        )

        self.assertEqual(result, self.manifest)

    def test_input_bundle_rejects_duplicate_json_fields(self):
        self.manifest_path.write_text(
            (
                '{"schema_version":"VISUAL-QC-DEPLOYMENT-MANIFEST-V1",'
                f'"commit_sha":"{"a" * 40}",'
                f'"commit_sha":"{"a" * 40}",'
                f'"archive_sha256":"{self.manifest["archive_sha256"]}",'
                f'"archive_bytes":{self.manifest["archive_bytes"]},'
                f'"runtime_manifest_sha256":'
                f'"{self.manifest["runtime_manifest_sha256"]}",'
                '"runtime_path_count":2}'
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "duplicate field"):
            verify_input_bundle(
                manifest_path=self.manifest_path,
                archive_path=self.archive,
                expected_manifest=self.manifest,
            )

    def test_input_bundle_rejects_unsafe_tar_members(self):
        unsafe_members = []
        traversal = tarfile.TarInfo("../escape.py")
        traversal.size = 0
        unsafe_members.append(traversal)
        symbolic = tarfile.TarInfo("scripts/link.py")
        symbolic.type = tarfile.SYMTYPE
        symbolic.linkname = "../../outside.py"
        unsafe_members.append(symbolic)
        hardlink = tarfile.TarInfo("scripts/hard.py")
        hardlink.type = tarfile.LNKTYPE
        hardlink.linkname = "scripts/a.py"
        unsafe_members.append(hardlink)

        for member in unsafe_members:
            with self.subTest(name=member.name, type=member.type):
                self.write_archive(extra_member=member)
                self.refresh_archive_evidence()
                with self.assertRaisesRegex(ValueError, "unsafe tar member"):
                    verify_input_bundle(
                        manifest_path=self.manifest_path,
                        archive_path=self.archive,
                        expected_manifest=self.manifest,
                    )

    def create_extracted_runtime(self) -> Path:
        app_root = self.root / "app"
        runtime_path = app_root / "deploy" / "visual-qc-runtime-files.txt"
        runtime_path.parent.mkdir(parents=True)
        runtime_path.write_bytes(self.runtime_content)
        script = app_root / "scripts" / "a.py"
        script.parent.mkdir(parents=True)
        script.write_bytes(b"print('ok')\n")
        return app_root

    def test_extracted_runtime_rejects_nested_symlink(self):
        app_root = self.create_extracted_runtime()
        external = self.root / "external"
        external.mkdir()
        (external / "outside.txt").write_bytes(b"outside")
        nested = app_root / "scripts" / "nested-link"
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(nested), str(external)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if result.returncode != 0:
                self.fail(f"Unable to create test junction: {result.stderr}")
        else:
            nested.symlink_to(external, target_is_directory=True)
        try:
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                verify_extracted_runtime(
                    app_root=app_root,
                    expected_manifest=self.manifest,
                )
        finally:
            if os.name == "nt":
                os.rmdir(nested)
            else:
                nested.unlink()

    def test_upgrade_report_requires_complete_schema(self):
        report = self.root / "upgrade-preflight.json"
        report.write_text(
            json.dumps(
                {
                    "schema_version": "VISUAL-QC-UPGRADE-PREFLIGHT-V1",
                    "status": "passed",
                    "target": {
                        "version": self.manifest["commit_sha"],
                        "archive_sha256": self.manifest["archive_sha256"],
                        "archive_bytes": self.manifest["archive_bytes"],
                        "runtime_manifest_sha256": self.manifest[
                            "runtime_manifest_sha256"
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        snapshot = self.root / "snapshot.sqlite3"
        snapshot.write_bytes(b"snapshot")

        with self.assertRaisesRegex(ValueError, "Schema"):
            verify_upgrade_report(
                report_path=report,
                schema_path=(
                    ROOT
                    / "knowledge-base"
                    / "visual-qc-upgrade-preflight-v1-schema.json"
                ),
                snapshot_path=snapshot,
                expected_manifest=self.manifest,
            )


if __name__ == "__main__":
    unittest.main()
