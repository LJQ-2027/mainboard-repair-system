import hashlib
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import jsonschema
import numpy as np

from scripts.visual_qc.intake import IntakeValidationError
from scripts.visual_qc.source_audit import (
    SOURCE_AUDIT_SCHEMA_VERSION,
    audit_source_library,
)
from scripts.visual_qc.source_library import stage_source_package


ROOT = Path(__file__).resolve().parents[1]


def encode_image(extension, *, width=180, height=120, value=170):
    image = np.full((height, width, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(extension, image)
    if not ok:
        raise RuntimeError(f"Unable to encode test image: {extension}")
    return encoded.tobytes()


def snapshot_tree(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class VisualQcSourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.library = self.root / "controlled-library"
        self.front = self.root / "incoming-front.jpg"
        self.back = self.root / "incoming-back.png"
        self.front.write_bytes(encode_image(".jpg", value=180))
        self.back.write_bytes(encode_image(".png", value=110))

    def tearDown(self):
        for link in reversed(getattr(self, "directory_links", [])):
            if link.exists():
                os.rmdir(link)
        self.temp_dir.cleanup()

    def create_directory_link(self, link, target):
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
        self.directory_links = getattr(self, "directory_links", [])
        self.directory_links.append(link)

    def stage(self):
        return stage_source_package(
            project_root=ROOT,
            library_root=self.library,
            package_id="km4-audit-source",
            batch_id="km4-audit-batch",
            board_key="km4-f151",
            capture_session_id="km4-audit-unit",
            capture_stage="before_repair",
            capture_setup_id="standard-bench",
            image_assignments=[
                ("main_page_1", self.front),
                ("main_page_2", self.back),
            ],
            milo_physical_source_confirmed=True,
            capture_checklist_confirmed=True,
        )

    def run_cli(self, library_root=None):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_visual_qc_source_library.py"),
                "--library-root",
                str(library_root or self.library),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_complete_library_is_healthy_deterministic_and_read_only(self):
        self.stage()
        before = snapshot_tree(self.library)

        first = audit_source_library(ROOT, self.library)
        second = audit_source_library(ROOT, self.library)

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], SOURCE_AUDIT_SCHEMA_VERSION)
        self.assertEqual(first["status"], "healthy")
        self.assertEqual(
            first["counts"],
            {
                "package_total": 1,
                "valid_packages": 1,
                "invalid_packages": 0,
                "incomplete_packages": 0,
                "object_total": 2,
                "referenced_objects": 2,
                "invalid_objects": 0,
                "orphaned_objects": 0,
                "library_issues": 0,
            },
        )
        self.assertEqual(
            first["packages"],
            [
                {
                    "package_id": "km4-audit-source",
                    "status": "valid",
                    "entry_count": 2,
                }
            ],
        )
        self.assertEqual(first["invalid_objects"], [])
        self.assertEqual(first["orphaned_objects"], [])
        self.assertEqual(first["library_issues"], [])
        self.assertEqual(snapshot_tree(self.library), before)

    def test_runtime_reports_satisfy_the_json_schema(self):
        result = self.stage()
        schema = json.loads(
            (
                ROOT
                / "knowledge-base"
                / "visual-qc-source-audit-v1-schema.json"
            ).read_text(encoding="utf-8")
        )

        healthy = audit_source_library(ROOT, self.library)
        jsonschema.Draft202012Validator(schema).validate(healthy)

        (result["source_package_path"].parent / ".complete").unlink()
        issues = audit_source_library(ROOT, self.library)
        jsonschema.Draft202012Validator(schema).validate(issues)

    def test_valid_unreferenced_object_is_attention_only(self):
        self.stage()
        content = encode_image(".jpg", value=35)
        sha256 = hashlib.sha256(content).hexdigest()
        object_path = (
            self.library
            / "objects"
            / "originals"
            / sha256[:2]
            / f"{sha256}.jpg"
        )
        object_path.parent.mkdir(parents=True)
        object_path.write_bytes(content)
        before = snapshot_tree(self.library)

        report = audit_source_library(ROOT, self.library)

        self.assertEqual(report["status"], "attention")
        self.assertEqual(report["counts"]["orphaned_objects"], 1)
        self.assertEqual(report["counts"]["invalid_objects"], 0)
        self.assertEqual(
            report["orphaned_objects"],
            [
                {
                    "object_path": object_path.relative_to(self.library).as_posix(),
                    "status": "orphaned",
                }
            ],
        )
        self.assertEqual(snapshot_tree(self.library), before)

    def test_incomplete_and_revoked_packages_are_stable_issues(self):
        result = self.stage()
        package_dir = result["source_package_path"].parent
        (package_dir / ".complete").unlink()

        incomplete = audit_source_library(ROOT, self.library)

        self.assertEqual(incomplete["status"], "issues")
        self.assertEqual(incomplete["counts"]["incomplete_packages"], 1)
        self.assertEqual(
            incomplete["packages"][0]["error_code"], "incomplete_package"
        )
        self.assertNotIn(str(self.root), json.dumps(incomplete))

        (package_dir / ".complete").write_text("complete\n", encoding="ascii")
        payload = json.loads(result["source_package_path"].read_text(encoding="utf-8"))
        revoked_hash = payload["entries"][0]["sha256"]
        with patch(
            "scripts.visual_qc.source_library.known_proxy_hashes",
            return_value=frozenset({revoked_hash}),
        ):
            revoked = audit_source_library(ROOT, self.library)

        self.assertEqual(revoked["status"], "issues")
        self.assertEqual(revoked["packages"][0]["error_code"], "revoked_proxy")
        self.assertNotIn(str(self.root), json.dumps(revoked))

    def test_invalid_manifest_and_unexpected_package_entry_are_reported(self):
        result = self.stage()
        result["source_package_path"].write_text("{broken", encoding="utf-8")
        stray = self.library / "packages" / "unexpected.txt"
        stray.write_text("unexpected", encoding="ascii")

        report = audit_source_library(ROOT, self.library)

        self.assertEqual(report["status"], "issues")
        self.assertEqual(report["counts"]["package_total"], 2)
        self.assertEqual(
            [(row["package_id"], row["error_code"]) for row in report["packages"]],
            [
                ("km4-audit-source", "invalid_package"),
                ("unexpected.txt", "invalid_package_entry"),
            ],
        )

    def test_missing_corrupt_or_mismatched_intake_invalidates_package(self):
        result = self.stage()
        intake_path = result["intake_manifest_path"]
        original_intake = intake_path.read_text(encoding="utf-8")

        intake_path.write_text("{broken", encoding="utf-8")
        corrupt = audit_source_library(ROOT, self.library)
        self.assertEqual(corrupt["packages"][0]["error_code"], "invalid_package")

        intake_path.unlink()
        missing = audit_source_library(ROOT, self.library)
        self.assertEqual(missing["packages"][0]["error_code"], "invalid_package")

        intake_payload = json.loads(original_intake)
        intake_payload["entries"][0]["capture_stage"] = "after_repair"
        intake_path.write_text(json.dumps(intake_payload), encoding="utf-8")
        mismatch = audit_source_library(ROOT, self.library)
        self.assertEqual(mismatch["packages"][0]["error_code"], "invalid_package")

    def test_noncanonical_and_corrupt_objects_are_reported(self):
        result = self.stage()
        malformed = self.library / "objects" / "originals" / "zz" / "bad.jpg"
        malformed.parent.mkdir()
        malformed.write_bytes(encode_image(".jpg", value=45))
        payload = json.loads(result["source_package_path"].read_text(encoding="utf-8"))
        corrupt = self.library / payload["entries"][0]["object_path"]
        corrupt.write_bytes(b"corrupt")

        report = audit_source_library(ROOT, self.library)

        self.assertEqual(report["status"], "issues")
        self.assertEqual(report["counts"]["invalid_objects"], 2)
        self.assertEqual(
            [row["error_code"] for row in report["invalid_objects"]],
            ["corrupt_object", "noncanonical_path"],
        )
        self.assertEqual(
            [row["object_path"] for row in report["invalid_objects"]],
            sorted(row["object_path"] for row in report["invalid_objects"]),
        )

    def test_object_prefix_junction_is_reported_without_traversal(self):
        self.library.mkdir()
        outside = self.root / "outside-objects"
        self.create_directory_link(
            self.library / "objects" / "originals" / "aa", outside
        )
        (outside / "should-not-be-read.jpg").write_bytes(encode_image(".jpg"))

        report = audit_source_library(ROOT, self.library)

        self.assertEqual(report["status"], "issues")
        self.assertEqual(report["counts"]["object_total"], 1)
        self.assertEqual(
            report["invalid_objects"],
            [
                {
                    "object_path": "objects/originals/aa",
                    "error_code": "unsafe_path",
                    "message": "Object path contains a symlink or reparse point.",
                }
            ],
        )

    def test_supplied_library_root_junction_is_rejected(self):
        self.stage()
        link = self.root / "controlled-library-link"
        self.create_directory_link(link, self.library)

        with self.assertRaisesRegex(IntakeValidationError, "library root.*reparse|symlink"):
            audit_source_library(ROOT, link)

    def test_controlled_root_junctions_are_issues_without_traversal(self):
        packages_library = self.root / "packages-library"
        packages_library.mkdir()
        outside_packages = self.root / "outside-packages"
        self.create_directory_link(
            packages_library / "packages", outside_packages
        )
        (outside_packages / "hidden-package").mkdir()

        package_report = audit_source_library(ROOT, packages_library)

        self.assertEqual(package_report["status"], "issues")
        self.assertEqual(
            package_report["library_issues"],
            [
                {
                    "path": "packages",
                    "error_code": "unsafe_path",
                    "message": "Packages root contains a symlink or reparse point.",
                }
            ],
        )
        self.assertEqual(package_report["counts"]["package_total"], 0)

        objects_library = self.root / "objects-library"
        objects_library.mkdir()
        outside_objects = self.root / "outside-originals"
        self.create_directory_link(
            objects_library / "objects" / "originals", outside_objects
        )
        (outside_objects / "hidden.jpg").write_bytes(encode_image(".jpg"))

        object_report = audit_source_library(ROOT, objects_library)

        self.assertEqual(object_report["status"], "issues")
        self.assertEqual(
            object_report["library_issues"],
            [
                {
                    "path": "objects/originals",
                    "error_code": "unsafe_path",
                    "message": "Originals root contains a symlink or reparse point.",
                }
            ],
        )
        self.assertEqual(object_report["counts"]["object_total"], 0)

    def test_internal_lock_and_objects_parent_junctions_are_issues(self):
        locks_library = self.root / "locks-library"
        (locks_library / "packages").mkdir(parents=True)
        outside_locks = self.root / "outside-locks"
        self.create_directory_link(
            locks_library / "packages" / ".locks", outside_locks
        )

        locks_report = audit_source_library(ROOT, locks_library)

        self.assertEqual(locks_report["status"], "issues")
        self.assertEqual(locks_report["counts"]["package_total"], 0)
        self.assertEqual(locks_report["library_issues"][0]["path"], "packages/.locks")
        self.assertEqual(locks_report["library_issues"][0]["error_code"], "unsafe_path")

        objects_library = self.root / "objects-parent-library"
        objects_library.mkdir()
        outside_objects = self.root / "outside-objects-parent"
        self.create_directory_link(objects_library / "objects", outside_objects)
        (outside_objects / "originals").mkdir()
        (outside_objects / "originals" / "hidden.jpg").write_bytes(
            encode_image(".jpg")
        )

        objects_report = audit_source_library(ROOT, objects_library)

        self.assertEqual(objects_report["status"], "issues")
        self.assertEqual(
            objects_report["library_issues"],
            [
                {
                    "path": "objects",
                    "error_code": "unsafe_path",
                    "message": "Objects root contains a symlink or reparse point.",
                }
            ],
        )

    def test_regular_files_at_structural_roots_are_library_issues(self):
        for relative in ("packages", "objects", "objects/originals"):
            with self.subTest(relative=relative):
                library = self.root / f"file-root-{relative.replace('/', '-')}"
                target = library / relative
                target.parent.mkdir(parents=True)
                target.write_text("not-a-directory", encoding="ascii")

                report = audit_source_library(ROOT, library)

                self.assertEqual(report["status"], "issues")
                self.assertEqual(report["counts"]["library_issues"], 1)
                self.assertEqual(report["library_issues"][0]["path"], relative)

    def test_cli_exit_codes_are_machine_readable_and_read_only(self):
        result = self.stage()
        before = snapshot_tree(self.library)

        healthy = self.run_cli()

        self.assertEqual(healthy.returncode, 0)
        self.assertEqual(healthy.stderr, "")
        self.assertEqual(json.loads(healthy.stdout)["status"], "healthy")
        self.assertEqual(snapshot_tree(self.library), before)

        content = encode_image(".png", value=25)
        sha256 = hashlib.sha256(content).hexdigest()
        orphan = (
            self.library
            / "objects"
            / "originals"
            / sha256[:2]
            / f"{sha256}.png"
        )
        orphan.parent.mkdir(parents=True)
        orphan.write_bytes(content)
        attention = self.run_cli()
        self.assertEqual(attention.returncode, 0)
        self.assertEqual(json.loads(attention.stdout)["status"], "attention")

        (result["source_package_path"].parent / ".complete").unlink()
        issues = self.run_cli()
        self.assertEqual(issues.returncode, 1)
        self.assertEqual(issues.stderr, "")
        self.assertEqual(json.loads(issues.stdout)["status"], "issues")

        missing = self.run_cli(self.root / "missing-library")
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(missing.stderr, "")
        self.assertEqual(json.loads(missing.stdout)["status"], "validation_failed")

    def test_cli_unexpected_failure_is_one_json_object(self):
        script = ROOT / "scripts" / "audit_visual_qc_source_library.py"
        spec = importlib.util.spec_from_file_location("visual_source_audit_cli", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stdout = StringIO()
        stderr = StringIO()

        with patch.object(module, "audit_source_library", side_effect=RuntimeError("boom")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = module.main(
                    ["--library-root", str(self.library)]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "status": "failed",
                "message": "Unexpected source library audit failure.",
            },
        )


if __name__ == "__main__":
    unittest.main()
