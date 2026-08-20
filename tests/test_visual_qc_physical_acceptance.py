import hashlib
import io
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import cv2
import jsonschema
import numpy as np

import scripts.visual_qc.physical_acceptance as physical_acceptance_module
from scripts.run_visual_qc_physical_acceptance import main as acceptance_cli_main

from scripts.visual_qc.physical_acceptance import (
    _output_lock,
    build_physical_registration_run,
    derive_next_action,
    publish_physical_registration_run,
    validate_physical_registration_report,
)
from scripts.visual_qc.source_library import (
    stage_source_package,
    validate_source_package,
)
from scripts.visual_qc.intake import IntakeValidationError
from scripts.visual_qc.synthetic import (
    SyntheticTransformConfig,
    generate_synthetic_capture,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "knowledge-base" / "visual-qc-physical-registration-run-v1-schema.json"
)


def minimal_report():
    return {
        "schema_version": "VISUAL-QC-PHYSICAL-REGISTRATION-RUN-V1",
        "status": "review_required",
        "evidence_role": "physical_capture",
        "physical_source_confirmed": True,
        "field_accuracy_claim_allowed": False,
        "source_package": {
            "package_id": "km4-physical-001",
            "batch_id": "km4-batch-001",
            "manifest_sha256": "d" * 64,
            "proxy_inventory_sha256": "a" * 64,
        },
        "board": {
            "board_key": "km4-f151",
            "board_id": "BOARD-KM4-F151-MAIN-V1.2",
        },
        "capture": {
            "stage": "before_repair",
            "session_id": "km4-session-001",
            "setup_id": "bench-a",
        },
        "summary": {
            "entry_count": 1,
            "automatic_candidate_count": 1,
            "manual_registration_count": 0,
            "image_retake_count": 0,
            "processing_issue_count": 0,
            "action_counts": {"automatic_candidate_review_required": 1},
        },
        "entries": [
            {
                "entry_id": "km4-session-001-main_page_2",
                "side_id": "main_page_2",
                "image": {
                    "original_filename": "board-back.jpg",
                    "mime_type": "image/jpeg",
                    "width": 1200,
                    "height": 900,
                    "byte_size": 12345,
                    "sha256": "b" * 64,
                },
                "quality": {
                    "schema_version": "VISUAL-QC-IMAGE-QUALITY-V1",
                    "score": 88,
                    "status": "good",
                    "metrics": {},
                    "guidance": [],
                },
                "registration": {
                    "schema_version": "VISUAL-QC-REGISTRATION-CANDIDATE-V1",
                    "status": "candidate",
                    "method": "automatic_feature_homography",
                    "review_status": "draft",
                    "requires_human_review": True,
                    "requires_manual_registration": False,
                    "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                    "evidence": {},
                    "failure": None,
                    "fallback": {
                        "method": "reviewed_manual_four_point",
                        "reason_code": None,
                    },
                },
                "registration_review_status": "pending",
                "next_action": "automatic_candidate_review_required",
                "overlay": {
                    "path": "artifacts/km4-session-001-main_page_2.registration-overlay.png",
                    "mime_type": "image/png",
                    "width": 1200,
                    "height": 900,
                    "byte_size": 45678,
                    "sha256": "c" * 64,
                },
                "processing_issue": None,
            }
        ],
    }


