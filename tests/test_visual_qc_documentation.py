import unittest
from pathlib import Path

from scripts.handoff_visual_qc_physical_package import (
    build_parser as build_handoff_parser,
)
from scripts.run_visual_qc_physical_acceptance import (
    build_parser as build_acceptance_parser,
)


ROOT = Path(__file__).resolve().parents[1]
CASE005_ID = "case-005-bg6-f069"
CASE005_REVISION = 1
CASE005_BOARD_KEY = "bg6h-f069"
CASE005_BOARD_ID = "BOARD-F069-MAIN-V1.2"
CASE005_MANIFEST_SHA256 = (
    "85c8c64cb97cf1ea1e567e4d1f7fc62ec00ebf02719939c74a5e0faf46298177"
)
CASE005_MODEL_IDENTITY_TOKEN = "model_identity_resolved=false"
CURRENT_PRODUCTION = "08d08cd38aaffc9b01d901dfe9ef7684a614abac"
CASE005_BOUNDARY_EQUIVALENTS = (
    ("not visual diagnosis evidence", "不是视觉诊断"),
    ("not confirmed defect evidence", "不是缺陷确认"),
    ("not Golden Sample evidence", "不是 Golden"),
    ("not training label evidence", "不是训练标签"),
    ("not repair causality evidence", "不是维修因果"),
    ("not field accuracy evidence", "不是现场精度"),
)
REPAIR_EVIDENCE_DOCUMENTS = (
    "README.md",
    "docs/visual-qc-capture-intake-spec-2026-07-20.md",
    "docs/visual-qc-server-api-2026-07-20.md",
    "docs/visual-qc-workbench-2026-07-17.md",
    "docs/visual-qc-f069-first-physical-acceptance-2026-07-24.md",
)
REPAIR_EVIDENCE_OWNER_SEQUENCE = (
    "repair case revision",
    "export linkable physical evidence",
    "stage repair evidence link revision",
    "validate/replay",
    "sync read-only projection",
    "inspect in internal workbench",
)


