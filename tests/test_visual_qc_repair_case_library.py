from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import cv2
import numpy as np

from scripts.visual_qc.intake import IntakeValidationError
from scripts.visual_qc.repair_case_library import (
    inspect_supporting_evidence,
    resolve_package_links,
    store_supporting_evidence,
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
        self.temporary.cleanup()

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


if __name__ == "__main__":
    unittest.main()