class PhysicalAcceptanceSchemaTests(unittest.TestCase):
    def test_schema_accepts_a_pending_physical_registration_report(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        jsonschema.Draft202012Validator(schema).validate(minimal_report())

    def test_schema_rejects_a_field_accuracy_claim(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        report = minimal_report()
        report["field_accuracy_claim_allowed"] = True

        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(report)

    def test_schema_rejects_unknown_nested_registration_fields(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        report = minimal_report()
        report["entries"][0]["registration"]["unreviewed_extension"] = True

        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(report)

    def test_schema_rejects_candidate_that_bypasses_human_review(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        invalid_mutations = (
            ("review_status", "reviewed"),
            ("requires_human_review", False),
            ("requires_manual_registration", True),
            ("board_to_image_matrix", None),
        )
        for field, value in invalid_mutations:
            with self.subTest(field=field):
                report = minimal_report()
                report["entries"][0]["registration"][field] = value
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(schema).validate(report)

    def test_schema_rejects_candidate_with_a_processing_issue(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        report = minimal_report()
        report["entries"][0]["processing_issue"] = {
            "code": "processing_failed",
            "message": "invalid mixed state",
        }

        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(report)

    def test_runtime_consistency_rejects_drifted_summary_counts(self):
        report = minimal_report()
        report["summary"]["entry_count"] = 99

        with self.assertRaisesRegex(ValueError, "summary"):
            validate_physical_registration_report(report)

    def test_runtime_consistency_rejects_candidate_that_bypasses_review(self):
        invalid_mutations = (
            ("review_status", "reviewed"),
            ("requires_human_review", False),
            ("requires_manual_registration", True),
            ("board_to_image_matrix", None),
        )
        for field, value in invalid_mutations:
            with self.subTest(field=field):
                report = minimal_report()
                report["entries"][0]["registration"][field] = value
                with self.assertRaisesRegex(ValueError, "registration|review"):
                    validate_physical_registration_report(report)

    def test_schema_rejects_report_status_without_matching_entry_action(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        for status in ("attention", "issues"):
            with self.subTest(status=status):
                report = minimal_report()
                report["status"] = status
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(schema).validate(report)

class PhysicalAcceptanceRunTests(unittest.TestCase):
    @staticmethod
    def snapshot_tree(root):
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def test_next_action_prioritizes_retake_and_never_approves_a_candidate(self):
        self.assertEqual(
            derive_next_action("retake", "candidate"),
            "image_retake_required",
        )
        self.assertEqual(
            derive_next_action("good", "manual_required"),
            "manual_registration_required",
        )
        self.assertEqual(
            derive_next_action("usable", "candidate"),
            "automatic_candidate_review_required",
        )

    def test_output_lock_serializes_publishers_for_the_same_target(self):
        with tempfile.TemporaryDirectory(prefix="physical-output-lock-") as directory:
            target = Path(directory) / "acceptance-run"
            acquired = threading.Event()

            def wait_for_lock():
                with _output_lock(target):
                    acquired.set()

            with _output_lock(target):
                worker = threading.Thread(target=wait_for_lock, daemon=True)
                worker.start()
                time.sleep(0.15)
                self.assertFalse(acquired.is_set())

            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
            self.assertTrue(acquired.is_set())

    def test_output_lock_serializes_separate_processes(self):
        with tempfile.TemporaryDirectory(prefix="physical-process-lock-") as directory:
            root = Path(directory)
            target = root / "acceptance-run"
            ready = root / "ready"
            acquired = root / "acquired"
            python = ROOT / ".venv" / "Scripts" / "python.exe"
            holder_code = (
                "import sys,time; from pathlib import Path; "
                "from scripts.visual_qc.physical_acceptance import _output_lock; "
                "target=Path(sys.argv[1]); ready=Path(sys.argv[2]); "
                "lock=_output_lock(target); lock.__enter__(); ready.write_text('ready'); "
                "time.sleep(1.0); lock.__exit__(None,None,None)"
            )
            waiter_code = (
                "import sys; from pathlib import Path; "
                "from scripts.visual_qc.physical_acceptance import _output_lock; "
                "target=Path(sys.argv[1]); acquired=Path(sys.argv[2]); "
                "lock=_output_lock(target); lock.__enter__(); acquired.write_text('yes'); "
                "lock.__exit__(None,None,None)"
            )
            holder = subprocess.Popen(
                [str(python), "-c", holder_code, str(target), str(ready)],
                cwd=ROOT,
            )
            waiter = None
            try:
                deadline = time.time() + 5
                while not ready.exists() and time.time() < deadline:
                    time.sleep(0.02)
                self.assertTrue(ready.exists())
                waiter = subprocess.Popen(
                    [str(python), "-c", waiter_code, str(target), str(acquired)],
                    cwd=ROOT,
                )
                time.sleep(0.2)
                self.assertFalse(acquired.exists())
                self.assertEqual(holder.wait(timeout=5), 0)
                self.assertEqual(waiter.wait(timeout=5), 0)
                self.assertTrue(acquired.exists())
            finally:
                if holder.poll() is None:
                    holder.terminate()
                if waiter is not None and waiter.poll() is None:
                    waiter.terminate()

    def test_directory_sync_uses_the_cross_platform_durable_implementation(self):
        with tempfile.TemporaryDirectory(prefix="physical-directory-sync-") as directory:
            with patch(
                "scripts.visual_qc.physical_acceptance._source_fsync_directory"
            ) as durable_sync:
                physical_acceptance_module._fsync_directory(Path(directory))

            durable_sync.assert_called_once_with(Path(directory))

    def test_output_lock_rejects_reparse_lock_directory(self):
        with tempfile.TemporaryDirectory(prefix="physical-lock-reparse-") as directory:
            root = Path(directory)
            redirected = root / "redirected"
            redirected.mkdir()
            locks_root = root / ".visual-qc-acceptance-locks"
            if os.name == "nt":
                created = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(locks_root), str(redirected)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if created.returncode != 0:
                    self.skipTest(f"Unable to create test junction: {created.stderr}")
            else:
                os.symlink(redirected, locks_root, target_is_directory=True)
            try:
                with self.assertRaisesRegex(
                    IntakeValidationError,
                    "reparse|symlink|escape",
                ):
                    with _output_lock(root / "acceptance-run"):
                        pass
                self.assertEqual(list(redirected.iterdir()), [])
            finally:
                if locks_root.exists() or locks_root.is_symlink():
                    os.rmdir(locks_root)

    def test_precreated_publishing_directory_rejects_reparse_path(self):
        with tempfile.TemporaryDirectory(prefix="physical-output-reparse-") as directory:
            root = Path(directory)
            library = root / "controlled-library"
            library.mkdir()
            redirected = root / "redirected"
            redirected.mkdir()
            publishing = root / "publishing"
            if os.name == "nt":
                created = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(publishing), str(redirected)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if created.returncode != 0:
                    self.skipTest(f"Unable to create test junction: {created.stderr}")
            else:
                os.symlink(redirected, publishing, target_is_directory=True)
            try:
                with self.assertRaisesRegex(
                    IntakeValidationError,
                    "reparse|symlink|escape",
                ):
                    physical_acceptance_module._prepare_output_root(
                        publishing,
                        library,
                        precreated_empty=True,
                    )
                self.assertEqual(list(redirected.iterdir()), [])
            finally:
                if publishing.exists() or publishing.is_symlink():
                    os.rmdir(publishing)

    def test_builds_deterministic_review_evidence_from_a_controlled_package(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="physical-acceptance-test-") as directory:
            root = Path(directory)
            library = root / "controlled-library"
            source = root / "incoming" / "km4-back.png"
            source.parent.mkdir()
            reference = cv2.imread(
                str(ROOT / "assets/board-atlas/km4-f151/main-point-map-page-2.png"),
                cv2.IMREAD_COLOR,
            )
            capture, _ = generate_synthetic_capture(
                reference,
                SyntheticTransformConfig(
                    rotation_degrees=4,
                    perspective_jitter=0.035,
                    crop_fraction=0.02,
                    brightness_delta=-35,
                    contrast=1.05,
                    max_dimension=1200,
                ),
                seed=20260722,
            )
            noise = np.random.default_rng(22).normal(0, 6, capture.shape)
            capture = np.clip(
                capture.astype(np.int16) + noise.astype(np.int16),
                0,
                255,
            ).astype(np.uint8)
            self.assertTrue(cv2.imwrite(str(source), capture))
            staged = stage_source_package(
                project_root=ROOT,
                library_root=library,
                package_id="km4-physical-acceptance-test",
                batch_id="km4-physical-acceptance-batch",
                board_key="km4-f151",
                capture_session_id="km4-physical-acceptance-session",
                capture_stage="before_repair",
                capture_setup_id="bench-a",
                image_assignments=[("main_page_2", source)],
                milo_physical_source_confirmed=True,
                capture_checklist_confirmed=True,
            )
            self.assertEqual(
                staged["validated_source_package"]["manifest_sha256"],
                hashlib.sha256(
                    Path(staged["source_package_path"]).read_bytes()
                ).hexdigest(),
            )
            source_snapshot = self.snapshot_tree(library)
            first_output = root / "run-a"
            second_output = root / "run-b"

            first = build_physical_registration_run(
                package_path=staged["source_package_path"],
                project_root=ROOT,
                library_root=library,
                output_root=first_output,
            )
            second = build_physical_registration_run(
                package_path=staged["source_package_path"],
                project_root=ROOT,
                library_root=library,
                output_root=second_output,
            )

            jsonschema.Draft202012Validator(schema).validate(first)
            self.assertEqual(first, second)
            self.assertEqual(first["status"], "review_required")
            self.assertTrue(first["physical_source_confirmed"])
            self.assertFalse(first["field_accuracy_claim_allowed"])
            self.assertEqual(
                first["source_package"]["manifest_sha256"],
                hashlib.sha256(
                    Path(staged["source_package_path"]).read_bytes()
                ).hexdigest(),
            )
            self.assertEqual(first["summary"]["automatic_candidate_count"], 1)
            entry = first["entries"][0]
            self.assertEqual(entry["registration"]["status"], "candidate")
            self.assertEqual(entry["registration_review_status"], "pending")
            self.assertEqual(
                entry["next_action"],
                "automatic_candidate_review_required",
            )
            first_overlay = first_output / entry["overlay"]["path"]
            second_overlay = second_output / entry["overlay"]["path"]
            self.assertEqual(first_overlay.read_bytes(), second_overlay.read_bytes())
            serialized = json.dumps(first, sort_keys=True)
            self.assertNotIn(str(root), serialized)
            self.assertEqual(self.snapshot_tree(library), source_snapshot)

            with self.assertRaisesRegex(ValueError, "already exists"):
                build_physical_registration_run(
                    package_path=staged["source_package_path"],
                    project_root=ROOT,
                    library_root=library,
                    output_root=first_output,
                )
            with self.assertRaisesRegex(ValueError, "outside"):
                build_physical_registration_run(
                    package_path=staged["source_package_path"],
                    project_root=ROOT,
                    library_root=library,
                    output_root=library / "acceptance-output",
                )

    def test_usable_unmatched_photo_requires_manual_registration(self):
        with tempfile.TemporaryDirectory(prefix="physical-manual-test-") as directory:
            root = Path(directory)
            library = root / "controlled-library"
            source = root / "incoming" / "unmatched.png"
            source.parent.mkdir()
            random_image = np.random.default_rng(20260722).integers(
                20,
                235,
                size=(720, 960, 3),
                dtype=np.uint8,
            )
            self.assertTrue(cv2.imwrite(str(source), random_image))
            staged = stage_source_package(
                project_root=ROOT,
                library_root=library,
                package_id="km4-manual-acceptance-test",
                batch_id="km4-manual-acceptance-batch",
                board_key="km4-f151",
                capture_session_id="km4-manual-acceptance-session",
                capture_stage="before_repair",
                capture_setup_id="bench-a",
                image_assignments=[("main_page_1", source)],
                milo_physical_source_confirmed=True,
                capture_checklist_confirmed=True,
            )

            report = build_physical_registration_run(
                package_path=staged["source_package_path"],
                project_root=ROOT,
                library_root=library,
                output_root=root / "run",
            )

            entry = report["entries"][0]
            self.assertIn(entry["quality"]["status"], {"good", "usable"})
            self.assertEqual(entry["registration"]["status"], "manual_required")
            self.assertEqual(entry["next_action"], "manual_registration_required")
            self.assertEqual(report["status"], "attention")
            self.assertEqual(report["summary"]["manual_registration_count"], 1)
            self.assertTrue((root / "run" / entry["overlay"]["path"]).is_file())

            def fail_overlay_fsync(path, content):
                Path(path).write_bytes(b"partial")
                raise OSError("simulated overlay fsync failure")

            with patch(
                "scripts.visual_qc.physical_acceptance._write_durable",
                side_effect=fail_overlay_fsync,
            ):
                failed = build_physical_registration_run(
                    package_path=staged["source_package_path"],
                    project_root=ROOT,
                    library_root=library,
                    output_root=root / "failed-run",
                )

            self.assertEqual(failed["status"], "issues")
            self.assertEqual(
                list((root / "failed-run" / "artifacts").iterdir()),
                [],
            )

    def test_rejects_object_bytes_changed_after_package_validation(self):
        with tempfile.TemporaryDirectory(prefix="physical-toctou-test-") as directory:
            root = Path(directory)
            library = root / "controlled-library"
            source = root / "incoming" / "capture.png"
            source.parent.mkdir()
            self.assertTrue(
                cv2.imwrite(
                    str(source),
                    np.full((180, 260, 3), 170, dtype=np.uint8),
                )
            )
            staged = stage_source_package(
                project_root=ROOT,
                library_root=library,
                package_id="km4-toctou-test",
                batch_id="km4-toctou-batch",
                board_key="km4-f151",
                capture_session_id="km4-toctou-session",
                capture_stage="before_repair",
                capture_setup_id="bench-a",
                image_assignments=[("main_page_2", source)],
                milo_physical_source_confirmed=True,
                capture_checklist_confirmed=True,
            )
            expected_manifest_sha256 = hashlib.sha256(
                Path(staged["source_package_path"]).read_bytes()
            ).hexdigest()

            def replace_after_validation(*args, **kwargs):
                package = validate_source_package(*args, **kwargs)
                changed = np.full((180, 260, 3), 30, dtype=np.uint8)
                encoded, payload = cv2.imencode(".png", changed)
                self.assertTrue(encoded)
                package["entries"][0]["object_file"].write_bytes(payload.tobytes())
                package_path = Path(staged["source_package_path"])
                package_path.write_bytes(package_path.read_bytes() + b"\n")
                return package

            with patch(
                "scripts.visual_qc.physical_acceptance.validate_source_package",
                side_effect=replace_after_validation,
            ):
                report = build_physical_registration_run(
                    package_path=staged["source_package_path"],
                    project_root=ROOT,
                    library_root=library,
                    output_root=root / "run",
                )

            entry = report["entries"][0]
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(schema).validate(report)
            self.assertEqual(report["status"], "issues")
            self.assertEqual(entry["next_action"], "processing_issue")
            self.assertIsNone(entry["registration"])
            self.assertIsNone(entry["overlay"])
            self.assertEqual(
                report["source_package"]["manifest_sha256"],
                expected_manifest_sha256,
            )


class PhysicalAcceptanceCliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [
                str(ROOT / ".venv" / "Scripts" / "python.exe"),
                str(ROOT / "scripts" / "run_visual_qc_physical_acceptance.py"),
                *map(str, arguments),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )

    def test_cli_atomically_publishes_attention_report_and_rejects_overwrite(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="physical-cli-test-") as directory:
            root = Path(directory)
            library = root / "controlled-library"
            source = root / "incoming" / "blank.png"
            source.parent.mkdir()
            self.assertTrue(
                cv2.imwrite(
                    str(source),
                    np.full((180, 260, 3), 190, dtype=np.uint8),
                )
            )
            staged = stage_source_package(
                project_root=ROOT,
                library_root=library,
                package_id="km4-cli-acceptance-test",
                batch_id="km4-cli-acceptance-batch",
                board_key="km4-f151",
                capture_session_id="km4-cli-acceptance-session",
                capture_stage="before_repair",
                capture_setup_id="bench-a",
                image_assignments=[("main_page_2", source)],
                milo_physical_source_confirmed=True,
                capture_checklist_confirmed=True,
            )
            output = root / "published-run"
            arguments = (
                "--project-root",
                ROOT,
                "--library-root",
                library,
                "--package",
                staged["source_package_path"],
                "--output",
                output,
            )

            completed = self.run_cli(*arguments)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            stdout = json.loads(completed.stdout)
            self.assertEqual(
                stdout,
                {
                    "entry_count": 1,
                    "schema_version": "VISUAL-QC-PHYSICAL-REGISTRATION-RUN-V1",
                    "status": "attention",
                },
            )
            report = json.loads(
                (output / "physical-registration-run.json").read_text(encoding="utf-8")
            )
            jsonschema.Draft202012Validator(schema).validate(report)
            markdown = (output / "physical-registration-run.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("does not establish field registration accuracy", markdown)
            self.assertTrue((output / report["entries"][0]["overlay"]["path"]).is_file())

            repeated = self.run_cli(*arguments)

            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(
                json.loads(repeated.stderr)["error"]["code"],
                "invalid_acceptance_input",
            )

            rollback_output = root / "rollback-run"
            sync_calls = 0

            def fail_parent_sync(path):
                nonlocal sync_calls
                sync_calls += 1
                if sync_calls == 3:
                    raise OSError("simulated parent directory sync failure")

            with patch(
                "scripts.visual_qc.physical_acceptance._fsync_directory",
                side_effect=fail_parent_sync,
            ):
                with self.assertRaises(OSError):
                    publish_physical_registration_run(
                        package_path=staged["source_package_path"],
                        project_root=ROOT,
                        library_root=library,
                        output_root=rollback_output,
                    )

            self.assertFalse(rollback_output.exists())
            self.assertEqual(
                list(root.glob(".rollback-run.publishing-*")),
                [],
            )

            no_recreate_output = root / "no-recreate-run"
            with patch.object(
                Path,
                "rmdir",
                side_effect=AssertionError("publishing directory must not be removed"),
            ):
                no_recreate_report = publish_physical_registration_run(
                    package_path=staged["source_package_path"],
                    project_root=ROOT,
                    library_root=library,
                    output_root=no_recreate_output,
                )

            self.assertEqual(no_recreate_report["status"], "attention")
            self.assertTrue(no_recreate_output.is_dir())

    def test_cli_rejects_invalid_package_without_partial_output(self):
        with tempfile.TemporaryDirectory(prefix="physical-cli-invalid-") as directory:
            root = Path(directory)
            library = root / "controlled-library"
            library.mkdir()
            output = root / "published-run"

            completed = self.run_cli(
                "--project-root",
                ROOT,
                "--library-root",
                library,
                "--package",
                library / "missing.json",
                "--output",
                output,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertFalse(output.exists())
            self.assertEqual(
                json.loads(completed.stderr)["error"]["code"],
                "invalid_acceptance_input",
            )

    def test_cli_unexpected_failure_does_not_leak_local_paths(self):
        stderr = io.StringIO()
        with patch(
            "scripts.run_visual_qc_physical_acceptance.publish_physical_registration_run",
            side_effect=RuntimeError("secret C:\\private\\board.png"),
        ), redirect_stderr(stderr):
            exit_code = acceptance_cli_main(
                [
                    "--library-root",
                    "C:\\controlled-library",
                    "--package",
                    "C:\\controlled-library\\package.json",
                    "--output",
                    "C:\\acceptance-output",
                ]
            )

        self.assertEqual(exit_code, 1)
        payload = json.loads(stderr.getvalue())
        self.assertEqual(payload["error"]["code"], "acceptance_run_failed")
        self.assertNotIn("private", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
