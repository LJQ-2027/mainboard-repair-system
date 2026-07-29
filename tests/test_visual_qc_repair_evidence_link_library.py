from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import cv2
import numpy as np
from PIL import Image
from pillow_heif import from_pillow

from scripts.visual_qc.repair_case_contract import (
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
    REPAIR_CASE_SCHEMA_V3,
)
from scripts.visual_qc.repair_case_library import stage_repair_case_revision
from scripts.visual_qc.repair_evidence_link_contract import (
    canonical_sha256,
    validate_physical_evidence_snapshot,
)
from scripts.visual_qc.source_library import stage_source_package


ROOT = Path(__file__).resolve().parents[1]

try:
    engineering = importlib.import_module(
        "scripts.visual_qc.repair_evidence_engineering"
    )
except ModuleNotFoundError:
    engineering = None

try:
    link_library = importlib.import_module(
        "scripts.visual_qc.repair_evidence_link_library"
    )
except ModuleNotFoundError:
    link_library = None


def encode_image(value: int) -> bytes:
    image = np.full((120, 180, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Unable to encode test image.")
    return encoded.tobytes()


def write_heic(path, value=120):
    image = Image.new("RGB", (180, 120), (value, value, value))
    from_pillow(image).save(path, quality=90)


def registration_point(x: float, y: float) -> dict:
    return {
        "board": {"x": x, "y": y},
        "image": {"x": x, "y": y},
    }


def physical_snapshot(
    *,
    package_sha256: str,
    image_sha256: str,
    side_id="main_page_2",
    capture_stage="after_repair",
) -> dict:
    handoff = {
        "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
        "handoff_schema_version": "VISUAL-QC-PHYSICAL-HANDOFF-V1",
        "source_package_manifest_sha256": package_sha256,
        "archived_intake_manifest_sha256": "a" * 64,
        "acceptance_report_sha256": "b" * 64,
        "acceptance_action": "manual_registration_required",
        "registration_review_required": True,
        "field_accuracy_claim_allowed": False,
    }
    anchors = [
        registration_point(0.1, 0.1),
        registration_point(0.9, 0.1),
        registration_point(0.9, 0.9),
        registration_point(0.1, 0.9),
    ]
    snapshot = {
        "schema_version": "VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1",
        "physical_evidence_id": f"physical-{side_id}",
        "server_case_id": f"server-{side_id}",
        "intake": {
            "batch_id": "batch-after",
            "entry_id": f"session-after-{side_id}",
        },
        "board_key": "bg6h-f069",
        "board_id": "BOARD-F069-MAIN-V1.2",
        "side_id": side_id,
        "capture_stage": capture_stage,
        "evidence_role": "physical_capture",
        "qualified_handoff": handoff,
        "qualified_handoff_sha256": canonical_sha256(handoff),
        "image_id": f"image-{side_id}",
        "image_sha256": image_sha256,
        "job_id": f"job-{side_id}",
        "registration_review_id": f"review-{side_id}",
        "registration": {
            "method": "reviewed_manual_four_point",
            "board_to_image_matrix": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            "solve_anchors": anchors,
            "independent_check_points": [registration_point(0.5, 0.5)],
            "error": {"count": 1, "rms": 0.0, "maximum": 0.0},
        },
        "physical_evidence_snapshot_sha256": "",
    }
    snapshot["physical_evidence_snapshot_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in snapshot.items()
            if key != "physical_evidence_snapshot_sha256"
        }
    )
    return validate_physical_evidence_snapshot(snapshot)


class VisualQcRepairEvidenceEngineeringTests(unittest.TestCase):
    def test_engineering_module_exists(self):
        self.assertIsNotNone(engineering)

    @unittest.skipUnless(engineering is not None, "engineering module not implemented")
    def test_resolves_f069_u4000_as_low_confidence_reviewed_point(self):
        snapshot = engineering.resolve_engineering_target(
            project_root=ROOT,
            board_key="bg6h-f069",
            target={
                "kind": "designator",
                "side_id": "main_page_2",
                "designator": "U4000",
            },
        )

        self.assertEqual(snapshot["component_id"], "F069-MAIN-U4000")
        self.assertEqual(snapshot["designator"], "U4000")
        self.assertEqual(snapshot["side_id"], "main_page_2")
        self.assertEqual(snapshot["geometry_source_status"], "low")
        self.assertEqual(snapshot["location"]["kind"], "normalized_point")
        self.assertFalse(snapshot["semantic_identity_proven"])

    @unittest.skipUnless(engineering is not None, "engineering module not implemented")
    def test_board_snapshot_binds_catalog_side_manifest_and_cross_source(self):
        snapshot = engineering.resolve_board_asset_snapshot(
            ROOT, "bg6h-f069"
        )

        self.assertEqual(snapshot["board_key"], "bg6h-f069")
        self.assertEqual(snapshot["board_id"], "BOARD-F069-MAIN-V1.2")
        self.assertEqual(
            snapshot["catalog_asset"]["path"],
            "knowledge-base/repair-workbench-boards.json",
        )
        kinds = {item["kind"] for item in snapshot["compiled_sources"]}
        self.assertIn("side_manifest", kinds)
        self.assertIn("cross_source_registration", kinds)
        self.assertRegex(snapshot["board_snapshot_sha256"], r"^[0-9a-f]{64}$")

    @unittest.skipUnless(engineering is not None, "engineering module not implemented")
    def test_resolves_whole_board_and_normalized_regions(self):
        whole = engineering.resolve_engineering_target(
            project_root=ROOT,
            board_key="bg6h-f069",
            target={"kind": "whole_board", "side_id": "main_page_1"},
        )
        rectangle = engineering.resolve_engineering_target(
            project_root=ROOT,
            board_key="bg6h-f069",
            target={
                "kind": "board_region",
                "side_id": "main_page_2",
                "region": {
                    "kind": "normalized_rectangle",
                    "x": 0.1,
                    "y": 0.2,
                    "width": 0.3,
                    "height": 0.4,
                },
            },
        )
        polygon = engineering.resolve_engineering_target(
            project_root=ROOT,
            board_key="bg6h-f069",
            target={
                "kind": "board_region",
                "side_id": "main_page_2",
                "region": {
                    "kind": "normalized_polygon",
                    "points": [
                        {"x": 0.1, "y": 0.1},
                        {"x": 0.8, "y": 0.1},
                        {"x": 0.4, "y": 0.8},
                    ],
                },
            },
        )

        self.assertEqual(whole, {"kind": "whole_board", "side_id": "main_page_1"})
        self.assertEqual(rectangle["region"]["width"], 0.3)
        self.assertEqual(len(polygon["region"]["points"]), 3)

    @unittest.skipUnless(engineering is not None, "engineering module not implemented")
    def test_rejects_unknown_cross_side_and_invalid_geometry(self):
        invalid_targets = [
            {"kind": "whole_board", "side_id": "missing"},
            {
                "kind": "designator",
                "side_id": "main_page_1",
                "designator": "U4000",
            },
            {
                "kind": "designator",
                "side_id": "main_page_2",
                "designator": "U9999",
            },
            {
                "kind": "board_region",
                "side_id": "main_page_2",
                "region": {
                    "kind": "normalized_rectangle",
                    "x": 0.9,
                    "y": 0.2,
                    "width": 0.2,
                    "height": 0.2,
                },
            },
            {
                "kind": "board_region",
                "side_id": "main_page_2",
                "region": {
                    "kind": "normalized_rectangle",
                    "x": float("nan"),
                    "y": 0.2,
                    "width": 0.2,
                    "height": 0.2,
                },
            },
            {
                "kind": "board_region",
                "side_id": "main_page_2",
                "region": {
                    "kind": "normalized_polygon",
                    "points": [
                        {"x": 0.1, "y": 0.1},
                        {"x": 0.2, "y": 0.2},
                        {"x": 0.3, "y": 0.3},
                    ],
                },
            },
            {
                "kind": "board_region",
                "side_id": "main_page_2",
                "region": {
                    "kind": "normalized_polygon",
                    "points": [
                        {"x": 0.1, "y": 0.1},
                        {"x": 0.9, "y": 0.9},
                        {"x": 0.1, "y": 0.9},
                        {"x": 0.9, "y": 0.1},
                    ],
                },
            },
        ]
        for target in invalid_targets:
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    engineering.resolve_engineering_target(
                        project_root=ROOT,
                        board_key="bg6h-f069",
                        target=target,
                    )

    @unittest.skipUnless(engineering is not None, "engineering module not implemented")
    def test_rejects_duplicate_entity_and_asset_hash_drift(self):
        with tempfile.TemporaryDirectory(prefix="repair-link-engineering-") as temp:
            project = Path(temp) / "project"
            shutil.copytree(ROOT / "knowledge-base", project / "knowledge-base")
            cross_path = (
                project / "knowledge-base" / "f069-cross-source-registration.json"
            )
            cross = json.loads(cross_path.read_text(encoding="utf-8"))
            entity = next(
                item for item in cross["entities"] if item["designator"] == "U4000"
            )
            cross["entities"].append(copy.deepcopy(entity))
            cross_path.write_text(
                json.dumps(cross, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                engineering.resolve_engineering_target(
                    project_root=project,
                    board_key="bg6h-f069",
                    target={
                        "kind": "designator",
                        "side_id": "main_page_2",
                        "designator": "U4000",
                    },
                )

            cross["entities"].pop()
            cross_path.write_text(
                json.dumps(cross, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            geometry_path = (
                project / "knowledge-base" / "f069-board-compiled-page-2.json"
            )
            geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
            component = next(
                item
                for item in geometry["components"]
                if item["designator"] == "U4000"
            )
            geometry["components"].append(copy.deepcopy(component))
            geometry_path.write_text(
                json.dumps(geometry, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                engineering.resolve_engineering_target(
                    project_root=project,
                    board_key="bg6h-f069",
                    target={
                        "kind": "designator",
                        "side_id": "main_page_2",
                        "designator": "U4000",
                    },
                )

            catalog_path = (
                project / "knowledge-base" / "repair-workbench-boards.json"
            )
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["boards"]["bg6h-f069"]["data"] = "../../outside.json"
            catalog_path.write_text(
                json.dumps(catalog, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                engineering.resolve_board_asset_snapshot(project, "bg6h-f069")


class VisualQcRepairEvidenceLinkLibraryAvailabilityTests(unittest.TestCase):
    def test_link_library_module_exists(self):
        self.assertIsNotNone(link_library)


@unittest.skipUnless(link_library is not None, "link library not implemented")
class VisualQcAuthorityTrackerTests(unittest.TestCase):
    def test_recheck_rejects_identical_bytes_replaced_between_check_and_open(self):
        with tempfile.TemporaryDirectory(
            prefix="visual-qc-authority-race-"
        ) as temporary:
            root = Path(temporary)
            authority = root / "authority.json"
            replacement = root / "replacement.json"
            content = b'{"same":"bytes"}\n'
            authority.write_bytes(content)
            replacement.write_bytes(content)
            tracker = link_library._AuthorityTracker()
            tracker.capture(authority, "authority")
            real_open = os.open
            swapped = False

            def race_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(path).absolute() == authority.absolute():
                    os.replace(replacement, authority)
                    swapped = True
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(
                link_library.os, "open", side_effect=race_open
            ):
                with self.assertRaisesRegex(
                    ValueError, "authority changed while validating"
                ):
                    tracker.recheck_all()
            self.assertTrue(swapped)
            self.assertEqual(authority.read_bytes(), content)

    def test_recheck_rejects_symlink_replacement_when_supported(self):
        with tempfile.TemporaryDirectory(
            prefix="visual-qc-authority-symlink-"
        ) as temporary:
            root = Path(temporary)
            authority = root / "authority.json"
            target = root / "target.json"
            content = b'{"same":"bytes"}\n'
            authority.write_bytes(content)
            target.write_bytes(content)
            tracker = link_library._AuthorityTracker()
            tracker.capture(authority, "authority")
            authority.unlink()
            try:
                authority.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"File symlink is unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "reparse point or symlink"):
                tracker.recheck_all()

    def test_recheck_rejects_directory_reparse_replacement_when_supported(self):
        with tempfile.TemporaryDirectory(
            prefix="visual-qc-authority-reparse-"
        ) as temporary:
            root = Path(temporary)
            original = root / "original"
            held = root / "held"
            alternate = root / "alternate"
            original.mkdir()
            alternate.mkdir()
            content = b'{"same":"bytes"}\n'
            authority = original / "authority.json"
            authority.write_bytes(content)
            (alternate / "authority.json").write_bytes(content)
            tracker = link_library._AuthorityTracker()
            tracker.capture(authority, "authority")
            original.rename(held)
            if os.name == "nt":
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(original), str(alternate)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=False,
                )
                if result.returncode != 0:
                    held.rename(original)
                    self.skipTest(
                        f"Directory junction is unavailable: {result.stderr}"
                    )
            else:
                original.symlink_to(alternate, target_is_directory=True)
            try:
                with self.assertRaisesRegex(
                    ValueError, "reparse point or symlink"
                ):
                    tracker.recheck_all()
            finally:
                if os.name == "nt" and original.exists():
                    os.rmdir(original)
                elif original.is_symlink():
                    original.unlink()


@unittest.skipUnless(link_library is not None, "link library not implemented")
class VisualQcRepairEvidenceDeepChainTests(unittest.TestCase):
    def test_deep_chain_is_iterative_single_scan_and_linear_dispatch(self):
        depth = min(sys.getrecursionlimit() + 75, 1500)
        with tempfile.TemporaryDirectory(
            prefix="visual-qc-link-deep-chain-"
        ) as temporary:
            library = Path(temporary) / "controlled-library"
            revisions = (
                library
                / "repair-evidence-links"
                / "deep-chain"
                / "revisions"
            )
            previous_sha = None
            head_path = None
            for revision in range(1, depth + 1):
                directory = revisions / f"{revision:04d}"
                directory.mkdir(parents=True)
                payload = {
                    "link_set_id": "deep-chain",
                    "revision": revision,
                    "previous_manifest_sha256": previous_sha,
                }
                serialized = (
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                ).encode("utf-8")
                head_path = directory / "repair-evidence-link.json"
                head_path.write_bytes(serialized)
                (directory / ".complete").write_bytes(b"complete\n")
                previous_sha = hashlib.sha256(serialized).hexdigest()

            original_scan = link_library._scan_revision_directories
            with mock.patch.object(
                link_library,
                "_scan_revision_directories",
                wraps=original_scan,
            ) as scan, mock.patch.object(
                link_library,
                "validate_repair_evidence_link_manifest",
                side_effect=lambda value: value,
            ) as contract, mock.patch.object(
                link_library,
                "_assert_append_only",
            ) as transition, mock.patch.object(
                link_library,
                "_validate_head_authorities",
            ) as authorities:
                result = (
                    link_library.validate_repair_evidence_link_revision_on_disk(
                        head_path,
                        project_root=ROOT,
                        library_root=library,
                    )
                )

            self.assertEqual(result["revision"], depth)
            self.assertEqual(scan.call_count, 1)
            self.assertEqual(contract.call_count, depth)
            self.assertEqual(transition.call_count, depth - 1)
            self.assertEqual(authorities.call_count, 1)


@unittest.skipUnless(link_library is not None, "link library not implemented")
class VisualQcRepairEvidenceLinkLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="visual-qc-repair-link-"
        )
        self.root = Path(self.temporary.name)
        self.library = self.root / "controlled-library"
        image = self.root / "after.jpg"
        image.write_bytes(encode_image(160))
        self.package = stage_source_package(
            project_root=ROOT,
            library_root=self.library,
            package_id="pkg-f069-after",
            batch_id="batch-after",
            board_key="bg6h-f069",
            capture_session_id="session-after",
            capture_stage="after_repair",
            capture_setup_id="standard-bench",
            image_assignments=[("main_page_2", image)],
            milo_physical_source_confirmed=True,
            capture_checklist_confirmed=True,
        )
        identity = {
            "reported_models": ["BG6H", "BG6h"],
            "catalog_models": ["BG6H", "BG6h"],
            "mapping_status": "exact_catalog_match",
            "resolved_models": ["BG6H", "BG6h"],
            "resolution_note": None,
            "evidence_refs": [],
        }
        case_record = {
            "device_identity": identity,
            "supporting_evidence_descriptions": {},
            "reported_symptoms": [
                {
                    "symptom_id": "symptom-no-power",
                    "text": "不开机",
                    "source_wording": None,
                    "fault_code": None,
                    "evidence_refs": [],
                }
            ],
            "findings": [
                {
                    "finding_id": "reported-emmc-fault",
                    "claim_status": "reported",
                    "description": "EMMC坏",
                    "defect_category": None,
                    "designator": None,
                    "side_id": None,
                    "region": None,
                    "evidence_refs": [],
                },
                {
                    "finding_id": "documented-u4000",
                    "claim_status": "documented",
                    "description": "U4000 is the documented target.",
                    "defect_category": None,
                    "designator": "U4000",
                    "side_id": "main_page_2",
                    "region": None,
                    "evidence_refs": [],
                },
                {
                    "finding_id": "cross-side-u4000",
                    "claim_status": "documented",
                    "description": "Opposite-side U4000 report.",
                    "defect_category": None,
                    "designator": "U4000",
                    "side_id": "main_page_1",
                    "region": None,
                    "evidence_refs": [],
                }
            ],
            "repair_actions": [
                {
                    "action_id": "inspect-u4000",
                    "description": "Inspect the documented target.",
                    "action_category": "inspection",
                    "target_designator": "U4000",
                    "side_id": "main_page_2",
                    "region": None,
                    "evidence_refs": [],
                }
            ],
            "outcome": {
                "status": "repair_completed",
                "description": "Repair completed.",
                "verification_description": None,
                "evidence_refs": [],
            },
            "corrections": [],
        }
        self.case_record = copy.deepcopy(case_record)
        self.case = stage_repair_case_revision(
            project_root=ROOT,
            library_root=self.library,
            repair_case_id="case-f069-0001",
            board_key="bg6h-f069",
            package_assignments=[
                ("after_repair", self.package["source_package_path"])
            ],
            case_record=case_record,
            supporting_assignments=[],
            previous_manifest_path=None,
        )
        package_sha = self.package["validated_source_package"]["manifest_sha256"]
        self.package_image_sha = self.package["validated_source_package"][
            "entries"
        ][0]["sha256"]
        self.physical_path = self.root / "physical.json"
        self.physical_path.write_text(
            json.dumps(
                physical_snapshot(
                    package_sha256=package_sha,
                    image_sha256=self.package_image_sha,
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.binding_path = self.root / "bindings.json"
        self.write_binding_record()

    def tearDown(self):
        self.temporary.cleanup()

    def binding(self, **overrides):
        binding = {
            "binding_id": "binding-emmc-u4000",
            "repair_case_reference_id": "case-f069-r1",
            "source_fact": {
                "kind": "finding",
                "fact_id": "reported-emmc-fault",
            },
            "physical_evidence_id": "physical-main_page_2",
            "target": {
                "kind": "designator",
                "side_id": "main_page_2",
                "designator": "U4000",
            },
            "association_status": "possibly_related",
            "visibility_status": "not_assessed",
            "evidence_bases": [
                {"kind": "repair_case_fact"},
                {"kind": "engineering_identity"},
            ],
            "supersedes_binding_id": None,
        }
        binding.update(overrides)
        return binding

    def write_binding_record(self, bindings=None):
        record = {
            "physical_evidence_ids": ["physical-main_page_2"],
            "bindings": bindings or [self.binding()],
        }
        self.binding_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record

    def publish(self, **overrides):
        options = {
            "project_root": ROOT,
            "library_root": self.library,
            "link_set_id": "link-f069-case-1",
            "repair_case_manifest_path": self.case["manifest_path"],
            "physical_evidence_paths": [self.physical_path],
            "binding_record_path": self.binding_path,
            "previous_manifest_path": None,
        }
        options.update(overrides)
        return link_library.publish_repair_evidence_link_revision(**options)

    def stage_v3_case(self, *, evidence_mode):
        record = copy.deepcopy(self.case_record)
        record["evidence_mode"] = evidence_mode
        record["supporting_evidence_contexts"] = []
        package_assignments = [
            ("after_repair", self.package["source_package_path"])
        ]
        supporting_assignments = []
        if evidence_mode == "supporting_only":
            evidence_id = "repair-progress-heic"
            source = self.root / "repair-progress.heic"
            write_heic(source, value=145)
            evidence_ref = {
                "kind": "supporting_evidence",
                "evidence_id": evidence_id,
            }
            record["device_identity"]["evidence_refs"] = [evidence_ref]
            record["supporting_evidence_contexts"] = [
                {
                    "evidence_id": evidence_id,
                    "evidence_role": "repair_in_progress_photo",
                    "source_capture_stage": "维修中",
                    "source_board_area": "屏蔽罩内局部",
                }
            ]
            record["supporting_evidence_descriptions"] = {
                evidence_id: "Milo supplied repair-in-progress HEIC"
            }
            package_assignments = []
            supporting_assignments = [(evidence_id, source)]
        return stage_repair_case_revision(
            project_root=ROOT,
            library_root=self.library,
            repair_case_id=f"case-f069-v3-{evidence_mode}",
            board_key="bg6h-f069",
            package_assignments=package_assignments,
            case_record=record,
            supporting_assignments=supporting_assignments,
            previous_manifest_path=None,
        )

    def stage_corrected_case(self):
        record = copy.deepcopy(self.case_record)
        record["corrections"] = [
            {
                "correction_id": "correct-emmc-report",
                "corrects_fact_id": "reported-emmc-fault",
                "description": "Replace the unlocated report with reviewed U4000.",
                "replacement_fact_id": "documented-u4000",
                "evidence_refs": [],
            }
        ]
        return stage_repair_case_revision(
            project_root=ROOT,
            library_root=self.library,
            repair_case_id="case-f069-0001",
            board_key="bg6h-f069",
            package_assignments=[
                ("after_repair", self.package["source_package_path"])
            ],
            case_record=record,
            supporting_assignments=[],
            previous_manifest_path=self.case["manifest_path"],
        )

    def publish_second_revision(
        self, first: dict, *, corrected_case: dict | None, supersedes: bool
    ):
        replacement = self.binding(
            binding_id="binding-reviewed-u4000",
            repair_case_reference_id=(
                "case-f069-r2" if corrected_case else "case-f069-r1"
            ),
            source_fact=(
                {"kind": "finding", "fact_id": "documented-u4000"}
                if corrected_case
                else {"kind": "finding", "fact_id": "reported-emmc-fault"}
            ),
            association_status=(
                "related" if corrected_case else "not_related"
            ),
            supersedes_binding_id=(
                "binding-emmc-u4000" if supersedes else None
            ),
        )
        self.write_binding_record([replacement])
        return self.publish(
            repair_case_manifest_path=(
                corrected_case["manifest_path"]
                if corrected_case
                else self.case["manifest_path"]
            ),
            previous_manifest_path=first["manifest_path"],
        )

    def test_first_publication_exact_replay_and_disk_validation(self):
        created = self.publish()
        replay = self.publish()
        validated = link_library.validate_repair_evidence_link_revision_on_disk(
            created["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )

        self.assertEqual(created["state"], "created")
        self.assertEqual(replay["state"], "existing")
        self.assertEqual(created["manifest_sha256"], replay["manifest_sha256"])
        self.assertEqual(validated["revision"], 1)
        self.assertEqual(
            (created["manifest_path"].parent / ".complete").read_bytes(),
            b"complete\n",
        )
        binding = validated["bindings"][0]
        self.assertTrue(binding["boundaries"]["model_identity_resolved"])
        self.assertEqual(
            binding["target"]["engineering"]["component_id"],
            "F069-MAIN-U4000",
        )
        self.assertEqual(
            binding["target"]["engineering"]["geometry_source_status"], "low"
        )

    def test_v3_supporting_only_cannot_bind_physical_evidence(self):
        supporting_only = self.stage_v3_case(evidence_mode="supporting_only")
        link_set_id = "link-v3-supporting-only"
        link_root = (
            self.library / "repair-evidence-links" / link_set_id / "revisions"
        )

        with self.assertRaisesRegex(
            link_library.RepairEvidenceLinkLibraryError,
            "source package is not linked",
        ):
            self.publish(
                link_set_id=link_set_id,
                repair_case_manifest_path=supporting_only["manifest_path"],
            )

        self.assertFalse(any(link_root.rglob(link_library.LINK_MANIFEST_NAME)))
        self.assertFalse(any(link_root.rglob(".complete")))
        self.assertEqual(
            list(link_root.iterdir()) if link_root.exists() else [],
            [],
        )

    def test_v3_package_linked_uses_v2_link_flow_and_exact_authority(self):
        package_linked = self.stage_v3_case(evidence_mode="package_linked")
        link_set_id = "link-v3-package-linked"
        created = self.publish(
            link_set_id=link_set_id,
            repair_case_manifest_path=package_linked["manifest_path"],
        )
        replay = self.publish(
            link_set_id=link_set_id,
            repair_case_manifest_path=package_linked["manifest_path"],
        )
        validated = link_library.validate_repair_evidence_link_revision_on_disk(
            created["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        package = self.package["validated_source_package"]
        reference = validated["repair_case_references"][0]
        physical = validated["physical_evidence"][0]

        self.assertEqual(created["state"], "created")
        self.assertEqual(replay["state"], "existing")
        self.assertEqual(created["manifest_sha256"], replay["manifest_sha256"])
        self.assertEqual(
            created["manifest_path"].read_bytes(),
            replay["manifest_path"].read_bytes(),
        )
        self.assertEqual(
            (created["manifest_path"].parent / ".complete").read_bytes(),
            b"complete\n",
        )
        self.assertEqual(reference["schema_version"], REPAIR_CASE_SCHEMA_V3)
        self.assertEqual(
            physical["qualified_handoff"]["source_package_manifest_sha256"],
            package["manifest_sha256"],
        )
        self.assertEqual(
            physical["intake"]["entry_id"],
            package["entries"][0]["entry_id"],
        )
        self.assertTrue(
            validated["bindings"][0]["boundaries"]["model_identity_resolved"]
        )

        forged_package = physical_snapshot(
            package_sha256="f" * 64,
            image_sha256=self.package_image_sha,
        )
        self.physical_path.write_text(
            json.dumps(forged_package, ensure_ascii=False),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            link_library.RepairEvidenceLinkLibraryError,
            "source package is not linked",
        ):
            self.publish(
                link_set_id="link-v3-forged-package",
                repair_case_manifest_path=package_linked["manifest_path"],
            )

        forged_entry = physical_snapshot(
            package_sha256=package["manifest_sha256"],
            image_sha256=self.package_image_sha,
        )
        forged_entry["intake"]["entry_id"] = "session-after-other-side"
        forged_entry["physical_evidence_snapshot_sha256"] = canonical_sha256(
            {
                key: value
                for key, value in forged_entry.items()
                if key != "physical_evidence_snapshot_sha256"
            }
        )
        self.physical_path.write_text(
            json.dumps(forged_entry, ensure_ascii=False),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            link_library.RepairEvidenceLinkLibraryError,
            "intake entry is not linked",
        ):
            self.publish(
                link_set_id="link-v3-forged-entry",
                repair_case_manifest_path=package_linked["manifest_path"],
            )
        for rejected_link_set in (
            "link-v3-forged-package",
            "link-v3-forged-entry",
        ):
            revisions = (
                self.library
                / "repair-evidence-links"
                / rejected_link_set
                / "revisions"
            )
            self.assertEqual(
                list(revisions.iterdir()) if revisions.exists() else [],
                [],
            )

    def test_model_identity_reader_preserves_v1_and_requires_exact_v2_v3_bool(self):
        self.assertTrue(
            link_library._model_identity_resolved(
                {"schema_version": REPAIR_CASE_SCHEMA_V1}
            )
        )
        for schema_version in (REPAIR_CASE_SCHEMA_V2, REPAIR_CASE_SCHEMA_V3):
            with self.subTest(schema_version=schema_version):
                self.assertFalse(
                    link_library._model_identity_resolved(
                        {
                            "schema_version": schema_version,
                            "boundaries": {"model_identity_resolved": False},
                        }
                    )
                )
                with self.assertRaisesRegex(
                    link_library.RepairEvidenceLinkLibraryError,
                    "model identity boundary is invalid",
                ):
                    link_library._model_identity_resolved(
                        {
                            "schema_version": schema_version,
                            "boundaries": {"model_identity_resolved": 0},
                        }
                    )
        with self.assertRaisesRegex(
            link_library.RepairEvidenceLinkLibraryError,
            "schema version is unsupported",
        ):
            link_library._model_identity_resolved(
                {
                    "schema_version": "VISUAL-QC-REPAIR-CASE-SOURCE-V999",
                    "boundaries": {"model_identity_resolved": False},
                }
            )

    def test_append_only_revision_and_binding_supersession(self):
        first = self.publish()
        replacement = self.binding(
            binding_id="binding-emmc-u4000-rejected",
            association_status="not_related",
            supersedes_binding_id="binding-emmc-u4000",
        )
        self.write_binding_record([replacement])
        second = self.publish(previous_manifest_path=first["manifest_path"])
        validated = link_library.validate_repair_evidence_link_revision_on_disk(
            second["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )

        self.assertEqual(second["revision"], 2)
        self.assertEqual(
            [item["binding_id"] for item in validated["bindings"]],
            ["binding-emmc-u4000", "binding-emmc-u4000-rejected"],
        )
        self.assertEqual(
            validated["bindings"][1]["supersedes_binding_id"],
            "binding-emmc-u4000",
        )

    def test_derives_source_fact_supersession_independently(self):
        first = self.publish()
        corrected = self.stage_corrected_case()
        second = self.publish_second_revision(
            first, corrected_case=corrected, supersedes=False
        )
        derived = link_library.derive_repair_evidence_link_states_on_disk(
            second["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        state = {item["binding_id"]: item for item in derived["bindings"]}[
            "binding-emmc-u4000"
        ]
        self.assertTrue(state["source_fact_superseded"])
        self.assertEqual(state["replacement_fact_id"], "documented-u4000")
        self.assertFalse(state["binding_superseded"])
        self.assertIsNone(state["replacement_binding_id"])

    def test_derives_binding_supersession_independently(self):
        first = self.publish()
        second = self.publish_second_revision(
            first, corrected_case=None, supersedes=True
        )
        derived = link_library.derive_repair_evidence_link_states_on_disk(
            second["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        state = {item["binding_id"]: item for item in derived["bindings"]}[
            "binding-emmc-u4000"
        ]
        self.assertFalse(state["source_fact_superseded"])
        self.assertIsNone(state["replacement_fact_id"])
        self.assertTrue(state["binding_superseded"])
        self.assertEqual(
            state["replacement_binding_id"], "binding-reviewed-u4000"
        )

    def test_derives_combined_supersession_without_conflating_states(self):
        first = self.publish()
        corrected = self.stage_corrected_case()
        second = self.publish_second_revision(
            first, corrected_case=corrected, supersedes=True
        )
        derived = link_library.derive_repair_evidence_link_states_on_disk(
            second["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        state = {item["binding_id"]: item for item in derived["bindings"]}[
            "binding-emmc-u4000"
        ]
        self.assertEqual(
            state,
            {
                "binding_id": "binding-emmc-u4000",
                "source_fact_superseded": True,
                "replacement_fact_id": "documented-u4000",
                "binding_superseded": True,
                "replacement_binding_id": "binding-reviewed-u4000",
            },
        )
        canonical = json.loads(
            second["manifest_path"].read_text(encoding="utf-8")
        )
        self.assertNotIn("source_fact_superseded", canonical["bindings"][0])
        self.assertNotIn("binding_superseded", canonical["bindings"][0])

    def test_related_u4000_requires_semantic_proof(self):
        self.write_binding_record(
            [self.binding(association_status="related")]
        )
        with self.assertRaises(ValueError):
            self.publish()

    def test_exact_source_fact_designator_can_prove_related_target(self):
        binding = self.binding(association_status="related")
        binding["source_fact"] = {
            "kind": "finding",
            "fact_id": "documented-u4000",
        }
        self.write_binding_record([binding])
        created = self.publish(link_set_id="link-documented-u4000")
        validated = link_library.validate_repair_evidence_link_revision_on_disk(
            created["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        self.assertTrue(
            validated["bindings"][0]["target"]["engineering"][
                "semantic_identity_proven"
            ]
        )

    def test_derives_all_source_fact_selector_snapshots(self):
        selectors = [
            ("symptom-binding", "reported_symptom", "symptom-no-power"),
            ("finding-binding", "finding", "reported-emmc-fault"),
            ("action-binding", "repair_action", "inspect-u4000"),
            ("outcome-binding", "outcome", "outcome"),
        ]
        bindings = []
        for binding_id, kind, fact_id in selectors:
            bindings.append(
                self.binding(
                    binding_id=binding_id,
                    source_fact={"kind": kind, "fact_id": fact_id},
                    target={"kind": "whole_board", "side_id": "main_page_2"},
                    evidence_bases=[{"kind": "repair_case_fact"}],
                )
            )
        self.write_binding_record(bindings)
        created = self.publish(link_set_id="link-all-source-facts")
        validated = link_library.validate_repair_evidence_link_revision_on_disk(
            created["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        facts = {
            item["source_fact"]["kind"]: item["source_fact"]
            for item in validated["bindings"]
        }
        self.assertEqual(facts["reported_symptom"]["display"]["text"], "不开机")
        self.assertEqual(
            facts["finding"]["display"]["claim_status"], "reported"
        )
        self.assertEqual(
            facts["repair_action"]["display"]["text"],
            "Inspect the documented target.",
        )
        self.assertEqual(facts["outcome"]["fact_id"], "outcome")

    def test_build_caches_board_assets_and_identical_target_selectors(self):
        bindings = [
            self.binding(binding_id="cached-target-one"),
            self.binding(binding_id="cached-target-two"),
        ]
        record = self.write_binding_record(bindings)
        with mock.patch.object(
            link_library,
            "load_board_asset_context",
            wraps=link_library.load_board_asset_context,
        ) as load_context, mock.patch.object(
            link_library,
            "resolve_engineering_target_from_context",
            wraps=link_library.resolve_engineering_target_from_context,
        ) as resolve_target:
            manifest = link_library.build_repair_evidence_link_revision(
                project_root=ROOT,
                library_root=self.library,
                link_set_id="link-build-cache",
                repair_case_manifest_path=self.case["manifest_path"],
                physical_evidence_paths=[self.physical_path],
                binding_record=record,
            )

        self.assertEqual(len(manifest["bindings"]), 2)
        self.assertEqual(load_context.call_count, 1)
        self.assertEqual(resolve_target.call_count, 1)

    def test_validation_caches_targets_and_reloads_board_only_for_toctou(self):
        self.write_binding_record(
            [
                self.binding(binding_id="cached-validation-one"),
                self.binding(binding_id="cached-validation-two"),
            ]
        )
        created = self.publish(link_set_id="link-validation-cache")
        with mock.patch.object(
            link_library,
            "load_board_asset_context",
            wraps=link_library.load_board_asset_context,
        ) as load_context, mock.patch.object(
            link_library,
            "resolve_engineering_target_from_context",
            wraps=link_library.resolve_engineering_target_from_context,
        ) as resolve_target:
            validated = (
                link_library.validate_repair_evidence_link_revision_on_disk(
                    created["manifest_path"],
                    project_root=ROOT,
                    library_root=self.library,
                )
            )

        self.assertEqual(len(validated["bindings"]), 2)
        self.assertEqual(load_context.call_count, 2)
        self.assertEqual(resolve_target.call_count, 1)

    def test_rejects_unlinked_source_package_and_cross_side(self):
        invalid = physical_snapshot(
            package_sha256="f" * 64,
            image_sha256=self.package_image_sha,
        )
        self.physical_path.write_text(
            json.dumps(invalid, ensure_ascii=False),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            self.publish()

        package_sha = self.package["validated_source_package"]["manifest_sha256"]
        opposite = physical_snapshot(
            package_sha256=package_sha,
            image_sha256=self.package_image_sha,
            side_id="main_page_1",
        )
        self.physical_path.write_text(
            json.dumps(opposite, ensure_ascii=False),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            self.publish()

    def test_rejects_forged_image_hash_and_capture_stage_swap(self):
        package_sha = self.package["validated_source_package"]["manifest_sha256"]
        forged = physical_snapshot(
            package_sha256=package_sha,
            image_sha256="f" * 64,
        )
        self.physical_path.write_text(
            json.dumps(forged, ensure_ascii=False),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "image hash"):
            self.publish(link_set_id="link-forged-image")

        stage_swap = physical_snapshot(
            package_sha256=package_sha,
            image_sha256=self.package_image_sha,
            capture_stage="before_repair",
        )
        self.physical_path.write_text(
            json.dumps(stage_swap, ensure_ascii=False),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "capture stage"):
            self.publish(link_set_id="link-stage-swap")

    def test_cross_side_source_fact_does_not_prove_designator(self):
        binding = self.binding()
        binding["source_fact"] = {
            "kind": "finding",
            "fact_id": "cross-side-u4000",
        }
        self.write_binding_record([binding])
        candidate = self.publish(link_set_id="link-cross-side-candidate")
        validated = link_library.validate_repair_evidence_link_revision_on_disk(
            candidate["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        self.assertFalse(
            validated["bindings"][0]["target"]["engineering"][
                "semantic_identity_proven"
            ]
        )

        binding["association_status"] = "related"
        self.write_binding_record([binding])
        with self.assertRaises(ValueError):
            self.publish(link_set_id="link-cross-side-related")

    def test_on_disk_validation_reopens_authoritative_repair_case(self):
        created = self.publish()
        case_path = self.case["manifest_path"]
        original = case_path.read_bytes()
        case_path.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            link_library.validate_repair_evidence_link_revision_on_disk(
                created["manifest_path"],
                project_root=ROOT,
                library_root=self.library,
            )

    def test_on_disk_validation_rejects_manifest_mutation_during_validation(self):
        created = self.publish()
        manifest_path = created["manifest_path"]
        original_bytes = manifest_path.read_bytes()
        original_authorities = link_library._reference_authorities

        def mutate_manifest(*args, **kwargs):
            result = original_authorities(*args, **kwargs)
            manifest_path.write_bytes(original_bytes + b" ")
            return result

        try:
            with mock.patch.object(
                link_library,
                "_reference_authorities",
                side_effect=mutate_manifest,
            ):
                with self.assertRaisesRegex(
                    ValueError, "manifest changed while validating"
                ):
                    link_library.validate_repair_evidence_link_revision_on_disk(
                        manifest_path,
                        project_root=ROOT,
                        library_root=self.library,
                    )
        finally:
            manifest_path.write_bytes(original_bytes)

    def test_on_disk_validation_rejects_board_mutation_during_validation(self):
        created = self.publish()
        catalog_path = ROOT / "knowledge-base" / "repair-workbench-boards.json"
        original_bytes = catalog_path.read_bytes()
        original_authorities = link_library._reference_authorities

        def mutate_board(*args, **kwargs):
            result = original_authorities(*args, **kwargs)
            catalog_path.write_bytes(original_bytes + b" ")
            return result

        try:
            with mock.patch.object(
                link_library,
                "_reference_authorities",
                side_effect=mutate_board,
            ):
                with self.assertRaisesRegex(
                    ValueError, "board catalog asset changed while validating"
                ):
                    link_library.validate_repair_evidence_link_revision_on_disk(
                        created["manifest_path"],
                        project_root=ROOT,
                        library_root=self.library,
                    )
        finally:
            catalog_path.write_bytes(original_bytes)

    def test_validation_rechecks_repair_case_after_dependency_validation(self):
        created = self.publish()
        case_path = self.case["manifest_path"]
        original_bytes = case_path.read_bytes()
        original_head_validation = link_library._validate_head_authorities

        def mutate_case(*args, **kwargs):
            result = original_head_validation(*args, **kwargs)
            case_path.write_bytes(original_bytes + b" ")
            return result

        try:
            with mock.patch.object(
                link_library,
                "_validate_head_authorities",
                side_effect=mutate_case,
            ):
                with self.assertRaisesRegex(
                    ValueError, "repair case manifest changed while validating"
                ):
                    link_library.validate_repair_evidence_link_revision_on_disk(
                        created["manifest_path"],
                        project_root=ROOT,
                        library_root=self.library,
                    )
        finally:
            case_path.write_bytes(original_bytes)

    def test_validation_rechecks_source_package_and_objects(self):
        created = self.publish()
        package_path = self.package["source_package_path"]
        original_bytes = package_path.read_bytes()
        original_head_validation = link_library._validate_head_authorities

        def mutate_package(*args, **kwargs):
            result = original_head_validation(*args, **kwargs)
            package_path.write_bytes(original_bytes + b" ")
            return result

        try:
            with mock.patch.object(
                link_library,
                "_validate_head_authorities",
                side_effect=mutate_package,
            ):
                with self.assertRaisesRegex(
                    ValueError, "source package manifest changed while validating"
                ):
                    link_library.validate_repair_evidence_link_revision_on_disk(
                        created["manifest_path"],
                        project_root=ROOT,
                        library_root=self.library,
                    )
        finally:
            package_path.write_bytes(original_bytes)

        object_path = self.package["validated_source_package"]["entries"][0][
            "object_file"
        ]
        original_object = object_path.read_bytes()

        def mutate_object(*args, **kwargs):
            result = original_head_validation(*args, **kwargs)
            object_path.write_bytes(original_object + b" ")
            return result

        try:
            with mock.patch.object(
                link_library,
                "_validate_head_authorities",
                side_effect=mutate_object,
            ):
                with self.assertRaisesRegex(
                    ValueError, "source package object changed while validating"
                ):
                    link_library.validate_repair_evidence_link_revision_on_disk(
                        created["manifest_path"],
                        project_root=ROOT,
                        library_root=self.library,
                    )
        finally:
            object_path.write_bytes(original_object)

    def test_validation_rechecks_revision_one_while_validating_revision_two(self):
        first = self.publish()
        second = self.publish_second_revision(
            first, corrected_case=None, supersedes=True
        )
        first_path = first["manifest_path"]
        original_bytes = first_path.read_bytes()
        original_head_validation = link_library._validate_head_authorities

        def mutate_prior(*args, **kwargs):
            result = original_head_validation(*args, **kwargs)
            first_path.write_bytes(original_bytes + b" ")
            return result

        try:
            with mock.patch.object(
                link_library,
                "_validate_head_authorities",
                side_effect=mutate_prior,
            ):
                with self.assertRaisesRegex(
                    ValueError, "link manifest changed while validating"
                ):
                    link_library.validate_repair_evidence_link_revision_on_disk(
                        second["manifest_path"],
                        project_root=ROOT,
                        library_root=self.library,
                    )
        finally:
            first_path.write_bytes(original_bytes)

    def test_conflicting_replay_does_not_clobber_revision(self):
        created = self.publish()
        self.write_binding_record(
            [self.binding(binding_id="different-binding")]
        )
        with self.assertRaisesRegex(ValueError, "conflict"):
            self.publish()
        validated = link_library.validate_repair_evidence_link_revision_on_disk(
            created["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
        self.assertEqual(
            [item["binding_id"] for item in validated["bindings"]],
            ["binding-emmc-u4000"],
        )

    def test_rejects_duplicate_active_replacements(self):
        first = self.publish()
        self.write_binding_record(
            [
                self.binding(
                    binding_id="replacement-one",
                    association_status="not_related",
                    supersedes_binding_id="binding-emmc-u4000",
                ),
                self.binding(
                    binding_id="replacement-two",
                    association_status="insufficient_evidence",
                    supersedes_binding_id="binding-emmc-u4000",
                ),
            ]
        )
        with self.assertRaises(ValueError):
            self.publish(previous_manifest_path=first["manifest_path"])

    def test_rejects_reference_drift_link_mutation_and_hardlinked_input(self):
        created = self.publish()
        manifest_path = created["manifest_path"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["repair_case_references"][0]["manifest_sha256"] = "f" * 64
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            link_library.validate_repair_evidence_link_revision_on_disk(
                manifest_path,
                project_root=ROOT,
                library_root=self.library,
            )

        alternate = self.root / "binding-hardlink.json"
        os.link(self.binding_path, alternate)
        with self.assertRaisesRegex(ValueError, "hard-linked"):
            self.publish(
                link_set_id="link-hardlink-input",
                binding_record_path=alternate,
            )

    def test_rejects_revision_gap_and_reparse_input_path(self):
        revisions = (
            self.library
            / "repair-evidence-links"
            / "link-gap"
            / "revisions"
        )
        (revisions / "0002").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "gap or fork"):
            self.publish(link_set_id="link-gap")

        target = self.root / "reparse-target"
        target.mkdir()
        linked = self.root / "reparse-input"
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(linked), str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if result.returncode != 0:
                self.skipTest("Unable to create a junction on this host.")
        else:
            linked.symlink_to(target, target_is_directory=True)
        try:
            linked_binding = linked / "bindings.json"
            linked_binding.write_bytes(self.binding_path.read_bytes())
            with self.assertRaisesRegex(ValueError, "reparse"):
                self.publish(
                    link_set_id="link-reparse-input",
                    binding_record_path=linked_binding,
                )
        finally:
            if os.name == "nt" and linked.exists():
                os.rmdir(linked)
            elif linked.is_symlink():
                linked.unlink()

    def _run_publish_workers(self, *, link_set_id, binding_paths):
        worker = (
            "import json,sys\n"
            "from pathlib import Path\n"
            "from scripts.visual_qc.repair_evidence_link_library import "
            "publish_repair_evidence_link_revision\n"
            "try:\n"
            " r=publish_repair_evidence_link_revision("
            "project_root=Path(sys.argv[1]),library_root=Path(sys.argv[2]),"
            "link_set_id=sys.argv[3],repair_case_manifest_path=Path(sys.argv[4]),"
            "physical_evidence_paths=[Path(sys.argv[5])],"
            "binding_record_path=Path(sys.argv[6]))\n"
            " print(json.dumps({'state':r['state'],'sha':r['manifest_sha256']}))\n"
            "except Exception as e:\n"
            " print(json.dumps({'error':type(e).__name__,'message':str(e)}))\n"
        )
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    worker,
                    str(ROOT),
                    str(self.library),
                    link_set_id,
                    str(self.case["manifest_path"]),
                    str(self.physical_path),
                    str(binding_path),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            for binding_path in binding_paths
        ]
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=60)
            self.assertEqual(process.returncode, 0, stderr)
            results.append(json.loads(stdout.strip().splitlines()[-1]))
        return results

    def test_process_race_identical_replay_is_created_and_existing(self):
        results = self._run_publish_workers(
            link_set_id="link-identical-race",
            binding_paths=[self.binding_path, self.binding_path],
        )
        self.assertEqual(
            sorted(item["state"] for item in results),
            ["created", "existing"],
        )
        self.assertEqual(len({item["sha"] for item in results}), 1)

    def test_process_race_conflict_leaves_one_complete_revision(self):
        alternate = self.root / "alternate-bindings.json"
        alternate.write_text(
            json.dumps(
                {
                    "physical_evidence_ids": ["physical-main_page_2"],
                    "bindings": [
                        self.binding(binding_id="competing-binding")
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        results = self._run_publish_workers(
            link_set_id="link-conflicting-race",
            binding_paths=[self.binding_path, alternate],
        )
        self.assertEqual(sum("state" in item for item in results), 1)
        self.assertEqual(sum("error" in item for item in results), 1)
        revisions = (
            self.library
            / "repair-evidence-links"
            / "link-conflicting-race"
            / "revisions"
        )
        completed = list(revisions.glob("*/.complete"))
        staging = list(revisions.glob(".*.staging"))
        self.assertEqual(len(completed), 1)
        self.assertEqual(staging, [])
