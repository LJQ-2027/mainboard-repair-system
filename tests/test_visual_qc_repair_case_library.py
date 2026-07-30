from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from unittest import mock
import zipfile

import cv2
import numpy as np
from PIL import Image
from pillow_heif import from_pillow

from scripts.visual_qc.intake import IntakeValidationError
from scripts.visual_qc.repair_case_contract import (
    FIXED_FALSE_BOUNDARIES,
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
    REPAIR_CASE_SCHEMA_V3,
)
from scripts.visual_qc.repair_case_library import (
    build_repair_case_revision,
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


def write_heic(path, width=180, height=120, value=120):
    image = Image.new("RGB", (width, height), (value, value, value))
    from_pillow(image).save(path, quality=90)


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

    def f069_package(self):
        if not hasattr(self, "_f069_package"):
            image = self.root / "f069-after.jpg"
            image.write_bytes(encode_image(".jpg", value=200))
            self._f069_package = stage_source_package(
                project_root=ROOT,
                library_root=self.library,
                package_id="pkg-f069-after",
                batch_id="batch-f069-after",
                board_key="bg6h-f069",
                capture_session_id="session-f069-after",
                capture_stage="after_repair",
                capture_setup_id="standard-bench",
                image_assignments=[("main_page_1", image)],
                milo_physical_source_confirmed=True,
                capture_checklist_confirmed=True,
            )
        return self._f069_package

    def catalog_patch(self, entry, *, board_key="km4-f151"):
        return self.catalog_data_patch(
            {"boards": {board_key: entry}},
            board_key=board_key,
        )

    def catalog_data_patch(
        self,
        catalog_data,
        *,
        board_key="km4-f151",
        construction_error=None,
        resolution_error=None,
    ):
        source_manifest = json.loads(
            self.before["source_package_path"].read_text(encoding="utf-8")
        )
        board_id = source_manifest["board_id"]

        class PatchedBoardCatalog:
            def __init__(self, project_root):
                if construction_error is not None:
                    raise construction_error
                self.catalog = catalog_data

            def resolve_board(self, requested_key):
                if requested_key != board_key:
                    raise AssertionError(f"unexpected board key: {requested_key}")
                if resolution_error is not None:
                    raise resolution_error
                return {"board_id": board_id}

        return mock.patch(
            "scripts.visual_qc.repair_case_library.BoardCatalog",
            PatchedBoardCatalog,
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

    def v2_case_record(self, identity, **overrides):
        record = self.case_record()
        del record["device_models"]
        record["device_identity"] = identity
        record.update(overrides)
        return record

    def v3_supporting_only_record(self, evidence_id="repair-photo", **overrides):
        evidence_ref = self.identity_reference(evidence_id)
        record = {
            "device_identity": self.unresolved_f069_identity(evidence_id),
            "evidence_mode": "supporting_only",
            "supporting_evidence_contexts": [
                {
                    "evidence_id": evidence_id,
                    "evidence_role": "repair_in_progress_photo",
                    "source_capture_stage": "维修中",
                    "source_board_area": "屏蔽罩内局部",
                }
            ],
            "supporting_evidence_descriptions": {
                evidence_id: "Milo supplied repair-in-progress photograph"
            },
            "reported_symptoms": [
                {
                    "symptom_id": "symptom-unable-to-charge",
                    "text": "无法充电",
                    "source_wording": "无法充电",
                    "fault_code": None,
                    "evidence_refs": [evidence_ref],
                }
            ],
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

    @staticmethod
    def exact_f069_identity():
        return {
            "reported_models": ["BG6H", "BG6h"],
            "catalog_models": ["BG6H", "BG6h"],
            "mapping_status": "exact_catalog_match",
            "resolved_models": ["BG6H", "BG6h"],
            "resolution_note": None,
            "evidence_refs": [],
        }

    @staticmethod
    def identity_reference(evidence_id):
        return {
            "kind": "supporting_evidence",
            "evidence_id": evidence_id,
        }

    def unresolved_f069_identity(self, *evidence_ids):
        return {
            "reported_models": ["TECNO/BG6"],
            "catalog_models": ["BG6H", "BG6h"],
            "mapping_status": "unresolved_alias",
            "resolved_models": [],
            "resolution_note": None,
            "evidence_refs": [
                self.identity_reference(evidence_id)
                for evidence_id in evidence_ids
            ],
        }

    def confirmed_f069_identity(self, *evidence_ids):
        return {
            "reported_models": ["TECNO/BG6"],
            "catalog_models": ["BG6H", "BG6h"],
            "mapping_status": "confirmed_alias",
            "resolved_models": ["BG6H"],
            "resolution_note": "The appended evidence confirms the BG6H alias.",
            "evidence_refs": [
                self.identity_reference(evidence_id)
                for evidence_id in evidence_ids
            ],
        }

    def conflict_transition_fixture(self, repair_case_id):
        first_source = self.root / f"{repair_case_id}-identity.txt"
        first_source.write_text("Conflicting model: TECNO/BG6", encoding="utf-8")
        unused_source = self.root / f"{repair_case_id}-unused.txt"
        unused_source.write_text("Existing uncited identity evidence", encoding="utf-8")
        conflict_identity = self.unresolved_f069_identity("identity-first")
        conflict_identity["mapping_status"] = "conflict"
        symptoms = [
            {
                "symptom_id": "symptom-old",
                "text": "Initial report.",
                "source_wording": None,
                "fault_code": None,
                "evidence_refs": [],
            },
            {
                "symptom_id": "symptom-new",
                "text": "Corrected report.",
                "source_wording": None,
                "fault_code": None,
                "evidence_refs": [],
            },
            {
                "symptom_id": "symptom-identity",
                "text": "Identity-confirmed report.",
                "source_wording": None,
                "fault_code": None,
                "evidence_refs": [],
            },
        ]
        historical_correction = {
            "correction_id": "correction-old",
            "corrects_fact_id": "symptom-old",
            "description": "Historical non-identity correction.",
            "replacement_fact_id": "symptom-new",
            "evidence_refs": [],
        }
        first = self.stage_f069_case(
            repair_case_id=repair_case_id,
            case_record=self.v2_case_record(
                conflict_identity,
                supporting_evidence_descriptions={
                    "identity-first": "Initial conflicting identity source",
                    "identity-unused": "Existing but initially uncited evidence",
                },
                reported_symptoms=symptoms,
                corrections=[historical_correction],
            ),
            supporting=[
                ("identity-first", first_source),
                ("identity-unused", unused_source),
            ],
        )
        appended_correction = {
            "correction_id": "correction-identity",
            "corrects_fact_id": "symptom-new",
            "description": "Correct the conflicting model identity.",
            "replacement_fact_id": "symptom-identity",
            "evidence_refs": [],
        }
        return first, symptoms, historical_correction, appended_correction

    def stage_f069_case(self, *, case_record, supporting=None, **overrides):
        options = {
            "project_root": ROOT,
            "library_root": self.library,
            "repair_case_id": "case-f069-0001",
            "board_key": "bg6h-f069",
            "package_assignments": [
                ("after_repair", self.f069_package()["source_package_path"])
            ],
            "case_record": case_record,
            "supporting_assignments": supporting or [],
            "previous_manifest_path": None,
        }
        options.update(overrides)
        return stage_repair_case_revision(**options)

    def stage_f069_supporting_only(
        self,
        *,
        source,
        repair_case_id="case-f069-supporting-only",
        case_record=None,
        **overrides,
    ):
        options = {
            "project_root": ROOT,
            "library_root": self.library,
            "repair_case_id": repair_case_id,
            "board_key": "bg6h-f069",
            "package_assignments": [],
            "case_record": (
                self.v3_supporting_only_record()
                if case_record is None
                else case_record
            ),
            "supporting_assignments": [("repair-photo", source)],
            "previous_manifest_path": None,
        }
        options.update(overrides)
        return stage_repair_case_revision(**options)

    def case_evidence_objects(self):
        root = self.library / "objects" / "case-evidence"
        return (
            {path for path in root.rglob("*") if path.is_file()}
            if root.exists()
            else set()
        )

    @staticmethod
    def v3_completion_marker_bytes(manifest_bytes):
        return (
            b"manifest-sha256:"
            + hashlib.sha256(manifest_bytes).hexdigest().encode("ascii")
            + b"\n"
        )

    def assert_no_supporting_only_artifacts(self, case_id, baseline_objects):
        self.assertFalse(
            (
                self.library
                / "cases"
                / case_id
                / "revisions"
                / "0001"
            ).exists()
        )
        self.assertEqual(self.case_evidence_objects(), baseline_objects)

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

    def test_unresolved_v2_revision_publishes_exact_shape_and_replays(self):
        source = self.root / "f069-identity.txt"
        source.write_text("Reported model: TECNO/BG6", encoding="utf-8")
        record = self.v2_case_record(
            self.unresolved_f069_identity("identity-source"),
            supporting_evidence_descriptions={
                "identity-source": "Milo supplied model identity record"
            },
        )

        created = self.stage_f069_case(
            case_record=record,
            supporting=[("identity-source", source)],
        )
        replayed = self.stage_f069_case(
            case_record=record,
            supporting=[("identity-source", source)],
        )

        self.assertEqual(created["state"], "created")
        self.assertEqual(replayed["state"], "existing")
        self.assertEqual(replayed["manifest_sha256"], created["manifest_sha256"])
        self.assertEqual(created["schema_version"], REPAIR_CASE_SCHEMA_V2)
        self.assertEqual(created["identity_status"], "unresolved_alias")
        payload = json.loads(created["manifest_path"].read_text(encoding="utf-8"))
        self.assertEqual(
            list(payload),
            [
                "schema_version",
                "repair_case_id",
                "revision",
                "previous_manifest_sha256",
                "source_origin",
                "board_key",
                "board_id",
                "device_identity",
                "package_links",
                "supporting_evidence",
                "reported_symptoms",
                "findings",
                "repair_actions",
                "outcome",
                "corrections",
                "completeness",
                "boundaries",
            ],
        )
        self.assertEqual(payload["schema_version"], REPAIR_CASE_SCHEMA_V2)
        self.assertIn("device_identity", payload)
        self.assertNotIn("device_models", payload)
        self.assertEqual(
            payload["device_identity"],
            self.unresolved_f069_identity("identity-source"),
        )
        self.assertEqual(
            payload["boundaries"],
            {**FIXED_FALSE_BOUNDARIES, "model_identity_resolved": False},
        )

        conflict = self.unresolved_f069_identity("identity-source")
        conflict["mapping_status"] = "conflict"
        with self.assertRaisesRegex(IntakeValidationError, "conflict"):
            self.stage_f069_case(
                case_record=self.v2_case_record(
                    conflict,
                    supporting_evidence_descriptions={
                        "identity-source": "Milo supplied model identity record"
                    },
                ),
                supporting=[("identity-source", source)],
            )
        with self.assertRaisesRegex(IntakeValidationError, "no evidence or context"):
            self.stage_f069_case(
                case_record=self.v2_case_record(
                    self.unresolved_f069_identity("identity-source")
                ),
                previous_manifest_path=created["manifest_path"],
            )
        self.assertEqual(
            hashlib.sha256(created["manifest_path"].read_bytes()).hexdigest(),
            created["manifest_sha256"],
        )

    def test_v3_supporting_only_stages_byte_exact_heic_without_packages(self):
        source = self.root / "repair-progress.heic"
        write_heic(source)

        created = self.stage_f069_supporting_only(source=source)
        payload = json.loads(created["manifest_path"].read_text(encoding="utf-8"))
        evidence = payload["supporting_evidence"][0]

        self.assertEqual(created["schema_version"], REPAIR_CASE_SCHEMA_V3)
        self.assertEqual(created["evidence_mode"], "supporting_only")
        self.assertEqual(created["package_count"], 0)
        self.assertEqual(payload["schema_version"], REPAIR_CASE_SCHEMA_V3)
        self.assertEqual(payload["evidence_mode"], "supporting_only")
        self.assertEqual(payload["package_links"], [])
        self.assertEqual(
            payload["supporting_evidence_contexts"],
            self.v3_supporting_only_record()["supporting_evidence_contexts"],
        )
        self.assertEqual(evidence["mime_type"], "image/heic")
        self.assertTrue(evidence["object_path"].endswith(".heic"))
        self.assertEqual(
            (self.library / evidence["object_path"]).read_bytes(),
            source.read_bytes(),
        )

    def test_v2_heic_inspection_remains_rejected_and_invalid_v3_mentions_heic(self):
        source = self.root / "v2-repair-progress.heic"
        write_heic(source)
        with self.assertRaisesRegex(IntakeValidationError, "unsupported"):
            inspect_supporting_evidence(
                [("repair-photo", source)],
                {"repair-photo": "Repair progress photograph"},
                schema_version=REPAIR_CASE_SCHEMA_V2,
            )

        invalid = self.root / "invalid.heic"
        invalid.write_bytes(b"not a valid HEIC container")
        with self.assertRaisesRegex(IntakeValidationError, "HEIC"):
            inspect_supporting_evidence(
                [("repair-photo", invalid)],
                {"repair-photo": "Repair progress photograph"},
                schema_version=REPAIR_CASE_SCHEMA_V3,
            )

    def test_supporting_only_requires_at_least_one_supporting_file(self):
        with self.assertRaisesRegex(
            IntakeValidationError,
            "requires.*supporting evidence",
        ):
            self.stage_f069_supporting_only(
                source=self.root / "unused.heic",
                supporting_assignments=[],
            )

        self.assertFalse(
            (
                self.library
                / "cases"
                / "case-f069-supporting-only"
                / "revisions"
                / "0001"
            ).exists()
        )
        self.assertEqual(self.case_evidence_objects(), set())

    def test_v3_supporting_only_replay_is_idempotent_and_corruption_is_detected(self):
        source = self.root / "replay.heic"
        write_heic(source, value=140)

        created = self.stage_f069_supporting_only(
            source=source,
            repair_case_id="case-f069-supporting-replay",
        )
        replayed = self.stage_f069_supporting_only(
            source=source,
            repair_case_id="case-f069-supporting-replay",
        )

        self.assertEqual(replayed["state"], "existing")
        self.assertEqual(replayed["manifest_sha256"], created["manifest_sha256"])
        payload = json.loads(created["manifest_path"].read_text(encoding="utf-8"))
        evidence_object = (
            self.library / payload["supporting_evidence"][0]["object_path"]
        )
        evidence_object.write_bytes(b"corrupted HEIC evidence")

        with self.assertRaisesRegex(IntakeValidationError, "integrity mismatch"):
            validate_repair_case_revision(
                manifest_path=created["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )

    def test_v3_supporting_only_mutation_calls_heic_inspection_and_publishes_nothing(
        self,
    ):
        source = self.root / "source-mutation.heic"
        replacement = self.root / "source-mutation-replacement.heic"
        write_heic(source, value=110)
        write_heic(replacement, value=180)
        baseline_objects = self.case_evidence_objects()

        from scripts.visual_qc.heic_derivative import inspect_heic_source

        def inspect_after_mutation(path):
            Path(path).write_bytes(replacement.read_bytes())
            return inspect_heic_source(path)

        case_id = "case-f069-supporting-mutation"
        with mock.patch(
            "scripts.visual_qc.repair_case_library.inspect_heic_source",
            side_effect=inspect_after_mutation,
        ) as inspection:
            with self.assertRaisesRegex(
                IntakeValidationError,
                "HEIC inspection does not match",
            ):
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )
        inspection.assert_called_once_with(source)
        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_v3_supporting_only_hardlink_failure_publishes_no_artifacts(self):
        original = self.root / "source-hardlink.heic"
        hardlink = self.root / "source-hardlink-link.heic"
        write_heic(original)
        os.link(original, hardlink)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-hardlink"

        with self.assertRaisesRegex(IntakeValidationError, "hard-linked"):
            self.stage_f069_supporting_only(
                source=hardlink,
                repair_case_id=case_id,
            )

        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_v3_supporting_only_reparse_failure_publishes_no_artifacts(self):
        junction_target = self.root / "source-junction-target"
        junction_target.mkdir()
        write_heic(junction_target / "source.heic")
        junction = self.root / "source-junction"
        self.create_directory_link(junction, junction_target)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-reparse"

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink"):
            self.stage_f069_supporting_only(
                source=junction / "source.heic",
                repair_case_id=case_id,
            )

        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_v3_supporting_only_symlink_failure_publishes_no_artifacts(self):
        original = self.root / "source-symlink.heic"
        write_heic(original)
        symlink = self.root / "source-symlink-link.heic"
        try:
            symlink.symlink_to(original)
        except OSError as exc:
            self.skipTest(f"Unable to create file symlink: {exc}")
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-symlink"

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink"):
            self.stage_f069_supporting_only(
                source=symlink,
                repair_case_id=case_id,
            )

        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_v3_post_link_store_failure_removes_owned_object(self):
        source = self.root / "post-link-failure.heic"
        write_heic(source)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-post-link"
        linked_objects = []

        def fail_post_link_integrity(path, expected_sha256):
            linked_objects.append(Path(path))
            self.assertTrue(Path(path).is_file())
            raise OSError("simulated post-link integrity failure")

        with mock.patch(
            "scripts.visual_qc.repair_case_library._assert_stored_object",
            side_effect=fail_post_link_integrity,
        ):
            with self.assertRaisesRegex(
                OSError,
                "simulated post-link integrity failure",
            ):
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        self.assertEqual(len(linked_objects), 1)
        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_v3_revision_rename_failure_publishes_no_supporting_object(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "post-storage-failure.heic"
        write_heic(source)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-post-storage"
        with (
            mock.patch(
                "scripts.visual_qc.repair_case_library.store_supporting_evidence",
            ) as store_path,
            mock.patch.object(
                Path,
                "rename",
                side_effect=OSError("simulated revision rename failure"),
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "simulated revision rename failure",
            ):
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        store_path.assert_not_called()
        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_v3_post_storage_revision_fsync_failure_removes_all_artifacts(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "post-storage-fsync.heic"
        write_heic(source)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-post-storage-fsync"
        stored_objects = []
        original_store = repair_case_library.store_supporting_evidence
        original_fsync = repair_case_library._fsync_directory

        def record_store(**kwargs):
            created = original_store(**kwargs)
            stored_objects.extend(created)
            return created

        def fail_revision_fsync_after_marker(path):
            path = Path(path)
            if path.name == "0001":
                self.assertEqual(len(stored_objects), 1)
                self.assertTrue(stored_objects[0].is_file())
                raise OSError("simulated post-storage revision fsync failure")
            return original_fsync(path)

        with (
            mock.patch(
                "scripts.visual_qc.repair_case_library.store_supporting_evidence",
                side_effect=record_store,
            ) as store_path,
            mock.patch(
                "scripts.visual_qc.repair_case_library._fsync_directory",
                side_effect=fail_revision_fsync_after_marker,
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "simulated post-storage revision fsync failure",
            ):
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        store_path.assert_called_once()
        self.assertEqual(len(stored_objects), 1)
        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_v3_completion_marker_failure_removes_revision_and_object(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "completion-marker-failure.heic"
        write_heic(source)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-completion-marker"
        stored_objects = []
        original_store = repair_case_library.store_supporting_evidence

        def record_store(**kwargs):
            created = original_store(**kwargs)
            stored_objects.extend(created)
            return created

        with (
            mock.patch(
                "scripts.visual_qc.repair_case_library.store_supporting_evidence",
                side_effect=record_store,
            ) as store_path,
            mock.patch(
                "scripts.visual_qc.repair_case_library._write_completion_marker",
                side_effect=OSError("simulated completion marker failure"),
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "simulated completion marker failure",
            ):
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        store_path.assert_called_once()
        self.assertEqual(len(stored_objects), 1)
        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_cleanup_retains_ownership_until_unlink_and_fsync_succeed(self):
        from scripts.visual_qc import repair_case_library

        for boundary in ("unlink", "fsync"):
            with self.subTest(boundary=boundary):
                parent = self.root / f"cleanup-{boundary}"
                parent.mkdir()
                evidence = parent / "evidence.heic"
                evidence.write_bytes(b"owned evidence")
                second_evidence = parent / "second-evidence.heic"
                second_evidence.write_bytes(b"second owned evidence")
                owned = [evidence, second_evidence]

                if boundary == "unlink":
                    original_unlink = Path.unlink
                    attempts = 0

                    def fail_unlink_once(path, *args, **kwargs):
                        nonlocal attempts
                        if Path(path) == evidence and attempts == 0:
                            attempts += 1
                            raise OSError("simulated cleanup unlink failure")
                        return original_unlink(path, *args, **kwargs)

                    patcher = mock.patch.object(
                        Path,
                        "unlink",
                        side_effect=fail_unlink_once,
                        autospec=True,
                    )
                else:
                    original_fsync = repair_case_library._fsync_directory
                    attempts = 0

                    def fail_fsync_once(path):
                        nonlocal attempts
                        if Path(path) == parent and attempts == 0:
                            attempts += 1
                            raise OSError("simulated cleanup fsync failure")
                        return original_fsync(path)

                    patcher = mock.patch(
                        "scripts.visual_qc.repair_case_library._fsync_directory",
                        side_effect=fail_fsync_once,
                    )

                with patcher:
                    with self.assertRaisesRegex(
                        OSError,
                        f"simulated cleanup {boundary} failure",
                    ):
                        repair_case_library._remove_created_supporting_objects(
                            owned
                        )
                    if boundary == "unlink":
                        self.assertEqual(owned, [evidence])
                        self.assertTrue(evidence.exists())
                        self.assertFalse(second_evidence.exists())
                    else:
                        self.assertEqual(owned, [evidence, second_evidence])
                        self.assertFalse(evidence.exists())
                        self.assertFalse(second_evidence.exists())
                    repair_case_library._remove_created_supporting_objects(owned)

                self.assertEqual(owned, [])
                self.assertFalse(evidence.exists())
                self.assertFalse(second_evidence.exists())

    def test_revision_removal_failure_retains_owned_object_and_allows_retry(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "revision-cleanup-failure.heic"
        write_heic(source)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-revision-cleanup"
        owned_objects = []
        original_store = repair_case_library.store_supporting_evidence

        def record_store(**kwargs):
            created = original_store(**kwargs)
            owned_objects.extend(created)
            return created

        with (
            mock.patch(
                "scripts.visual_qc.repair_case_library._write_completion_marker",
                side_effect=OSError("primary completion marker failure"),
            ),
            mock.patch(
                "scripts.visual_qc.repair_case_library.shutil.rmtree",
                side_effect=OSError("secondary revision cleanup failure"),
            ),
            mock.patch(
                "scripts.visual_qc.repair_case_library.store_supporting_evidence",
                side_effect=record_store,
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "primary completion marker failure",
            ) as raised:
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        target = (
            self.library / "cases" / case_id / "revisions" / "0001"
        )
        self.assertTrue(target.is_dir())
        self.assertFalse((target / ".complete").exists())
        self.assertEqual(len(owned_objects), 1)
        self.assertTrue(owned_objects[0].is_file())
        self.assertEqual(
            owned_objects[0].read_bytes(),
            source.read_bytes(),
        )
        self.assertIn(
            "secondary revision cleanup failure",
            "\n".join(getattr(raised.exception, "__notes__", [])),
        )
        recovered = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        self.assertEqual(recovered["state"], "existing")
        self.assertTrue((target / ".complete").is_file())
        current_objects = self.case_evidence_objects()
        self.assertEqual(
            len(current_objects),
            len(baseline_objects) + 1,
        )
        self.assertTrue(
            any(
                os.path.samefile(path, owned_objects[0])
                for path in current_objects
            )
        )
        self.assertEqual(owned_objects[0].read_bytes(), source.read_bytes())

    def test_revision_removal_fsync_failure_retains_owned_object_for_retry(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "revision-removal-fsync-failure.heic"
        write_heic(source, value=135)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-removal-fsync"
        revisions_root = (
            self.library / "cases" / case_id / "revisions"
        )
        owned_objects = []
        original_store = repair_case_library.store_supporting_evidence
        original_fsync = repair_case_library._fsync_directory
        marker_failed = False

        def record_store(**kwargs):
            created = original_store(**kwargs)
            owned_objects.extend(created)
            return created

        def fail_rollback_fsync(path):
            path = Path(path)
            if marker_failed and path.name == "revisions":
                raise OSError("secondary rollback fsync failure")
            return original_fsync(path)

        def fail_marker(path):
            nonlocal marker_failed
            marker_failed = True
            raise OSError("primary completion marker failure")

        with (
            mock.patch(
                "scripts.visual_qc.repair_case_library.store_supporting_evidence",
                side_effect=record_store,
            ),
            mock.patch(
                "scripts.visual_qc.repair_case_library._write_completion_marker",
                side_effect=fail_marker,
            ),
            mock.patch(
                "scripts.visual_qc.repair_case_library._fsync_directory",
                side_effect=fail_rollback_fsync,
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "primary completion marker failure",
            ) as raised:
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        self.assertFalse((revisions_root / "0001").exists())
        self.assertEqual(len(owned_objects), 1)
        self.assertTrue(owned_objects[0].is_file())
        self.assertEqual(owned_objects[0].read_bytes(), source.read_bytes())
        self.assertIn(
            "secondary rollback fsync failure",
            "\n".join(getattr(raised.exception, "__notes__", [])),
        )

        recovered = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        self.assertEqual(recovered["state"], "created")
        current_objects = self.case_evidence_objects()
        self.assertEqual(
            len(current_objects),
            len(baseline_objects) + 1,
        )
        self.assertTrue(
            any(
                os.path.samefile(path, owned_objects[0])
                for path in current_objects
            )
        )
        self.assertEqual(owned_objects[0].read_bytes(), source.read_bytes())

    def test_post_storage_publication_durability_failures_are_recoverable(self):
        from scripts.visual_qc import repair_case_library

        boundaries = {
            "post_rename_revisions_root": 1,
            "target_after_complete": 1,
            "final_revisions_root": 2,
        }
        for boundary, failing_occurrence in boundaries.items():
            with self.subTest(boundary=boundary):
                source = self.root / f"{boundary}.heic"
                write_heic(source, value=145 + len(boundary))
                baseline_objects = self.case_evidence_objects()
                case_id = f"case-f069-{boundary.replace('_', '-')}"
                revisions_root = (
                    self.library / "cases" / case_id / "revisions"
                )
                target = revisions_root / "0001"
                original_fsync = repair_case_library._fsync_directory
                staging_synced = False
                revisions_root_calls = 0
                failed = False

                def inject_publication_fsync(path):
                    nonlocal staging_synced, revisions_root_calls, failed
                    path = Path(path)
                    if (
                        path.name.endswith(".staging")
                        and path.parent.name == "revisions"
                    ):
                        result = original_fsync(path)
                        staging_synced = True
                        return result
                    if not staging_synced or failed:
                        return original_fsync(path)
                    if path.name == "revisions":
                        revisions_root_calls += 1
                        if (
                            boundary != "target_after_complete"
                            and revisions_root_calls == failing_occurrence
                        ):
                            failed = True
                            raise OSError(f"simulated {boundary} failure")
                    elif (
                        boundary == "target_after_complete"
                        and path.name == "0001"
                        and path.parent.name == "revisions"
                    ):
                        failed = True
                        raise OSError(f"simulated {boundary} failure")
                    return original_fsync(path)

                with mock.patch(
                    "scripts.visual_qc.repair_case_library._fsync_directory",
                    side_effect=inject_publication_fsync,
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        f"simulated {boundary} failure",
                    ):
                        self.stage_f069_supporting_only(
                            source=source,
                            repair_case_id=case_id,
                        )

                if target.exists() and (target / ".complete").is_file():
                    validated = validate_repair_case_revision(
                        manifest_path=target / "repair-case.json",
                        project_root=ROOT,
                        library_root=self.library,
                    )
                    evidence = validated["supporting_evidence"][0]
                    self.assertEqual(
                        (self.library / evidence["object_path"]).read_bytes(),
                        source.read_bytes(),
                    )
                else:
                    self.assertFalse(target.exists())

                recovered = self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )
                self.assertIn(recovered["state"], {"created", "existing"})
                payload = json.loads(
                    recovered["manifest_path"].read_text(encoding="utf-8")
                )
                evidence_object = (
                    self.library
                    / payload["supporting_evidence"][0]["object_path"]
                )
                self.assertEqual(evidence_object.read_bytes(), source.read_bytes())
                self.assertEqual(
                    self.case_evidence_objects(),
                    baseline_objects | {evidence_object},
                )

    def test_corrupt_completion_marker_fails_closed_without_rewrite(self):
        source = self.root / "corrupt-marker.heic"
        write_heic(source, value=177)
        case_id = "case-f069-corrupt-marker"
        created = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        manifest_path = created["manifest_path"]
        target = manifest_path.parent
        marker = target / ".complete"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        evidence_object = (
            self.library / payload["supporting_evidence"][0]["object_path"]
        )
        manifest_bytes = manifest_path.read_bytes()
        object_bytes = evidence_object.read_bytes()
        marker.write_bytes(b"corrupt\n")
        changed_record = copy.deepcopy(self.v3_supporting_only_record())
        changed_record["reported_symptoms"][0]["text"] = "Changed symptom"

        with self.assertRaisesRegex(
            IntakeValidationError,
            "completion marker",
        ):
            self.stage_f069_supporting_only(
                source=source,
                repair_case_id=case_id,
                case_record=changed_record,
            )

        self.assertEqual(marker.read_bytes(), b"corrupt\n")
        self.assertEqual(manifest_path.read_bytes(), manifest_bytes)
        self.assertEqual(evidence_object.read_bytes(), object_bytes)

    def test_v3_revision_one_marker_rejects_schema_valid_manifest_mutation(self):
        source = self.root / "revision-one-anchor.heic"
        write_heic(source, value=182)
        created = self.stage_f069_supporting_only(
            source=source,
            repair_case_id="case-f069-v3-revision-one-anchor",
        )
        manifest_path = created["manifest_path"]
        marker = manifest_path.parent / ".complete"
        manifest_bytes = manifest_path.read_bytes()
        marker_bytes = marker.read_bytes()
        payload = json.loads(manifest_bytes.decode("utf-8"))
        object_path = self.library / payload["supporting_evidence"][0]["object_path"]
        object_bytes = object_path.read_bytes()
        payload["evidence_mode"] = "package_linked"
        payload["package_links"] = resolve_package_links(
            project_root=ROOT,
            library_root=self.library,
            assignments=[
                ("after_repair", self.f069_package()["source_package_path"])
            ],
            board_key="bg6h-f069",
        )
        manifest_path.write_bytes(
            (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode(
                "utf-8"
            )
        )

        with self.assertRaisesRegex(
            IntakeValidationError,
            "completion marker|manifest SHA-256",
        ):
            validate_repair_case_revision(
                manifest_path=manifest_path,
                project_root=ROOT,
                library_root=self.library,
            )

        self.assertEqual(
            marker_bytes,
            self.v3_completion_marker_bytes(manifest_bytes),
        )
        self.assertEqual(marker.read_bytes(), marker_bytes)
        self.assertEqual(object_path.read_bytes(), object_bytes)

    def test_v3_latest_marker_rejects_schema_valid_manifest_mutations(self):
        source = self.root / "latest-anchor-first.heic"
        appended_source = self.root / "latest-anchor-second.heic"
        write_heic(source, value=183)
        write_heic(appended_source, value=184)
        case_id = "case-f069-v3-latest-anchor"
        first = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        revised = copy.deepcopy(self.v3_supporting_only_record())
        revised["supporting_evidence_contexts"].append(
            {
                "evidence_id": "repair-photo-2",
                "evidence_role": "repair_in_progress_photo",
                "source_capture_stage": "维修中",
                "source_board_area": "主板局部",
            }
        )
        revised["supporting_evidence_descriptions"] = {
            "repair-photo-2": "Second repair-in-progress photograph"
        }
        second = self.stage_f069_supporting_only(
            source=appended_source,
            repair_case_id=case_id,
            case_record=revised,
            supporting_assignments=[("repair-photo-2", appended_source)],
            previous_manifest_path=first["manifest_path"],
        )
        manifest_path = second["manifest_path"]
        manifest_bytes = manifest_path.read_bytes()
        marker = manifest_path.parent / ".complete"
        marker_bytes = marker.read_bytes()
        payload = json.loads(manifest_bytes.decode("utf-8"))
        object_path = self.library / payload["supporting_evidence"][1]["object_path"]
        object_bytes = object_path.read_bytes()
        mutators = {
            "new_context": lambda value: value[
                "supporting_evidence_contexts"
            ][-1].update(source_board_area="改写后的最新区域"),
            "new_symptom": lambda value: value["reported_symptoms"].append(
                {
                    "symptom_id": "symptom-latest-mutation",
                    "text": "Schema-valid latest mutation.",
                    "source_wording": None,
                    "fault_code": None,
                    "evidence_refs": [],
                }
            ),
        }

        for label, mutate in mutators.items():
            with self.subTest(label=label):
                changed = json.loads(manifest_bytes.decode("utf-8"))
                mutate(changed)
                manifest_path.write_bytes(
                    (
                        json.dumps(changed, ensure_ascii=False, indent=2) + "\n"
                    ).encode("utf-8")
                )
                with self.assertRaisesRegex(
                    IntakeValidationError,
                    "completion marker|manifest SHA-256",
                ):
                    validate_repair_case_revision(
                        manifest_path=manifest_path,
                        project_root=ROOT,
                        library_root=self.library,
                    )
                self.assertEqual(marker.read_bytes(), marker_bytes)
                self.assertEqual(object_path.read_bytes(), object_bytes)
                manifest_path.write_bytes(manifest_bytes)

        self.assertEqual(
            marker_bytes,
            self.v3_completion_marker_bytes(manifest_bytes),
        )
        self.assertEqual(manifest_path.read_bytes(), manifest_bytes)

    def test_v1_v2_completion_markers_remain_legacy_compatible(self):
        v1 = self.stage_case(repair_case_id="case-km4-v1-legacy-marker")
        v2 = self.stage_f069_case(
            repair_case_id="case-f069-v2-legacy-marker",
            case_record=self.v2_case_record(self.exact_f069_identity()),
        )

        for created in (v1, v2):
            with self.subTest(schema=created["schema_version"]):
                marker = created["manifest_path"].parent / ".complete"
                self.assertEqual(marker.read_bytes(), b"complete\n")
                replayed = validate_repair_case_revision(
                    manifest_path=created["manifest_path"],
                    project_root=ROOT,
                    library_root=self.library,
                )
                self.assertEqual(replayed["schema_version"], created["schema_version"])

    def test_marker_free_conflicting_manifest_fails_closed_unchanged(self):
        source = self.root / "marker-free-conflict.heic"
        write_heic(source, value=178)
        case_id = "case-f069-marker-free-conflict"
        created = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        manifest_path = created["manifest_path"]
        marker = manifest_path.parent / ".complete"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        evidence_object = (
            self.library / payload["supporting_evidence"][0]["object_path"]
        )
        manifest_bytes = manifest_path.read_bytes()
        object_bytes = evidence_object.read_bytes()
        marker.unlink()
        changed_record = copy.deepcopy(self.v3_supporting_only_record())
        changed_record["reported_symptoms"][0]["text"] = "Conflicting symptom"

        with self.assertRaisesRegex(
            IntakeValidationError,
            "conflict|incomplete",
        ):
            self.stage_f069_supporting_only(
                source=source,
                repair_case_id=case_id,
                case_record=changed_record,
            )

        self.assertFalse(marker.exists())
        self.assertEqual(manifest_path.read_bytes(), manifest_bytes)
        self.assertEqual(evidence_object.read_bytes(), object_bytes)

    def test_marker_free_exact_manifest_recovers_same_publication_in_place(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "marker-free-exact.heic"
        write_heic(source, value=179)
        case_id = "case-f069-marker-free-exact"
        created = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        manifest_path = created["manifest_path"]
        target = manifest_path.parent
        revisions_root = target.parent
        marker = target / ".complete"
        manifest_bytes = manifest_path.read_bytes()
        payload = json.loads(manifest_bytes.decode("utf-8"))
        evidence_object = (
            self.library / payload["supporting_evidence"][0]["object_path"]
        )
        object_bytes = evidence_object.read_bytes()
        marker.unlink()
        original_fsync = repair_case_library._fsync_directory
        fsynced = []

        def observe_fsync(path):
            path = Path(path)
            if path.name in {"0001", "revisions"}:
                fsynced.append(path.name)
            return original_fsync(path)

        with mock.patch(
            "scripts.visual_qc.repair_case_library._fsync_directory",
            side_effect=observe_fsync,
        ):
            recovered = self.stage_f069_supporting_only(
                source=source,
                repair_case_id=case_id,
            )

        self.assertEqual(recovered["state"], "existing")
        self.assertEqual(fsynced, ["0001", "0001", "revisions"])
        self.assertEqual(
            marker.read_bytes(),
            self.v3_completion_marker_bytes(manifest_bytes),
        )
        self.assertEqual(manifest_path.read_bytes(), manifest_bytes)
        self.assertEqual(evidence_object.read_bytes(), object_bytes)
        validated = validate_repair_case_revision(
            manifest_path=manifest_path,
            project_root=ROOT,
            library_root=self.library,
        )
        self.assertEqual(validated, payload)

    def test_surviving_valid_marker_is_resynced_before_existing_retry(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "surviving-marker.heic"
        write_heic(source, value=180)
        case_id = "case-f069-surviving-marker"
        original_fsync = repair_case_library._fsync_directory
        target_fsync_failed = False

        def fail_target_fsync_after_marker(path):
            nonlocal target_fsync_failed
            path = Path(path)
            if (
                path.name == "0001"
                and (path / ".complete").is_file()
                and not target_fsync_failed
            ):
                target_fsync_failed = True
                raise OSError("simulated target fsync failure")
            return original_fsync(path)

        with (
            mock.patch(
                "scripts.visual_qc.repair_case_library._fsync_directory",
                side_effect=fail_target_fsync_after_marker,
            ),
            mock.patch(
                "scripts.visual_qc.repair_case_library.shutil.rmtree",
                side_effect=OSError("simulated rollback removal failure"),
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "simulated target fsync failure",
            ):
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        target = (
            self.library / "cases" / case_id / "revisions" / "0001"
        )
        manifest_path = target / "repair-case.json"
        marker = target / ".complete"
        manifest_bytes = manifest_path.read_bytes()
        self.assertEqual(
            marker.read_bytes(),
            self.v3_completion_marker_bytes(manifest_bytes),
        )
        payload = json.loads(manifest_bytes.decode("utf-8"))
        evidence_object = (
            self.library / payload["supporting_evidence"][0]["object_path"]
        )
        object_bytes = evidence_object.read_bytes()
        target_resynced = False
        parent_resynced = False

        def probe_retry_fsync(path):
            nonlocal target_resynced, parent_resynced
            path = Path(path)
            if path.name == "0001":
                target_resynced = True
            elif path.name == "revisions":
                parent_resynced = True
            return original_fsync(path)

        with mock.patch(
            "scripts.visual_qc.repair_case_library._fsync_directory",
            side_effect=probe_retry_fsync,
        ):
            replayed = self.stage_f069_supporting_only(
                source=source,
                repair_case_id=case_id,
            )

        self.assertEqual(replayed["state"], "existing")
        self.assertTrue(target_resynced)
        self.assertTrue(parent_resynced)
        self.assertEqual(manifest_path.read_bytes(), manifest_bytes)
        self.assertEqual(evidence_object.read_bytes(), object_bytes)

    def test_completed_revision_replay_resyncs_and_never_overwrites(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "completed-replay.heic"
        write_heic(source, value=181)
        case_id = "case-f069-completed-replay"
        created = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        manifest_path = created["manifest_path"]
        target = manifest_path.parent
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        evidence_object = (
            self.library / payload["supporting_evidence"][0]["object_path"]
        )
        manifest_bytes = manifest_path.read_bytes()
        object_bytes = evidence_object.read_bytes()
        original_fsync = repair_case_library._fsync_directory
        fsynced = []

        def observe_fsync(path):
            path = Path(path)
            if path.name in {"0001", "revisions"}:
                fsynced.append(path.name)
            return original_fsync(path)

        with mock.patch(
            "scripts.visual_qc.repair_case_library._fsync_directory",
            side_effect=observe_fsync,
        ):
            replayed = self.stage_f069_supporting_only(
                source=source,
                repair_case_id=case_id,
            )
        self.assertEqual(replayed["state"], "existing")
        self.assertEqual(fsynced, ["0001", "revisions"])

        changed_record = copy.deepcopy(self.v3_supporting_only_record())
        changed_record["reported_symptoms"][0]["text"] = "Conflicting symptom"
        with self.assertRaisesRegex(IntakeValidationError, "conflict"):
            self.stage_f069_supporting_only(
                source=source,
                repair_case_id=case_id,
                case_record=changed_record,
            )
        self.assertEqual(
            (target / ".complete").read_bytes(),
            self.v3_completion_marker_bytes(manifest_bytes),
        )
        self.assertEqual(manifest_path.read_bytes(), manifest_bytes)
        self.assertEqual(evidence_object.read_bytes(), object_bytes)

    def test_publication_cleanup_retries_unlink_and_preserves_primary_error(self):
        source = self.root / "publication-cleanup-retry.heic"
        write_heic(source)
        baseline_objects = self.case_evidence_objects()
        case_id = "case-f069-supporting-cleanup-retry"
        original_unlink = Path.unlink
        cleanup_attempts = 0

        def fail_evidence_unlink_once(path, *args, **kwargs):
            nonlocal cleanup_attempts
            path = Path(path)
            if (
                "case-evidence" in path.parts
                and path.suffix == ".heic"
                and cleanup_attempts == 0
            ):
                cleanup_attempts += 1
                raise OSError("transient evidence unlink failure")
            return original_unlink(path, *args, **kwargs)

        with (
            mock.patch(
                "scripts.visual_qc.repair_case_library._write_completion_marker",
                side_effect=OSError("primary completion marker failure"),
            ),
            mock.patch.object(
                Path,
                "unlink",
                side_effect=fail_evidence_unlink_once,
                autospec=True,
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "primary completion marker failure",
            ) as raised:
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        self.assertEqual(cleanup_attempts, 1)
        self.assertIn(
            "transient evidence unlink failure",
            "\n".join(getattr(raised.exception, "__notes__", [])),
        )
        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_supporting_object_publication_follows_durable_residual_manifest(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "manifest-before-object.heic"
        write_heic(source)
        case_id = "case-f069-manifest-before-object"
        target = (
            self.library
            / "cases"
            / case_id
            / "revisions"
            / "0001"
        )
        original_store = repair_case_library.store_supporting_evidence
        observed = []

        def observe_store(**kwargs):
            observed.append(
                (
                    (target / "repair-case.json").is_file(),
                    (target / ".complete").exists(),
                )
            )
            return original_store(**kwargs)

        with mock.patch(
            "scripts.visual_qc.repair_case_library.store_supporting_evidence",
            side_effect=observe_store,
        ):
            created = self.stage_f069_supporting_only(
                source=source,
                repair_case_id=case_id,
            )

        self.assertEqual(created["state"], "created")
        self.assertEqual(observed, [(True, False)])

    def test_marker_free_manifest_recovers_missing_supporting_object(self):
        source = self.root / "recover-missing-object.heic"
        write_heic(source)
        case_id = "case-f069-recover-missing-object"
        created = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        manifest_path = created["manifest_path"]
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        object_path = self.library / payload["supporting_evidence"][0]["object_path"]

        (manifest_path.parent / ".complete").unlink()
        object_path.unlink()

        replayed = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )

        self.assertEqual(replayed["state"], "existing")
        self.assertTrue(object_path.is_file())
        self.assertTrue((manifest_path.parent / ".complete").is_file())
        self.assertEqual(
            hashlib.sha256(object_path.read_bytes()).hexdigest(),
            payload["supporting_evidence"][0]["sha256"],
        )

    def test_keyboard_interrupt_after_object_storage_rolls_back_revision_and_object(self):
        source = self.root / "interrupt-after-object.heic"
        write_heic(source)
        case_id = "case-f069-interrupt-after-object"
        baseline_objects = self.case_evidence_objects()

        with mock.patch(
            "scripts.visual_qc.repair_case_library._write_completion_marker",
            side_effect=KeyboardInterrupt("simulated operator interrupt"),
        ):
            with self.assertRaisesRegex(
                KeyboardInterrupt,
                "simulated operator interrupt",
            ):
                self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )

        self.assert_no_supporting_only_artifacts(case_id, baseline_objects)

    def test_cross_case_shared_object_publication_is_globally_serialized(self):
        from scripts.visual_qc import repair_case_library

        source = self.root / "shared-concurrent.heic"
        write_heic(source)
        original_lock = repair_case_library._package_lock
        original_store = repair_case_library.store_supporting_evidence
        original_marker = repair_case_library._write_completion_marker
        a_stored = threading.Event()
        release_a = threading.Event()
        b_global_requested = threading.Event()
        b_store_entered = threading.Event()
        outcomes = {}

        @contextmanager
        def observe_lock(lock_root, lock_id):
            if (
                threading.current_thread().name == "case-b"
                and lock_id
                == repair_case_library.CASE_EVIDENCE_PUBLICATION_LOCK_ID
            ):
                b_global_requested.set()
            with original_lock(lock_root, lock_id):
                yield

        def observe_store(**kwargs):
            if threading.current_thread().name == "case-b":
                b_store_entered.set()
            created = original_store(**kwargs)
            if threading.current_thread().name == "case-a":
                self.assertEqual(len(created), 1)
                self.assertTrue(created[0].is_file())
                a_stored.set()
            return created

        def controlled_marker(path):
            if threading.current_thread().name == "case-a":
                self.assertTrue(release_a.wait(timeout=10))
                raise OSError("simulated case A publication failure")
            return original_marker(path)

        def stage_case(case_id):
            try:
                outcomes[case_id] = self.stage_f069_supporting_only(
                    source=source,
                    repair_case_id=case_id,
                )
            except Exception as exc:
                outcomes[case_id] = exc

        with (
            mock.patch(
                "scripts.visual_qc.repair_case_library._package_lock",
                side_effect=observe_lock,
            ),
            mock.patch(
                "scripts.visual_qc.repair_case_library.store_supporting_evidence",
                side_effect=observe_store,
            ),
            mock.patch(
                "scripts.visual_qc.repair_case_library._write_completion_marker",
                side_effect=controlled_marker,
            ),
        ):
            case_a = threading.Thread(
                target=stage_case,
                args=("case-f069-concurrent-a",),
                name="case-a",
            )
            case_b = threading.Thread(
                target=stage_case,
                args=("case-f069-concurrent-b",),
                name="case-b",
            )
            case_a.start()
            self.assertTrue(a_stored.wait(timeout=10))
            case_b.start()
            global_requested = b_global_requested.wait(timeout=2)
            if global_requested:
                self.assertFalse(b_store_entered.is_set())
            release_a.set()
            case_a.join(timeout=10)
            case_b.join(timeout=10)

        self.assertFalse(case_a.is_alive())
        self.assertFalse(case_b.is_alive())
        self.assertTrue(global_requested)
        self.assertIsInstance(outcomes["case-f069-concurrent-a"], OSError)
        self.assertEqual(
            outcomes["case-f069-concurrent-b"]["state"],
            "created",
        )
        self.assert_no_supporting_only_artifacts(
            "case-f069-concurrent-a",
            self.case_evidence_objects(),
        )
        validated = validate_repair_case_revision(
            manifest_path=outcomes["case-f069-concurrent-b"]["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        self.assertEqual(validated["repair_case_id"], "case-f069-concurrent-b")

    def test_v2_requires_exact_catalog_model_order(self):
        valid = build_repair_case_revision(
            project_root=ROOT,
            library_root=self.library,
            repair_case_id="case-f069-order",
            board_key="bg6h-f069",
            package_assignments=[
                ("after_repair", self.f069_package()["source_package_path"])
            ],
            case_record=self.v2_case_record(self.exact_f069_identity()),
            supporting_assignments=[],
            previous_manifest_path=None,
        )
        self.assertEqual(
            valid["device_identity"]["catalog_models"],
            ["BG6H", "BG6h"],
        )

        mismatched = self.exact_f069_identity()
        mismatched["reported_models"] = ["BG6h", "BG6H"]
        mismatched["catalog_models"] = ["BG6h", "BG6H"]
        mismatched["resolved_models"] = ["BG6h", "BG6H"]
        with self.assertRaisesRegex(IntakeValidationError, "catalog_models"):
            self.stage_f069_case(
                repair_case_id="case-f069-order-mismatch",
                case_record=self.v2_case_record(mismatched),
            )

    def test_builder_rejects_present_malformed_catalog_models(self):
        malformed_values = (
            [],
            "",
            0,
            None,
            [""],
            ["   "],
            ["KM4", None],
            ["KM4", "KM4"],
        )
        for value in malformed_values:
            with self.subTest(compatible_models=value):
                with self.catalog_patch(
                    {"model": "KM4", "compatible_models": value}
                ):
                    with self.assertRaisesRegex(
                        IntakeValidationError,
                        "catalog compatible models",
                    ):
                        build_repair_case_revision(
                            project_root=ROOT,
                            library_root=self.library,
                            repair_case_id="case-km4-malformed-catalog",
                            board_key="km4-f151",
                            package_assignments=[
                                (
                                    "before_repair",
                                    self.before["source_package_path"],
                                )
                            ],
                            case_record=self.case_record(),
                            supporting_assignments=[],
                            previous_manifest_path=None,
                        )

        with self.catalog_patch({"model": "KM4"}):
            payload = build_repair_case_revision(
                project_root=ROOT,
                library_root=self.library,
                repair_case_id="case-km4-model-fallback",
                board_key="km4-f151",
                package_assignments=[
                    ("before_repair", self.before["source_package_path"])
                ],
                case_record=self.case_record(),
                supporting_assignments=[],
                previous_manifest_path=None,
            )
        self.assertEqual(payload["device_models"], ["KM4"])

        with self.catalog_patch({"model": ""}):
            with self.assertRaisesRegex(
                IntakeValidationError,
                "catalog compatible models",
            ):
                build_repair_case_revision(
                    project_root=ROOT,
                    library_root=self.library,
                    repair_case_id="case-km4-invalid-model-fallback",
                    board_key="km4-f151",
                    package_assignments=[
                        ("before_repair", self.before["source_package_path"])
                    ],
                    case_record=self.case_record(),
                    supporting_assignments=[],
                    previous_manifest_path=None,
                )

    def test_disk_validator_rejects_present_malformed_catalog_models(self):
        created = self.stage_case(repair_case_id="case-km4-disk-catalog")
        malformed_values = (
            [],
            "",
            0,
            None,
            [""],
            ["   "],
            ["KM4", None],
            ["KM4", "KM4"],
        )
        for value in malformed_values:
            with self.subTest(compatible_models=value):
                with self.catalog_patch(
                    {"model": "KM4", "compatible_models": value}
                ):
                    with self.assertRaisesRegex(
                        IntakeValidationError,
                        "catalog compatible models",
                    ):
                        validate_repair_case_revision(
                            manifest_path=created["manifest_path"],
                            project_root=ROOT,
                            library_root=self.library,
                        )

    def test_builder_normalizes_malformed_selected_catalog_entries(self):
        malformed_entries = (
            ["truthy-list"],
            "truthy-string",
            7,
            None,
        )
        for entry in malformed_entries:
            with self.subTest(entry=entry):
                with self.catalog_patch(entry):
                    with self.assertRaisesRegex(
                        IntakeValidationError,
                        "board catalog identity",
                    ):
                        build_repair_case_revision(
                            project_root=ROOT,
                            library_root=self.library,
                            repair_case_id="case-km4-malformed-entry",
                            board_key="km4-f151",
                            package_assignments=[
                                (
                                    "before_repair",
                                    self.before["source_package_path"],
                                )
                            ],
                            case_record=self.case_record(),
                            supporting_assignments=[],
                            previous_manifest_path=None,
                        )

    def test_disk_validator_normalizes_catalog_loading_and_indexing_errors(self):
        created = self.stage_case(repair_case_id="case-km4-catalog-structure")
        malformed_catalogs = (
            [],
            {},
            {"boards": []},
            {"boards": None},
            {"boards": {}},
            {"boards": "truthy-string"},
        )
        for catalog_data in malformed_catalogs:
            with self.subTest(catalog_data=catalog_data):
                with self.catalog_data_patch(catalog_data):
                    with self.assertRaisesRegex(
                        IntakeValidationError,
                        "board catalog identity",
                    ):
                        validate_repair_case_revision(
                            manifest_path=created["manifest_path"],
                            project_root=ROOT,
                            library_root=self.library,
                        )

        failure_modes = (
            {"construction_error": OSError("catalog unreadable")},
            {"resolution_error": KeyError("side_manifest")},
        )
        valid_catalog = {
            "boards": {
                "km4-f151": {
                    "model": "KM4",
                }
            }
        }
        for errors in failure_modes:
            with self.subTest(errors=errors):
                with self.catalog_data_patch(valid_catalog, **errors):
                    with self.assertRaisesRegex(
                        IntakeValidationError,
                        "board catalog identity",
                    ):
                        validate_repair_case_revision(
                            manifest_path=created["manifest_path"],
                            project_root=ROOT,
                            library_root=self.library,
                        )

    def test_identity_shape_errors_fail_before_cases_directory_creation(self):
        common = self.case_record()
        del common["device_models"]
        both = {
            **common,
            "device_models": ["BG6H"],
            "device_identity": self.exact_f069_identity(),
        }
        neither = dict(common)
        extra = {**common, "device_identity": self.exact_f069_identity(), "extra": 1}

        for record in (both, neither, extra):
            with self.subTest(fields=sorted(record)):
                with self.assertRaisesRegex(IntakeValidationError, "fields"):
                    self.stage_f069_case(case_record=record)
                self.assertFalse((self.library / "cases").exists())

    def test_v1_publication_shape_and_result_remain_unchanged(self):
        created = self.stage_case(repair_case_id="case-km4-v1-compat")
        payload = json.loads(created["manifest_path"].read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], REPAIR_CASE_SCHEMA_V1)
        self.assertEqual(payload["device_models"], ["KM4"])
        self.assertNotIn("device_identity", payload)
        self.assertEqual(payload["boundaries"], FIXED_FALSE_BOUNDARIES)
        self.assertEqual(
            list(payload).index("device_models"),
            list(payload).index("board_id") + 1,
        )
        self.assertEqual(created["schema_version"], REPAIR_CASE_SCHEMA_V1)
        self.assertEqual(created["identity_status"], "exact_catalog_match")

    def test_v1_to_v2_exact_migration_preserves_prior_bytes(self):
        first = self.stage_f069_case(
            case_record=self.case_record(device_models=["BG6H", "BG6h"])
        )
        prior_bytes = first["manifest_path"].read_bytes()
        prior_hash = first["manifest_sha256"]

        second = self.stage_f069_case(
            case_record=self.v2_case_record(self.exact_f069_identity()),
            previous_manifest_path=first["manifest_path"],
        )

        self.assertEqual(first["manifest_path"].read_bytes(), prior_bytes)
        self.assertEqual(hashlib.sha256(prior_bytes).hexdigest(), prior_hash)
        self.assertEqual(second["schema_version"], REPAIR_CASE_SCHEMA_V2)
        self.assertEqual(second["identity_status"], "exact_catalog_match")
        self.assertEqual(
            json.loads(second["manifest_path"].read_text(encoding="utf-8"))[
                "previous_manifest_sha256"
            ],
            prior_hash,
        )

    def test_v1_to_v2_rejects_unresolved_and_mismatched_models(self):
        first = self.stage_f069_case(
            case_record=self.case_record(device_models=["BG6H", "BG6h"])
        )
        evidence = self.root / "migration-identity.txt"
        evidence.write_text("Reported model: TECNO/BG6", encoding="utf-8")
        unresolved = self.v2_case_record(
            self.unresolved_f069_identity("migration-identity"),
            supporting_evidence_descriptions={
                "migration-identity": "Migration identity source"
            },
        )
        mismatched = self.exact_f069_identity()
        mismatched["reported_models"] = ["BG6H"]
        mismatched["resolved_models"] = ["BG6H"]

        with self.assertRaisesRegex(IntakeValidationError, "migration|exact"):
            self.stage_f069_case(
                case_record=unresolved,
                supporting=[("migration-identity", evidence)],
                previous_manifest_path=first["manifest_path"],
            )
        with self.assertRaisesRegex(IntakeValidationError, "migration|models"):
            self.stage_f069_case(
                case_record=self.v2_case_record(mismatched),
                previous_manifest_path=first["manifest_path"],
            )
        self.assertFalse(
            (first["manifest_path"].parents[1] / "0002").exists()
        )

    def test_v2_to_v1_is_rejected(self):
        first = self.stage_f069_case(
            case_record=self.v2_case_record(self.exact_f069_identity())
        )

        with self.assertRaisesRegex(IntakeValidationError, "V2.*V1|downgrade"):
            self.stage_f069_case(
                case_record=self.case_record(device_models=["BG6H", "BG6h"]),
                previous_manifest_path=first["manifest_path"],
            )

    def test_unresolved_confirmation_requires_appended_identity_evidence(self):
        first_source = self.root / "identity-first.txt"
        first_source.write_text("Reported model: TECNO/BG6", encoding="utf-8")
        first = self.stage_f069_case(
            case_record=self.v2_case_record(
                self.unresolved_f069_identity("identity-first"),
                supporting_evidence_descriptions={
                    "identity-first": "Initial identity source"
                },
            ),
            supporting=[("identity-first", first_source)],
        )

        with self.assertRaisesRegex(IntakeValidationError, "new evidence"):
            self.stage_f069_case(
                case_record=self.v2_case_record(
                    self.confirmed_f069_identity("identity-first")
                ),
                previous_manifest_path=first["manifest_path"],
            )

        second_source = self.root / "identity-second.txt"
        second_source.write_text("Confirmed alias: BG6H", encoding="utf-8")
        confirmed = self.stage_f069_case(
            case_record=self.v2_case_record(
                self.confirmed_f069_identity(
                    "identity-first",
                    "identity-second",
                ),
                supporting_evidence_descriptions={
                    "identity-second": "Appended identity confirmation"
                },
            ),
            supporting=[("identity-second", second_source)],
            previous_manifest_path=first["manifest_path"],
        )
        self.assertEqual(confirmed["identity_status"], "confirmed_alias")

    def test_conflict_confirmation_requires_appended_correction_and_evidence(self):
        first_source = self.root / "conflict-first.txt"
        first_source.write_text("Conflicting model: TECNO/BG6", encoding="utf-8")
        conflict_identity = self.unresolved_f069_identity("conflict-first")
        conflict_identity["mapping_status"] = "conflict"
        symptoms = [
            {
                "symptom_id": "symptom-old",
                "text": "Initial report.",
                "source_wording": None,
                "fault_code": None,
                "evidence_refs": [],
            },
            {
                "symptom_id": "symptom-new",
                "text": "Corrected report.",
                "source_wording": None,
                "fault_code": None,
                "evidence_refs": [],
            },
            {
                "symptom_id": "symptom-identity",
                "text": "Identity-confirmed report.",
                "source_wording": None,
                "fault_code": None,
                "evidence_refs": [],
            },
        ]
        historical_correction = {
            "correction_id": "correction-old",
            "corrects_fact_id": "symptom-old",
            "description": "Historical non-identity correction.",
            "replacement_fact_id": "symptom-new",
            "evidence_refs": [],
        }
        first = self.stage_f069_case(
            case_record=self.v2_case_record(
                conflict_identity,
                supporting_evidence_descriptions={
                    "conflict-first": "Initial conflicting identity source"
                },
                reported_symptoms=symptoms,
                corrections=[historical_correction],
            ),
            supporting=[("conflict-first", first_source)],
        )
        second_source = self.root / "conflict-second.txt"
        second_source.write_text("Confirmed alias: BG6H", encoding="utf-8")
        confirmation_record = self.v2_case_record(
            self.confirmed_f069_identity(
                "conflict-first",
                "conflict-second",
            ),
            supporting_evidence_descriptions={
                "conflict-second": "Appended identity confirmation"
            },
            reported_symptoms=symptoms,
            corrections=[historical_correction],
        )

        with self.assertRaisesRegex(IntakeValidationError, "new correction"):
            self.stage_f069_case(
                case_record=confirmation_record,
                supporting=[("conflict-second", second_source)],
                previous_manifest_path=first["manifest_path"],
            )

        appended = dict(historical_correction)
        appended.update(
            correction_id="correction-identity",
            corrects_fact_id="symptom-new",
            description="Correct the conflicting model identity.",
            replacement_fact_id="symptom-identity",
        )
        confirmation_record["corrections"] = [historical_correction, appended]
        confirmed = self.stage_f069_case(
            case_record=confirmation_record,
            supporting=[("conflict-second", second_source)],
            previous_manifest_path=first["manifest_path"],
        )
        self.assertEqual(confirmed["identity_status"], "confirmed_alias")

    def test_identity_transition_rejects_new_citation_to_old_evidence_target(self):
        case_id = "case-f069-old-evidence-stage"
        first, symptoms, historical, appended = (
            self.conflict_transition_fixture(case_id)
        )
        stale_evidence_record = self.v2_case_record(
            self.confirmed_f069_identity(
                "identity-first",
                "identity-unused",
            ),
            reported_symptoms=symptoms,
            corrections=[historical, appended],
        )

        with self.assertRaisesRegex(
            IntakeValidationError,
            "newly published identity evidence",
        ):
            self.stage_f069_case(
                repair_case_id=case_id,
                case_record=stale_evidence_record,
                previous_manifest_path=first["manifest_path"],
            )

        self.assertFalse(
            (first["manifest_path"].parents[1] / "0002").exists()
        )

    def test_disk_validator_rejects_new_citation_to_old_evidence_target(self):
        case_id = "case-f069-old-evidence-disk"
        first, symptoms, historical, appended = (
            self.conflict_transition_fixture(case_id)
        )
        new_source = self.root / "genuinely-new-identity.txt"
        new_source.write_text("Confirmed alias: BG6H", encoding="utf-8")
        second = self.stage_f069_case(
            repair_case_id=case_id,
            case_record=self.v2_case_record(
                self.confirmed_f069_identity(
                    "identity-first",
                    "identity-new",
                ),
                supporting_evidence_descriptions={
                    "identity-new": "Newly published identity confirmation"
                },
                reported_symptoms=symptoms,
                corrections=[historical, appended],
            ),
            supporting=[("identity-new", new_source)],
            previous_manifest_path=first["manifest_path"],
        )
        payload = json.loads(
            second["manifest_path"].read_text(encoding="utf-8")
        )
        payload["device_identity"]["evidence_refs"][-1] = (
            self.identity_reference("identity-unused")
        )
        second["manifest_path"].write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            IntakeValidationError,
            "newly published identity evidence",
        ):
            validate_repair_case_revision(
                manifest_path=second["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )

    def test_disk_validator_accepts_v2_and_mixed_revision_chains(self):
        v2 = self.stage_f069_case(
            repair_case_id="case-f069-v2-disk",
            case_record=self.v2_case_record(self.exact_f069_identity()),
        )
        self.assertEqual(
            validate_repair_case_revision(
                manifest_path=v2["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )["schema_version"],
            REPAIR_CASE_SCHEMA_V2,
        )

        first = self.stage_f069_case(
            repair_case_id="case-f069-mixed-disk",
            case_record=self.case_record(device_models=["BG6H", "BG6h"]),
        )
        second = self.stage_f069_case(
            repair_case_id="case-f069-mixed-disk",
            case_record=self.v2_case_record(self.exact_f069_identity()),
            previous_manifest_path=first["manifest_path"],
        )
        validated = validate_repair_case_revision(
            manifest_path=second["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        self.assertEqual(validated["revision"], 2)
        self.assertEqual(validated["schema_version"], REPAIR_CASE_SCHEMA_V2)

    def test_supporting_only_mode_is_immutable_across_v3_revisions(self):
        source = self.root / "immutable-mode.heic"
        write_heic(source, value=131)
        case_id = "case-f069-v3-immutable-mode"
        first = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        manifest_bytes = first["manifest_path"].read_bytes()
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        payload = json.loads(manifest_bytes.decode("utf-8"))
        evidence_path = self.library / payload["supporting_evidence"][0]["object_path"]
        evidence_bytes = evidence_path.read_bytes()
        evidence_sha256 = hashlib.sha256(evidence_bytes).hexdigest()
        package_linked = copy.deepcopy(self.v3_supporting_only_record())
        package_linked["evidence_mode"] = "package_linked"
        package_linked["supporting_evidence_descriptions"] = {}

        with self.assertRaisesRegex(IntakeValidationError, "evidence mode"):
            self.stage_f069_supporting_only(
                source=source,
                repair_case_id=case_id,
                case_record=package_linked,
                package_assignments=[
                    ("after_repair", self.f069_package()["source_package_path"])
                ],
                supporting_assignments=[],
                previous_manifest_path=first["manifest_path"],
            )

        self.assertFalse((first["manifest_path"].parents[1] / "0002").exists())
        self.assertEqual(first["manifest_path"].read_bytes(), manifest_bytes)
        self.assertEqual(
            hashlib.sha256(first["manifest_path"].read_bytes()).hexdigest(),
            manifest_sha256,
        )
        self.assertEqual(evidence_path.read_bytes(), evidence_bytes)
        self.assertEqual(
            hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            evidence_sha256,
        )

    def test_disk_validator_skips_package_resolution_for_supporting_only(self):
        source = self.root / "disk-supporting-only.heic"
        write_heic(source, value=132)
        created = self.stage_f069_supporting_only(source=source)

        with mock.patch(
            "scripts.visual_qc.repair_case_library.resolve_package_links",
            side_effect=AssertionError("package resolution must be skipped"),
        ) as resolver:
            validated = validate_repair_case_revision(
                manifest_path=created["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )

        resolver.assert_not_called()
        self.assertEqual(validated["package_links"], [])
        self.assertEqual(validated["evidence_mode"], "supporting_only")

    def test_v1_v2_to_v3_require_package_linked(self):
        for prior_version in (REPAIR_CASE_SCHEMA_V1, REPAIR_CASE_SCHEMA_V2):
            with self.subTest(prior_version=prior_version):
                case_id = f"case-f069-{prior_version[-2:].lower()}-to-v3"
                prior_record = (
                    self.case_record(device_models=["BG6H", "BG6h"])
                    if prior_version == REPAIR_CASE_SCHEMA_V1
                    else self.v2_case_record(self.exact_f069_identity())
                )
                first = self.stage_f069_case(
                    repair_case_id=case_id,
                    case_record=prior_record,
                )
                prior_bytes = first["manifest_path"].read_bytes()
                prior_sha256 = hashlib.sha256(prior_bytes).hexdigest()
                source = self.root / f"{case_id}.heic"
                write_heic(source, value=133)
                baseline_objects = self.case_evidence_objects()

                with self.assertRaisesRegex(
                    IntakeValidationError,
                    "package_linked|evidence mode",
                ):
                    self.stage_f069_supporting_only(
                        source=source,
                        repair_case_id=case_id,
                        previous_manifest_path=first["manifest_path"],
                    )

                self.assertFalse(
                    (first["manifest_path"].parents[1] / "0002").exists()
                )
                self.assertEqual(first["manifest_path"].read_bytes(), prior_bytes)
                self.assertEqual(
                    hashlib.sha256(first["manifest_path"].read_bytes()).hexdigest(),
                    prior_sha256,
                )
                self.assertEqual(self.case_evidence_objects(), baseline_objects)

                upgraded = self.stage_f069_case(
                    repair_case_id=case_id,
                    case_record={
                        **self.v2_case_record(self.exact_f069_identity()),
                        "evidence_mode": "package_linked",
                        "supporting_evidence_contexts": [],
                    },
                    previous_manifest_path=first["manifest_path"],
                )
                self.assertEqual(upgraded["schema_version"], REPAIR_CASE_SCHEMA_V3)
                self.assertEqual(upgraded["evidence_mode"], "package_linked")
                self.assertEqual(first["manifest_path"].read_bytes(), prior_bytes)

    def test_v3_cannot_downgrade(self):
        case_id = "case-f069-v3-no-downgrade"
        first = self.stage_f069_case(
            repair_case_id=case_id,
            case_record={
                **self.v2_case_record(self.exact_f069_identity()),
                "evidence_mode": "package_linked",
                "supporting_evidence_contexts": [],
            },
        )
        prior_bytes = first["manifest_path"].read_bytes()
        prior_sha256 = hashlib.sha256(prior_bytes).hexdigest()

        with self.assertRaisesRegex(
            IntakeValidationError,
            "V3 repair case downgrade is not allowed",
        ):
            self.stage_f069_case(
                repair_case_id=case_id,
                case_record=self.v2_case_record(
                    self.exact_f069_identity(),
                    reported_symptoms=[
                        {
                            "symptom_id": "symptom-new",
                            "text": "New source context.",
                            "source_wording": None,
                            "fault_code": None,
                            "evidence_refs": [],
                        }
                    ],
                ),
                previous_manifest_path=first["manifest_path"],
            )

        self.assertFalse((first["manifest_path"].parents[1] / "0002").exists())
        self.assertEqual(first["manifest_path"].read_bytes(), prior_bytes)
        self.assertEqual(
            hashlib.sha256(first["manifest_path"].read_bytes()).hexdigest(),
            prior_sha256,
        )

    def test_v3_contexts_are_append_only(self):
        source = self.root / "context-first.heic"
        appended_source = self.root / "context-second.heic"
        write_heic(source, value=134)
        write_heic(appended_source, value=135)
        case_id = "case-f069-v3-context-prefix"
        first = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        prior_bytes = first["manifest_path"].read_bytes()
        prior_sha256 = hashlib.sha256(prior_bytes).hexdigest()
        payload = json.loads(prior_bytes.decode("utf-8"))
        evidence_path = self.library / payload["supporting_evidence"][0]["object_path"]
        evidence_bytes = evidence_path.read_bytes()
        evidence_sha256 = hashlib.sha256(evidence_bytes).hexdigest()
        baseline_objects = self.case_evidence_objects()
        revised = copy.deepcopy(self.v3_supporting_only_record())
        revised["supporting_evidence_contexts"][0]["source_board_area"] = (
            "改写后的区域"
        )
        revised["supporting_evidence_contexts"].append(
            {
                "evidence_id": "repair-photo-2",
                "evidence_role": "repair_in_progress_photo",
                "source_capture_stage": "维修中",
                "source_board_area": "主板局部",
            }
        )
        revised["supporting_evidence_descriptions"] = {
            "repair-photo-2": "Second repair-in-progress photograph"
        }

        with self.assertRaisesRegex(
            IntakeValidationError,
            "historical supporting evidence contexts",
        ):
            self.stage_f069_supporting_only(
                source=appended_source,
                repair_case_id=case_id,
                case_record=revised,
                supporting_assignments=[("repair-photo-2", appended_source)],
                previous_manifest_path=first["manifest_path"],
            )

        self.assertFalse((first["manifest_path"].parents[1] / "0002").exists())
        self.assertEqual(first["manifest_path"].read_bytes(), prior_bytes)
        self.assertEqual(evidence_path.read_bytes(), evidence_bytes)
        self.assertEqual(
            hashlib.sha256(first["manifest_path"].read_bytes()).hexdigest(),
            prior_sha256,
        )
        self.assertEqual(
            hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            evidence_sha256,
        )
        self.assertEqual(self.case_evidence_objects(), baseline_objects)

    def test_v3_cannot_rewrite_mode_heic_or_context_wording(self):
        source = self.root / "rewrite-history.heic"
        write_heic(source, value=136)
        case_id = "case-f069-v3-rewrite-history"
        first = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        manifest_path = first["manifest_path"]
        manifest_bytes = manifest_path.read_bytes()
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        payload = json.loads(manifest_bytes.decode("utf-8"))
        evidence_path = self.library / payload["supporting_evidence"][0]["object_path"]
        evidence_bytes = evidence_path.read_bytes()
        evidence_sha256 = hashlib.sha256(evidence_bytes).hexdigest()

        for field, value, error in (
            ("evidence_mode", "package_linked", "evidence mode"),
            (
                "supporting_evidence_contexts",
                [
                    {
                        **payload["supporting_evidence_contexts"][0],
                        "source_capture_stage": "改写阶段",
                    }
                ],
                "supporting evidence contexts",
            ),
        ):
            with self.subTest(field=field):
                baseline_objects = self.case_evidence_objects()
                changed = copy.deepcopy(self.v3_supporting_only_record())
                changed[field] = value
                changed["supporting_evidence_descriptions"] = {}
                supporting_assignments = []
                if field == "supporting_evidence_contexts":
                    appended_source = self.root / "rewrite-context-appended.heic"
                    write_heic(appended_source, value=137)
                    changed["supporting_evidence_contexts"].append(
                        {
                            "evidence_id": "repair-photo-2",
                            "evidence_role": "repair_in_progress_photo",
                            "source_capture_stage": "维修中",
                            "source_board_area": "主板局部",
                        }
                    )
                    changed["supporting_evidence_descriptions"] = {
                        "repair-photo-2": "Appended repair photograph"
                    }
                    supporting_assignments = [
                        ("repair-photo-2", appended_source)
                    ]
                with self.assertRaisesRegex(IntakeValidationError, error):
                    self.stage_f069_supporting_only(
                        source=source,
                        repair_case_id=case_id,
                        case_record=changed,
                        package_assignments=(
                            [
                                (
                                    "after_repair",
                                    self.f069_package()["source_package_path"],
                                )
                            ]
                            if field == "evidence_mode"
                            else []
                        ),
                        supporting_assignments=supporting_assignments,
                        previous_manifest_path=manifest_path,
                    )
                self.assertFalse((manifest_path.parents[1] / "0002").exists())
                self.assertEqual(manifest_path.read_bytes(), manifest_bytes)
                self.assertEqual(evidence_path.read_bytes(), evidence_bytes)
                self.assertEqual(self.case_evidence_objects(), baseline_objects)

        tampered = bytearray(evidence_bytes)
        tampered[-1] ^= 1
        evidence_path.write_bytes(tampered)
        with self.assertRaisesRegex(IntakeValidationError, "integrity mismatch"):
            validate_repair_case_revision(
                manifest_path=manifest_path,
                project_root=ROOT,
                library_root=self.library,
            )
        evidence_path.write_bytes(evidence_bytes)
        self.assertEqual(
            hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            manifest_sha256,
        )
        self.assertEqual(
            hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            evidence_sha256,
        )

    def test_v3_revision_preparation_cannot_replace_historical_heic(self):
        source = self.root / "historical-heic.heic"
        replacement = self.root / "historical-heic-replacement.heic"
        write_heic(source, value=141)
        write_heic(replacement, value=142)
        case_id = "case-f069-v3-historical-heic"
        first = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        manifest_bytes = first["manifest_path"].read_bytes()
        payload = json.loads(manifest_bytes.decode("utf-8"))
        historical_path = (
            self.library / payload["supporting_evidence"][0]["object_path"]
        )
        historical_bytes = historical_path.read_bytes()
        inspected = inspect_supporting_evidence(
            [("repair-photo", replacement)],
            {"repair-photo": "Replacement repair photograph"},
            schema_version=REPAIR_CASE_SCHEMA_V3,
        )
        replacement_path = (
            self.library / inspected[0]["record"]["object_path"]
        )
        self.assertNotEqual(replacement_path, historical_path)
        self.assertFalse(replacement_path.exists())
        baseline_objects = self.case_evidence_objects()

        with self.assertRaisesRegex(
            IntakeValidationError,
            "duplicates a historical evidence_id|historical supporting evidence",
        ):
            self.stage_f069_supporting_only(
                source=replacement,
                repair_case_id=case_id,
                case_record=self.v3_supporting_only_record(
                    supporting_evidence_descriptions={
                        "repair-photo": "Replacement repair photograph"
                    }
                ),
                supporting_assignments=[("repair-photo", replacement)],
                previous_manifest_path=first["manifest_path"],
            )

        self.assertFalse((first["manifest_path"].parents[1] / "0002").exists())
        self.assertFalse(replacement_path.exists())
        self.assertEqual(self.case_evidence_objects(), baseline_objects)
        self.assertEqual(first["manifest_path"].read_bytes(), manifest_bytes)
        self.assertEqual(historical_path.read_bytes(), historical_bytes)

    def test_v3_new_context_requires_consistent_appended_evidence(self):
        source = self.root / "consistent-context.jpg"
        source.write_bytes(encode_image(".jpg", value=137))
        case_id = "case-f069-v3-consistent-context"
        first_record = {
            **self.v2_case_record(
                self.exact_f069_identity(),
                supporting_evidence_descriptions={
                    "historical-note": "Historical supporting evidence"
                },
            ),
            "evidence_mode": "package_linked",
            "supporting_evidence_contexts": [],
        }
        first = self.stage_f069_case(
            repair_case_id=case_id,
            case_record=first_record,
            supporting=[("historical-note", source)],
        )
        prior_bytes = first["manifest_path"].read_bytes()
        prior_sha256 = hashlib.sha256(prior_bytes).hexdigest()
        payload = json.loads(prior_bytes.decode("utf-8"))
        evidence_path = self.library / payload["supporting_evidence"][0]["object_path"]
        evidence_bytes = evidence_path.read_bytes()
        evidence_sha256 = hashlib.sha256(evidence_bytes).hexdigest()
        changed = copy.deepcopy(first_record)
        changed["supporting_evidence_descriptions"] = {}
        changed["supporting_evidence_contexts"] = [
            {
                "evidence_id": "historical-note",
                "evidence_role": "repair_in_progress_photo",
                "source_capture_stage": "维修中",
                "source_board_area": "主板局部",
            }
        ]

        with self.assertRaisesRegex(
            IntakeValidationError,
            "new supporting evidence context.*appended evidence",
        ):
            self.stage_f069_case(
                repair_case_id=case_id,
                case_record=changed,
                supporting_assignments=[],
                previous_manifest_path=first["manifest_path"],
            )

        self.assertFalse((first["manifest_path"].parents[1] / "0002").exists())
        self.assertEqual(first["manifest_path"].read_bytes(), prior_bytes)
        self.assertEqual(evidence_path.read_bytes(), evidence_bytes)
        self.assertEqual(
            hashlib.sha256(first["manifest_path"].read_bytes()).hexdigest(),
            prior_sha256,
        )
        self.assertEqual(
            hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            evidence_sha256,
        )

    def test_v3_disk_validation_rejects_changed_object_context_or_manifest(self):
        source = self.root / "disk-history-first.heic"
        appended_source = self.root / "disk-history-second.heic"
        write_heic(source, value=138)
        write_heic(appended_source, value=139)
        case_id = "case-f069-v3-disk-history"
        first = self.stage_f069_supporting_only(
            source=source,
            repair_case_id=case_id,
        )
        revised = copy.deepcopy(self.v3_supporting_only_record())
        revised["supporting_evidence_contexts"].append(
            {
                "evidence_id": "repair-photo-2",
                "evidence_role": "repair_in_progress_photo",
                "source_capture_stage": "维修中",
                "source_board_area": "主板局部",
            }
        )
        revised["supporting_evidence_descriptions"] = {
            "repair-photo-2": "Second repair-in-progress photograph"
        }
        second = self.stage_f069_supporting_only(
            source=appended_source,
            repair_case_id=case_id,
            case_record=revised,
            supporting_assignments=[("repair-photo-2", appended_source)],
            previous_manifest_path=first["manifest_path"],
        )
        first_bytes = first["manifest_path"].read_bytes()
        second_bytes = second["manifest_path"].read_bytes()
        first_sha256 = hashlib.sha256(first_bytes).hexdigest()
        second_sha256 = hashlib.sha256(second_bytes).hexdigest()
        second_payload = json.loads(second_bytes.decode("utf-8"))
        object_path = (
            self.library
            / second_payload["supporting_evidence"][1]["object_path"]
        )
        object_bytes = object_path.read_bytes()
        object_sha256 = hashlib.sha256(object_bytes).hexdigest()

        object_path.write_bytes(object_bytes + b"tamper")
        with self.assertRaisesRegex(IntakeValidationError, "integrity mismatch"):
            validate_repair_case_revision(
                manifest_path=second["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )
        object_path.write_bytes(object_bytes)

        for mutation, error in (
            (
                lambda value: value["supporting_evidence_contexts"][0].update(
                    source_board_area="改写区域"
                ),
                "completion marker|manifest SHA-256",
            ),
            (
                lambda value: value.update(
                    evidence_mode="package_linked",
                    package_links=resolve_package_links(
                        project_root=ROOT,
                        library_root=self.library,
                        assignments=[
                            (
                                "after_repair",
                                self.f069_package()["source_package_path"],
                            )
                        ],
                        board_key="bg6h-f069",
                    ),
                ),
                "completion marker|manifest SHA-256",
            ),
        ):
            with self.subTest(error=error):
                changed_payload = json.loads(second_bytes.decode("utf-8"))
                mutation(changed_payload)
                try:
                    second["manifest_path"].write_bytes(
                        (json.dumps(changed_payload, indent=2) + "\n").encode(
                            "utf-8"
                        )
                    )
                    with self.assertRaisesRegex(IntakeValidationError, error):
                        validate_repair_case_revision(
                            manifest_path=second["manifest_path"],
                            project_root=ROOT,
                            library_root=self.library,
                        )
                finally:
                    second["manifest_path"].write_bytes(second_bytes)

        self.assertEqual(first["manifest_path"].read_bytes(), first_bytes)
        self.assertEqual(second["manifest_path"].read_bytes(), second_bytes)
        self.assertEqual(object_path.read_bytes(), object_bytes)
        self.assertEqual(
            hashlib.sha256(first["manifest_path"].read_bytes()).hexdigest(),
            first_sha256,
        )
        self.assertEqual(
            hashlib.sha256(second["manifest_path"].read_bytes()).hexdigest(),
            second_sha256,
        )
        self.assertEqual(
            hashlib.sha256(object_path.read_bytes()).hexdigest(),
            object_sha256,
        )

    def test_disk_validator_rejects_tampered_v2_identity_boundary_and_catalog(self):
        mutators = {
            "identity": lambda payload: payload["device_identity"].update(
                mapping_status="unresolved_alias",
                resolved_models=[],
                evidence_refs=[],
            ),
            "boundary": lambda payload: payload["boundaries"].update(
                model_identity_resolved=False
            ),
            "catalog": lambda payload: payload["device_identity"].update(
                catalog_models=["BG6h", "BG6H"]
            ),
        }
        for label, mutate in mutators.items():
            with self.subTest(label=label):
                created = self.stage_f069_case(
                    repair_case_id=f"case-f069-tampered-{label}",
                    case_record=self.v2_case_record(self.exact_f069_identity()),
                )
                payload = json.loads(
                    created["manifest_path"].read_text(encoding="utf-8")
                )
                mutate(payload)
                created["manifest_path"].write_text(
                    json.dumps(payload, indent=2) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaises(IntakeValidationError):
                    validate_repair_case_revision(
                        manifest_path=created["manifest_path"],
                        project_root=ROOT,
                        library_root=self.library,
                    )

    def test_disk_validator_rejects_nonstring_board_key_as_validation_error(self):
        created = self.stage_case(repair_case_id="case-km4-board-key-tamper")
        original = json.loads(
            created["manifest_path"].read_text(encoding="utf-8")
        )
        for board_key in (["km4-f151"], {"key": "km4-f151"}, 7, None):
            with self.subTest(board_key=board_key):
                payload = dict(original)
                payload["board_key"] = board_key
                created["manifest_path"].write_text(
                    json.dumps(payload, indent=2) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    IntakeValidationError,
                    "board_key",
                ):
                    validate_repair_case_revision(
                        manifest_path=created["manifest_path"],
                        project_root=ROOT,
                        library_root=self.library,
                    )

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

    def test_failed_publication_leaves_no_revision(self):
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
        self.assertFalse((revision_root / "0001").exists())
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

    def test_preexisting_case_root_link_is_rejected_before_external_write(self):
        external_case = self.root / "external-case"
        case_root = (
            self.library / "cases" / "case-km4-prelinked"
        )
        self.create_directory_link(case_root, external_case)

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink"):
            self.stage_case(repair_case_id="case-km4-prelinked")

        self.assertFalse((external_case / "revisions").exists())

    def test_preexisting_cases_root_link_is_rejected_before_external_write(self):
        external_cases = self.root / "external-cases"
        cases_root = self.library / "cases"
        self.create_directory_link(cases_root, external_cases)

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink"):
            self.stage_case(repair_case_id="case-km4-linked-cases")

        self.assertEqual(list(external_cases.iterdir()), [])

    def test_preexisting_revisions_link_is_rejected_before_external_write(self):
        external_revisions = self.root / "external-revisions"
        revisions_root = (
            self.library
            / "cases"
            / "case-km4-linked-revisions"
            / "revisions"
        )
        self.create_directory_link(revisions_root, external_revisions)

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink"):
            self.stage_case(repair_case_id="case-km4-linked-revisions")

        self.assertEqual(list(external_revisions.iterdir()), [])

    def test_known_outcome_cannot_be_rewritten_by_a_later_revision(self):
        completed = self.case_record(
            outcome={
                "status": "repair_completed",
                "description": "Phone powered on after repair.",
                "verification_description": "Power-on test passed.",
                "evidence_refs": [],
            }
        )
        first = self.stage_case(case_record=completed)
        rewritten = self.case_record(
            reported_symptoms=[
                {
                    "symptom_id": "symptom-1",
                    "text": "Phone does not power on.",
                    "source_wording": None,
                    "fault_code": None,
                    "evidence_refs": [],
                }
            ],
            outcome={
                "status": "not_repaired",
                "description": "Repair did not restore power.",
                "verification_description": None,
                "evidence_refs": [],
            },
        )

        with self.assertRaisesRegex(IntakeValidationError, "historical outcome"):
            self.stage_case(
                case_record=rewritten,
                previous_manifest_path=first["manifest_path"],
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
