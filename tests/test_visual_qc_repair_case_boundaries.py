import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import cv2
from fastapi.testclient import TestClient
import numpy as np

from scripts.visual_qc.repair_case_contract import FIXED_FALSE_BOUNDARIES
from scripts.visual_qc.repair_case_library import (
    stage_repair_case_revision,
    validate_repair_case_revision,
)
from scripts.visual_qc.server.api import create_app
from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.source_audit import audit_source_library
from scripts.visual_qc.source_library import stage_source_package


ROOT = Path(__file__).resolve().parents[1]


def encode_image(value):
    image = np.full((120, 180, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Unable to encode test image.")
    return encoded.tobytes()


class VisualQcRepairCaseBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="visual-qc-repair-boundary-"
        )
        self.root = Path(self.temporary.name)
        self.library = self.root / "controlled-library"
        before_image = self.root / "before.jpg"
        after_image = self.root / "after.jpg"
        before_image.write_bytes(encode_image(90))
        after_image.write_bytes(encode_image(160))
        self.before = self.stage_package(
            package_id="pkg-before",
            batch_id="batch-before",
            session_id="session-before",
            capture_stage="before_repair",
            image=before_image,
        )
        self.after = self.stage_package(
            package_id="pkg-after",
            batch_id="batch-after",
            session_id="session-after",
            capture_stage="after_repair",
            image=after_image,
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

    @staticmethod
    def record(**overrides):
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

    def stage_revision(
        self,
        *,
        record,
        packages,
        previous=None,
        supporting=None,
    ):
        return stage_repair_case_revision(
            project_root=ROOT,
            library_root=self.library,
            repair_case_id="case-km4-boundary-0001",
            board_key="km4-f151",
            package_assignments=packages,
            case_record=record,
            supporting_assignments=supporting or [],
            previous_manifest_path=(
                None if previous is None else previous["manifest_path"]
            ),
        )

    def test_case_revisions_never_enter_governed_qc_or_training_state(self):
        before_ref = {
            "kind": "package_entry",
            "package_id": "pkg-before",
            "entry_id": "session-before-main_page_1",
        }
        packages = [
            ("before_repair", self.before["source_package_path"]),
            ("after_repair", self.after["source_package_path"]),
        ]
        first = self.stage_revision(
            record=self.record(),
            packages=packages[:1],
        )
        second = self.stage_revision(
            record=self.record(),
            packages=packages,
            previous=first,
        )
        facts = self.record(
            reported_symptoms=[
                {
                    "symptom_id": "symptom-1",
                    "text": "Phone does not power on.",
                    "source_wording": "No power",
                    "fault_code": None,
                    "evidence_refs": [before_ref],
                }
            ],
            findings=[
                {
                    "finding_id": "finding-1",
                    "claim_status": "documented",
                    "description": "Initial record identifies U2001.",
                    "defect_category": "power_management",
                    "designator": "U2001",
                    "side_id": "main_page_1",
                    "region": None,
                    "evidence_refs": [before_ref],
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
                    "evidence_refs": [before_ref],
                }
            ],
            outcome={
                "status": "repair_completed",
                "description": "Phone powered on after repair.",
                "verification_description": "Power-on test passed.",
                "evidence_refs": [before_ref],
            },
        )
        third = self.stage_revision(
            record=facts,
            packages=packages,
            previous=second,
        )
        corrected = json.loads(json.dumps(facts))
        corrected["findings"].append(
            {
                "finding_id": "finding-2",
                "claim_status": "documented",
                "description": "Later record identifies U2002 instead.",
                "defect_category": "power_management",
                "designator": "U2002",
                "side_id": "main_page_1",
                "region": None,
                "evidence_refs": [before_ref],
            }
        )
        corrected["corrections"] = [
            {
                "correction_id": "correction-1",
                "corrects_fact_id": "finding-1",
                "description": "Later evidence supersedes the initial designator.",
                "replacement_fact_id": "finding-2",
                "evidence_refs": [before_ref],
            }
        ]
        fourth = self.stage_revision(
            record=corrected,
            packages=packages,
            previous=third,
        )

        for revision in (first, second, third, fourth):
            payload = json.loads(
                revision["manifest_path"].read_text(encoding="utf-8")
            )
            self.assertEqual(payload["boundaries"], FIXED_FALSE_BOUNDARIES)
            self.assertEqual(payload["source_origin"], "milo_supplied")

        server_root = self.library / "server-runtime"
        settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=server_root,
            minimum_free_bytes=0,
            warning_free_bytes=0,
            worker_count=0,
        )
        app = create_app(settings)
        with TestClient(app) as client:
            service = app.state.visual_qc_service
            counts = service.store.operational_counts()
            manifest = service.training_manifest()
            coco = service.training_coco()
            bundle = service.training_bundle()

            self.assertEqual(counts["cases"]["total"], 0)
            self.assertEqual(counts["golden_samples"]["active"], 0)
            self.assertEqual(manifest["case_count"], 0)
            self.assertEqual(manifest["annotation_count"], 0)
            self.assertEqual(manifest["cases"], [])
            self.assertEqual(coco["images"], [])
            self.assertEqual(coco["annotations"], [])

            response = client.get(
                "/api/v1/visual-qc/datasets/training-manifest",
                headers={
                    "X-Actor-Id": "reviewer-001",
                    "X-Actor-Role": "reviewer",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["cases"], [])

        with zipfile.ZipFile(bundle) as archive:
            names = set(archive.namelist())
            content = b"".join(archive.read(name) for name in sorted(names))
        self.assertEqual(
            names,
            {"manifest.json", "annotations.coco.json", "bundle-index.json"},
        )
        self.assertNotIn(b"case-km4-boundary-0001", content)
        case_manifest_sha256 = hashlib.sha256(
            fourth["manifest_path"].read_bytes()
        ).hexdigest()
        self.assertNotIn(case_manifest_sha256.encode("ascii"), content)

    def test_repository_external_two_revision_rehearsal_preserves_evidence(self):
        note = self.root / "repair-note.txt"
        note.write_text("Milo supplied synthetic rehearsal note", encoding="utf-8")
        note_hash = hashlib.sha256(note.read_bytes()).hexdigest()
        before_manifest = json.loads(
            self.before["source_package_path"].read_text(encoding="utf-8")
        )
        before_object = (
            self.library / before_manifest["entries"][0]["object_path"]
        )
        before_hash = hashlib.sha256(before_object.read_bytes()).hexdigest()

        initial_audit = audit_source_library(ROOT, self.library)
        self.assertEqual(initial_audit["status"], "healthy")
        first = self.stage_revision(
            record=self.record(
                supporting_evidence_descriptions={
                    "repair-note": "Synthetic plumbing rehearsal note"
                }
            ),
            packages=[
                ("before_repair", self.before["source_package_path"])
            ],
            supporting=[("repair-note", note)],
        )
        packages = [
            ("before_repair", self.before["source_package_path"]),
            ("after_repair", self.after["source_package_path"]),
        ]
        second = self.stage_revision(
            record=self.record(),
            packages=packages,
            previous=first,
        )
        replay = self.stage_revision(
            record=self.record(),
            packages=packages,
            previous=first,
        )
        validated = validate_repair_case_revision(
            manifest_path=second["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        supporting_object = (
            self.library / validated["supporting_evidence"][0]["object_path"]
        )
        final_audit = audit_source_library(ROOT, self.library)

        self.assertEqual(second["state"], "created")
        self.assertEqual(replay["state"], "existing")
        self.assertEqual(
            replay["manifest_sha256"],
            second["manifest_sha256"],
        )
        self.assertEqual(validated["revision"], 2)
        self.assertEqual(final_audit["status"], "healthy")
        self.assertEqual(
            hashlib.sha256(before_object.read_bytes()).hexdigest(),
            before_hash,
        )
        self.assertEqual(
            hashlib.sha256(supporting_object.read_bytes()).hexdigest(),
            note_hash,
        )


if __name__ == "__main__":
    unittest.main()
