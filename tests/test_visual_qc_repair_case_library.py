from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
import zipfile

import cv2
import numpy as np

from scripts.visual_qc.intake import IntakeValidationError
from scripts.visual_qc.repair_case_library import (
    inspect_supporting_evidence,
    resolve_package_links,
    stage_repair_case_revision,
    store_supporting_evidence,
    validate_repair_case_revision,
)
from scripts.visual_qc.source_library import stage_source_package


ROOT = Path(__file__).resolve().parents[1]


def encode_image(extension, *, value):
    image = np.full((120, 180, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(extension, image)
    if not ok:
        raise RuntimeError("Unable to encode test image.")
    return encoded.tobytes()


class VisualQcRepairCaseLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="visual-qc-repair-case-library-"
        )
        self.root = Path(self.temporary.name)
        self.library = self.root / "controlled-library"
        self.before_image = self.root / "before.jpg"
        self.after_image = self.root / "after.jpg"
        self.before_image.write_bytes(encode_image(".jpg", value=90))
        self.after_image.write_bytes(encode_image(".jpg", value=160))
        self.before = self.stage_package(
            package_id="pkg-before",
            batch_id="batch-before",
            session_id="session-before",
            capture_stage="before_repair",
            image=self.before_image,
        )
        self.after = self.stage_package(
            package_id="pkg-after",
            batch_id="batch-after",
            session_id="session-after",
            capture_stage="after_repair",
            image=self.after_image,
        )

    def tearDown(self):
        for link in reversed(getattr(self, "directory_links", [])):
            if link.exists():
                os.rmdir(link)
        self.temporary.cleanup()

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

    def stage_package(
        self,
        *,
        package_id,
        batch_id,
        session_id,
        capture_stage,
        image,
    ):
        return stage_source_package(
            project_root=ROOT,
            library_root=self.library,
            package_id=package_id,
            batch_id=batch_id,
            board_key="km4-f151",
            capture_session_id=session_id,
            capture_stage=capture_stage,
            capture_setup_id="standard-bench",
            image_assignments=[("main_page_1", image)],
            milo_physical_source_confirmed=True,
            capture_checklist_confirmed=True,
        )

    def test_package_links_bind_exact_validated_source_packages(self):
        links = resolve_package_links(
            project_root=ROOT,
            library_root=self.library,
            assignments=[
                ("after_repair", self.after["source_package_path"]),
                ("before_repair", self.before["source_package_path"]),
            ],
            board_key="km4-f151",
        )

        self.assertEqual(
            [link["package_id"] for link in links],
            ["pkg-after", "pkg-before"],
        )
        self.assertEqual(links[0]["capture_stage"], "after_repair")
        self.assertEqual(links[0]["role"], "after_repair")
        self.assertEqual(links[0]["entry_ids"], ["session-after-main_page_1"])
        self.assertEqual(
            links[0]["source_package_manifest_sha256"],
            self.after["validated_source_package"]["manifest_sha256"],
        )

    def test_package_links_reject_role_board_and_duplicate_drift(self):
        with self.assertRaisesRegex(IntakeValidationError, "role"):
            resolve_package_links(
                project_root=ROOT,
                library_root=self.library,
                assignments=[
                    ("after_repair", self.before["source_package_path"])
                ],
                board_key="km4-f151",
            )

        with self.assertRaisesRegex(IntakeValidationError, "board"):
            resolve_package_links(
                project_root=ROOT,
                library_root=self.library,
                assignments=[
                    ("before_repair", self.before["source_package_path"])
                ],
                board_key="kl4-f201",
            )

        with self.assertRaisesRegex(IntakeValidationError, "duplicate"):
            resolve_package_links(
                project_root=ROOT,
                library_root=self.library,
                assignments=[
                    ("before_repair", self.before["source_package_path"]),
                    ("supplemental", self.before["source_package_path"]),
                ],
                board_key="km4-f151",
            )

    def create_allowed_supporting_files(self):
        files = {}
        values = {
            "pdf": b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n",
            "txt": "维修记录：不开机\n".encode("utf-8"),
            "csv": "fault,action\nno_power,replace_pmu\n".encode("utf-8"),
            "xls": bytes.fromhex("D0CF11E0A1B11AE1") + b"\0" * 64,
            "png": encode_image(".png", value=110),
            "jpg": encode_image(".jpg", value=130),
        }
        for key, content in values.items():
            path = self.root / f"record.{key}"
            path.write_bytes(content)
            files[key] = path
        xlsx = self.root / "record.xlsx"
        with zipfile.ZipFile(xlsx, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("xl/workbook.xml", "<workbook/>")
        files["xlsx"] = xlsx
        return files

    def test_supporting_evidence_allowlist_is_content_addressed_and_stored(self):
        files = self.create_allowed_supporting_files()
        assignments = [
            (f"evidence-{name}", path) for name, path in files.items()
        ]
        descriptions = {
            evidence_id: f"Supplied {evidence_id}"
            for evidence_id, _ in assignments
        }

        inspected = inspect_supporting_evidence(assignments, descriptions)
        store_supporting_evidence(
            library_root=self.library,
            inspected=inspected,
        )

        expected_mimes = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "csv": "text/csv",
            "xls": "application/vnd.ms-excel",
            "xlsx": (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            "png": "image/png",
            "jpg": "image/jpeg",
        }
        self.assertEqual(len(inspected), len(files))
        for item in inspected:
            record = item["record"]
            key = record["evidence_id"].removeprefix("evidence-")
            source = files[key]
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(record["mime_type"], expected_mimes[key])
            self.assertEqual(record["sha256"], digest)
            stored = self.library / record["object_path"]
            self.assertEqual(stored.read_bytes(), source.read_bytes())

    def test_supporting_evidence_rejects_unsafe_or_untrusted_files(self):
        empty = self.root / "empty.txt"
        empty.write_bytes(b"")
        executable = self.root / "program.exe"
        executable.write_bytes(b"MZ" + b"\0" * 32)
        archive = self.root / "archive.zip"
        archive.write_bytes(b"PK\x03\x04" + b"\0" * 32)
        invalid_utf8 = self.root / "invalid.txt"
        invalid_utf8.write_bytes(b"\xff\xfe")
        original = self.root / "linked.txt"
        original.write_text("linked", encoding="utf-8")
        hardlink = self.root / "hardlink.txt"
        os.link(original, hardlink)

        for path in (empty, executable, archive, invalid_utf8, hardlink):
            with self.subTest(path=path.name):
                with self.assertRaises(IntakeValidationError):
                    inspect_supporting_evidence(
                        [("evidence-1", path)],
                        {"evidence-1": "Supplied record"},
                    )

    def test_supporting_evidence_rejects_missing_description_and_duplicate_id(self):
        record = self.root / "record.txt"
        record.write_text("record", encoding="utf-8")
        with self.assertRaisesRegex(IntakeValidationError, "description"):
            inspect_supporting_evidence([("evidence-1", record)], {})
        with self.assertRaisesRegex(IntakeValidationError, "duplicate"):
            inspect_supporting_evidence(
                [("evidence-1", record), ("evidence-1", record)],
                {"evidence-1": "Record"},
            )

    def case_record(self, **overrides):
        record = {
            "device_models": ["KM4"],
            "supporting_evidence_descriptions": {},
            "reported_symptoms": [],
            "findings": [],
            "repair_actions": [],
            "outcome": {
                "status": "unknown",
                "description": None,
                "verification_description": None,
                "evidence_refs": [],
            },
            "corrections": [],
        }
        record.update(overrides)
        return record

    def stage_case(self, **overrides):
        options = {
            "project_root": ROOT,
            "library_root": self.library,
            "repair_case_id": "case-km4-0001",
            "board_key": "km4-f151",
            "package_assignments": [
                ("before_repair", self.before["source_package_path"])
            ],
            "case_record": self.case_record(),
            "supporting_assignments": [],
            "previous_manifest_path": None,
        }
        options.update(overrides)
        return stage_repair_case_revision(**options)

    def test_first_revision_publication_is_complete_and_idempotent(self):
        created = self.stage_case()

        self.assertEqual(created["state"], "created")
        self.assertEqual(created["revision"], 1)
        self.assertEqual(created["completeness"], "photos_only")
        self.assertEqual(created["package_count"], 1)
        self.assertEqual(created["supporting_evidence_count"], 0)
        manifest = created["manifest_path"]
        self.assertEqual(
            manifest,
            (
                self.library
                / "cases"
                / "case-km4-0001"
                / "revisions"
                / "0001"
                / "repair-case.json"
            ).resolve(),
        )
        self.assertTrue((manifest.parent / ".complete").is_file())
        self.assertEqual(
            hashlib.sha256(manifest.read_bytes()).hexdigest(),
            created["manifest_sha256"],
        )

        replayed = self.stage_case()
        self.assertEqual(replayed["state"], "existing")
        self.assertEqual(replayed["manifest_sha256"], created["manifest_sha256"])

    def test_conflicting_first_revision_cannot_overwrite_completed_case(self):
        created = self.stage_case()
        changed = self.case_record(
            reported_symptoms=[
                {
                    "symptom_id": "symptom-1",
                    "text": "No power",
                    "source_wording": None,
                    "fault_code": None,
                    "evidence_refs": [],
                }
            ]
        )

        with self.assertRaisesRegex(IntakeValidationError, "conflict"):
            self.stage_case(case_record=changed)

        self.assertEqual(
            hashlib.sha256(created["manifest_path"].read_bytes()).hexdigest(),
            created["manifest_sha256"],
        )

    def test_second_revision_binds_prior_hash_and_complete_case_context(self):
        first = self.stage_case()
        package_ref = {
            "kind": "package_entry",
            "package_id": "pkg-before",
            "entry_id": "session-before-main_page_1",
        }
        complete_record = self.case_record(
            reported_symptoms=[
                {
                    "symptom_id": "symptom-1",
                    "text": "Phone does not power on.",
                    "source_wording": "No power",
                    "fault_code": None,
                    "evidence_refs": [package_ref],
                }
            ],
            findings=[
                {
                    "finding_id": "finding-1",
                    "claim_status": "documented",
                    "description": "Repair record identifies U2001.",
                    "defect_category": "power_management",
                    "designator": "U2001",
                    "side_id": "main_page_1",
                    "region": None,
                    "evidence_refs": [package_ref],
                }
            ],
            repair_actions=[
                {
                    "action_id": "action-1",
                    "description": "Replaced U2001.",
                    "action_category": "component_replacement",
                    "target_designator": "U2001",
                    "side_id": "main_page_1",
                    "region": None,
                    "evidence_refs": [package_ref],
                }
            ],
            outcome={
                "status": "repair_completed",
                "description": "Phone powered on after repair.",
                "verification_description": "Power-on test passed.",
                "evidence_refs": [package_ref],
            },
        )

        second = self.stage_case(
            package_assignments=[
                ("before_repair", self.before["source_package_path"]),
                ("after_repair", self.after["source_package_path"]),
            ],
            case_record=complete_record,
            previous_manifest_path=first["manifest_path"],
        )

        self.assertEqual(second["revision"], 2)
        self.assertEqual(second["completeness"], "repair_outcome_linked")
        payload = json.loads(second["manifest_path"].read_text(encoding="utf-8"))
        self.assertEqual(
            payload["previous_manifest_sha256"],
            first["manifest_sha256"],
        )
        validated = validate_repair_case_revision(
            manifest_path=second["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        self.assertEqual(validated["revision"], 2)
        self.assertEqual(len(validated["package_links"]), 2)

    def test_historical_manifest_mutation_invalidates_later_revision(self):
        first = self.stage_case()
        changed = self.case_record(
            reported_symptoms=[
                {
                    "symptom_id": "symptom-1",
                    "text": "Phone does not power on.",
                    "source_wording": None,
                    "fault_code": None,
                    "evidence_refs": [],
                }
            ]
        )
        second = self.stage_case(
            case_record=changed,
            previous_manifest_path=first["manifest_path"],
        )
        original = first["manifest_path"].read_bytes()
        first["manifest_path"].write_bytes(original + b" ")

        with self.assertRaisesRegex(IntakeValidationError, "previous manifest"):
            validate_repair_case_revision(
                manifest_path=second["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )

    def test_concurrent_publishers_create_one_revision_and_replay_one(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.stage_case(), range(2)))

        self.assertEqual(
            sorted(result["state"] for result in results),
            ["created", "existing"],
        )
        self.assertEqual(
            len({result["manifest_sha256"] for result in results}),
            1,
        )

    def test_revision_gap_is_rejected_before_publication(self):
        first = self.stage_case()
        gap = (
            self.library
            / "cases"
            / "case-km4-0001"
            / "revisions"
            / "0003"
        )
        gap.mkdir(parents=True)
        (gap / ".complete").write_text("complete\n", encoding="ascii")
        changed = self.case_record(
            reported_symptoms=[
                {
                    "symptom_id": "symptom-1",
                    "text": "Phone does not power on.",
                    "source_wording": None,
                    "fault_code": None,
                    "evidence_refs": [],
                }
            ]
        )

        with self.assertRaisesRegex(IntakeValidationError, "gap or fork"):
            self.stage_case(
                case_record=changed,
                previous_manifest_path=first["manifest_path"],
            )

        self.assertFalse((gap.parent / "0002" / ".complete").exists())

    def test_modified_supporting_object_invalidates_revision_chain(self):
        supporting = self.root / "repair-note.txt"
        supporting.write_text("Original repair note", encoding="utf-8")
        first = self.stage_case(
            case_record=self.case_record(
                supporting_evidence_descriptions={
                    "repair-note": "Milo supplied repair note"
                }
            ),
            supporting_assignments=[("repair-note", supporting)],
        )
        changed = self.case_record(
            reported_symptoms=[
                {
                    "symptom_id": "symptom-1",
                    "text": "Phone does not power on.",
                    "source_wording": None,
                    "fault_code": None,
                    "evidence_refs": [],
                }
            ]
        )
        second = self.stage_case(
            case_record=changed,
            previous_manifest_path=first["manifest_path"],
        )
        first_payload = json.loads(
            first["manifest_path"].read_text(encoding="utf-8")
        )
        evidence_object = (
            self.library / first_payload["supporting_evidence"][0]["object_path"]
        )
        evidence_object.write_text("Tampered repair note", encoding="utf-8")

        with self.assertRaisesRegex(IntakeValidationError, "integrity mismatch"):
            validate_repair_case_revision(
                manifest_path=second["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )

    def test_failed_publication_leaves_no_complete_revision(self):
        with mock.patch(
            "scripts.visual_qc.repair_case_library.write_json_atomic",
            side_effect=OSError("simulated write failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated write failure"):
                self.stage_case(repair_case_id="case-km4-failed")

        revision_root = (
            self.library
            / "cases"
            / "case-km4-failed"
            / "revisions"
        )
        self.assertFalse((revision_root / "0001" / ".complete").exists())
        self.assertEqual(
            list(revision_root.glob(".*.staging")),
            [],
        )

    def test_completion_marker_is_created_only_after_final_directory_rename(self):
        from scripts.visual_qc import repair_case_library

        original = repair_case_library._write_completion_marker
        marker_parents = []

        def record_marker(path):
            marker_parents.append(path.parent.name)
            original(path)

        with mock.patch(
            "scripts.visual_qc.repair_case_library._write_completion_marker",
            side_effect=record_marker,
        ):
            self.stage_case(repair_case_id="case-km4-marker-order")

        self.assertEqual(marker_parents, ["0001"])

    def test_malformed_completed_manifest_fails_as_validation_error(self):
        first = self.stage_case()
        first["manifest_path"].write_text(
            '{"repair_case_id":"case-km4-0001"}\n',
            encoding="utf-8",
        )

        with self.assertRaises(IntakeValidationError):
            validate_repair_case_revision(
                manifest_path=first["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )

    def test_library_root_link_is_rejected(self):
        first = self.stage_case()
        alias = self.root / "library-alias"
        self.create_directory_link(alias, self.library)

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink"):
            validate_repair_case_revision(
                manifest_path=first["manifest_path"],
                project_root=ROOT,
                library_root=alias,
            )

    def test_case_root_link_is_rejected(self):
        first = self.stage_case()
        case_root = first["manifest_path"].parents[2]
        relocated = self.root / "relocated-case"
        case_root.rename(relocated)
        self.create_directory_link(case_root, relocated)

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink"):
            validate_repair_case_revision(
                manifest_path=case_root / "revisions/0001/repair-case.json",
                project_root=ROOT,
                library_root=self.library,
            )

    def test_canonical_evidence_hardlink_is_rejected(self):
        supporting = self.root / "repair-note.txt"
        supporting.write_text("Original repair note", encoding="utf-8")
        first = self.stage_case(
            case_record=self.case_record(
                supporting_evidence_descriptions={
                    "repair-note": "Milo supplied repair note"
                }
            ),
            supporting_assignments=[("repair-note", supporting)],
        )
        payload = json.loads(
            first["manifest_path"].read_text(encoding="utf-8")
        )
        evidence_object = (
            self.library / payload["supporting_evidence"][0]["object_path"]
        )
        linked_copy = self.root / "linked-evidence.txt"
        os.link(evidence_object, linked_copy)

        with self.assertRaisesRegex(IntakeValidationError, "regular file"):
            validate_repair_case_revision(
                manifest_path=first["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )


if __name__ == "__main__":
    unittest.main()
