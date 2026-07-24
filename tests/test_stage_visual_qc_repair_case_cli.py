from contextlib import redirect_stderr, redirect_stdout
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

from scripts.visual_qc.source_library import stage_source_package


ROOT = Path(__file__).resolve().parents[1]


def encode_image():
    image = np.full((120, 180, 3), 125, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Unable to encode test image.")
    return encoded.tobytes()


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

    def test_direct_invocation_creates_then_replays_exact_case(self):
        created = self.run_cli()

        self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
        payload = json.loads(created.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["state"], "created")
        self.assertEqual(payload["repair_case_id"], "case-km4-cli-0001")
        self.assertEqual(payload["revision"], 1)
        self.assertEqual(payload["completeness"], "photos_only")
        self.assertEqual(len(payload["manifest_sha256"]), 64)
        self.assertTrue(Path(payload["manifest_path"]).is_file())
        self.assertEqual(created.stderr, "")

        replayed = self.run_cli()
        self.assertEqual(replayed.returncode, 0, replayed.stdout)
        self.assertEqual(json.loads(replayed.stdout)["state"], "existing")

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
