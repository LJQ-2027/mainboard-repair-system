from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import cv2
from fastapi.testclient import TestClient
import numpy as np

import scripts.build_f069_registration as f069_builder
from scripts.visual_qc.repair_case_library import stage_repair_case_revision
from scripts.visual_qc.server.api import create_app
from scripts.visual_qc.server.config import VisualQcServerSettings
from tests import test_visual_qc_repair_evidence_link_library as fixture_module
from tests import test_visual_qc_training_manifest as training_fixture_module


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FACT_SENTINEL = "TASK4_BOUNDARY_SOURCE_FACT_SENTINEL_91A6D2"
BINDING_SENTINEL = "task4-boundary-binding-sentinel-91a6d2"


def serialized(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class VisualQcRepairEvidenceLinkBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.VisualQcRepairEvidenceLinkLibraryTests(
            methodName="runTest"
        )
        self.fixture.setUp()
        case_record = copy.deepcopy(self.fixture.case_record)
        case_record["findings"].append(
            {
                "finding_id": "task4-boundary-source-fact",
                "claim_status": "reported",
                "description": SOURCE_FACT_SENTINEL,
                "defect_category": None,
                "designator": None,
                "side_id": None,
                "region": None,
                "evidence_refs": [],
            }
        )
        self.fixture.case = stage_repair_case_revision(
            project_root=ROOT,
            library_root=self.fixture.library,
            repair_case_id="case-f069-0001",
            board_key="bg6h-f069",
            package_assignments=[
                (
                    "after_repair",
                    self.fixture.package["source_package_path"],
                )
            ],
            case_record=case_record,
            supporting_assignments=[],
            previous_manifest_path=self.fixture.case["manifest_path"],
        )
        self.fixture.write_binding_record(
            [
                self.fixture.binding(
                    binding_id=BINDING_SENTINEL,
                    repair_case_reference_id="case-f069-r2",
                    source_fact={
                        "kind": "finding",
                        "fact_id": "task4-boundary-source-fact",
                    },
                )
            ]
        )
        self.case_path = Path(self.fixture.case["manifest_path"])
        self.case_bytes_before = self.case_path.read_bytes()
        self.repair_history_before = {
            path.relative_to(self.fixture.library): path.read_bytes()
            for path in (
                self.fixture.library
                / "cases"
                / "case-f069-0001"
                / "revisions"
            ).rglob("*")
            if path.is_file()
        }
        self.published = self.fixture.publish(
            link_set_id="link-case005-f069-boundary"
        )
        self.manifest_path = Path(self.published["manifest_path"])
        self.manifest_bytes = self.manifest_path.read_bytes()
        self.manifest = json.loads(self.manifest_bytes.decode("utf-8"))
        self.projection = {
            "schema_version": "VISUAL-QC-REPAIR-EVIDENCE-LINK-PROJECTION-TEST",
            "link_set_id": self.manifest["link_set_id"],
            "binding_id": BINDING_SENTINEL,
            "manifest_sha256": self.published["manifest_sha256"],
            "source_fact_sentinel": SOURCE_FACT_SENTINEL,
            "canonical_manifest": self.manifest,
            "canonical_manifest_bytes": self.manifest_bytes.decode("utf-8"),
        }
        settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=self.fixture.root / "shared-server-runtime",
            maximum_upload_bytes=20 * 1024 * 1024,
            minimum_image_dimension=64,
            minimum_free_bytes=0,
            warning_free_bytes=0,
            worker_count=0,
        )
        self.app = create_app(settings)
        self.client = TestClient(self.app)
        reference = cv2.imread(
            str(
                ROOT
                / "assets/board-atlas/km4-f151/main-point-map-page-2.png"
            ),
            cv2.IMREAD_COLOR,
        )
        reference = np.clip(
            reference.astype(np.float32) * 0.65,
            0,
            255,
        ).astype(np.uint8)
        ok, encoded = cv2.imencode(
            ".jpg",
            reference,
            [cv2.IMWRITE_JPEG_QUALITY, 95],
        )
        self.assertTrue(ok)
        self.image_bytes = encoded.tobytes()

    def tearDown(self):
        self.client.close()
        self.fixture.tearDown()

    def create_processed_case(self, request_id, capture_stage):
        checklist = {
            "status": "confirmed",
            "items": {
                "board_and_side_confirmed": True,
                "focus_and_lens_confirmed": True,
                "lighting_and_occlusion_confirmed": True,
            },
            "confirmed_at": "2026-07-20T10:00:00.000Z",
        }
        response = self.client.post(
            "/api/v1/visual-qc/cases",
            data={
                "board_key": "km4-f151",
                "side_id": "main_page_2",
                "capture_stage": capture_stage,
                "evidence_role": "physical_capture",
                "capture_session_id": f"capture-{request_id}",
                "capture_setup_id": "bench-a",
                "capture_checklist": json.dumps(checklist),
                "sha256": hashlib.sha256(self.image_bytes).hexdigest(),
                "intake_batch_id": f"batch-{request_id}",
                "intake_entry_id": f"entry-{request_id}",
                "qualified_handoff": json.dumps(
                    training_fixture_module.qualified_handoff(),
                    separators=(",", ":"),
                ),
            },
            files={
                "file": (
                    "ordinary-reference.jpg",
                    self.image_bytes,
                    "image/jpeg",
                )
            },
            headers={
                "X-Actor-Id": "technician-001",
                "X-Actor-Role": "reviewer",
                "Idempotency-Key": request_id,
            },
        )
        self.assertEqual(response.status_code, 202)
        processed = self.app.state.visual_qc_service.process_next_job()
        self.assertEqual(processed["status"], "succeeded")
        return response.json()

    def test_publication_cannot_write_back_to_repair_case_history(self):
        repair_history_after = {
            path.relative_to(self.fixture.library): path.read_bytes()
            for path in (
                self.fixture.library
                / "cases"
                / "case-f069-0001"
                / "revisions"
            ).rglob("*")
            if path.is_file()
        }
        self.assertEqual(repair_history_after, self.repair_history_before)
        self.assertEqual(self.case_path.read_bytes(), self.case_bytes_before)

        history_bytes = b"\n".join(
            repair_history_after[path] for path in sorted(repair_history_after)
        )
        for link_only_value in (
            self.manifest["link_set_id"].encode("utf-8"),
            self.manifest["bindings"][0]["binding_id"].encode("utf-8"),
            self.published["manifest_sha256"].encode("ascii"),
            self.manifest_bytes,
        ):
            self.assertNotIn(link_only_value, history_bytes)

        self.assertIn(SOURCE_FACT_SENTINEL.encode("utf-8"), self.case_bytes_before)

    def test_link_facts_are_absent_from_every_governed_downstream_surface(self):
        case = self.create_processed_case(
            "task4-boundary-nonempty-qc",
            "before_repair",
        )
        registration = self.client.post(
            (
                f"/api/v1/visual-qc/cases/{case['case_id']}/"
                "registration-reviews"
            ),
            json={
                "decision": "accept_manual",
                "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                "anchors": [
                    {"board": [0, 0], "image": [0, 0]},
                    {"board": [1, 0], "image": [1, 0]},
                    {"board": [1, 1], "image": [1, 1]},
                    {"board": [0, 1], "image": [0, 1]},
                ],
                "check_points": [
                    {"board": [0.5, 0.5], "image": [0.5, 0.5]},
                ],
                "error": {"count": 1, "rms": 0, "maximum": 0},
                "notes": "Task 4 nonempty downstream fixture.",
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        final = self.client.post(
            f"/api/v1/visual-qc/cases/{case['case_id']}/qc-reviews",
            json={
                "qc_result": "confirmed_anomaly",
                "annotations": [
                    {
                        "annotation_id": "ordinary-annotation-001",
                        "category": "burn_or_heat_damage",
                        "source": "human_annotation",
                        "review_status": "confirmed",
                        "component": None,
                        "image_geometry": {
                            "type": "rectangle",
                            "points": [
                                {"x": 0.1, "y": 0.2},
                                {"x": 0.3, "y": 0.5},
                            ],
                        },
                        "board_geometry": {
                            "type": "polygon",
                            "points": [
                                {"x": 0.1, "y": 0.2},
                                {"x": 0.3, "y": 0.2},
                                {"x": 0.3, "y": 0.5},
                                {"x": 0.1, "y": 0.5},
                            ],
                        },
                        "note": "Ordinary reviewed visible damage.",
                    }
                ],
                "notes": "Ordinary final QC review.",
                "repair_evidence_link_projection": self.projection,
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(registration.status_code, 201)
        self.assertEqual(final.status_code, 201)
        service = self.app.state.visual_qc_service
        final_qc_reviews = service.store.list_latest_case_qc_reviews()
        annotations = [
            annotation
            for review in final_qc_reviews
            for annotation in review["annotations"]
        ]
        original_reviews = service.store.list_latest_case_qc_reviews
        injected_review_calls = 0

        def projected_reviews():
            nonlocal injected_review_calls
            injected_review_calls += 1
            rows = copy.deepcopy(original_reviews())
            for row in rows:
                row["repair_evidence_link_projection"] = copy.deepcopy(
                    self.projection
                )
            return rows

        with patch.object(
            service.store,
            "list_latest_case_qc_reviews",
            side_effect=projected_reviews,
        ):
            training_manifest = service.training_manifest()
            coco = service.training_coco()
            bundle_path = service.training_bundle()
        with zipfile.ZipFile(bundle_path) as archive:
            bundle_bytes = b"\n".join(
                archive.read(name) for name in sorted(archive.namelist())
            )

        golden_case = self.create_processed_case(
            "task4-boundary-nonempty-golden",
            "golden_reference",
        )
        golden_registration = self.client.post(
            (
                f"/api/v1/visual-qc/cases/{golden_case['case_id']}/"
                "registration-reviews"
            ),
            json={
                "decision": "accept_automatic",
                "notes": "Ordinary Golden registration.",
            },
            headers={"X-Actor-Id": "technician-001"},
        )
        self.assertEqual(golden_registration.status_code, 201)
        golden_response = self.client.post(
            "/api/v1/visual-qc/golden-samples",
            json={
                "case_id": golden_case["case_id"],
                "capture_setup_id": "bench-a",
                "confirmed_normal": True,
                "repair_evidence_link_projection": self.projection,
            },
            headers={
                "X-Actor-Id": "reviewer-001",
                "X-Actor-Role": "reviewer",
            },
        )
        self.assertEqual(golden_response.status_code, 201)
        golden = golden_response.json()

        original_read_json = f069_builder._read_json
        injected_model_calls = 0

        def projected_model_source(root, path):
            nonlocal injected_model_calls
            injected_model_calls += 1
            payload = original_read_json(root, path)
            payload["repair_evidence_link_projection"] = copy.deepcopy(
                self.projection
            )
            return payload

        with patch.object(
            f069_builder,
            "_read_json",
            side_effect=projected_model_source,
        ):
            model_repair_output = f069_builder.build_dataset(ROOT)
        governed_surfaces = {
            "annotations": serialized(annotations),
            "final_qc_reviews": serialized(final_qc_reviews),
            "golden": serialized(golden),
            "training_manifest": serialized(training_manifest),
            "coco": serialized(coco),
            "dataset_bundle": bundle_bytes,
            "model_repair_output": serialized(model_repair_output),
        }
        forbidden_values = {
            "link_set_id": self.manifest["link_set_id"].encode("utf-8"),
            "binding_id": BINDING_SENTINEL.encode("utf-8"),
            "physical_evidence_id": self.manifest["physical_evidence"][0][
                "physical_evidence_id"
            ].encode("utf-8"),
            "manifest_sha256": self.published["manifest_sha256"].encode("ascii"),
            "source_fact_text": SOURCE_FACT_SENTINEL.encode("utf-8"),
            "manifest_bytes": self.manifest_bytes,
        }
        for surface_name, surface in governed_surfaces.items():
            for value_name, value in forbidden_values.items():
                with self.subTest(
                    surface=surface_name,
                    forbidden_value=value_name,
                ):
                    self.assertNotIn(value, surface)

        self.assertGreater(len(annotations), 0)
        self.assertGreater(len(final_qc_reviews), 0)
        self.assertEqual(golden["status"], "active")
        self.assertGreater(training_manifest["case_count"], 0)
        self.assertGreater(training_manifest["annotation_count"], 0)
        self.assertGreater(len(coco["images"]), 0)
        self.assertGreater(len(coco["annotations"]), 0)
        self.assertGreater(len(bundle_bytes), 0)
        self.assertGreaterEqual(injected_review_calls, 3)
        self.assertEqual(injected_model_calls, 3)
        self.assertEqual(model_repair_output["model"], "BG6H")
        self.assertGreater(len(model_repair_output["entities"]), 0)

    def test_link_exposes_only_fixed_false_governance_boundaries(self):
        fixed_false = {
            "visual_defect_confirmed": False,
            "qc_annotation_created": False,
            "golden_approved": False,
            "training_label_allowed": False,
            "repair_causality_confirmed": False,
            "repair_instruction_allowed": False,
            "field_accuracy_claim_allowed": False,
        }
        self.assertEqual(self.manifest["boundaries"], fixed_false)
        for binding in self.manifest["bindings"]:
            self.assertEqual(
                {
                    key: binding["boundaries"][key]
                    for key in fixed_false
                },
                fixed_false,
            )
        self.assertEqual(
            hashlib.sha256(self.manifest_bytes).hexdigest(),
            self.published["manifest_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