class VisualQcDocumentationTests(unittest.TestCase):
    def test_canonical_documents_record_current_repair_evidence_link_boundary(self):
        for relative_path in REPAIR_EVIDENCE_DOCUMENTS:
            document = (ROOT / relative_path).read_text(encoding="utf-8")
            normalized = " ".join(document.split())
            normalized_lower = normalized.lower()

            self.assertIn("2026-07-29", document, relative_path)
            self.assertIn(
                "controlled library is the authoritative source of truth",
                normalized,
                relative_path,
            )
            self.assertIn("read-only projection", normalized, relative_path)
            self.assertIn("one photo per binding", normalized, relative_path)
            self.assertIn(
                "administrator/reviewer detail API",
                normalized,
                relative_path,
            )
            self.assertIn(
                "technicians have no repair-evidence detail route",
                normalized_lower,
                relative_path,
            )
            self.assertIn(
                "no annotation, QC, Golden Sample, training-label, "
                "repair-causality, or repair-action authority",
                normalized,
                relative_path,
            )
            self.assertIn("possibly_related", normalized, relative_path)
            self.assertIn("not_assessed", normalized, relative_path)
            self.assertIn(
                "no visual defect conclusion",
                normalized,
                relative_path,
            )
            self.assertTrue(
                "Production remains unchanged" in normalized
                or CURRENT_PRODUCTION in normalized,
                relative_path,
            )
            for stage in REPAIR_EVIDENCE_OWNER_SEQUENCE:
                self.assertIn(stage, normalized, relative_path)

    def test_repair_case_documents_record_v2_identity_and_case005_boundaries(self):
        documents = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "physical acceptance": (
                ROOT
                / "docs"
                / "visual-qc-f069-first-physical-acceptance-2026-07-24.md"
            ).read_text(encoding="utf-8"),
            "capture intake": (
                ROOT / "docs" / "visual-qc-capture-intake-spec-2026-07-20.md"
            ).read_text(encoding="utf-8"),
            "repair case source design": (
                ROOT
                / "docs"
                / "superpowers"
                / "specs"
                / "2026-07-24-visual-qc-repair-case-source-design.md"
            ).read_text(encoding="utf-8"),
        }

        for name, document in documents.items():
            self.assertIn("VISUAL-QC-REPAIR-CASE-SOURCE-V1", document)
            self.assertIn("VISUAL-QC-REPAIR-CASE-SOURCE-V2", document)
            self.assertIn("unresolved_alias", document)
            self.assertIn(CASE005_ID, document, name)
            self.assertRegex(
                document,
                rf"(?i)\brevision(?:\s*:\s*|\s+)`?{CASE005_REVISION}`?",
                name,
            )
            self.assertIn(CASE005_BOARD_KEY, document, name)
            self.assertIn(CASE005_BOARD_ID, document, name)
            self.assertIn(CASE005_MANIFEST_SHA256, document, name)
            self.assertIn(CASE005_MODEL_IDENTITY_TOKEN, document, name)
            self.assertIn("symptom_linked", document)
            self.assertIn("TECNO/BG6", document)
            self.assertIn("BG6H/BG6h", document)
            self.assertTrue(
                "Production remains `f278061`" in document
                or CURRENT_PRODUCTION in document,
                name,
            )
            for equivalents in CASE005_BOUNDARY_EQUIVALENTS:
                self.assertTrue(
                    any(token in document for token in equivalents),
                    f"{name} is missing CASE005 boundary {equivalents}",
                )
            self.assertRegex(
                document,
                r"(complete revision|完整 revision)",
                name,
            )
            self.assertIn("appended evidence", document, name)
            self.assertIn("conflict -> confirmed_alias", document, name)
            self.assertRegex(
                document,
                r"(requires a new correction record|强制新增 correction record)",
                name,
            )
            self.assertRegex(
                document,
                r"(resolved\s+identity\s+is\s+immutable"
                r"|resolved\s+identity\s+不可变)",
                name,
            )

        for document in (
            documents["README.md"],
            documents["capture intake"],
            documents["repair case source design"],
        ):
            self.assertRegex(
                document,
                r"V1[^\n]*(immutable|不可变)[^\n]*(readable|可读)"
                r"|V1[^\n]*(readable|可读)[^\n]*(immutable|不可变)",
            )
        self.assertNotIn(
            "身份状态变化只能通过追加 correction",
            documents["README.md"],
        )
        self.assertNotIn(
            "Identity status may change only through",
            documents["capture intake"],
        )
        self.assertNotIn(
            "Any later\nresolution or conflict",
            documents["repair case source design"],
        )
        self.assertNotIn(
            "when changing status, an explicit correction record",
            documents["repair case source design"],
        )
        self.assertNotIn(
            "Any later resolution must be recorded through a new",
            documents["physical acceptance"],
        )
        self.assertNotIn(
            "Bind CASE005's text repair facts",
            documents["physical acceptance"],
        )

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
        self.assertIn(CURRENT_PRODUCTION, readme)
        self.assertNotIn("再由数据管理员批量导入受控 FastAPI 服务", readme)
        self.assertIn("海外维修员不上传视觉照片", product_vision)
        self.assertNotIn("前端负责图片上传", product_vision)
        self.assertIn(CURRENT_PRODUCTION, product_vision)
        self.assertIn("来源审计、实物验收和验收合格交接", product_vision)
        self.assertIn("Milo 是实物照片的唯一来源", security)
        self.assertIn("验收合格交接", security)
        self.assertIn(CURRENT_PRODUCTION, security)
        self.assertIn("来源审计、实物验收和干跑全部通过", security)
        self.assertIn("acceptance-qualified handoff CLI", deployment)
        self.assertIn(CURRENT_PRODUCTION, workbench)
        self.assertIn("does not upload new physical captures", workbench)
        self.assertIn("VISUAL-QC-SERVER-CASE-V3", architecture)
        self.assertIn("handoff_visual_qc_physical_package.py", architecture)
        self.assertNotIn("scripts.import_visual_qc_batch", architecture)
        self.assertIn("## Current Implemented Increment", registration)
        self.assertNotIn("## Next Increment", registration)
        self.assertNotIn("technician or reviewer", registration)
        self.assertIn("data administrator", registration)
        self.assertIn(f"production revision `{CURRENT_PRODUCTION}`", registration)
        self.assertIn("Production admission remains fail-closed", registration)
        self.assertIn("direct generic-import transport", owner_intake)
        self.assertIn("direct importer use superseded", batch_builder)
        self.assertNotIn(
            "passed directly to `scripts/import_visual_qc_batch.py`",
            batch_builder,
        )
        self.assertIn("HISTORICAL COMPLETED PLAN", legacy_intake_plan)
        self.assertIn("Do not execute this plan", legacy_intake_plan)
        self.assertIn(f"Production is `{CURRENT_PRODUCTION}`", server_api)
        self.assertIn("only after source audit, physical acceptance", server_api)

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
