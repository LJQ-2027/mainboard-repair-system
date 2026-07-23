import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import jsonschema
import numpy as np

from scripts.visual_qc.physical_acceptance import publish_physical_registration_run
from scripts.visual_qc import physical_handoff as physical_handoff_module
from scripts.visual_qc.physical_handoff import (
    PhysicalHandoffError,
    run_physical_handoff,
    validate_physical_handoff_evidence,
    validate_physical_handoff_receipt,
)
from scripts.visual_qc.server.catalog import BoardCatalog
from scripts.visual_qc.source_library import stage_source_package
from scripts.visual_qc.synthetic import (
    SyntheticTransformConfig,
    generate_synthetic_capture,
)


ROOT = Path(__file__).resolve().parents[1]
HANDOFF_SCHEMA_PATH = (
    ROOT / "knowledge-base" / "visual-qc-physical-handoff-v1-schema.json"
)


class FakeTransport:
    def __init__(self, *, fail_entries=None, job_states=None):
        self.uploads = []
        self.job_requests = []
        self.fail_entries = set(fail_entries or [])
        self.job_states = list(job_states or ["succeeded"])

    def upload(self, entry, *, idempotency_key):
        self.uploads.append((entry["entry_id"], idempotency_key))
        if entry["entry_id"] in self.fail_entries:
            raise RuntimeError("simulated transfer failure")
        return {
            "case_id": f"case-{entry['entry_id']}",
            "job": {"job_id": f"job-{entry['entry_id']}", "status": "queued"},
        }

    def get_job(self, job_id):
        self.job_requests.append(job_id)
        state = self.job_states.pop(0) if len(self.job_states) > 1 else self.job_states[0]
        payload = {
            "job_id": job_id,
            "case_id": job_id.replace("job-", "case-", 1),
            "status": state,
        }
        if state == "failed":
            payload["error"] = {
                "code": "processing_failed",
                "message": "worker failed",
            }
        return payload


class PhysicalHandoffEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_temporary = tempfile.TemporaryDirectory(
            prefix="physical-handoff-template-"
        )
        root = Path(cls.template_temporary.name)
        library = root / "controlled-library"
        incoming = root / "incoming"
        incoming.mkdir()
        reference = BoardCatalog(ROOT).resolve_side("km4-f151", "main_page_2")[
            "reference_path"
        ]
        reference_image = cv2.imread(str(reference), cv2.IMREAD_COLOR)
        if reference_image is None:
            raise RuntimeError("Unable to load KM4 registration reference")
        capture_image, _manifest = generate_synthetic_capture(
            reference_image,
            SyntheticTransformConfig(
                rotation_degrees=4,
                perspective_jitter=0.035,
                crop_fraction=0.02,
                brightness_delta=-35,
                contrast=1.05,
                max_dimension=1200,
            ),
            seed=20260723,
        )
        noise = np.random.default_rng(23).normal(0, 6, capture_image.shape)
        capture_image = np.clip(
            capture_image.astype(np.int16) + noise.astype(np.int16), 0, 255
        ).astype(np.uint8)
        capture = incoming / "km4-main-page-2.png"
        if not cv2.imwrite(str(capture), capture_image):
            raise RuntimeError("Unable to write KM4 handoff fixture")
        staged = stage_source_package(
            project_root=ROOT,
            library_root=library,
            package_id="km4-handoff-package",
            batch_id="km4-handoff-batch",
            board_key="km4-f151",
            capture_session_id="km4-handoff-session",
            capture_stage="before_repair",
            capture_setup_id="bench-a",
            image_assignments=[("main_page_2", capture)],
            milo_physical_source_confirmed=True,
            capture_checklist_confirmed=True,
        )
        report = publish_physical_registration_run(
            package_path=staged["source_package_path"],
            project_root=ROOT,
            library_root=library,
            output_root=root / "acceptance",
        )
        if report["entries"][0]["next_action"] != "automatic_candidate_review_required":
            raise RuntimeError("KM4 handoff fixture did not produce an automatic candidate")

    @classmethod
    def tearDownClass(cls):
        cls.template_temporary.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="physical-handoff-test-")
        self.root = Path(self.temporary.name)
        self.directory_links = []
        template_root = Path(self.template_temporary.name)
        shutil.copytree(template_root / "controlled-library", self.root / "controlled-library")
        shutil.copytree(template_root / "acceptance", self.root / "acceptance")
        self.library = self.root / "controlled-library"
        package_path = (
            self.library
            / "packages"
            / "km4-handoff-package"
            / "source-package.json"
        )
        package = json.loads(package_path.read_text(encoding="utf-8"))
        intake_path = package_path.parent / "km4-handoff-batch.intake.json"
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        objects_by_side = {
            entry["side_id"]: str((self.library / entry["object_path"]).resolve())
            for entry in package["entries"]
        }
        for entry in intake["entries"]:
            entry["file_path"] = objects_by_side[entry["side_id"]]
        intake_path.write_text(
            json.dumps(intake, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def tearDown(self):
        for link in reversed(getattr(self, "file_links", [])):
            if link.exists() or link.is_symlink():
                link.unlink()
        for link in reversed(self.directory_links):
            if link.exists():
                os.rmdir(link)
        self.temporary.cleanup()

    def create_file_link(self, link, target):
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", str(link), str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if result.returncode != 0:
                self.skipTest(f"Unable to create test file symlink: {result.stderr}")
        else:
            link.symlink_to(target)
        self.file_links = getattr(self, "file_links", [])
        self.file_links.append(link)

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
        self.directory_links.append(link)

    def create_evidence(self):
        package_path = (
            self.library
            / "packages"
            / "km4-handoff-package"
            / "source-package.json"
        )
        acceptance_dir = self.root / "acceptance"
        report = json.loads(
            (acceptance_dir / "physical-registration-run.json").read_text(
                encoding="utf-8"
            )
        )
        staged = {"source_package_path": package_path}
        return staged, acceptance_dir, report

    def write_report(self, acceptance_dir, report):
        path = acceptance_dir / "physical-registration-run.json"
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    def test_validates_exact_package_report_entry_and_overlay_identity(self):
        staged, acceptance_dir, report = self.create_evidence()
        report_path = acceptance_dir / "physical-registration-run.json"

        evidence = validate_physical_handoff_evidence(
            package_path=staged["source_package_path"],
            acceptance_report_path=report_path,
            project_root=ROOT,
            library_root=self.library,
        )

        self.assertEqual(
            evidence["package"]["manifest_sha256"],
            report["source_package"]["manifest_sha256"],
        )
        self.assertEqual(
            evidence["acceptance"]["sha256"],
            hashlib.sha256(report_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            [entry["entry_id"] for entry in evidence["entries"]],
            ["km4-handoff-session-main_page_2"],
        )
        self.assertEqual(
            evidence["entries"][0]["acceptance_action"],
            "automatic_candidate_review_required",
        )
        self.assertNotIn(str(self.root), json.dumps(evidence, default=str))

    def test_rejects_report_image_that_no_longer_matches_package(self):
        staged, acceptance_dir, report = self.create_evidence()
        changed = copy.deepcopy(report)
        changed["entries"][0]["image"]["sha256"] = "f" * 64
        report_path = self.write_report(acceptance_dir, changed)

        with self.assertRaisesRegex(PhysicalHandoffError, "image evidence"):
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=report_path,
                project_root=ROOT,
                library_root=self.library,
            )

    def test_rejects_unrecognized_acceptance_summary_field(self):
        staged, acceptance_dir, report = self.create_evidence()
        changed = copy.deepcopy(report)
        changed["summary"]["unreviewed_extension"] = 1
        report_path = self.write_report(acceptance_dir, changed)

        with self.assertRaisesRegex(PhysicalHandoffError, "summary"):
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=report_path,
                project_root=ROOT,
                library_root=self.library,
            )

    def test_rejects_archived_intake_capture_identity_drift(self):
        staged, acceptance_dir, _report = self.create_evidence()
        intake_path = (
            Path(staged["source_package_path"]).parent
            / "km4-handoff-batch.intake.json"
        )
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        intake["entries"][0]["capture_stage"] = "golden_reference"
        intake_path.write_text(
            json.dumps(intake, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        with self.assertRaisesRegex(PhysicalHandoffError, "intake.*identity|identity"):
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
            )

    def test_rejects_archived_intake_that_drops_the_expected_hash_binding(self):
        staged, acceptance_dir, _report = self.create_evidence()
        intake_path = (
            Path(staged["source_package_path"]).parent
            / "km4-handoff-batch.intake.json"
        )
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        intake["entries"][0]["expected_sha256"] = None
        intake_path.write_text(
            json.dumps(intake, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        with self.assertRaisesRegex(PhysicalHandoffError, "intake"):
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
            )

    def test_rejects_archived_intake_replaced_by_external_file_link(self):
        staged, acceptance_dir, _report = self.create_evidence()
        intake_path = (
            Path(staged["source_package_path"]).parent
            / "km4-handoff-batch.intake.json"
        )
        external_intake = self.root / "external-intake.json"
        intake_path.replace(external_intake)
        if os.name == "nt":
            redirected = self.root / "external-intake-directory"
            self.create_directory_link(intake_path, redirected)
        else:
            self.create_file_link(intake_path, external_intake)

        with self.assertRaises(PhysicalHandoffError) as captured:
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
            )

        self.assertEqual(captured.exception.code, "unsafe_archived_intake")

    def test_rejects_archived_intake_path_substitution_with_identical_bytes(self):
        staged, acceptance_dir, _report = self.create_evidence()
        intake_path = (
            Path(staged["source_package_path"]).parent
            / "km4-handoff-batch.intake.json"
        )
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        original = (intake_path.parent / intake["entries"][0]["file_path"]).resolve()
        substitute = self.root / "same-bytes.png"
        substitute.write_bytes(original.read_bytes())
        intake["entries"][0]["file_path"] = str(substitute)
        intake_path.write_text(
            json.dumps(intake, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        with self.assertRaisesRegex(PhysicalHandoffError, "intake.*identity|identity"):
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
            )

    def test_rejects_overlay_renamed_away_from_its_entry_identity(self):
        staged, acceptance_dir, report = self.create_evidence()
        changed = copy.deepcopy(report)
        original = acceptance_dir / changed["entries"][0]["overlay"]["path"]
        renamed = acceptance_dir / "artifacts" / "renamed.registration-overlay.png"
        renamed.write_bytes(original.read_bytes())
        changed["entries"][0]["overlay"]["path"] = "artifacts/renamed.registration-overlay.png"
        self.write_report(acceptance_dir, changed)

        with self.assertRaisesRegex(PhysicalHandoffError, "overlay"):
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
            )

    def test_rejects_retake_even_when_report_is_internally_consistent(self):
        staged, acceptance_dir, report = self.create_evidence()
        changed = copy.deepcopy(report)
        entry = changed["entries"][0]
        entry["quality"]["status"] = "retake"
        entry["next_action"] = "image_retake_required"
        changed["status"] = "attention"
        changed["summary"].update(
            {
                "image_retake_count": 1,
                "action_counts": {"image_retake_required": 1},
            }
        )
        report_path = self.write_report(acceptance_dir, changed)

        with self.assertRaisesRegex(PhysicalHandoffError, "retake"):
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=report_path,
                project_root=ROOT,
                library_root=self.library,
            )

    def test_rejects_changed_overlay_bytes(self):
        staged, acceptance_dir, report = self.create_evidence()
        overlay = acceptance_dir / report["entries"][0]["overlay"]["path"]
        overlay.write_bytes(b"changed")

        with self.assertRaisesRegex(PhysicalHandoffError, "overlay"):
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
            )

    def test_dry_run_publishes_hash_bound_review_pending_receipt(self):
        staged, acceptance_dir, _report = self.create_evidence()
        handoff_root = self.root / "handoff"

        receipt = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=handoff_root,
            transport=None,
            dry_run=True,
        )

        self.assertEqual(receipt["schema_version"], "VISUAL-QC-PHYSICAL-HANDOFF-V1")
        self.assertEqual(receipt["status"], "validated")
        self.assertFalse(receipt["field_accuracy_claim_allowed"])
        self.assertTrue(receipt["registration_review_required"])
        self.assertEqual(receipt["summary"]["state_counts"], {"validated": 1})
        self.assertEqual(receipt["entries"][0]["transfer_state"], "validated")
        self.assertTrue(receipt["entries"][0]["registration_review_required"])
        intake_path = (
            Path(staged["source_package_path"]).parent
            / "km4-handoff-batch.intake.json"
        )
        self.assertEqual(
            receipt["archived_intake"]["manifest_sha256"],
            hashlib.sha256(intake_path.read_bytes()).hexdigest(),
        )
        self.assertTrue((handoff_root / "physical-handoff.json").is_file())
        self.assertTrue((handoff_root / "intake-receipt.json").is_file())
        self.assertNotIn(str(self.root), json.dumps(receipt))
        schema = json.loads(HANDOFF_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(receipt)

    def test_schema_rejects_unknown_state_count(self):
        staged, acceptance_dir, _report = self.create_evidence()
        receipt = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=self.root / "handoff",
            transport=None,
            dry_run=True,
        )
        receipt["summary"]["state_counts"] = {"invented_state": 1}
        schema = json.loads(HANDOFF_SCHEMA_PATH.read_text(encoding="utf-8"))

        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(receipt)

    def test_runtime_rejects_tampered_hash_and_server_state(self):
        staged, acceptance_dir, _report = self.create_evidence()
        receipt = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=self.root / "handoff",
            transport=None,
            dry_run=True,
        )
        invalid_hash = copy.deepcopy(receipt)
        invalid_hash["entries"][0]["image_sha256"] = "NOT-A-SHA"
        with self.assertRaisesRegex(PhysicalHandoffError, "entry"):
            validate_physical_handoff_receipt(invalid_hash)

        invalid_state = copy.deepcopy(receipt)
        invalid_state["entries"][0].update(
            {
                "transfer_state": "completed",
                "server_case_id": None,
                "server_job_id": None,
            }
        )
        invalid_state["summary"]["state_counts"] = {"completed": 1}
        invalid_state["status"] = "transferred"
        with self.assertRaisesRegex(PhysicalHandoffError, "entry"):
            validate_physical_handoff_receipt(invalid_state)
        schema = json.loads(HANDOFF_SCHEMA_PATH.read_text(encoding="utf-8"))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(invalid_state)

        invalid_status = copy.deepcopy(receipt)
        invalid_status["status"] = "transferred"
        with self.assertRaisesRegex(PhysicalHandoffError, "summary"):
            validate_physical_handoff_receipt(invalid_status)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(invalid_status)

        failed_without_error = copy.deepcopy(receipt)
        failed_without_error["status"] = "failed"
        failed_without_error["summary"]["state_counts"] = {"failed": 1}
        failed_without_error["entries"][0]["transfer_state"] = "failed"
        with self.assertRaisesRegex(PhysicalHandoffError, "entry"):
            validate_physical_handoff_receipt(failed_without_error)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(failed_without_error)

    def test_transfer_is_resumable_and_projects_server_ids(self):
        staged, acceptance_dir, _report = self.create_evidence()
        transport = FakeTransport(job_states=["running", "succeeded"])
        options = {
            "package_path": staged["source_package_path"],
            "acceptance_report_path": acceptance_dir / "physical-registration-run.json",
            "project_root": ROOT,
            "library_root": self.library,
            "handoff_root": self.root / "handoff",
            "transport": transport,
            "wait_for_jobs": True,
            "poll_interval_seconds": 0,
        }

        first = run_physical_handoff(**options)
        resumed = run_physical_handoff(**options)

        self.assertEqual(first["status"], "transferred")
        self.assertEqual(resumed, first)
        self.assertEqual(len(transport.uploads), 1)
        self.assertEqual(first["entries"][0]["transfer_state"], "completed")
        self.assertIsNotNone(first["entries"][0]["server_case_id"])
        self.assertIsNotNone(first["entries"][0]["server_job_id"])
        schema = json.loads(HANDOFF_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(first)

    def test_forged_nested_completion_cannot_promote_handoff_without_server_match(self):
        staged, acceptance_dir, _report = self.create_evidence()
        handoff_root = self.root / "handoff"
        run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=handoff_root,
            transport=None,
            dry_run=True,
        )
        intake_path = handoff_root / "intake-receipt.json"
        nested = json.loads(intake_path.read_text(encoding="utf-8"))
        nested["entries"][0].update(
            {
                "state": "completed",
                "server_case_id": "forged-case",
                "server_job_id": "job-other",
            }
        )
        intake_path.write_text(
            json.dumps(nested, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        transport = FakeTransport(job_states=["succeeded"])

        receipt = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=handoff_root,
            transport=transport,
            wait_for_jobs=True,
            poll_interval_seconds=0,
        )

        self.assertNotEqual(receipt["status"], "transferred")
        self.assertEqual(transport.uploads, [])
        self.assertEqual(receipt["entries"][0]["error"]["code"], "job_identity_mismatch")

    def test_intake_changed_after_evidence_validation_is_blocked_before_upload(self):
        staged, acceptance_dir, _report = self.create_evidence()
        handoff_root = self.root / "handoff"
        run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=handoff_root,
            transport=None,
            dry_run=True,
        )
        intake_path = (
            Path(staged["source_package_path"]).parent
            / "km4-handoff-batch.intake.json"
        )
        changed_image = self.root / "changed-after-evidence.png"
        image = cv2.imread(
            str(
                self.library
                / json.loads(
                    Path(staged["source_package_path"]).read_text(encoding="utf-8")
                )["entries"][0]["object_path"]
            ),
            cv2.IMREAD_COLOR,
        )
        self.assertIsNotNone(image)
        image[0, 0] = (image[0, 0].astype(np.int16) + 17) % 255
        self.assertTrue(cv2.imwrite(str(changed_image), image))
        changed_sha = hashlib.sha256(changed_image.read_bytes()).hexdigest()
        original_run_intake = physical_handoff_module.run_intake

        def replace_intake_before_transfer(*args, **kwargs):
            manifest = json.loads(intake_path.read_text(encoding="utf-8"))
            manifest["entries"][0]["file_path"] = str(changed_image.resolve())
            manifest["entries"][0]["expected_sha256"] = changed_sha
            intake_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            return original_run_intake(*args, **kwargs)

        transport = FakeTransport()
        with patch(
            "scripts.visual_qc.physical_handoff.run_intake",
            side_effect=replace_intake_before_transfer,
        ):
            with self.assertRaises(PhysicalHandoffError) as captured:
                run_physical_handoff(
                    package_path=staged["source_package_path"],
                    acceptance_report_path=acceptance_dir
                    / "physical-registration-run.json",
                    project_root=ROOT,
                    library_root=self.library,
                    handoff_root=handoff_root,
                    transport=transport,
                    wait_for_jobs=True,
                    poll_interval_seconds=0,
                )

        self.assertEqual(captured.exception.code, "intake_changed_after_validation")
        self.assertEqual(transport.uploads, [])

    def test_non_waiting_upload_remains_processing_and_failure_is_typed(self):
        staged, acceptance_dir, _report = self.create_evidence()
        processing = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=self.root / "processing-handoff",
            transport=FakeTransport(),
        )
        self.assertEqual(processing["status"], "processing")
        self.assertEqual(processing["entries"][0]["transfer_state"], "uploaded")

        failed = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=self.root / "failed-handoff",
            transport=FakeTransport(
                fail_entries={"km4-handoff-session-main_page_2"}
            ),
        )
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["entries"][0]["transfer_state"], "failed")
        self.assertEqual(failed["entries"][0]["error"]["code"], "transfer_failure")
        schema = json.loads(HANDOFF_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(processing)
        jsonschema.Draft202012Validator(schema).validate(failed)

    def test_existing_handoff_rejects_a_different_acceptance_report_hash(self):
        staged, acceptance_dir, report = self.create_evidence()
        report_path = acceptance_dir / "physical-registration-run.json"
        handoff_root = self.root / "handoff"
        run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=report_path,
            project_root=ROOT,
            library_root=self.library,
            handoff_root=handoff_root,
            transport=None,
            dry_run=True,
        )
        changed = copy.deepcopy(report)
        changed["entries"][0]["registration"]["evidence"]["test_marker"] = 1
        self.write_report(acceptance_dir, changed)

        with self.assertRaisesRegex(PhysicalHandoffError, "conflict"):
            run_physical_handoff(
                package_path=staged["source_package_path"],
                acceptance_report_path=report_path,
                project_root=ROOT,
                library_root=self.library,
                handoff_root=handoff_root,
                transport=None,
                dry_run=True,
            )

    def test_manual_registration_action_is_admitted_but_not_reviewed(self):
        staged, acceptance_dir, report = self.create_evidence()
        changed = copy.deepcopy(report)
        entry = changed["entries"][0]
        entry["registration"].update(
            {
                "status": "manual_required",
                "method": None,
                "review_status": None,
                "requires_human_review": False,
                "requires_manual_registration": True,
                "board_to_image_matrix": None,
                "failure": {"code": "insufficient_matches"},
                "fallback": {
                    "method": "reviewed_manual_four_point",
                    "reason_code": "insufficient_matches",
                },
            }
        )
        entry["next_action"] = "manual_registration_required"
        changed["status"] = "attention"
        changed["summary"].update(
            {
                "automatic_candidate_count": 0,
                "manual_registration_count": 1,
                "action_counts": {"manual_registration_required": 1},
            }
        )
        self.write_report(acceptance_dir, changed)

        receipt = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_dir / "physical-registration-run.json",
            project_root=ROOT,
            library_root=self.library,
            handoff_root=self.root / "manual-handoff",
            transport=None,
            dry_run=True,
        )

        self.assertEqual(
            receipt["entries"][0]["acceptance_action"],
            "manual_registration_required",
        )
        self.assertTrue(receipt["entries"][0]["registration_review_required"])

    def test_processing_issue_is_rejected_with_a_specific_gate(self):
        staged, acceptance_dir, report = self.create_evidence()
        changed = copy.deepcopy(report)
        entry = changed["entries"][0]
        entry.update(
            {
                "quality": None,
                "registration": None,
                "next_action": "processing_issue",
                "overlay": None,
                "processing_issue": {
                    "code": "processing_failed",
                    "message": "The validated entry could not be processed.",
                },
            }
        )
        changed["status"] = "issues"
        changed["summary"].update(
            {
                "automatic_candidate_count": 0,
                "processing_issue_count": 1,
                "action_counts": {"processing_issue": 1},
            }
        )
        self.write_report(acceptance_dir, changed)

        with self.assertRaises(PhysicalHandoffError) as captured:
            validate_physical_handoff_evidence(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
            )

        self.assertEqual(captured.exception.code, "acceptance_processing_issue")

    def test_rejects_project_contained_handoff_without_creating_lock_artifacts(self):
        staged, acceptance_dir, _report = self.create_evidence()
        unsafe_parent = ROOT / ".physical-handoff-unsafe-test"
        try:
            with self.assertRaises(PhysicalHandoffError) as captured:
                run_physical_handoff(
                    package_path=staged["source_package_path"],
                    acceptance_report_path=acceptance_dir
                    / "physical-registration-run.json",
                    project_root=ROOT,
                    library_root=self.library,
                    handoff_root=unsafe_parent / "handoff",
                    transport=None,
                    dry_run=True,
                )
            self.assertEqual(captured.exception.code, "unsafe_handoff_root")
            self.assertFalse(unsafe_parent.exists())
        finally:
            shutil.rmtree(unsafe_parent, ignore_errors=True)

    def test_rejects_reparse_handoff_root_before_creating_lock_artifacts(self):
        staged, acceptance_dir, _report = self.create_evidence()
        handoffs = self.root / "handoffs"
        redirected = self.root / "redirected-handoff"
        handoff_root = handoffs / "km4"
        self.create_directory_link(handoff_root, redirected)

        with self.assertRaises(PhysicalHandoffError) as captured:
            run_physical_handoff(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
                handoff_root=handoff_root,
                transport=None,
                dry_run=True,
            )

        self.assertEqual(captured.exception.code, "unsafe_handoff_root")
        self.assertFalse((handoffs / ".visual-qc-handoff-locks").exists())
        self.assertEqual(list(redirected.iterdir()), [])

    def test_rejects_reparse_receipt_paths_before_read_or_write(self):
        staged, acceptance_dir, _report = self.create_evidence()
        for receipt_name in ("physical-handoff.json", "intake-receipt.json"):
            with self.subTest(receipt_name=receipt_name):
                handoff_root = self.root / f"linked-{receipt_name}"
                handoff_root.mkdir()
                redirected = self.root / f"redirected-{receipt_name}"
                self.create_directory_link(handoff_root / receipt_name, redirected)

                with self.assertRaises(PhysicalHandoffError) as captured:
                    run_physical_handoff(
                        package_path=staged["source_package_path"],
                        acceptance_report_path=acceptance_dir
                        / "physical-registration-run.json",
                        project_root=ROOT,
                        library_root=self.library,
                        handoff_root=handoff_root,
                        transport=None,
                        dry_run=True,
                    )

                self.assertEqual(captured.exception.code, "unsafe_handoff_root")
                self.assertEqual(list(redirected.iterdir()), [])

    def test_new_handoff_directory_syncs_its_parent_metadata(self):
        staged, acceptance_dir, _report = self.create_evidence()
        handoff_root = self.root / "handoffs" / "km4"
        handoff_root.parent.mkdir()

        with patch(
            "scripts.visual_qc.physical_handoff._fsync_directory"
        ) as sync_directory:
            run_physical_handoff(
                package_path=staged["source_package_path"],
                acceptance_report_path=acceptance_dir
                / "physical-registration-run.json",
                project_root=ROOT,
                library_root=self.library,
                handoff_root=handoff_root,
                transport=None,
                dry_run=True,
            )

        synced = [Path(call.args[0]).resolve() for call in sync_directory.call_args_list]
        self.assertIn(handoff_root.parent.resolve(), synced)

    def test_two_side_proxy_handoff_preserves_source_and_acceptance_bytes(self):
        root = self.root / "two-side-proxy"
        library = root / "controlled-library"
        incoming = root / "incoming"
        incoming.mkdir(parents=True)
        assignments = []
        for index, side_id in enumerate(("main_page_1", "main_page_2"), start=1):
            reference = BoardCatalog(ROOT).resolve_side("km4-f151", side_id)[
                "reference_path"
            ]
            reference_image = cv2.imread(str(reference), cv2.IMREAD_COLOR)
            self.assertIsNotNone(reference_image)
            capture_image, _manifest = generate_synthetic_capture(
                reference_image,
                SyntheticTransformConfig(
                    rotation_degrees=4,
                    perspective_jitter=0.035,
                    crop_fraction=0.02,
                    brightness_delta=-35,
                    contrast=1.05,
                    max_dimension=1200,
                ),
                seed=20260723 + index,
            )
            noise = np.random.default_rng(20260723 + index).normal(
                0, 6, capture_image.shape
            )
            capture_image = np.clip(
                capture_image.astype(np.int16) + noise.astype(np.int16), 0, 255
            ).astype(np.uint8)
            capture_path = incoming / f"{side_id}.png"
            self.assertTrue(cv2.imwrite(str(capture_path), capture_image))
            assignments.append((side_id, capture_path))

        staged = stage_source_package(
            project_root=ROOT,
            library_root=library,
            package_id="km4-two-side-proxy-package",
            batch_id="km4-two-side-proxy-batch",
            board_key="km4-f151",
            capture_session_id="km4-two-side-proxy-session",
            capture_stage="before_repair",
            capture_setup_id="proxy-bench",
            image_assignments=assignments,
            milo_physical_source_confirmed=True,
            capture_checklist_confirmed=True,
        )
        acceptance_root = root / "acceptance"
        report = publish_physical_registration_run(
            package_path=staged["source_package_path"],
            project_root=ROOT,
            library_root=library,
            output_root=acceptance_root,
        )
        self.assertEqual(len(report["entries"]), 2)
        self.assertTrue(
            all(
                entry["next_action"]
                in {
                    "automatic_candidate_review_required",
                    "manual_registration_required",
                }
                for entry in report["entries"]
            ),
            [entry["next_action"] for entry in report["entries"]],
        )

        def snapshot_tree(path):
            return {
                item.relative_to(path).as_posix(): hashlib.sha256(
                    item.read_bytes()
                ).hexdigest()
                for item in sorted(path.rglob("*"))
                if item.is_file()
            }

        source_snapshot = snapshot_tree(library)
        acceptance_snapshot = snapshot_tree(acceptance_root)
        handoff_root = root / "handoff"
        dry_run = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_root
            / "physical-registration-run.json",
            project_root=ROOT,
            library_root=library,
            handoff_root=handoff_root,
            transport=None,
            dry_run=True,
        )
        self.assertEqual(dry_run["status"], "validated")
        transport = FakeTransport()
        transferred = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_root
            / "physical-registration-run.json",
            project_root=ROOT,
            library_root=library,
            handoff_root=handoff_root,
            transport=transport,
            wait_for_jobs=True,
        )
        resumed = run_physical_handoff(
            package_path=staged["source_package_path"],
            acceptance_report_path=acceptance_root
            / "physical-registration-run.json",
            project_root=ROOT,
            library_root=library,
            handoff_root=handoff_root,
            transport=transport,
            wait_for_jobs=True,
        )

        self.assertEqual(transferred, resumed)
        self.assertEqual(transferred["status"], "transferred")
        self.assertEqual(len(transport.uploads), 2)
        self.assertEqual(snapshot_tree(library), source_snapshot)
        self.assertEqual(snapshot_tree(acceptance_root), acceptance_snapshot)
        self.assertTrue(
            all(entry["registration_review_required"] for entry in resumed["entries"])
        )
        self.assertFalse(resumed["field_accuracy_claim_allowed"])

    def test_handoff_cli_help_and_dry_run_emit_stable_path_free_json(self):
        help_result = subprocess.run(
            [sys.executable, "scripts/handoff_visual_qc_physical_package.py", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("acceptance-qualified", help_result.stdout)

        staged, acceptance_dir, _report = self.create_evidence()
        result = subprocess.run(
            [
                sys.executable,
                "scripts/handoff_visual_qc_physical_package.py",
                str(staged["source_package_path"]),
                str(acceptance_dir / "physical-registration-run.json"),
                "--library-root",
                str(self.library),
                "--handoff-root",
                str(self.root / "handoff"),
                "--dry-run",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "validated")
        self.assertEqual(payload["batch_id"], "km4-handoff-batch")
        self.assertEqual(payload["counts"], {"validated": 1})
        self.assertNotIn(str(self.root), result.stdout + result.stderr)

        secret_path = "C:/secret/physical-board-photo.png"
        invalid_arguments = subprocess.run(
            [
                sys.executable,
                "scripts/handoff_visual_qc_physical_package.py",
                "--unknown",
                secret_path,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(invalid_arguments.returncode, 2)
        self.assertEqual(invalid_arguments.stdout, "")
        self.assertNotIn(secret_path, invalid_arguments.stderr)
        argument_error = json.loads(invalid_arguments.stderr)
        self.assertEqual(argument_error["code"], "invalid_arguments")

    def test_handoff_cli_returns_exit_two_for_invalid_acceptance(self):
        staged, _acceptance_dir, _report = self.create_evidence()
        result = subprocess.run(
            [
                sys.executable,
                "scripts/handoff_visual_qc_physical_package.py",
                str(staged["source_package_path"]),
                str(self.root / "missing" / "physical-registration-run.json"),
                "--library-root",
                str(self.library),
                "--handoff-root",
                str(self.root / "handoff"),
                "--dry-run",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "validation_failed")
        self.assertEqual(payload["code"], "invalid_acceptance_report")
        self.assertNotIn(str(self.root), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
