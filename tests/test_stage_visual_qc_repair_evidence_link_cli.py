from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from io import StringIO
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.visual_qc.repair_case_library import stage_repair_case_revision
from scripts.visual_qc.repair_evidence_link_contract import canonical_sha256
from scripts.visual_qc.repair_evidence_link_library import (
    RepairEvidenceLinkLibraryError,
)
from tests import test_visual_qc_repair_evidence_link_library as fixture_module


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FACT_SENTINEL = "TASK4_SOURCE_FACT_SENTINEL_7F3C19"
BINDING_SENTINEL = "task4-binding-sentinel-7f3c19"
MANIFEST_SENTINEL = '"schema_version":"VISUAL-QC-REPAIR-EVIDENCE-LINK-V1"'


class StageVisualQcRepairEvidenceLinkCliTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.VisualQcRepairEvidenceLinkLibraryTests(
            methodName="runTest"
        )
        self.fixture.setUp()
        self.library = self.fixture.library
        self.script = ROOT / "scripts" / "stage_visual_qc_repair_evidence_link.py"
        case_record = copy.deepcopy(self.fixture.case_record)
        case_record["findings"].append(
            {
                "finding_id": "task4-source-fact-sentinel",
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
            library_root=self.library,
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

        first = json.loads(
            self.fixture.physical_path.read_text(encoding="utf-8")
        )
        second = copy.deepcopy(first)
        second.update(
            {
                "physical_evidence_id": "physical-main-page-2-second",
                "server_case_id": "server-main-page-2-second",
                "image_id": "image-main-page-2-second",
                "job_id": "job-main-page-2-second",
                "registration_review_id": "review-main-page-2-second",
            }
        )
        second["physical_evidence_snapshot_sha256"] = canonical_sha256(
            {
                key: value
                for key, value in second.items()
                if key != "physical_evidence_snapshot_sha256"
            }
        )
        self.second_physical = self.fixture.root / "physical-second.json"
        self.second_physical.write_text(
            json.dumps(second, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        first_binding = self.fixture.binding(
            binding_id=BINDING_SENTINEL,
            repair_case_reference_id="case-f069-r2",
            source_fact={
                "kind": "finding",
                "fact_id": "task4-source-fact-sentinel",
            },
        )
        second_binding = self.fixture.binding(
            binding_id="case005-no-power-page-2",
            repair_case_reference_id="case-f069-r2",
            source_fact={
                "kind": "reported_symptom",
                "fact_id": "symptom-no-power",
            },
            physical_evidence_id="physical-main-page-2-second",
            target={"kind": "whole_board", "side_id": "main_page_2"},
            association_status="related",
            visibility_status="visible",
            evidence_bases=[
                {"kind": "repair_case_fact"},
                {
                    "kind": "human_observation",
                    "observation_code": "target_visible",
                },
            ],
        )
        third_binding = copy.deepcopy(second_binding)
        third_binding["binding_id"] = "case005-no-power-page-2-context"
        self.binding_record = self.fixture.binding_path
        self.binding_record.write_text(
            json.dumps(
                {
                    "physical_evidence_ids": [
                        "physical-main_page_2",
                        "physical-main-page-2-second",
                    ],
                    "bindings": [
                        first_binding,
                        second_binding,
                        third_binding,
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.fixture.tearDown()

    @property
    def link_root(self):
        return self.library / "repair-evidence-links"

    def command(self, *extra):
        return [
            sys.executable,
            str(self.script),
            "--library-root",
            str(self.library),
            "--link-set-id",
            "link-case005-f069-after",
            "--repair-case-manifest",
            str(self.fixture.case["manifest_path"]),
            "--physical-evidence",
            str(self.fixture.physical_path),
            "--physical-evidence",
            str(self.second_physical),
            "--binding-record",
            str(self.binding_record),
            *extra,
        ]

    def run_cli(self, *extra, command=None):
        return subprocess.run(
            self.command(*extra) if command is None else command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def assert_validation_failed_before_link_root(self, result):
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"status", "message"})
        self.assertEqual(payload["status"], "validation_failed")
        self.assertFalse(self.link_root.exists())
        self.assert_no_sensitive_output(result.stdout, result.stderr)

    def assert_no_sensitive_output(self, *streams):
        combined = "\n".join(streams)
        sensitive_values = [
            SOURCE_FACT_SENTINEL,
            BINDING_SENTINEL,
            MANIFEST_SENTINEL,
        ]
        if self.binding_record.is_file():
            binding_text = self.binding_record.read_text(encoding="utf-8")
            sensitive_values.extend(
                [
                    binding_text,
                    json.dumps(
                        json.loads(binding_text),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ]
            )
        manifests = list(self.link_root.glob("*/revisions/*/*.json"))
        for manifest_path in manifests:
            manifest_text = manifest_path.read_text(encoding="utf-8")
            sensitive_values.extend(
                [
                    manifest_text,
                    json.dumps(
                        json.loads(manifest_text),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ]
            )
        for sensitive in sensitive_values:
            self.assertNotIn(sensitive, combined)
        self.assertNotIn("Traceback", combined)

    def test_direct_invocation_creates_then_replays_exact_revision(self):
        created = self.run_cli()

        self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
        self.assertEqual(created.stderr, "")
        payload = json.loads(created.stdout)
        self.assertEqual(
            set(payload),
            {
                "status",
                "state",
                "link_set_id",
                "revision",
                "binding_count",
                "physical_evidence_count",
                "manifest_sha256",
                "manifest_path",
            },
        )
        self.assertEqual(
            {
                key: payload[key]
                for key in (
                    "status",
                    "state",
                    "link_set_id",
                    "revision",
                    "binding_count",
                    "physical_evidence_count",
                )
            },
            {
                "status": "ok",
                "state": "created",
                "link_set_id": "link-case005-f069-after",
                "revision": 1,
                "binding_count": 3,
                "physical_evidence_count": 2,
            },
        )
        self.assertRegex(payload["manifest_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(Path(payload["manifest_path"]).is_file())
        self.assert_no_sensitive_output(created.stdout, created.stderr)

        replay = self.run_cli()
        self.assertEqual(replay.returncode, 0, replay.stderr or replay.stdout)
        replay_payload = json.loads(replay.stdout)
        self.assertEqual(replay_payload["state"], "existing")
        self.assertEqual(
            replay_payload["manifest_sha256"],
            payload["manifest_sha256"],
        )
        self.assertEqual(
            Path(replay_payload["manifest_path"]).read_bytes(),
            Path(payload["manifest_path"]).read_bytes(),
        )
        self.assert_no_sensitive_output(replay.stdout, replay.stderr)

    def test_duplicate_json_key_fails_before_link_root(self):
        self.binding_record.write_text(
            (
                '{"physical_evidence_ids":["physical-main_page_2"],'
                '"physical_evidence_ids":["physical-main_page_2"],'
                '"bindings":[]}'
            ),
            encoding="utf-8",
        )

        self.assert_validation_failed_before_link_root(self.run_cli())

    def test_unsafe_id_fails_before_link_root(self):
        command = self.command()
        command[command.index("link-case005-f069-after")] = "../escape"

        self.assert_validation_failed_before_link_root(
            self.run_cli(command=command)
        )

    def test_incomplete_arguments_fail_before_link_root(self):
        for option in ("--binding-record", "--physical-evidence"):
            with self.subTest(option=option):
                command = self.command()
                index = command.index(option)
                if option == "--physical-evidence":
                    while option in command:
                        index = command.index(option)
                        del command[index : index + 2]
                else:
                    del command[index : index + 2]
                result = self.run_cli(command=command)
                self.assert_validation_failed_before_link_root(result)

    def test_inference_and_governed_output_flags_are_not_exposed(self):
        forbidden_flags = (
            "--model-normalization",
            "--confirm-defect",
            "--annotation",
            "--qc-result",
            "--golden",
            "--training",
            "--repair-action",
        )
        for flag in forbidden_flags:
            with self.subTest(flag=flag):
                result = self.run_cli(flag)
                self.assert_validation_failed_before_link_root(result)

    def test_truncated_long_arguments_are_not_abbreviated(self):
        command = self.command()
        command[command.index("--library-root")] = "--library-roo"

        self.assert_validation_failed_before_link_root(
            self.run_cli(command=command)
        )

    def test_validation_error_never_echoes_library_exception_content(self):
        from scripts import stage_visual_qc_repair_evidence_link as command_module

        stdout = StringIO()
        stderr = StringIO()
        with patch.object(
            command_module,
            "_read_safe_json",
            side_effect=RepairEvidenceLinkLibraryError(
                f"{SOURCE_FACT_SENTINEL}:{BINDING_SENTINEL}:{MANIFEST_SENTINEL}"
            ),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = command_module.main(self.command()[2:])

        self.assertEqual(exit_code, 2)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            payload,
            {
                "status": "validation_failed",
                "message": "repair evidence link input failed validation",
            },
        )
        self.assertEqual(stderr.getvalue(), "")
        self.assert_no_sensitive_output(stdout.getvalue(), stderr.getvalue())

    def test_unexpected_exception_is_generic_and_has_no_traceback(self):
        from scripts import stage_visual_qc_repair_evidence_link as command_module

        stdout = StringIO()
        stderr = StringIO()
        with patch.object(
            command_module,
            "_read_safe_json",
            return_value=({"bindings": "not emitted"}, "a" * 64),
        ), patch.object(
            command_module,
            "build_repair_evidence_link_revision",
            return_value={"preflight": "ok"},
        ), patch.object(
            command_module,
            "publish_repair_evidence_link_revision",
            side_effect=RuntimeError(
                f"{SOURCE_FACT_SENTINEL}:{BINDING_SENTINEL}:{MANIFEST_SENTINEL}"
            ),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = command_module.main(self.command()[2:])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            payload,
            {
                "status": "failed",
                "message": "repair evidence link staging failed",
            },
        )
        self.assertEqual(stderr.getvalue(), "")
        self.assert_no_sensitive_output(stdout.getvalue(), stderr.getvalue())

    @staticmethod
    def mocked_preflight(link_set_id="link-nonascii-receipt"):
        return {
            "link_set_id": link_set_id,
            "revision": 1,
            "bindings": [{BINDING_SENTINEL: True}],
            "physical_evidence": [{"evidence": "ordinary"}],
        }

    @staticmethod
    def mocked_result(library_root, link_set_id="link-nonascii-receipt"):
        return {
            "state": "created",
            "link_set_id": link_set_id,
            "revision": 1,
            "binding_count": 1,
            "physical_evidence_count": 1,
            "manifest_sha256": "a" * 64,
            "manifest_path": (
                Path(library_root).expanduser().resolve()
                / "repair-evidence-links"
                / link_set_id
                / "revisions"
                / "0001"
                / "repair-evidence-link.json"
            ),
        }

    def test_malformed_post_publish_result_uses_indeterminate_receipt(self):
        from scripts import stage_visual_qc_repair_evidence_link as command_module

        stdout = StringIO()
        stderr = StringIO()
        with patch.object(
            command_module,
            "_read_safe_json",
            return_value=({"binding": BINDING_SENTINEL}, "a" * 64),
        ), patch.object(
            command_module,
            "build_repair_evidence_link_revision",
            return_value=self.mocked_preflight(
                "link-case005-f069-after"
            ),
        ), patch.object(
            command_module,
            "publish_repair_evidence_link_revision",
            return_value={"state": "created"},
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = command_module.main(self.command()[2:])

        self.assertEqual(exit_code, 3)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "status": "receipt_delivery_failed",
                "message": "publication outcome is indeterminate; replay safely",
            },
        )
        self.assertEqual(stderr.getvalue(), "")
        self.assert_no_sensitive_output(stdout.getvalue(), stderr.getvalue())

    def test_ascii_safe_receipt_supports_nonascii_path_and_stdout(self):
        from scripts import stage_visual_qc_repair_evidence_link as command_module

        library_root = self.fixture.root / "受控资料库"
        link_set_id = "link-nonascii-receipt"
        command = [
            "--library-root",
            str(library_root),
            "--link-set-id",
            link_set_id,
            "--repair-case-manifest",
            str(self.fixture.case["manifest_path"]),
            "--physical-evidence",
            str(self.fixture.physical_path),
            "--binding-record",
            str(self.binding_record),
        ]
        output_bytes = io.BytesIO()
        ascii_stdout = io.TextIOWrapper(
            output_bytes,
            encoding="ascii",
            errors="strict",
        )
        with patch.object(
            command_module,
            "_read_safe_json",
            return_value=({"binding": BINDING_SENTINEL}, "a" * 64),
        ), patch.object(
            command_module,
            "build_repair_evidence_link_revision",
            return_value=self.mocked_preflight(link_set_id),
        ), patch.object(
            command_module,
            "publish_repair_evidence_link_revision",
            return_value=self.mocked_result(library_root, link_set_id),
        ), patch.object(command_module.sys, "stdout", ascii_stdout):
            exit_code = command_module.main(command)
            ascii_stdout.flush()
        output = output_bytes.getvalue().decode("ascii")

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output)["manifest_path"], str(
            self.mocked_result(library_root, link_set_id)["manifest_path"]
        ))
        self.assertIn("\\u53d7\\u63a7\\u8d44\\u6599\\u5e93", output)
        self.assert_no_sensitive_output(output, "")

    def test_broken_stdout_after_publish_returns_receipt_delivery_failure(self):
        from scripts import stage_visual_qc_repair_evidence_link as command_module

        class BrokenStdout:
            def write(self, _value):
                raise BrokenPipeError("closed")

            def flush(self):
                raise BrokenPipeError("closed")

        link_set_id = "link-case005-f069-after"
        replacement_stdout = None
        with patch.object(
            command_module,
            "_read_safe_json",
            return_value=({"binding": BINDING_SENTINEL}, "a" * 64),
        ), patch.object(
            command_module,
            "build_repair_evidence_link_revision",
            return_value=self.mocked_preflight(link_set_id),
        ), patch.object(
            command_module,
            "publish_repair_evidence_link_revision",
            return_value=self.mocked_result(self.library, link_set_id),
        ), patch.object(command_module.sys, "stdout", BrokenStdout()):
            exit_code = command_module.main(self.command()[2:])
            replacement_stdout = command_module.sys.stdout

        self.assertEqual(exit_code, 3)
        if hasattr(replacement_stdout, "close"):
            replacement_stdout.close()

    def test_real_subprocess_closed_receipt_pipe_exits_three_without_stderr(self):
        worker = r'''
import sys
import time
from pathlib import Path
import scripts.stage_visual_qc_repair_evidence_link as command

library_root = Path(sys.argv[1]).resolve()
link_set_id = "link-broken-pipe-subprocess"
source_sentinel = "TASK4_BROKEN_PIPE_SOURCE_SENTINEL_4C22"
binding_sentinel = "task4-broken-pipe-binding-sentinel-4c22"
command._read_safe_json = lambda *_args, **_kwargs: (
    {"binding": binding_sentinel, "source": source_sentinel},
    "a" * 64,
)
command.build_repair_evidence_link_revision = lambda **_kwargs: {
    "link_set_id": link_set_id,
    "revision": 1,
    "bindings": [{"binding_id": binding_sentinel}],
    "physical_evidence": [{"physical_evidence_id": "ordinary-evidence"}],
}

def publish(**_kwargs):
    time.sleep(0.35)
    return {
        "state": "created",
        "link_set_id": link_set_id,
        "revision": 1,
        "binding_count": 1,
        "physical_evidence_count": 1,
        "manifest_sha256": "b" * 64,
        "manifest_path": (
            library_root
            / "repair-evidence-links"
            / link_set_id
            / "revisions"
            / "0001"
            / "repair-evidence-link.json"
        ),
    }

command.publish_repair_evidence_link_revision = publish
raise SystemExit(command.main([
    "--library-root", str(library_root),
    "--link-set-id", link_set_id,
    "--repair-case-manifest", "unused-case.json",
    "--physical-evidence", "unused-physical.json",
    "--binding-record", "unused-bindings.json",
]))
'''
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                worker,
                str(self.fixture.root / "broken-pipe-library"),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        self.assertIsNotNone(process.stdout)
        self.assertIsNotNone(process.stderr)
        process.stdout.close()
        stderr = process.stderr.read()
        process.stderr.close()
        return_code = process.wait(timeout=30)

        self.assertEqual(return_code, 3)
        self.assertEqual(stderr, b"")
        for leaked in (
            b"Exception ignored",
            b"Traceback",
            b"TASK4_BROKEN_PIPE_SOURCE_SENTINEL_4C22",
            b"task4-broken-pipe-binding-sentinel-4c22",
        ):
            self.assertNotIn(leaked, stderr)


if __name__ == "__main__":
    unittest.main()
