import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import cv2
from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
from pillow_heif import from_pillow

from scripts.build_f069_registration import build_dataset
from scripts.visual_qc.repair_case_contract import (
    FIXED_FALSE_BOUNDARIES,
    REPAIR_CASE_SCHEMA_V3,
)
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


def write_heic(path, value=120):
    image = Image.new("RGB", (180, 120), (value, value, value))
    from_pillow(image).save(path, quality=90)


def collect_json_strings(value):
    strings = []
    if isinstance(value, dict):
        for key, child in value.items():
            strings.append(key)
            strings.extend(collect_json_strings(child))
    elif isinstance(value, list):
        for child in value:
            strings.extend(collect_json_strings(child))
    elif isinstance(value, str):
        strings.append(value)
    return strings


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
        board_key="km4-f151",
    ):
        return stage_source_package(
            project_root=ROOT,
            library_root=self.library,
            package_id=package_id,
            batch_id=batch_id,
            board_key=board_key,
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
        registration_path = (
            ROOT / "knowledge-base" / "f069-cross-source-registration.json"
        )
        registration_bytes_before = registration_path.read_bytes()
        registration_sha256_before = hashlib.sha256(
            registration_bytes_before
        ).hexdigest()
        f069_image = self.root / "f069-after.jpg"
        f069_image.write_bytes(encode_image(175))
        f069_after = self.stage_package(
            package_id="pkg-f069-after",
            batch_id="batch-f069-after",
            session_id="session-f069-after",
            capture_stage="after_repair",
            image=f069_image,
            board_key="bg6h-f069",
        )
        identity_source = self.root / "f069-identity.txt"
        identity_source.write_text(
            "Milo supplied model: TECNO/BG6，mapping to BG6H is unresolved.",
            encoding="utf-8",
        )
        identity_source_bytes = identity_source.read_bytes()
        identity_source_hash = hashlib.sha256(identity_source_bytes).hexdigest()
        after_ref = {
            "kind": "package_entry",
            "package_id": "pkg-f069-after",
            "entry_id": "session-f069-after-main_page_1",
        }
        identity_ref = {
            "kind": "supporting_evidence",
            "evidence_id": "identity-source",
        }
        record = self.record(
            device_identity={
                "reported_models": ["TECNO/BG6"],
                "catalog_models": ["BG6H", "BG6h"],
                "mapping_status": "unresolved_alias",
                "resolved_models": [],
                "resolution_note": None,
                "evidence_refs": [identity_ref],
            },
            supporting_evidence_descriptions={
                "identity-source": "Milo supplied UTF-8 identity record"
            },
            reported_symptoms=[
                {
                    "symptom_id": "symptom-1",
                    "text": "用户反馈：设备不开机",
                    "source_wording": "案例原话：不开机",
                    "fault_code": None,
                    "evidence_refs": [after_ref],
                }
            ],
            findings=[
                {
                    "finding_id": "finding-1",
                    "claim_status": "documented",
                    "description": "案例判断：EMMC坏",
                    "defect_category": "power_management",
                    "designator": "U4000",
                    "side_id": "main_page_1",
                    "region": None,
                    "evidence_refs": [after_ref],
                }
            ],
            repair_actions=[
                {
                    "action_id": "action-1",
                    "description": "案例记录：已做检测",
                    "action_category": "diagnostic_test",
                    "target_designator": "U4000",
                    "side_id": "main_page_1",
                    "region": None,
                    "evidence_refs": [after_ref],
                }
            ],
            outcome={
                "status": "repair_completed",
                "description": "Phone powered on after repair.",
                "verification_description": "Power-on test passed.",
                "evidence_refs": [after_ref],
            },
        )
        del record["device_models"]
        revision = stage_repair_case_revision(
            project_root=ROOT,
            library_root=self.library,
            repair_case_id="case-f069-boundary-0001",
            board_key="bg6h-f069",
            package_assignments=[
                ("after_repair", f069_after["source_package_path"])
            ],
            case_record=record,
            supporting_assignments=[("identity-source", identity_source)],
            previous_manifest_path=None,
        )
        self.assertEqual(registration_path.read_bytes(), registration_bytes_before)
        self.assertEqual(
            hashlib.sha256(registration_path.read_bytes()).hexdigest(),
            registration_sha256_before,
        )

        payload = json.loads(
            revision["manifest_path"].read_text(encoding="utf-8")
        )
        self.assertEqual(
            payload["boundaries"],
            {**FIXED_FALSE_BOUNDARIES, "model_identity_resolved": False},
        )
        self.assertEqual(payload["source_origin"], "milo_supplied")
        self.assertEqual(payload["completeness"], "repair_outcome_linked")

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

            manifest_response = client.get(
                "/api/v1/visual-qc/datasets/training-manifest",
                headers={
                    "X-Actor-Id": "reviewer-001",
                    "X-Actor-Role": "reviewer",
                },
            )
            coco_response = client.get(
                "/api/v1/visual-qc/datasets/coco",
                headers={
                    "X-Actor-Id": "reviewer-001",
                    "X-Actor-Role": "reviewer",
                },
            )
            self.assertEqual(manifest_response.status_code, 200)
            self.assertEqual(manifest_response.json()["cases"], [])
            self.assertEqual(manifest_response.json()["annotation_count"], 0)
            self.assertEqual(coco_response.status_code, 200)
            self.assertEqual(coco_response.json()["images"], [])
            self.assertEqual(coco_response.json()["annotations"], [])
            self.assertEqual(service.store.operational_counts()["cases"]["total"], 0)

        with zipfile.ZipFile(bundle) as archive:
            names = set(archive.namelist())
            content = b"".join(archive.read(name) for name in sorted(names))
        self.assertEqual(
            names,
            {"manifest.json", "annotations.coco.json", "bundle-index.json"},
        )
        self.assertNotIn(b"case-f069-boundary-0001", content)
        case_manifest_sha256 = hashlib.sha256(
            revision["manifest_path"].read_bytes()
        ).hexdigest()
        for excluded_bundle_value in (
            case_manifest_sha256.encode("ascii"),
            b"identity-source",
            identity_source_hash.encode("ascii"),
            identity_source_bytes,
            b"TECNO/BG6",
            "用户反馈：设备不开机".encode("utf-8"),
            "案例原话：不开机".encode("utf-8"),
            "案例判断：EMMC坏".encode("utf-8"),
            "案例记录：已做检测".encode("utf-8"),
        ):
            self.assertNotIn(excluded_bundle_value, content)

        rebuilt_registration = build_dataset(ROOT)
        committed_registration = json.loads(
            registration_bytes_before.decode("utf-8")
        )
        self.assertEqual(rebuilt_registration, committed_registration)
        self.assertEqual(registration_path.read_bytes(), registration_bytes_before)

        def collect_values_for_key(value, target_key):
            collected = []
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == target_key:
                        collected.append(child)
                    collected.extend(collect_values_for_key(child, target_key))
            elif isinstance(value, list):
                for child in value:
                    collected.extend(collect_values_for_key(child, target_key))
            return collected

        registration_surfaces = {
            "repair_flows": rebuilt_registration["repair_flows"],
            "repair_links": collect_values_for_key(
                rebuilt_registration,
                "repair_links",
            ),
            "full_output": rebuilt_registration,
        }
        excluded_case_values = (
            "case-f069-boundary-0001",
            case_manifest_sha256,
            "identity-source",
            identity_source_hash,
            "TECNO/BG6",
            "用户反馈：设备不开机",
            "案例原话：不开机",
            "案例判断：EMMC坏",
            "案例记录：已做检测",
        )
        for surface_name, surface in registration_surfaces.items():
            serialized = json.dumps(
                surface,
                ensure_ascii=False,
                sort_keys=True,
            )
            for excluded_value in excluded_case_values:
                with self.subTest(
                    surface=surface_name,
                    excluded_value=excluded_value,
                ):
                    self.assertNotIn(excluded_value, serialized)

    def test_v3_supporting_only_heic_never_enters_downstream_surfaces(self):
        repair_case_id = "case-f069-supporting-only-boundary"
        evidence_id = "repair-progress-heic"
        symptom = "无法充电"
        finding = "维修记录：屏蔽罩内发现异常"
        source_capture_stage = "维修中"
        source_board_area = "屏蔽罩内局部"
        heic_source = self.root / "repair-progress.heic"
        write_heic(heic_source, value=145)
        heic_bytes = heic_source.read_bytes()
        heic_sha256 = hashlib.sha256(heic_bytes).hexdigest()
        evidence_ref = {
            "kind": "supporting_evidence",
            "evidence_id": evidence_id,
        }
        record = {
            "device_identity": {
                "reported_models": ["TECNO/BG6"],
                "catalog_models": ["BG6H", "BG6h"],
                "mapping_status": "unresolved_alias",
                "resolved_models": [],
                "resolution_note": None,
                "evidence_refs": [evidence_ref],
            },
            "evidence_mode": "supporting_only",
            "supporting_evidence_contexts": [
                {
                    "evidence_id": evidence_id,
                    "evidence_role": "repair_in_progress_photo",
                    "source_capture_stage": source_capture_stage,
                    "source_board_area": source_board_area,
                }
            ],
            "supporting_evidence_descriptions": {
                evidence_id: "Milo supplied repair-in-progress HEIC"
            },
            "reported_symptoms": [
                {
                    "symptom_id": "symptom-unable-to-charge",
                    "text": symptom,
                    "source_wording": symptom,
                    "fault_code": None,
                    "evidence_refs": [evidence_ref],
                }
            ],
            "findings": [
                {
                    "finding_id": "finding-shield-area",
                    "claim_status": "reported",
                    "description": finding,
                    "defect_category": None,
                    "designator": None,
                    "side_id": None,
                    "region": None,
                    "evidence_refs": [evidence_ref],
                }
            ],
            "repair_actions": [],
            "outcome": {
                "status": "unknown",
                "description": None,
                "verification_description": None,
                "evidence_refs": [],
            },
            "corrections": [],
        }
        revision = stage_repair_case_revision(
            project_root=ROOT,
            library_root=self.library,
            repair_case_id=repair_case_id,
            board_key="bg6h-f069",
            package_assignments=[],
            case_record=record,
            supporting_assignments=[(evidence_id, heic_source)],
            previous_manifest_path=None,
        )
        payload = validate_repair_case_revision(
            manifest_path=revision["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )

        self.assertEqual(payload["schema_version"], REPAIR_CASE_SCHEMA_V3)
        self.assertEqual(payload["package_links"], [])
        self.assertEqual(payload["evidence_mode"], "supporting_only")
        self.assertEqual(
            payload["boundaries"],
            {**FIXED_FALSE_BOUNDARIES, "model_identity_resolved": False},
        )
        self.assertEqual(payload["supporting_evidence"][0]["sha256"], heic_sha256)

        settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=self.library / "supporting-only-server-runtime",
            minimum_free_bytes=0,
            warning_free_bytes=0,
            worker_count=0,
        )
        app = create_app(settings)
        with TestClient(app):
            service = app.state.visual_qc_service
            counts = service.store.operational_counts()
            manifest = service.training_manifest()
            coco = service.training_coco()
            bundle = service.training_bundle()

            self.assertEqual(counts["cases"]["total"], 0)
            self.assertEqual(counts["golden_samples"]["active"], 0)
            self.assertEqual(manifest["cases"], [])
            self.assertEqual(coco["images"], [])
            self.assertEqual(coco["annotations"], [])

        forbidden_strings = {
            repair_case_id,
            heic_sha256,
            evidence_id,
            source_capture_stage,
            source_board_area,
            symptom,
            finding,
        }
        with zipfile.ZipFile(bundle) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {"manifest.json", "annotations.coco.json", "bundle-index.json"},
            )
            decoded_members = {}
            for name in sorted(archive.namelist()):
                raw = archive.read(name)
                decoded_members[name] = json.loads(raw.decode("utf-8"))
                self.assertNotIn(heic_bytes, raw, name)
                for forbidden in forbidden_strings:
                    with self.subTest(member=name, forbidden=forbidden):
                        self.assertNotIn(forbidden.encode("utf-8"), raw)

        self.assertEqual(decoded_members["manifest.json"]["cases"], [])
        self.assertEqual(decoded_members["annotations.coco.json"]["images"], [])
        self.assertEqual(
            decoded_members["annotations.coco.json"]["annotations"],
            [],
        )
        for name, decoded in decoded_members.items():
            traversed_strings = collect_json_strings(decoded)
            for forbidden in forbidden_strings:
                with self.subTest(decoded_member=name, forbidden=forbidden):
                    self.assertFalse(
                        any(forbidden in value for value in traversed_strings)
                    )

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
