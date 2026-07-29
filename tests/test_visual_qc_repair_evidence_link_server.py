from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cv2
import jsonschema
import numpy as np
from fastapi.testclient import TestClient

from scripts.visual_qc.repair_evidence_engineering import (
    RepairEvidenceEngineeringError,
    resolve_board_asset_snapshot,
)
from scripts.visual_qc.repair_evidence_link_library import (
    _reference_authorities as real_reference_authorities,
)
from scripts.visual_qc.repair_evidence_link_contract import (
    canonical_json_bytes,
    canonical_sha256,
)
from scripts.visual_qc.server.api import create_app
from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server import service as service_module
from scripts.visual_qc.server.service import _LinuxImageLeaseGuard
from tests.test_visual_qc_repair_evidence_link_contract import (
    FIXED_FALSE_BOUNDARIES,
    binding,
    link_manifest,
    qualified_handoff,
)


ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"X-Actor-Id": "link-reviewer", "X-Actor-Role": "reviewer"}
TECHNICIAN_HEADERS = {
    "X-Actor-Id": "link-reviewer",
    "X-Actor-Role": "technician",
}
IMPORTED_AT = "2026-07-27T08:00:00.000Z"


def encode_jpeg(value: int = 120) -> bytes:
    image = np.full((120, 180, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Unable to encode test image")
    return encoded.tobytes()


def registration_points():
    return [
        {"board": {"x": 0.1, "y": 0.1}, "image": {"x": 0.1, "y": 0.1}},
        {"board": {"x": 0.9, "y": 0.1}, "image": {"x": 0.9, "y": 0.1}},
        {"board": {"x": 0.9, "y": 0.9}, "image": {"x": 0.9, "y": 0.9}},
        {"board": {"x": 0.1, "y": 0.9}, "image": {"x": 0.1, "y": 0.9}},
    ]


class LinuxImageLeaseGuardCleanupTests(unittest.TestCase):
    def test_release_attempts_every_lease_drain_and_mask_restore(self):
        lease_calls = []

        class FakeFcntl:
            F_SETLEASE = 100
            F_UNLCK = 200

            @staticmethod
            def fcntl(descriptor, operation, value):
                lease_calls.append((descriptor, operation, value))
                if descriptor == 22:
                    raise OSError("first lease release failed")

        guard = _LinuxImageLeaseGuard(
            (11, 22),
            {"previous-mask"},
            threading.get_native_id(),
            fcntl_module=FakeFcntl,
        )
        mask_calls = []

        with (
            patch.object(
                guard,
                "_drain_sigio",
                side_effect=RuntimeError("drain failed"),
            ),
            patch.object(
                service_module.signal,
                "pthread_sigmask",
                side_effect=lambda *args: mask_calls.append(args),
                create=True,
            ),
            patch.object(
                service_module.signal,
                "SIG_SETMASK",
                2,
                create=True,
            ),
        ):
            errors = guard.release()

        self.assertEqual(
            lease_calls,
            [(22, 100, 200), (11, 100, 200)],
        )
        self.assertEqual(mask_calls, [(2, {"previous-mask"})])
        self.assertEqual(len(errors), 2)
        self.assertEqual(guard.descriptors, ())

    def test_cleanup_attempts_every_close_after_release_and_close_failures(self):
        read_one, write_one = os.pipe()
        read_two, write_two = os.pipe()
        real_close = os.close
        close_calls = []

        class FailingGuard:
            def release(self):
                raise OSError("lease release failed")

        def close_then_maybe_fail(descriptor):
            close_calls.append(descriptor)
            real_close(descriptor)
            if descriptor == read_one:
                raise OSError("close reported failure")

        try:
            with patch.object(
                service_module.os,
                "close",
                side_effect=close_then_maybe_fail,
            ):
                errors = service_module.VisualQcService._cleanup_image_proofs(
                    FailingGuard(),
                    {
                        "one": {"descriptor": read_one},
                        "two": {"descriptor": read_two},
                    },
                )

            self.assertEqual(close_calls, [read_one, read_two])
            self.assertEqual(len(errors), 2)
            with self.assertRaises(OSError):
                os.fstat(read_one)
            with self.assertRaises(OSError):
                os.fstat(read_two)
        finally:
            for descriptor in (write_one, write_two):
                try:
                    real_close(descriptor)
                except OSError:
                    pass


class VisualQcRepairEvidenceLinkStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = VisualQcServerSettings(
            project_root=ROOT,
            data_root=Path(self.temp_dir.name),
            minimum_image_dimension=64,
            minimum_free_bytes=0,
            warning_free_bytes=0,
            retention_days=30,
            retention_batch_limit=100,
            worker_count=0,
        )
        self.app = create_app(self.settings)
        self.service = self.app.state.visual_qc_service
        (self.settings.data_root / "library").mkdir(parents=True)
        self.authority_patcher = patch(
            "scripts.visual_qc.server.service._reference_authorities",
            side_effect=lambda references, **_kwargs: {
                reference["repair_case_reference_id"]: {"corrections": []}
                for reference in references
            },
        )
        self.authority_patcher.start()
        self.addCleanup(self.authority_patcher.stop)
        self.manifest = self._create_active_manifest()
        self.manifest_sha256 = canonical_sha256(self.manifest)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registration_snapshot_normalizes_persisted_coordinate_pairs(self):
        snapshot = self.service._registration_snapshot(
            {
                "method": "reviewed_manual_four_point",
                "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                "anchors": [
                    {"board": [0.1, 0.2], "image": [0.3, 0.4]},
                ],
                "check_points": [
                    {"board": [0.5, 0.6], "image": [0.7, 0.8]},
                ],
                "error": {"count": 1, "rms": 0.0, "maximum": 0.0},
            }
        )
        self.assertEqual(
            snapshot["solve_anchors"],
            [{"board": {"x": 0.1, "y": 0.2}, "image": {"x": 0.3, "y": 0.4}}],
        )
        self.assertEqual(
            snapshot["independent_check_points"],
            [{"board": {"x": 0.5, "y": 0.6}, "image": {"x": 0.7, "y": 0.8}}],
        )

    def _create_active_manifest(self):
        content = encode_jpeg()
        case = self.service.create_case(
            actor_id="link-reviewer",
            idempotency_key="link-case",
            board_key="bg6h-f069",
            side_id="main_page_2",
            capture_stage="after_repair",
            evidence_role="physical_capture",
            intake_batch_id="link-batch",
            intake_entry_id="link-entry",
            qualified_handoff=json.dumps(qualified_handoff()),
            claimed_sha256=hashlib.sha256(content).hexdigest(),
            original_filename="linked.jpg",
            mime_type="image/jpeg",
            content=content,
        )
        with self.service.store.connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = 'succeeded' WHERE job_id = ?",
                (case["job"]["job_id"],),
            )
            connection.commit()
        points = registration_points()
        check_points = [
            {
                "board": {"x": 0.5, "y": 0.5},
                "image": {"x": 0.5, "y": 0.5},
            }
        ]
        review = self.service.store.create_registration_review(
            {
                "review_id": "link-review",
                "case_id": case["case_id"],
                "job_id": case["job"]["job_id"],
                "reviewer_id": "link-reviewer",
                "decision": "accept_manual",
                "method": "reviewed_manual_four_point",
                "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                "anchors": points,
                "check_points": check_points,
                "error": {"count": 1, "rms": 0.0, "maximum": 0.0},
                "notes": "",
                "created_at": IMPORTED_AT,
            }
        )
        stored = self.service.store.get_case(case["case_id"])
        handoff = qualified_handoff()
        physical = {
            "schema_version": "VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1",
            "physical_evidence_id": "physical-linked",
            "server_case_id": case["case_id"],
            "intake": {"batch_id": "link-batch", "entry_id": "link-entry"},
            "board_key": "bg6h-f069",
            "board_id": stored["case"]["board_id"],
            "side_id": "main_page_2",
            "capture_stage": "after_repair",
            "evidence_role": "physical_capture",
            "qualified_handoff": handoff,
            "qualified_handoff_sha256": canonical_sha256(handoff),
            "image_id": stored["image"]["image_id"],
            "image_sha256": stored["image"]["sha256"],
            "job_id": stored["job"]["job_id"],
            "registration_review_id": review["review_id"],
            "registration": {
                "method": review["method"],
                "board_to_image_matrix": review["board_to_image_matrix"],
                "solve_anchors": review["anchors"],
                "independent_check_points": review["check_points"],
                "error": review["error"],
            },
            "physical_evidence_snapshot_sha256": "",
        }
        physical["physical_evidence_snapshot_sha256"] = canonical_sha256(
            {
                key: value
                for key, value in physical.items()
                if key != "physical_evidence_snapshot_sha256"
            }
        )
        manifest = link_manifest(
            bindings=[
                binding(
                    binding_id="binding-linked",
                    target_kind="whole_board",
                    association_status="possibly_related",
                    visibility_status="not_assessed",
                )
            ]
        )
        board = resolve_board_asset_snapshot(ROOT, "bg6h-f069")
        manifest.update(
            {
                "link_set_id": "link-server-projection",
                "repair_case_references": [
                    {
                        **manifest["repair_case_references"][0],
                        "repair_case_reference_id": "case-ref",
                        "board_key": board["board_key"],
                        "board_id": board["board_id"],
                    }
                ],
                "board": board,
                "physical_evidence": [physical],
            }
        )
        manifest["bindings"][0]["repair_case_reference_id"] = "case-ref"
        manifest["bindings"][0]["physical_evidence_id"] = "physical-linked"
        manifest["bindings"][0]["target"]["side_id"] = "main_page_2"
        manifest["bindings"][0]["boundaries"] = {
            **FIXED_FALSE_BOUNDARIES,
            "model_identity_resolved": False,
        }
        return manifest

    def test_migration_creates_exact_additive_tables_and_old_database_is_readable(self):
        with self.service.store.connect() as connection:
            revision_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' "
                "AND name='repair_evidence_link_revisions'"
            ).fetchone()["sql"]
            case_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' "
                "AND name='repair_evidence_link_cases'"
            ).fetchone()["sql"]
        self.assertIn("UNIQUE (manifest_sha256)", revision_sql)
        self.assertIn("PRIMARY KEY (link_set_id, revision)", revision_sql)
        self.assertIn(
            "PRIMARY KEY (link_set_id, revision, server_case_id)", case_sql
        )
        self.assertIsNotNone(
            self.service.store.get_case(
                self.manifest["physical_evidence"][0]["server_case_id"]
            )
        )

    def test_store_import_is_idempotent_conflict_safe_and_rolls_back(self):
        first = self.service.store.import_repair_evidence_link_revision(
            manifest=self.manifest,
            manifest_sha256=self.manifest_sha256,
            actor_id="link-reviewer",
            imported_at=IMPORTED_AT,
        )
        replay = self.service.store.import_repair_evidence_link_revision(
            manifest=copy.deepcopy(self.manifest),
            manifest_sha256=self.manifest_sha256,
            actor_id="other-actor",
            imported_at="2026-07-27T09:00:00.000Z",
        )
        self.assertEqual(first, replay)

        conflict = copy.deepcopy(self.manifest)
        conflict["source_origin"] = "conflicting_origin"
        with self.assertRaisesRegex(ValueError, "projection_conflict"):
            self.service.store.import_repair_evidence_link_revision(
                manifest=conflict,
                manifest_sha256=canonical_sha256(conflict),
                actor_id="link-reviewer",
                imported_at=IMPORTED_AT,
            )

        invalid = copy.deepcopy(self.manifest)
        invalid["link_set_id"] = "rollback-link"
        invalid["physical_evidence"].append(
            {**invalid["physical_evidence"][0], "server_case_id": "missing"}
        )
        with self.assertRaises(Exception):
            self.service.store.import_repair_evidence_link_revision(
                manifest=invalid,
                manifest_sha256=canonical_sha256(invalid),
                actor_id="link-reviewer",
                imported_at=IMPORTED_AT,
            )
        self.assertEqual(
            self.service.store.list_repair_evidence_link_revisions(
                repair_case_id="repair-case-generic"
            ),
            [first],
        )

    def test_store_rejects_oversized_manifest_before_persisting(self):
        with patch(
            "scripts.visual_qc.server.store."
            "MAX_REPAIR_EVIDENCE_LINK_MANIFEST_BYTES",
            1,
        ):
            with self.assertRaisesRegex(
                ValueError, "projection_manifest_too_large"
            ):
                self.service.store.import_repair_evidence_link_revision(
                    manifest=self.manifest,
                    manifest_sha256=self.manifest_sha256,
                    actor_id="link-reviewer",
                    imported_at=IMPORTED_AT,
                )
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], self.manifest["revision"]
            )
        )

    def test_store_requires_contiguous_revision_chain_and_parent_hash(self):
        orphan = copy.deepcopy(self.manifest)
        orphan["revision"] = 2
        orphan["previous_manifest_sha256"] = "8" * 64
        with self.assertRaisesRegex(ValueError, "projection_revision_gap"):
            self.service.store.import_repair_evidence_link_revision(
                manifest=orphan,
                manifest_sha256=canonical_sha256(orphan),
                actor_id="link-reviewer",
                imported_at=IMPORTED_AT,
            )

        self.service.store.import_repair_evidence_link_revision(
            manifest=self.manifest,
            manifest_sha256=self.manifest_sha256,
            actor_id="link-reviewer",
            imported_at=IMPORTED_AT,
        )
        wrong_parent = copy.deepcopy(orphan)
        with self.assertRaisesRegex(
            ValueError, "projection_previous_manifest_mismatch"
        ):
            self.service.store.import_repair_evidence_link_revision(
                manifest=wrong_parent,
                manifest_sha256=canonical_sha256(wrong_parent),
                actor_id="link-reviewer",
                imported_at=IMPORTED_AT,
            )
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], 2
            )
        )

    def test_store_list_filters_orders_latest_and_detail_is_immutable(self):
        first = self.service.store.import_repair_evidence_link_revision(
            manifest=self.manifest,
            manifest_sha256=self.manifest_sha256,
            actor_id="link-reviewer",
            imported_at=IMPORTED_AT,
        )
        second_manifest = copy.deepcopy(self.manifest)
        second_manifest["revision"] = 2
        second_manifest["previous_manifest_sha256"] = self.manifest_sha256
        second = self.service.store.import_repair_evidence_link_revision(
            manifest=second_manifest,
            manifest_sha256=canonical_sha256(second_manifest),
            actor_id="link-reviewer",
            imported_at="2026-07-27T09:00:00.000Z",
        )
        rows = self.service.store.list_repair_evidence_link_revisions(
            server_case_id=self.manifest["physical_evidence"][0]["server_case_id"]
        )
        self.assertEqual(rows, [second, first])
        detail = self.service.store.get_repair_evidence_link_revision(
            self.manifest["link_set_id"], 1
        )
        self.assertEqual(detail["manifest"], self.manifest)
        detail["manifest"]["source_origin"] = "mutated"
        self.assertEqual(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], 1
            )["manifest"],
            self.manifest,
        )


