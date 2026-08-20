from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image
from pillow_heif import from_pillow

from scripts.visual_qc.source_library import stage_source_package
from scripts.visual_qc.repair_case_contract import (
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
    REPAIR_CASE_SCHEMA_V3,
)


ROOT = Path(__file__).resolve().parents[1]


def encode_image():
    image = np.full((120, 180, 3), 125, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Unable to encode test image.")
    return encoded.tobytes()


def write_heic(path, width=180, height=120, value=120):
    image = Image.new("RGB", (width, height), (value, value, value))
    from_pillow(image).save(path, quality=90)


class StageVisualQcRepairCaseCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="visual-qc-repair-case-cli-"
        )
        self.root = Path(self.temporary.name)
        self.library = self.root / "controlled-library"
        self.image = self.root / "before.jpg"
        self.image.write_bytes(encode_image())
        self.package = stage_source_package(
            project_root=ROOT,
            library_root=self.library,
            package_id="pkg-before",
            batch_id="batch-before",
            board_key="km4-f151",
            capture_session_id="session-before",
            capture_stage="before_repair",
            capture_setup_id="standard-bench",
            image_assignments=[("main_page_1", self.image)],
            milo_physical_source_confirmed=True,
            capture_checklist_confirmed=True,
        )
        self.case_record = self.root / "case-record.json"
        self.case_record.write_text(
            json.dumps(
                {
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
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.script = ROOT / "scripts" / "stage_visual_qc_repair_case.py"

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, *extra):
        return [
            sys.executable,
            str(self.script),
            "--library-root",
            str(self.library),
            "--repair-case-id",
            "case-km4-cli-0001",
            "--board-key",
            "km4-f151",
            "--case-record",
            str(self.case_record),
            "--source-package",
            f"before_repair={self.package['source_package_path']}",
            *extra,
        ]

    def run_cli(self, *extra):
        return subprocess.run(
            self.command(*extra),
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def supporting_only_record(self, **overrides):
        record = {
            "device_identity": {
                "reported_models": ["TECNO/BG6"],
                "catalog_models": ["BG6H", "BG6h"],
                "mapping_status": "unresolved_alias",
                "resolved_models": [],
                "resolution_note": None,
                "evidence_refs": [
                    {
                        "kind": "supporting_evidence",
                        "evidence_id": "repair-photo",
                    }
                ],
            },
            "evidence_mode": "supporting_only",
            "supporting_evidence_contexts": [
                {
                    "evidence_id": "repair-photo",
                    "evidence_role": "repair_in_progress_photo",
                    "source_capture_stage": "维修中",
                    "source_board_area": "屏蔽罩内局部",
                }
            ],
            "supporting_evidence_descriptions": {
                "repair-photo": "Milo supplied repair-in-progress photograph"
            },
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

    def supporting_only_command(self, photo):
        self.case_record.write_text(
            json.dumps(self.supporting_only_record(), ensure_ascii=False),
            encoding="utf-8",
        )
        return [
            sys.executable,
            str(self.script),
            "--library-root",
            str(self.library),
            "--repair-case-id",
            "case-f069-supporting-only-cli",
            "--board-key",
            "bg6h-f069",
            "--case-record",
            str(self.case_record),
            "--supporting-file",
            f"repair-photo={photo}",
        ]

    def run_command(self, command):
        return subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def case_evidence_objects(self):
        root = self.library / "objects" / "case-evidence"
        return (
            {
                (
                    path.relative_to(self.library),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
                for path in root.rglob("*")
                if path.is_file()
            }
            if root.exists()
            else set()
        )

    def test_direct_invocation_creates_then_replays_exact_case(self):
        created = self.run_cli()

        self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
        payload = json.loads(created.stdout)
        self.assertEqual(
            set(payload),
            {
                "status",
                "state",
                "repair_case_id",
                "revision",
                "schema_version",
                "evidence_mode",
                "identity_status",
                "completeness",
                "manifest_sha256",
                "manifest_path",
                "package_count",
                "supporting_evidence_count",
            },
        )
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["state"], "created")
        self.assertEqual(payload["repair_case_id"], "case-km4-cli-0001")
        self.assertEqual(payload["revision"], 1)
        self.assertEqual(payload["schema_version"], REPAIR_CASE_SCHEMA_V1)
        self.assertEqual(payload["evidence_mode"], "package_linked")
        self.assertEqual(payload["package_count"], 1)
        self.assertEqual(payload["supporting_evidence_count"], 0)
        self.assertEqual(payload["identity_status"], "exact_catalog_match")
        self.assertEqual(payload["completeness"], "photos_only")
        self.assertEqual(len(payload["manifest_sha256"]), 64)
        self.assertTrue(Path(payload["manifest_path"]).is_file())
        self.assertEqual(created.stderr, "")

        replayed = self.run_cli()
        self.assertEqual(replayed.returncode, 0, replayed.stdout)
        replayed_payload = json.loads(replayed.stdout)
        self.assertEqual(replayed_payload["state"], "existing")
        self.assertEqual(
            replayed_payload["manifest_sha256"],
            payload["manifest_sha256"],
        )
        self.assertEqual(
            replayed_payload["schema_version"],
            REPAIR_CASE_SCHEMA_V1,
        )
        self.assertEqual(
            replayed_payload["identity_status"],
            "exact_catalog_match",
        )
        self.assertEqual(replayed.stderr, "")

    def test_direct_v3_supporting_only_heic_creates_then_replays_exact_case(self):
        photo = self.root / "repair-progress.heic"
        write_heic(photo, value=145)
        photo_sha256 = hashlib.sha256(photo.read_bytes()).hexdigest()
        command = self.supporting_only_command(photo)

        created = self.run_command(command)
        replayed = self.run_command(command)

        self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
        self.assertEqual(replayed.returncode, 0, replayed.stderr or replayed.stdout)
        self.assertEqual(created.stderr, "")
        self.assertEqual(replayed.stderr, "")
        created_payload = json.loads(created.stdout)
        replayed_payload = json.loads(replayed.stdout)
        expected_manifest_path = str(
            (
                self.library
                / "cases"
                / "case-f069-supporting-only-cli"
                / "revisions"
                / "0001"
                / "repair-case.json"
            ).resolve()
        )
        expected_receipt = {
            "status": "ok",
            "state": "created",
            "repair_case_id": "case-f069-supporting-only-cli",
            "revision": 1,
            "schema_version": REPAIR_CASE_SCHEMA_V3,
            "evidence_mode": "supporting_only",
            "identity_status": "unresolved_alias",
            "completeness": "photos_only",
            "manifest_sha256": created_payload["manifest_sha256"],
            "manifest_path": expected_manifest_path,
            "package_count": 0,
            "supporting_evidence_count": 1,
        }
        self.assertEqual(created_payload, expected_receipt)
        self.assertEqual(
            replayed_payload,
            {**expected_receipt, "state": "existing"},
        )

        manifest = json.loads(
            Path(created_payload["manifest_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["package_links"], [])
        self.assertEqual(
            manifest["supporting_evidence"][0]["sha256"],
            photo_sha256,
        )
        evidence_path = (
            self.library / manifest["supporting_evidence"][0]["object_path"]
        )
        self.assertEqual(
            hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            photo_sha256,
        )

    def test_direct_v2_invocation_creates_then_replays_unresolved_identity(self):
        after_image = self.root / "f069-after.jpg"
        after_image.write_bytes(encode_image())
        package = stage_source_package(
            project_root=ROOT,
            library_root=self.library,
            package_id="pkg-f069-after",
            batch_id="batch-f069-after",
            board_key="bg6h-f069",
            capture_session_id="session-f069-after",
            capture_stage="after_repair",
            capture_setup_id="standard-bench",
            image_assignments=[("main_page_1", after_image)],
            milo_physical_source_confirmed=True,
            capture_checklist_confirmed=True,
        )
        supporting_source = self.root / "f069-identity.txt"
        supporting_source_bytes = (
            "Milo supplied model record: TECNO/BG6，待确认 BG6H 映射。"
        ).encode("utf-8")
        supporting_source.write_bytes(supporting_source_bytes)
        supporting_source_sha256 = hashlib.sha256(
            supporting_source_bytes
        ).hexdigest()
        self.case_record.write_text(
            json.dumps(
                {
                    "device_identity": {
                        "reported_models": ["TECNO/BG6"],
                        "catalog_models": ["BG6H", "BG6h"],
                        "mapping_status": "unresolved_alias",
                        "resolved_models": [],
                        "resolution_note": None,
                        "evidence_refs": [
                            {
                                "kind": "supporting_evidence",
                                "evidence_id": "identity-source",
                            }
                        ],
                    },
                    "supporting_evidence_descriptions": {
                        "identity-source": "Milo supplied UTF-8 identity record"
                    },
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
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        command = [
            sys.executable,
            str(self.script),
            "--library-root",
            str(self.library),
            "--repair-case-id",
            "case-f069-cli-0001",
            "--board-key",
            "bg6h-f069",
            "--case-record",
            str(self.case_record),
            "--source-package",
            f"after_repair={package['source_package_path']}",
            "--supporting-file",
            f"identity-source={supporting_source}",
        ]

        created = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        replayed = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
        self.assertEqual(replayed.returncode, 0, replayed.stderr or replayed.stdout)
        created_payload = json.loads(created.stdout)
        replayed_payload = json.loads(replayed.stdout)
        self.assertEqual(created_payload["status"], "ok")
        self.assertEqual(replayed_payload["status"], "ok")
        self.assertEqual(created_payload["state"], "created")
        self.assertEqual(replayed_payload["state"], "existing")
        self.assertEqual(
            replayed_payload["manifest_sha256"],
            created_payload["manifest_sha256"],
        )
        self.assertEqual(
            created_payload["schema_version"],
            REPAIR_CASE_SCHEMA_V2,
        )
        self.assertEqual(
            replayed_payload["schema_version"],
            REPAIR_CASE_SCHEMA_V2,
        )
        self.assertEqual(
            created_payload["identity_status"],
            "unresolved_alias",
        )
        self.assertEqual(
            replayed_payload["identity_status"],
            "unresolved_alias",
        )
        self.assertEqual(created_payload["completeness"], "photos_only")
        self.assertEqual(
            replayed_payload["completeness"],
            created_payload["completeness"],
        )
        self.assertEqual(created_payload["evidence_mode"], "package_linked")
        self.assertEqual(created_payload["package_count"], 1)
        self.assertEqual(created_payload["supporting_evidence_count"], 1)
        self.assertEqual(replayed_payload["evidence_mode"], "package_linked")
        self.assertEqual(replayed_payload["package_count"], 1)
        self.assertEqual(replayed_payload["supporting_evidence_count"], 1)
        self.assertEqual(created.stderr, "")
        self.assertEqual(replayed.stderr, "")

        manifest = json.loads(
            Path(created_payload["manifest_path"]).read_text(encoding="utf-8")
        )
        evidence = manifest["supporting_evidence"][0]
        expected_object_path = (
            f"objects/case-evidence/{supporting_source_sha256[:2]}/"
            f"{supporting_source_sha256}.txt"
        )
        self.assertEqual(
            evidence,
            {
                "evidence_id": "identity-source",
                "original_filename": "f069-identity.txt",
                "object_path": expected_object_path,
                "mime_type": "text/plain",
                "byte_size": len(supporting_source_bytes),
                "sha256": supporting_source_sha256,
                "description": "Milo supplied UTF-8 identity record",
            },
        )
        evidence_object = self.library / evidence["object_path"]
        self.assertEqual(evidence_object.read_bytes(), supporting_source_bytes)
        self.assertEqual(
            hashlib.sha256(evidence_object.read_bytes()).hexdigest(),
            supporting_source_sha256,
        )
        source_manifest_bytes = Path(package["source_package_path"]).read_bytes()
        source_manifest = json.loads(
            source_manifest_bytes.decode("utf-8")
        )
        self.assertEqual(
            manifest["package_links"][0],
            {
                "package_id": source_manifest["package_id"],
                "source_package_manifest_sha256": hashlib.sha256(
                    source_manifest_bytes
                ).hexdigest(),
                "capture_stage": source_manifest["capture_stage"],
                "role": "after_repair",
                "entry_ids": [
                    entry["entry_id"] for entry in source_manifest["entries"]
                ],
            },
        )
        for reference in manifest["device_identity"]["evidence_refs"]:
            self.assertEqual(reference["kind"], "supporting_evidence")
            self.assertEqual(reference["evidence_id"], evidence["evidence_id"])
            self.assertIn(
                reference["evidence_id"],
                {
                    item["evidence_id"]
                    for item in manifest["supporting_evidence"]
                },
            )

    def test_invalid_evidence_mode_combinations_fail_without_publication(self):
        valid_heic = self.root / "valid-repair-progress.heic"
        write_heic(valid_heic, value=155)
        invalid_heic = self.root / "invalid-repair-progress.heic"
        invalid_heic.write_bytes(b"not-a-heic")
        f069_image = self.root / "f069-existing-package.jpg"
        f069_image.write_bytes(encode_image())
        f069_package = stage_source_package(
            project_root=ROOT,
            library_root=self.library,
            package_id="pkg-f069-existing",
            batch_id="batch-f069-existing",
            board_key="bg6h-f069",
            capture_session_id="session-f069-existing",
            capture_stage="after_repair",
            capture_setup_id="standard-bench",
            image_assignments=[("main_page_1", f069_image)],
            milo_physical_source_confirmed=True,
            capture_checklist_confirmed=True,
        )
        v2_record = {
            "device_identity": {
                "reported_models": ["BG6H"],
                "catalog_models": ["BG6H", "BG6h"],
                "mapping_status": "exact_catalog_match",
                "resolved_models": ["BG6H"],
                "resolution_note": None,
                "evidence_refs": [],
            },
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
        v3_package_linked = self.supporting_only_record(
            evidence_mode="package_linked",
            supporting_evidence_contexts=[],
            supporting_evidence_descriptions={},
            device_identity={
                "reported_models": ["BG6H"],
                "catalog_models": ["BG6H", "BG6h"],
                "mapping_status": "exact_catalog_match",
                "resolved_models": ["BG6H"],
                "resolution_note": None,
                "evidence_refs": [],
            },
        )
        cases = [
            (
                "v1-no-package",
                "km4-f151",
                json.loads(self.case_record.read_text(encoding="utf-8")),
                None,
                False,
            ),
            ("v2-no-package", "bg6h-f069", v2_record, None, False),
            (
                "v3-package-linked-no-package",
                "bg6h-f069",
                v3_package_linked,
                None,
                False,
            ),
            (
                "v3-supporting-only-no-file",
                "bg6h-f069",
                self.supporting_only_record(),
                None,
                False,
            ),
            (
                "v3-supporting-only-with-package",
                "bg6h-f069",
                self.supporting_only_record(),
                valid_heic,
                True,
            ),
            (
                "v3-contexts-object",
                "bg6h-f069",
                self.supporting_only_record(supporting_evidence_contexts={}),
                valid_heic,
                False,
            ),
            (
                "v3-invalid-heic",
                "bg6h-f069",
                self.supporting_only_record(),
                invalid_heic,
                False,
            ),
        ]

        for suffix, board_key, record, supporting_file, include_package in cases:
            with self.subTest(case=suffix):
                case_id = f"case-f069-cli-invalid-{suffix}"
                record_path = self.root / f"{suffix}.json"
                record_path.write_text(
                    json.dumps(record, ensure_ascii=False),
                    encoding="utf-8",
                )
                command = [
                    sys.executable,
                    str(self.script),
                    "--library-root",
                    str(self.library),
                    "--repair-case-id",
                    case_id,
                    "--board-key",
                    board_key,
                    "--case-record",
                    str(record_path),
                ]
                if include_package:
                    command.extend(
                        [
                            "--source-package",
                            (
                                "after_repair="
                                f"{f069_package['source_package_path']}"
                            ),
                        ]
                    )
                if supporting_file is not None:
                    command.extend(
                        [
                            "--supporting-file",
                            f"repair-photo={supporting_file}",
                        ]
                    )
                baseline_objects = self.case_evidence_objects()

                result = self.run_command(command)

                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(
                    json.loads(result.stdout)["status"],
                    "validation_failed",
                )
                self.assertEqual(result.stderr, "")
                revision = (
                    self.library
                    / "cases"
                    / case_id
                    / "revisions"
                    / "0001"
                )
                self.assertFalse((revision / ".complete").exists())
                self.assertFalse(revision.exists())
                self.assertEqual(self.case_evidence_objects(), baseline_objects)

    def test_identity_shape_is_rejected_before_case_or_evidence_publication(self):
        supporting_source = self.root / "identity.txt"
        supporting_source.write_text("Milo supplied identity", encoding="utf-8")
        baseline_objects = {
            path.relative_to(self.library)
            for path in (self.library / "objects").rglob("*")
            if path.is_file()
        }
        identity = {
            "reported_models": ["KM4"],
            "catalog_models": ["KM4", "F151"],
            "mapping_status": "exact_catalog_match",
            "resolved_models": ["KM4"],
            "resolution_note": None,
            "evidence_refs": [],
        }

        for identity_fields in (
            {"device_models": ["KM4"], "device_identity": identity},
            {},
        ):
            with self.subTest(identity_fields=set(identity_fields)):
                record = {
                    **identity_fields,
                    "supporting_evidence_descriptions": {
                        "identity-source": "Milo supplied identity"
                    },
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
                self.case_record.write_text(
                    json.dumps(record),
                    encoding="utf-8",
                )

                result = self.run_cli(
                    "--supporting-file",
                    f"identity-source={supporting_source}",
                )

                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    json.loads(result.stdout)["status"],
                    "validation_failed",
                )
                self.assertEqual(result.stderr, "")
                self.assertFalse((self.library / "cases").exists())
                self.assertEqual(
                    {
                        path.relative_to(self.library)
                        for path in (self.library / "objects").rglob("*")
                        if path.is_file()
                    },
                    baseline_objects,
                )

    def test_duplicate_json_key_is_validation_failure_without_case_write(self):
        self.case_record.write_text(
            (
                '{"device_models":["KM4"],'
                '"supporting_evidence_descriptions":{},'
                '"reported_symptoms":[],"findings":[],"repair_actions":[],'
                '"outcome":{"status":"unknown","status":"repair_completed",'
                '"description":null,"verification_description":null,'
                '"evidence_refs":[]},"corrections":[]}'
            ),
            encoding="utf-8",
        )

        result = self.run_cli()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            json.loads(result.stdout)["status"],
            "validation_failed",
        )
        self.assertEqual(result.stderr, "")
        self.assertFalse((self.library / "cases").exists())

    def test_parser_rejects_inference_flags_as_machine_readable_validation(self):
        result = self.run_cli("--model", "KM4")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            json.loads(result.stdout)["status"],
            "validation_failed",
        )
        self.assertEqual(result.stderr, "")
        self.assertFalse((self.library / "cases").exists())

    def test_assignment_splits_only_on_first_equals_character(self):
        note = self.root / "repair=note.txt"
        note.write_text("Milo supplied note", encoding="utf-8")
        record = json.loads(self.case_record.read_text(encoding="utf-8"))
        record["supporting_evidence_descriptions"] = {
            "repair-note": "Milo supplied repair note"
        }
        self.case_record.write_text(
            json.dumps(record, ensure_ascii=False),
            encoding="utf-8",
        )

        result = self.run_cli(
            "--supporting-file",
            f"repair-note={note}",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        manifest = json.loads(
            Path(json.loads(result.stdout)["manifest_path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            manifest["supporting_evidence"][0]["original_filename"],
            "repair=note.txt",
        )

    def test_unexpected_failure_is_machine_readable(self):
        from scripts import stage_visual_qc_repair_case as command_module

        stdout = StringIO()
        stderr = StringIO()
        with patch.object(
            command_module,
            "stage_repair_case_revision",
            side_effect=RuntimeError("simulated failure"),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = command_module.main(self.command()[2:])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "failed")
        self.assertIn("simulated failure", payload["message"])
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
