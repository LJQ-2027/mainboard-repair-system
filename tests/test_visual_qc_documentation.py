import unittest
from pathlib import Path

from scripts.handoff_visual_qc_physical_package import (
    build_parser as build_handoff_parser,
)
from scripts.run_visual_qc_physical_acceptance import (
    build_parser as build_acceptance_parser,
)


ROOT = Path(__file__).resolve().parents[1]


class VisualQcDocumentationTests(unittest.TestCase):
    def test_repair_case_documents_record_v2_identity_and_case005_boundaries(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        acceptance = (
            ROOT / "docs" / "visual-qc-f069-first-physical-acceptance-2026-07-24.md"
        ).read_text(encoding="utf-8")
        intake = (
            ROOT / "docs" / "visual-qc-capture-intake-spec-2026-07-20.md"
        ).read_text(encoding="utf-8")
        source_design = (
            ROOT
            / "docs"
            / "superpowers"
            / "specs"
            / "2026-07-24-visual-qc-repair-case-source-design.md"
        ).read_text(encoding="utf-8")
        documents = (readme, acceptance, intake, source_design)

        for document in documents:
            self.assertIn("VISUAL-QC-REPAIR-CASE-SOURCE-V1", document)
            self.assertIn("VISUAL-QC-REPAIR-CASE-SOURCE-V2", document)
            self.assertIn("unresolved_alias", document)
            self.assertIn("case-005-bg6-f069", document)
            self.assertIn(
                "85c8c64cb97cf1ea1e567e4d1f7fc62ec00ebf02719939c74a5e0faf46298177",
                document,
            )
            self.assertIn("symptom_linked", document)
            self.assertIn("TECNO/BG6", document)
            self.assertIn("BG6H/BG6h", document)
            self.assertIn("Production remains `f278061`", document)

        for document in (readme, intake, source_design):
            self.assertRegex(
                document,
                r"V1[^\n]*(immutable|不可变)[^\n]*(readable|可读)"
                r"|V1[^\n]*(readable|可读)[^\n]*(immutable|不可变)",
            )
        self.assertIn("append-only correction revision", source_design)
        self.assertIn("complete identity evidence", source_design)
        self.assertIn("monotonic identity transition", source_design)
        self.assertNotIn("Bind CASE005's text repair facts", acceptance)
        for forbidden_claim in (
            "visual diagnosis evidence",
            "confirmed defect evidence",
            "Golden Sample evidence",
            "training label evidence",
            "repair causality evidence",
            "field accuracy evidence",
        ):
            self.assertIn(f"not {forbidden_claim}", acceptance)

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
        self.assertRegex(
            intake,
            r"run_visual_qc_physical_acceptance\.py `\s+"
            r"--library-root [^\r\n]+ `\s+"
            r"--package [^\r\n]+ `\s+"
            r"--output [^\r\n]+",
        )
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
        arguments = build_handoff_parser().parse_args(
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

    def test_canonical_visual_qc_documents_share_the_current_intake_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        product_vision = (
            ROOT / "docs" / "product-vision-and-requirements.md"
        ).read_text(encoding="utf-8")
        security = (
            ROOT / "docs" / "security-and-data-boundary.md"
        ).read_text(encoding="utf-8")
        deployment = (ROOT / "docs" / "beta-deployment.md").read_text(
            encoding="utf-8"
        )
        workbench = (
            ROOT / "docs" / "visual-qc-workbench-2026-07-17.md"
        ).read_text(encoding="utf-8")
        architecture = (
            ROOT
            / "docs"
            / "superpowers"
            / "specs"
            / "2026-07-20-visual-qc-server-architecture-design.md"
        ).read_text(encoding="utf-8")
        registration = (
            ROOT / "docs" / "visual-qc-auto-registration-2026-07-20.md"
        ).read_text(encoding="utf-8")
        owner_intake = (
            ROOT
            / "docs"
            / "superpowers"
            / "specs"
            / "2026-07-21-owner-managed-visual-qc-intake-design.md"
        ).read_text(encoding="utf-8")
        batch_builder = (
            ROOT
            / "docs"
            / "superpowers"
            / "specs"
            / "2026-07-22-visual-qc-intake-batch-builder-design.md"
        ).read_text(encoding="utf-8")
        legacy_intake_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-07-21-owner-managed-visual-qc-intake.md"
        ).read_text(encoding="utf-8")
        server_api = (
            ROOT / "docs" / "visual-qc-server-api-2026-07-20.md"
        ).read_text(encoding="utf-8")

        self.assertIn("acceptance-qualified handoff", readme)
        self.assertIn("生产仍为 `f278061`", readme)
        self.assertNotIn("再由数据管理员批量导入受控 FastAPI 服务", readme)
        self.assertIn("海外维修员不上传视觉照片", product_vision)
        self.assertNotIn("前端负责图片上传", product_vision)
        self.assertIn("生产仍为 `f278061`", product_vision)
        self.assertIn("不得把 qualified handoff 指向生产", product_vision)
        self.assertIn("Milo 是实物照片的唯一来源", security)
        self.assertIn("验收合格交接", security)
        self.assertIn("生产仍为 `f278061`", security)
        self.assertIn("qualified handoff 禁止指向生产", security)
        self.assertIn("acceptance-qualified handoff CLI", deployment)
        self.assertIn("Production remains `f278061`", workbench)
        self.assertIn("must not be used for physical intake", workbench)
        self.assertIn("VISUAL-QC-SERVER-CASE-V3", architecture)
        self.assertIn("handoff_visual_qc_physical_package.py", architecture)
        self.assertNotIn("scripts.import_visual_qc_batch", architecture)
        self.assertIn("## Current Implemented Increment", registration)
        self.assertNotIn("## Next Increment", registration)
        self.assertNotIn("technician or reviewer", registration)
        self.assertIn("data administrator", registration)
        self.assertIn("production revision `f278061`", registration)
        self.assertIn("Later admission hardening is local only", registration)
        self.assertIn("direct generic-import transport", owner_intake)
        self.assertIn("direct importer use superseded", batch_builder)
        self.assertNotIn(
            "passed directly to `scripts/import_visual_qc_batch.py`",
            batch_builder,
        )
        self.assertIn("HISTORICAL COMPLETED PLAN", legacy_intake_plan)
        self.assertIn("Do not execute this plan", legacy_intake_plan)
        self.assertIn("Local HEAD contract", server_api)
        self.assertIn("Production remains `f278061`", server_api)
        self.assertIn("must not target production", server_api)

    def test_documented_acceptance_arguments_are_accepted_by_the_cli_parser(self):
        arguments = build_acceptance_parser().parse_args(
            [
                "--library-root",
                "D:/visual-qc-source-library",
                "--package",
                "D:/visual-qc-source-library/packages/km4/source-package.json",
                "--output",
                "D:/visual-qc-acceptance/km4",
            ]
        )

        self.assertEqual(
            arguments.library_root,
            Path("D:/visual-qc-source-library"),
        )
        self.assertEqual(
            arguments.package,
            Path(
                "D:/visual-qc-source-library/packages/km4/source-package.json"
            ),
        )
        self.assertEqual(
            arguments.output,
            Path("D:/visual-qc-acceptance/km4"),
        )


if __name__ == "__main__":
    unittest.main()