class VisualQcRepairEvidenceLinkApiTests(
    VisualQcRepairEvidenceLinkStoreTests
):
    def setUp(self):
        super().setUp()
        self.client = TestClient(self.app)
        self.link_authority_patcher = patch(
            "scripts.visual_qc.server.service."
            "validate_repair_evidence_link_revision_on_disk",
            side_effect=lambda path, **_kwargs: json.loads(
                path.read_text(encoding="utf-8")
            ),
        )
        self.link_authority_patcher.start()
        self.addCleanup(self.link_authority_patcher.stop)
        self.authority_path = self._stage_link_authority(self.manifest)

    def tearDown(self):
        self.client.close()
        super().tearDown()

    def _stage_link_authority(self, manifest, library_root=None):
        path = (
            (library_root or (self.settings.data_root / "library"))
            / "repair-evidence-links"
            / manifest["link_set_id"]
            / "revisions"
            / f"{manifest['revision']:04d}"
            / "repair-evidence-link.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        return path

    def _import(self):
        self._stage_link_authority(self.manifest)
        return self.client.post(
            "/api/v1/visual-qc/admin/repair-evidence-links",
            headers=HEADERS,
            json={
                "manifest": self.manifest,
                "manifest_sha256": self.manifest_sha256,
            },
        )

    def test_import_requires_published_controlled_authority(self):
        self.authority_path.unlink()
        response = self.client.post(
            "/api/v1/visual-qc/admin/repair-evidence-links",
            headers=HEADERS,
            json={
                "manifest": self.manifest,
                "manifest_sha256": self.manifest_sha256,
            },
        )
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "repair_evidence_link_authority_unavailable",
        )
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], self.manifest["revision"]
            )
        )

    def test_read_health_rechecks_published_controlled_authority(self):
        imported = self._import()
        self.assertEqual(imported.status_code, 201, imported.text)
        self.authority_path.unlink()
        detail = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links/"
            f"{self.manifest['link_set_id']}/revisions/"
            f"{self.manifest['revision']}",
            headers=HEADERS,
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(
            detail.json()["health"],
            {
                "state": "unavailable",
                "reasons": ["link_authority_missing"],
            },
        )

    def test_routes_require_reviewer_and_import_active_projection(self):
        paths = [
            ("post", "/api/v1/visual-qc/admin/repair-evidence-links"),
            ("get", "/api/v1/visual-qc/admin/repair-evidence-links"),
            (
                "get",
                "/api/v1/visual-qc/admin/repair-evidence-links/"
                "link-server-projection/revisions/1",
            ),
        ]
        for method, path in paths:
            if method == "post":
                response = self.client.post(
                    path,
                    headers=TECHNICIAN_HEADERS,
                    json={
                        "manifest": self.manifest,
                        "manifest_sha256": self.manifest_sha256,
                    },
                )
            else:
                response = self.client.get(path, headers=TECHNICIAN_HEADERS)
            self.assertEqual(response.status_code, 403)

        response = self._import()
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["health"], {"state": "active", "reasons": []})

    def test_import_rejects_hash_and_non_active_state(self):
        mismatch = self.client.post(
            "/api/v1/visual-qc/admin/repair-evidence-links",
            headers=HEADERS,
            json={"manifest": self.manifest, "manifest_sha256": "0" * 64},
        )
        self.assertEqual(mismatch.status_code, 422)

        with self.service.store.connect() as connection:
            connection.execute(
                "UPDATE images SET sha256 = ? WHERE image_id = ?",
                ("9" * 64, self.manifest["physical_evidence"][0]["image_id"]),
            )
            connection.commit()
        stale = self._import()
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(
            stale.json()["detail"]["code"], "repair_evidence_link_not_active"
        )

    def test_import_fails_closed_when_controlled_authority_is_unmounted(self):
        with patch.object(
            self.service, "_controlled_library_root", return_value=None
        ):
            response = self._import()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"]["code"],
            "repair_evidence_link_authority_unavailable",
        )
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], self.manifest["revision"]
            )
        )

    def test_list_is_redacted_detail_is_canonical_and_schema_valid(self):
        self.assertEqual(self._import().status_code, 201)
        list_response = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links",
            headers=HEADERS,
            params={
                "server_case_id": self.manifest["physical_evidence"][0][
                    "server_case_id"
                ]
            },
        )
        detail_response = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links/"
            "link-server-projection/revisions/1",
            headers=HEADERS,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        listing = list_response.json()
        detail = detail_response.json()
        self.assertNotIn('"manifest":', json.dumps(listing))
        self.assertNotIn("Generic reviewed source fact", json.dumps(listing))
        self.assertEqual(detail["manifest"], self.manifest)
        self.assertEqual(
            canonical_json_bytes(detail["manifest"]),
            canonical_json_bytes(self.manifest),
        )
        for name, payload in (
            ("visual-qc-repair-evidence-link-list-v1-schema.json", listing),
            ("visual-qc-repair-evidence-link-detail-v1-schema.json", detail),
        ):
            schema = json.loads(
                (ROOT / "knowledge-base" / name).read_text(encoding="utf-8")
            )
            jsonschema.Draft202012Validator(schema).validate(payload)

    def test_read_time_health_is_derived_without_mutating_projection(self):
        self.assertEqual(self._import().status_code, 201)
        original = self.service.store.get_repair_evidence_link_revision(
            "link-server-projection", 1
        )["manifest_json"]
        with self.service.store.connect() as connection:
            connection.execute(
                "UPDATE images SET sha256 = ? WHERE image_id = ?",
                ("9" * 64, self.manifest["physical_evidence"][0]["image_id"]),
            )
            connection.commit()
        detail = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links/"
            "link-server-projection/revisions/1",
            headers=HEADERS,
        ).json()
        self.assertEqual(detail["health"]["state"], "stale")
        self.assertIn("image_identity_mismatch", detail["health"]["reasons"])
        self.assertEqual(
            self.service.store.get_repair_evidence_link_revision(
                "link-server-projection", 1
            )["manifest_json"],
            original,
        )

    def test_projection_manifest_tampering_fails_closed_for_list_and_detail(self):
        self.assertEqual(self._import().status_code, 201)
        with self.service.store.connect() as connection:
            connection.execute(
                """
                UPDATE repair_evidence_link_revisions
                SET manifest_json = replace(
                    manifest_json, 'possibly_related', 'related'
                )
                WHERE link_set_id = ? AND revision = ?
                """,
                (self.manifest["link_set_id"], self.manifest["revision"]),
            )
            connection.commit()

        detail = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links/"
            "link-server-projection/revisions/1",
            headers=HEADERS,
        )
        listing = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links",
            headers=HEADERS,
        )
        replay = self._import()

        for response in (detail, listing, replay):
            self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(
                response.json()["detail"]["code"],
                "repair_evidence_link_projection_corrupt",
            )

    def _assert_projection_corrupt_on_all_read_paths(
        self, *, detail_link_set_id=None, detail_revision=None
    ):
        detail = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links/"
            f"{detail_link_set_id or self.manifest['link_set_id']}/revisions/"
            f"{detail_revision or self.manifest['revision']}",
            headers=HEADERS,
        )
        listing = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links",
            headers=HEADERS,
        )
        replay = self._import()
        for response in (detail, listing, replay):
            self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(
                response.json()["detail"]["code"],
                "repair_evidence_link_projection_corrupt",
            )

    def test_projection_summary_fields_are_bound_to_canonical_manifest(self):
        self.assertEqual(self._import().status_code, 201)
        original_link_set_id = self.manifest["link_set_id"]
        original_revision = self.manifest["revision"]
        mutations = (
            ("link_set_id", "tampered-link-set", original_revision),
            ("revision", 9, original_link_set_id),
            ("repair_case_id", "tampered-repair-case", None),
            ("board_key", "tampered-board", None),
            ("board_id", "BOARD-TAMPERED", None),
            ("manifest_sha256", "9" * 64, None),
        )
        for column, changed, _detail_identity in mutations:
            with self.subTest(column=column):
                connection = sqlite3.connect(
                    self.service.store.database_path
                )
                try:
                    connection.execute("PRAGMA foreign_keys = OFF")
                    connection.execute(
                        f"""
                        UPDATE repair_evidence_link_revisions
                        SET {column} = ?
                        WHERE link_set_id = ? AND revision = ?
                        """,
                        (changed, original_link_set_id, original_revision),
                    )
                    connection.commit()
                finally:
                    connection.close()
                try:
                    self._assert_projection_corrupt_on_all_read_paths(
                        detail_link_set_id=(
                            changed
                            if column == "link_set_id"
                            else original_link_set_id
                        ),
                        detail_revision=(
                            changed if column == "revision" else original_revision
                        ),
                    )
                finally:
                    connection = sqlite3.connect(
                        self.service.store.database_path
                    )
                    try:
                        connection.execute("PRAGMA foreign_keys = OFF")
                        connection.execute(
                            f"""
                            UPDATE repair_evidence_link_revisions
                            SET {column} = ?
                            WHERE link_set_id = ? AND revision = ?
                            """,
                            (
                                (
                                    self.manifest_sha256
                                    if column == "manifest_sha256"
                                    else (
                                        self.manifest["board"][column]
                                        if column in {"board_key", "board_id"}
                                        else (
                                            "repair-case-generic"
                                            if column == "repair_case_id"
                                            else (
                                                original_link_set_id
                                                if column == "link_set_id"
                                                else original_revision
                                            )
                                        )
                                    )
                                ),
                                (
                                    changed
                                    if column == "link_set_id"
                                    else original_link_set_id
                                ),
                                (
                                    changed
                                    if column == "revision"
                                    else original_revision
                                ),
                            ),
                        )
                        connection.commit()
                    finally:
                        connection.close()

    def test_projection_child_rows_are_exactly_bound_to_manifest(self):
        self.assertEqual(self._import().status_code, 201)
        evidence = self.manifest["physical_evidence"][0]
        exact_row = (
            self.manifest["link_set_id"],
            self.manifest["revision"],
            evidence["server_case_id"],
            evidence["physical_evidence_snapshot_sha256"],
        )

        def restore_exact_child():
            connection = sqlite3.connect(self.service.store.database_path)
            try:
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.execute(
                    "DELETE FROM repair_evidence_link_cases "
                    "WHERE link_set_id = ? AND revision = ?",
                    exact_row[:2],
                )
                connection.execute(
                    """
                    INSERT INTO repair_evidence_link_cases (
                        link_set_id, revision, server_case_id,
                        physical_evidence_snapshot_sha256
                    ) VALUES (?, ?, ?, ?)
                    """,
                    exact_row,
                )
                connection.commit()
            finally:
                connection.close()

        mutations = (
            (
                "case",
                "UPDATE repair_evidence_link_cases SET server_case_id = ? "
                "WHERE link_set_id = ? AND revision = ?",
                ("tampered-server-case", *exact_row[:2]),
            ),
            (
                "snapshot",
                "UPDATE repair_evidence_link_cases "
                "SET physical_evidence_snapshot_sha256 = ? "
                "WHERE link_set_id = ? AND revision = ?",
                ("8" * 64, *exact_row[:2]),
            ),
            (
                "extra",
                "INSERT INTO repair_evidence_link_cases VALUES (?, ?, ?, ?)",
                (*exact_row[:2], "extra-server-case", "7" * 64),
            ),
            (
                "missing",
                "DELETE FROM repair_evidence_link_cases "
                "WHERE link_set_id = ? AND revision = ?",
                exact_row[:2],
            ),
        )
        for name, statement, parameters in mutations:
            with self.subTest(mutation=name):
                connection = sqlite3.connect(
                    self.service.store.database_path
                )
                try:
                    connection.execute("PRAGMA foreign_keys = OFF")
                    connection.execute(statement, parameters)
                    connection.commit()
                finally:
                    connection.close()
                try:
                    self._assert_projection_corrupt_on_all_read_paths()
                finally:
                    restore_exact_child()

    def test_list_rejects_more_than_hard_cap_before_health_evaluation(self):
        manifest_json = json.dumps(
            self.manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self.service.store.connect() as connection:
            connection.executemany(
                """
                INSERT INTO repair_evidence_link_revisions (
                    link_set_id, revision, manifest_sha256, repair_case_id,
                    board_key, board_id, manifest_json, import_actor_id,
                    imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        f"over-cap-{index:03d}",
                        1,
                        f"{index:064x}",
                        "repair-case-generic",
                        self.manifest["board"]["board_key"],
                        self.manifest["board"]["board_id"],
                        manifest_json,
                        "link-reviewer",
                        IMPORTED_AT,
                    )
                    for index in range(101)
                ],
            )
            connection.commit()

        with (
            patch.object(
                self.service,
                "_repair_evidence_link_health",
                wraps=self.service._repair_evidence_link_health,
            ) as health,
            patch.object(
                self.service,
                "_repair_evidence_link_binding_states",
                wraps=self.service._repair_evidence_link_binding_states,
            ) as authority,
        ):
            response = self.client.get(
                "/api/v1/visual-qc/admin/repair-evidence-links",
                headers=HEADERS,
                params={"repair_case_id": "repair-case-generic"},
            )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "repair_evidence_link_result_limit_exceeded",
        )
        health.assert_not_called()
        authority.assert_not_called()

    def test_list_caches_repeated_authority_board_and_image_verification(self):
        self.assertEqual(self._import().status_code, 201)
        second_manifest = copy.deepcopy(self.manifest)
        second_manifest["revision"] = 2
        second_manifest["previous_manifest_sha256"] = self.manifest_sha256
        replacement = copy.deepcopy(second_manifest["bindings"][0])
        replacement["binding_id"] = "binding-linked-replacement"
        replacement["supersedes_binding_id"] = "binding-linked"
        second_manifest["bindings"].append(replacement)
        self.service.store.import_repair_evidence_link_revision(
            manifest=second_manifest,
            manifest_sha256=canonical_sha256(second_manifest),
            actor_id="link-reviewer",
            imported_at="2026-07-27T09:00:00.000Z",
        )
        authority_result = {
            reference["repair_case_reference_id"]: {"corrections": []}
            for reference in self.manifest["repair_case_references"]
        }

        with (
            patch(
                "scripts.visual_qc.server.service._reference_authorities",
                return_value=authority_result,
            ) as authority_loader,
            patch(
                "scripts.visual_qc.server.service.resolve_board_asset_snapshot",
                wraps=resolve_board_asset_snapshot,
            ) as board_loader,
            patch.object(
                self.service,
                "_stored_image_file_reason",
                wraps=self.service._stored_image_file_reason,
            ) as image_verifier,
        ):
            response = self.client.get(
                "/api/v1/visual-qc/admin/repair-evidence-links",
                headers=HEADERS,
                params={
                    "server_case_id": self.manifest["physical_evidence"][0][
                        "server_case_id"
                    ]
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["links"]), 2)
        counts_by_revision = {
            item["revision"]: item["counts"]["binding_superseded"]
            for item in response.json()["links"]
        }
        self.assertEqual(counts_by_revision, {2: 1, 1: 0})
        self.assertEqual(authority_loader.call_count, 1)
        self.assertEqual(board_loader.call_count, 1)
        self.assertEqual(image_verifier.call_count, 1)

    def test_image_health_checks_missing_changed_and_unsafe_storage_bytes(self):
        evidence = self.manifest["physical_evidence"][0]
        image = self.service.store.get_image(evidence["image_id"])
        original_path = Path(image["storage_path"])
        original_bytes = original_path.read_bytes()

        original_path.unlink()
        health = self.service._repair_evidence_link_health(self.manifest)
        self.assertIn("image_missing", health["reasons"])

        original_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.write_bytes(b"\0" * len(original_bytes))
        health = self.service._repair_evidence_link_health(self.manifest)
        self.assertIn("image_identity_mismatch", health["reasons"])

        original_path.write_bytes(original_bytes)
        unsafe_path = Path(self.temp_dir.name).parent / "unsafe-linked-image.jpg"
        unsafe_path.write_bytes(original_bytes)
        try:
            with self.service.store.connect() as connection:
                connection.execute(
                    "UPDATE images SET storage_path = ? WHERE image_id = ?",
                    (str(unsafe_path), evidence["image_id"]),
                )
                connection.commit()
            health = self.service._repair_evidence_link_health(self.manifest)
            self.assertIn("image_identity_mismatch", health["reasons"])
        finally:
            unsafe_path.unlink(missing_ok=True)

    def test_stable_file_identity_includes_ctime_nanoseconds(self):
        baseline = SimpleNamespace(
            st_dev=1,
            st_ino=2,
            st_nlink=1,
            st_size=128,
            st_mtime_ns=10,
            st_ctime_ns=20,
        )
        rewritten = SimpleNamespace(**vars(baseline))
        rewritten.st_ctime_ns = 21

        self.assertNotEqual(
            self.service._file_identity(baseline),
            self.service._file_identity(rewritten),
        )

    def test_image_health_treats_unreadable_managed_file_as_missing(self):
        with patch.object(
            self.service,
            "_open_stable_image_descriptor",
            side_effect=PermissionError("simulated unreadable image"),
        ):
            health = self.service._repair_evidence_link_health(self.manifest)
        self.assertIn("image_missing", health["reasons"])

    def test_image_health_rejects_reparse_or_symlink_storage_path(self):
        evidence = self.manifest["physical_evidence"][0]
        image = self.service.store.get_image(evidence["image_id"])
        original_path = Path(image["storage_path"])
        link_path = original_path.with_name("linked-image.jpg")
        try:
            link_path.symlink_to(original_path)
        except OSError as exc:
            with patch(
                "scripts.visual_qc.server.service._is_reparse_or_symlink",
                side_effect=lambda path: Path(path) == original_path.parent,
            ):
                health = self.service._repair_evidence_link_health(
                    self.manifest
                )
            self.assertIn("image_identity_mismatch", health["reasons"])
            return
        try:
            with self.service.store.connect() as connection:
                connection.execute(
                    "UPDATE images SET storage_path = ? WHERE image_id = ?",
                    (str(link_path), evidence["image_id"]),
                )
                connection.commit()
            health = self.service._repair_evidence_link_health(self.manifest)
            self.assertIn("image_identity_mismatch", health["reasons"])
        finally:
            link_path.unlink(missing_ok=True)

    def test_import_rechecks_db_facts_inside_write_transaction_and_rolls_back(self):
        original_import = (
            self.service.store.import_repair_evidence_link_revision
        )
        evidence = self.manifest["physical_evidence"][0]
        mutation_finished = threading.Event()

        def mutate_then_import(**kwargs):
            with self.service.store.connect() as connection:
                connection.execute(
                    "UPDATE jobs SET status = 'failed' WHERE job_id = ?",
                    (evidence["job_id"],),
                )
                connection.commit()
            mutation_finished.set()
            return original_import(**kwargs)

        with patch.object(
            self.service.store,
            "import_repair_evidence_link_revision",
            side_effect=mutate_then_import,
        ):
            response = self._import()

        self.assertTrue(mutation_finished.is_set())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "repair_evidence_link_not_active",
        )
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], self.manifest["revision"]
            )
        )

    def test_import_never_hashes_image_bytes_inside_write_transaction(self):
        original_import = (
            self.service.store.import_repair_evidence_link_revision
        )
        original_hash = self.service._hash_image_descriptor
        transaction_active = False
        hash_observations = []

        def observe_store_import(**kwargs):
            validate_current = kwargs["validate_current"]
            validate_after = kwargs["validate_after"]

            def observed(callback):
                def run(connection):
                    nonlocal transaction_active
                    self.assertTrue(connection.in_transaction)
                    transaction_active = True
                    try:
                        return callback(connection)
                    finally:
                        transaction_active = False

                return run

            kwargs["validate_current"] = observed(validate_current)
            kwargs["validate_after"] = observed(validate_after)
            return original_import(**kwargs)

        def observe_hash(descriptor):
            hash_observations.append(transaction_active)
            return original_hash(descriptor)

        with (
            patch.object(
                self.service.store,
                "import_repair_evidence_link_revision",
                side_effect=observe_store_import,
            ),
            patch.object(
                self.service,
                "_hash_image_descriptor",
                side_effect=observe_hash,
            ),
        ):
            response = self._import()

        self.assertEqual(response.status_code, 201, response.text)
        self.assertGreaterEqual(len(hash_observations), 1)
        self.assertFalse(any(hash_observations))

    def test_import_fails_closed_when_kernel_exclusion_is_unavailable(self):
        with (
            patch(
                "scripts.visual_qc.server.service.sys.platform",
                "linux",
            ),
            patch(
                "scripts.visual_qc.server.service."
                "_LinuxImageLeaseGuard.acquire",
                side_effect=OSError("leases unavailable"),
            ),
        ):
            response = self._import()

        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "repair_evidence_link_file_exclusion_unavailable",
        )
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], self.manifest["revision"]
            )
        )

    def test_import_fails_closed_on_unproven_non_windows_platforms(self):
        for platform in ("darwin", "freebsd14", "aix"):
            with self.subTest(platform=platform), patch(
                "scripts.visual_qc.server.service.sys.platform",
                platform,
            ):
                response = self._import()

            self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(
                response.json()["detail"]["code"],
                "repair_evidence_link_file_exclusion_unavailable",
            )
            self.assertIsNone(
                self.service.store.get_repair_evidence_link_revision(
                    self.manifest["link_set_id"],
                    self.manifest["revision"],
                )
            )

    def test_post_commit_cleanup_failure_requires_exact_replay(self):
        class FailingGuard:
            release_calls = 0

            def release(self):
                self.release_calls += 1
                raise OSError("lease release failed")

        guard = FailingGuard()
        with patch.object(
            self.service,
            "_acquire_kernel_image_exclusion",
            return_value=guard,
        ):
            response = self._import()

        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "repair_evidence_link_cleanup_uncertain",
        )
        self.assertIn(
            "may already exist",
            response.json()["detail"]["message"],
        )
        self.assertIn("replay", response.json()["detail"]["message"])
        self.assertEqual(guard.release_calls, 1)
        stored = self.service.store.get_repair_evidence_link_revision(
            self.manifest["link_set_id"], self.manifest["revision"]
        )
        self.assertEqual(stored["manifest_sha256"], self.manifest_sha256)

        replay = self._import()

        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(
            replay.json()["manifest_sha256"],
            self.manifest_sha256,
        )

    def test_pre_commit_failure_rolls_back_and_reports_cleanup_failure(self):
        original_import = (
            self.service.store.import_repair_evidence_link_revision
        )

        class FailingGuard:
            def release(self):
                raise OSError("lease release failed")

        def fail_before_commit(**kwargs):
            validate_after = kwargs["validate_after"]

            def validate_then_fail(connection):
                validate_after(connection)
                raise RuntimeError("commit proxy failed")

            kwargs["validate_after"] = validate_then_fail
            return original_import(**kwargs)

        with (
            patch.object(
                self.service,
                "_acquire_kernel_image_exclusion",
                return_value=FailingGuard(),
            ),
            patch.object(
                self.service.store,
                "import_repair_evidence_link_revision",
                side_effect=fail_before_commit,
            ),
        ):
            response = self._import()

        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "repair_evidence_link_cleanup_failed",
        )
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], self.manifest["revision"]
            )
        )

    @unittest.skipUnless(
        sys.platform.startswith("linux"), "Linux lease enforcement"
    )
    def test_linux_lease_blocks_writer_in_commit_proxy_window(self):
        image = self.service.store.get_image(
            self.manifest["physical_evidence"][0]["image_id"]
        )
        path = Path(image["storage_path"])
        original_bytes = path.read_bytes()
        original_import = (
            self.service.store.import_repair_evidence_link_revision
        )
        writer_observed_blocked = False
        writer = None

        def import_with_writer_probe(**kwargs):
            validate_after = kwargs["validate_after"]

            def probe_after_final_validation(connection):
                nonlocal writer, writer_observed_blocked
                validate_after(connection)
                writer = subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        (
                            "import sys;"
                            "from pathlib import Path;"
                            f"p=Path({str(path)!r});"
                            "print('READY', flush=True);"
                            "p.write_bytes(b'X' * p.stat().st_size);"
                            "print('DONE', flush=True)"
                        ),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    self.assertEqual(writer.stdout.readline().strip(), "READY")
                    with self.assertRaises(subprocess.TimeoutExpired):
                        writer.wait(timeout=0.25)
                    writer_observed_blocked = True
                except BaseException:
                    writer.kill()
                    writer.wait(timeout=5)
                    raise

            kwargs["validate_after"] = probe_after_final_validation
            return original_import(**kwargs)

        with patch.object(
            self.service.store,
            "import_repair_evidence_link_revision",
            side_effect=import_with_writer_probe,
        ):
            response = self._import()

        writer.wait(timeout=5)
        self.assertEqual(writer.stdout.readline().strip(), "DONE")
        self.assertEqual(writer.returncode, 0, writer.stderr.read())
        self.assertEqual(response.status_code, 201, response.text)
        self.assertTrue(writer_observed_blocked)
        self.assertEqual(response.json()["health"]["state"], "active")
        self.assertNotEqual(path.read_bytes(), original_bytes)
        replayed = self.client.get(
            "/api/v1/visual-qc/admin/repair-evidence-links/"
            f"{self.manifest['link_set_id']}/revisions/"
            f"{self.manifest['revision']}",
            headers=HEADERS,
        )
        self.assertEqual(replayed.status_code, 200, replayed.text)
        self.assertEqual(replayed.json()["health"]["state"], "stale")
        self.assertIn(
            "image_identity_mismatch",
            replayed.json()["health"]["reasons"],
        )

    @unittest.skipUnless(os.name == "posix", "POSIX ctime assurance")
    def test_posix_same_inode_rewrite_before_begin_rolls_back(self):
        image = self.service.store.get_image(
            self.manifest["physical_evidence"][0]["image_id"]
        )
        path = Path(image["storage_path"])
        original = path.read_bytes()
        original_stat = path.stat()
        original_import = (
            self.service.store.import_repair_evidence_link_revision
        )

        def rewrite_then_import(**kwargs):
            time.sleep(0.01)
            with path.open("r+b") as stream:
                stream.write(bytes(value ^ 0x01 for value in original))
                stream.flush()
                os.fsync(stream.fileno())
            os.utime(
                path,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )
            changed = path.stat()
            self.assertEqual(changed.st_ino, original_stat.st_ino)
            self.assertEqual(changed.st_size, original_stat.st_size)
            self.assertEqual(changed.st_mtime_ns, original_stat.st_mtime_ns)
            self.assertNotEqual(changed.st_ctime_ns, original_stat.st_ctime_ns)
            return original_import(**kwargs)

        with patch.object(
            self.service.store,
            "import_repair_evidence_link_revision",
            side_effect=rewrite_then_import,
        ):
            response = self._import()

        self.assertEqual(response.status_code, 409, response.text)
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], self.manifest["revision"]
            )
        )

    @unittest.skipUnless(os.name == "posix", "POSIX ctime assurance")
    def test_posix_same_inode_rewrite_before_commit_rolls_back_insert(self):
        image = self.service.store.get_image(
            self.manifest["physical_evidence"][0]["image_id"]
        )
        path = Path(image["storage_path"])
        original = path.read_bytes()
        original_stat = path.stat()
        original_import = (
            self.service.store.import_repair_evidence_link_revision
        )

        def import_with_commit_drift(**kwargs):
            validate_after = kwargs["validate_after"]

            def rewrite_then_validate(connection):
                time.sleep(0.01)
                with path.open("r+b") as stream:
                    stream.write(bytes(value ^ 0x01 for value in original))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.utime(
                    path,
                    ns=(
                        original_stat.st_atime_ns,
                        original_stat.st_mtime_ns,
                    ),
                )
                changed = path.stat()
                self.assertEqual(changed.st_ino, original_stat.st_ino)
                self.assertEqual(changed.st_size, original_stat.st_size)
                self.assertEqual(
                    changed.st_mtime_ns, original_stat.st_mtime_ns
                )
                self.assertNotEqual(
                    changed.st_ctime_ns, original_stat.st_ctime_ns
                )
                return validate_after(connection)

            kwargs["validate_after"] = rewrite_then_validate
            return original_import(**kwargs)

        with patch.object(
            self.service.store,
            "import_repair_evidence_link_revision",
            side_effect=import_with_commit_drift,
        ):
            response = self._import()

        self.assertEqual(response.status_code, 409, response.text)
        self.assertIsNone(
            self.service.store.get_repair_evidence_link_revision(
                self.manifest["link_set_id"], self.manifest["revision"]
            )
        )

    def test_source_and_binding_supersession_are_derived_independently(self):
        from tests.test_visual_qc_repair_evidence_link_library import (
            VisualQcRepairEvidenceLinkLibraryTests,
        )

        authority_fixture = VisualQcRepairEvidenceLinkLibraryTests(
            "test_derives_source_fact_supersession_independently"
        )
        authority_fixture.setUp()
        self.addCleanup(authority_fixture.tearDown)
        corrected_case = authority_fixture.stage_corrected_case()
        manifest = copy.deepcopy(self.manifest)
        manifest["revision"] = 2
        manifest["previous_manifest_sha256"] = "8" * 64
        first_reference = manifest["repair_case_references"][0]
        first_reference.update(
            {
                "repair_case_id": authority_fixture.case["repair_case_id"],
                "revision": authority_fixture.case["revision"],
                "schema_version": authority_fixture.case["schema_version"],
                "manifest_sha256": authority_fixture.case["manifest_sha256"],
            }
        )
        second_reference = {
            **copy.deepcopy(first_reference),
            "repair_case_reference_id": "case-ref-r2",
            "revision": corrected_case["revision"],
            "schema_version": corrected_case["schema_version"],
            "manifest_sha256": corrected_case["manifest_sha256"],
        }
        manifest["repair_case_references"].append(second_reference)
        old_binding = manifest["bindings"][0]
        old_binding["source_fact"]["fact_id"] = "reported-emmc-fault"
        old_binding["source_fact"]["fact_sha256"] = canonical_sha256(
            {
                key: value
                for key, value in old_binding["source_fact"].items()
                if key != "fact_sha256"
            }
        )
        replacement = copy.deepcopy(old_binding)
        replacement["binding_id"] = "binding-linked-replacement"
        replacement["repair_case_reference_id"] = "case-ref-r2"
        replacement["supersedes_binding_id"] = old_binding["binding_id"]
        replacement["source_fact"]["fact_id"] = "documented-u4000"
        replacement["source_fact"]["fact_sha256"] = canonical_sha256(
            {
                key: value
                for key, value in replacement["source_fact"].items()
                if key != "fact_sha256"
            }
        )
        predecessor = copy.deepcopy(manifest)
        predecessor["revision"] = 1
        predecessor["previous_manifest_sha256"] = None
        predecessor["repair_case_references"] = [
            predecessor["repair_case_references"][0]
        ]
        predecessor_sha256 = canonical_sha256(predecessor)
        self.service.store.import_repair_evidence_link_revision(
            manifest=predecessor,
            manifest_sha256=predecessor_sha256,
            actor_id="link-reviewer",
            imported_at=IMPORTED_AT,
        )
        manifest["previous_manifest_sha256"] = predecessor_sha256
        manifest["bindings"].append(replacement)

        with (
            patch.object(
                self.service,
                "_controlled_library_root",
                return_value=authority_fixture.library,
            ),
            patch(
                "scripts.visual_qc.server.service._reference_authorities",
                side_effect=real_reference_authorities,
            ),
        ):
            states = self.service._repair_evidence_link_binding_states(
                manifest
            )
            counts = self.service._repair_evidence_link_counts(
                manifest, states
            )
            self._stage_link_authority(
                manifest, library_root=authority_fixture.library
            )
            response = self.client.post(
                "/api/v1/visual-qc/admin/repair-evidence-links",
                headers=HEADERS,
                json={
                    "manifest": manifest,
                    "manifest_sha256": canonical_sha256(manifest),
                },
            )

        old_state = {
            item["binding_id"]: item for item in states
        }[old_binding["binding_id"]]
        self.assertTrue(old_state["source_fact_superseded"])
        self.assertEqual(
            old_state["replacement_fact_id"], "documented-u4000"
        )
        self.assertTrue(old_state["binding_superseded"])
        self.assertEqual(
            old_state["replacement_binding_id"],
            replacement["binding_id"],
        )
        self.assertEqual(counts["source_fact_superseded"], 1)
        self.assertEqual(counts["binding_superseded"], 1)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            response.json()["counts"]["source_fact_superseded"], 1
        )
        self.assertEqual(
            {
                item["binding_id"]: item
                for item in response.json()["binding_states"]
            }[old_binding["binding_id"]],
            old_state,
        )

        stored_before = self.service.store.get_repair_evidence_link_revision(
            manifest["link_set_id"], manifest["revision"]
        )["manifest_json"]
        with patch.object(
            self.service, "_controlled_library_root", return_value=None
        ):
            detail = self.client.get(
                "/api/v1/visual-qc/admin/repair-evidence-links/"
                f"{manifest['link_set_id']}/revisions/{manifest['revision']}",
                headers=HEADERS,
            )
            listing = self.client.get(
                "/api/v1/visual-qc/admin/repair-evidence-links",
                headers=HEADERS,
            )
            replay = self.client.post(
                "/api/v1/visual-qc/admin/repair-evidence-links",
                headers=HEADERS,
                json={
                    "manifest": manifest,
                    "manifest_sha256": canonical_sha256(manifest),
                },
            )
        for unavailable in (detail, listing, replay):
            self.assertEqual(unavailable.status_code, 503)
            self.assertEqual(
                unavailable.json()["detail"]["code"],
                "repair_evidence_link_authority_unavailable",
            )
        self.assertEqual(
            self.service.store.get_repair_evidence_link_revision(
                manifest["link_set_id"], manifest["revision"]
            )["manifest_json"],
            stored_before,
        )

    def test_health_derives_every_exact_stale_and_unavailable_reason(self):
        evidence = self.manifest["physical_evidence"][0]
        case = self.service.store.get_case_identity(evidence["server_case_id"])
        image = self.service.store.get_image(evidence["image_id"])
        job = self.service.store.get_job(evidence["job_id"])
        review = self.service.store.get_registration_review(
            evidence["registration_review_id"]
        )
        board = copy.deepcopy(self.manifest["board"])
        changed_case = {**case, "board_id": "BOARD-OTHER"}
        changed_handoff_case = {
            **case,
            "qualified_handoff_json": json.dumps(
                {**qualified_handoff(), "acceptance_report_sha256": "9" * 64}
            ),
        }
        changed_review = {
            **review,
            "board_to_image_matrix": [1, 0, 0.1, 0, 1, 0, 0, 0, 1],
        }
        cases = [
            (
                "server_case_missing",
                "get_case_identity",
                None,
                None,
            ),
            (
                "server_case_identity_mismatch",
                "get_case_identity",
                changed_case,
                None,
            ),
            ("image_missing", "get_image", None, None),
            (
                "image_identity_mismatch",
                "get_image",
                {**image, "sha256": "9" * 64},
                None,
            ),
            (
                "qualified_handoff_mismatch",
                "get_case_identity",
                changed_handoff_case,
                None,
            ),
            ("registration_job_missing", "get_job", None, None),
            (
                "registration_job_mismatch",
                "get_job",
                {**job, "status": "failed"},
                None,
            ),
            (
                "registration_review_missing",
                "get_registration_review",
                None,
                None,
            ),
            (
                "registration_review_mismatch",
                "get_registration_review",
                changed_review,
                None,
            ),
            (
                "board_asset_missing",
                None,
                None,
                RepairEvidenceEngineeringError("missing"),
            ),
            (
                "board_asset_mismatch",
                None,
                None,
                {**board, "board_id": "BOARD-OTHER"},
            ),
        ]
        for reason, store_method, return_value, board_result in cases:
            with self.subTest(reason=reason):
                store_patch = (
                    patch.object(
                        self.service.store,
                        store_method,
                        return_value=return_value,
                    )
                    if store_method
                    else patch.object(
                        self.service.store,
                        "get_case_identity",
                        wraps=self.service.store.get_case_identity,
                    )
                )
                board_patch = (
                    patch(
                        "scripts.visual_qc.server.service."
                        "resolve_board_asset_snapshot",
                        side_effect=board_result,
                    )
                    if isinstance(board_result, Exception)
                    else patch(
                        "scripts.visual_qc.server.service."
                        "resolve_board_asset_snapshot",
                        return_value=board_result or board,
                    )
                )
                with store_patch, board_patch:
                    health = self.service._repair_evidence_link_health(
                        self.manifest
                    )
                self.assertEqual(health["reasons"], [reason])
                self.assertEqual(
                    health["state"],
                    "unavailable" if reason.endswith("_missing") else "stale",
                )

    def test_projection_does_not_leak_to_technician_or_dataset_counts(self):
        case_id = self.manifest["physical_evidence"][0]["server_case_id"]
        before_case = self.client.get(
            f"/api/v1/visual-qc/cases/{case_id}",
            headers={"X-Actor-Id": "link-reviewer"},
        ).json()
        before_training = self.service.training_manifest()
        self.assertEqual(self._import().status_code, 201)
        after_case = self.client.get(
            f"/api/v1/visual-qc/cases/{case_id}",
            headers={"X-Actor-Id": "link-reviewer"},
        ).json()
        self.assertEqual(after_case, before_case)
        after_training = self.service.training_manifest()
        for key in (
            "case_count",
            "annotation_count",
            "category_counts",
            "cases",
        ):
            self.assertEqual(after_training[key], before_training[key])


if __name__ == "__main__":
    unittest.main()
