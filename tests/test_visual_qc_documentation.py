import unittest
from pathlib import Path

from scripts.handoff_visual_qc_physical_package import build_parser


ROOT = Path(__file__).resolve().parents[1]


class VisualQcDocumentationTests(unittest.TestCase):
    def test_server_api_documents_current_contracts_and_controlled_handoff(self):
        server_api = (
            ROOT / "docs" / "visual-qc-server-api-2026-07-20.md"
        ).read_text(encoding="utf-8")
        workbench = (
            ROOT / "docs" / "visual-qc-workbench-2026-07-17.md"
        ).read_text(encoding="utf-8")
        intake = (
            ROOT / "docs" / "visual-qc-capture-intake-spec-2026-07-20.md"
        ).read_text(encoding="utf-8")

        self.assertIn("VISUAL-QC-SERVER-CASE-V2", server_api)
        self.assertIn("VISUAL-QC-SERVER-CASE-V3", server_api)
        self.assertIn("VISUAL-QC-ADMIN-CASE-LIST-V2", server_api)
        self.assertIn("acceptance-qualified handoff", server_api)
        self.assertIn("does not upload new physical captures", workbench)
        self.assertIn("handoff_visual_qc_physical_package.py", intake)
        for document in (server_api, intake):
            self.assertIn("--library-root", document)
            self.assertIn("--handoff-root", document)
            self.assertNotIn("--receipt", document)
        self.assertNotIn(
            "internal browser draft",
            server_api,
        )
        self.assertNotIn(
            "IndexedDB draft recovery before and after upload",
            server_api,
        )

    def test_documented_handoff_arguments_are_accepted_by_the_cli_parser(self):
        arguments = build_parser().parse_args(
            [
                "source-package.json",
                "physical-registration-run.json",
                "--library-root",
                "D:/visual-qc-source-library",
                "--handoff-root",
                "D:/visual-qc-handoffs/km4-physical-001",
                "--api-base",
                "https://example.test/api/v1/visual-qc",
                "--credential-file",
                "D:/secure/visual-qc-credential.json",
                "--wait",
            ]
        )

        self.assertEqual(arguments.package, Path("source-package.json"))
        self.assertEqual(
            arguments.acceptance_report,
            Path("physical-registration-run.json"),
        )
        self.assertEqual(
            arguments.library_root,
            Path("D:/visual-qc-source-library"),
        )
        self.assertEqual(
            arguments.handoff_root,
            Path("D:/visual-qc-handoffs/km4-physical-001"),
        )
        self.assertTrue(arguments.wait)


if __name__ == "__main__":
    unittest.main()
