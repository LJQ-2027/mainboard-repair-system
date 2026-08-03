import json
from copy import deepcopy
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from pathlib import Path

from scripts.board_batch_acceptance import (
    audit_board,
    audit_catalog,
    evaluate_coverage,
    publish_reports,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


class BoardBatchAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads(
            (ROOT / "knowledge-base/repair-workbench-boards.json").read_text(encoding="utf-8")
        )
        cls.f069m_entry = catalog["boards"]["bg6m-f069m"]
        cls.f069_entry = catalog["boards"]["bg6h-f069"]
        cls.xk67j_entry = catalog["boards"]["xk67j-shared"]
        cls.h897_entry = catalog["boards"]["kj6-h897"]

    def test_reference_only_board_passes_the_shared_board_contract(self):
        result = audit_board(ROOT, "bg6m-f069m", self.f069m_entry)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["board_id"], "BOARD-F069M-MAIN-V1.0")
        self.assertEqual(result["side_ids"], ["main_page_1", "main_page_2"])
        self.assertEqual(result["accepted_designators"], 1115)
        self.assertEqual(result["schematic_linked_designators"], 604)
        self.assertEqual(result["schematic_occurrences"], 619)
        self.assertEqual(result["reviewed_entities"], 10)
        self.assertEqual(result["repair_flows"], 0)
        self.assertEqual(result["repair_coverage"], "source_unavailable")
        self.assertEqual(result["reference_mode"], "point_map_only")
        self.assertGreaterEqual(result["location_only_entities"], 2)

    def test_f069_v12_passes_without_becoming_f069m_or_a_reviewed_repair_flow(self):
        result = audit_board(ROOT, "bg6h-f069", self.f069_entry)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["board_id"], "BOARD-F069-MAIN-V1.2")
        self.assertEqual(result["side_ids"], ["main_page_1", "main_page_2"])
        self.assertEqual(result["accepted_designators"], 1126)
        self.assertEqual(result["schematic_linked_designators"], 604)
        self.assertEqual(result["schematic_occurrences"], 620)
        self.assertEqual(result["reviewed_entities"], 12)
        self.assertEqual(result["repair_flows"], 0)
        self.assertEqual(result["repair_coverage"], "source_available_pending_review")
        self.assertEqual(result["reference_mode"], "point_map_only")
        self.assertNotEqual(result["board_id"], "BOARD-F069M-MAIN-V1.0")

    def test_xk67j_passes_as_an_evidence_tiered_shared_platform(self):
        result = audit_board(ROOT, "xk67j-shared", self.xk67j_entry)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["board_id"], "BOARD-XK67J-MAIN-V1.0B")
        self.assertEqual(result["side_ids"], ["main_page_1", "main_page_2"])
        self.assertEqual(result["accepted_designators"], 1040)
        self.assertEqual(result["schematic_linked_designators"], 505)
        self.assertEqual(result["schematic_occurrences"], 524)
        self.assertEqual(result["reviewed_entities"], 13)
        self.assertEqual(result["repair_flows"], 1)
        self.assertEqual(result["repair_coverage"], "source_boundary_only")
        self.assertEqual(
            result["reference_mode"],
            "reviewed_physical_photo_navigation",
        )
        self.assertEqual(
            result["compatible_models"],
            ["KM4n", "KM4k", "KM5", "KM5n", "KM5s"],
        )

    def test_h897_passes_as_the_eighth_exact_source_board(self):
        result = audit_board(ROOT, "kj6-h897", self.h897_entry)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["board_id"], "BOARD-H897-MAIN-V1.2")
        self.assertEqual(result["side_ids"], ["main_page_1", "main_page_2"])
        self.assertEqual(result["accepted_designators"], 1240)
        self.assertEqual(result["schematic_linked_designators"], 361)
        self.assertEqual(result["schematic_occurrences"], 388)
        self.assertEqual(result["reviewed_entities"], 15)
        self.assertEqual(result["repair_flows"], 0)
        self.assertEqual(
            result["repair_coverage"],
            "source_available_pending_review",
        )
        self.assertEqual(
            result["reference_mode"],
            "reviewed_physical_photo_navigation",
        )

    def test_legacy_registration_uses_its_dataset_side_when_entities_omit_it(self):
        catalog = json.loads(
            (ROOT / "knowledge-base/repair-workbench-boards.json").read_text(encoding="utf-8")
        )

        result = audit_board(ROOT, "km4-f151", catalog["boards"]["km4-f151"])

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["repair_coverage"], "reviewed_flows_with_boundaries")

    def test_current_catalog_covers_the_declared_pipeline_risk_classes(self):
        audit = audit_catalog(ROOT)

        self.assertEqual([board["board_key"] for board in audit["boards"]], [
            "km4-f151",
            "kl4-f201",
            "cm6-h8918",
            "ck6n-h6929",
            "bg6m-f069m",
            "bg6h-f069",
            "xk67j-shared",
            "kj6-h897",
        ])
        self.assertEqual(audit["audit_id"], "BOARD-CATALOG-BATCH-ACCEPTANCE-V2")
        self.assertTrue(all(board["status"] == "pass" for board in audit["boards"]))
        self.assertEqual(set(audit["coverage"]), {
            "minimum_board_count",
            "shared_platform_models",
            "reference_modes",
            "repair_coverage_modes",
            "point_map_source_layouts",
            "source_named_sides",
            "confidence_limited_locations",
        })
        self.assertTrue(all(gate["covered"] for gate in audit["coverage"].values()))
        self.assertTrue(audit["sufficient_for_current_pipeline"])
        self.assertIn("visual_defect_recognition", audit["scope_boundaries"])

    def test_reference_only_coverage_is_required_for_sufficiency(self):
        boards = deepcopy(audit_catalog(ROOT)["boards"])
        for board in boards:
            board["repair_coverage"] = "reviewed_flows"

        coverage = evaluate_coverage(boards)

        self.assertFalse(coverage["repair_coverage_modes"]["covered"])

    def test_markdown_report_exposes_board_evidence_and_scope(self):
        report = render_markdown(audit_catalog(ROOT))

        self.assertIn("# Board Catalog Batch Acceptance", report)
        self.assertIn("| `bg6m-f069m` | PASS | 1,115 | 604 | 10 | 0 |", report)
        self.assertIn("| `bg6h-f069` | PASS | 1,126 | 604 | 12 | 0 |", report)
        self.assertIn("| `xk67j-shared` | PASS | 1,040 | 505 | 13 | 1 |", report)
        self.assertIn("| `kj6-h897` | PASS | 1,240 | 361 | 15 | 0 |", report)
        self.assertIn("source_boundary_only", report)
        self.assertIn("reference-only repair coverage", report)
        self.assertIn("Visual defect recognition", report)
        self.assertIn("**Sufficient for current source-to-2.5D pipeline: YES**", report)

    def test_failed_audit_does_not_publish_reports(self):
        audit = audit_catalog(ROOT)
        audit["sufficient_for_current_pipeline"] = False
        with TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            json_path = output_root / "audit.json"
            markdown_path = output_root / "audit.md"

            with self.assertRaisesRegex(ValueError, "acceptance audit failed"):
                publish_reports(audit, json_path, markdown_path)

            self.assertFalse(json_path.exists())
            self.assertFalse(markdown_path.exists())

    def test_successful_report_publication_is_deterministic_utf8(self):
        audit = audit_catalog(ROOT)
        with TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            json_path = output_root / "audit.json"
            markdown_path = output_root / "audit.md"

            publish_reports(audit, json_path, markdown_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), audit)
            self.assertEqual(markdown_path.read_text(encoding="utf-8"), render_markdown(audit))

    def test_cli_runs_from_the_repository_root(self):
        with TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/board_batch_acceptance.py",
                    "--json-output",
                    str(output_root / "audit.json"),
                    "--markdown-output",
                    str(output_root / "audit.md"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Batch acceptance passed: 8 boards, 7 coverage gates", completed.stdout)


if __name__ == "__main__":
    unittest.main()
