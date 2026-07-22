import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import cv2
import numpy as np

from scripts.visual_qc.intake import IntakeValidationError, validate_intake_batch
from scripts.visual_qc.intake_builder import (
    build_intake_manifest,
    create_validated_intake_manifest,
    parse_image_assignment,
)


ROOT = Path(__file__).resolve().parents[1]


def encode_jpeg(width=180, height=120, value=170):
    image = np.full((height, width, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("Unable to encode test JPEG")
    return encoded.tobytes()


class VisualQcIntakeBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.front = self.root / "front.jpg"
        self.back = self.root / "back.jpg"
        self.front.write_bytes(encode_jpeg(value=180))
        self.back.write_bytes(encode_jpeg(value=120))

    def tearDown(self):
        self.temp_dir.cleanup()

    def options(self, **overrides):
        options = {
            "project_root": ROOT,
            "batch_id": "km4-physical-001",
            "board_key": "km4-f151",
            "capture_session_id": "km4-unit-001",
            "capture_stage": "golden_reference",
            "capture_setup_id": "standard-bench",
            "image_assignments": [
                ("main_page_2", self.back),
                ("main_page_1", self.front),
            ],
            "capture_checklist_confirmed": True,
        }
        options.update(overrides)
        return options

    def test_parse_image_assignment_preserves_path_after_first_equals(self):
        side_id, path = parse_image_assignment("main_page_1=C:/photos/set=1/front.jpg")

        self.assertEqual(side_id, "main_page_1")
        self.assertEqual(path, Path("C:/photos/set=1/front.jpg"))

    def test_parse_image_assignment_rejects_missing_side_or_path(self):
        for raw in ("front.jpg", "=front.jpg", "main_page_1=", "  =  "):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(IntakeValidationError, "side_id=path"):
                    parse_image_assignment(raw)

    def test_build_manifest_is_sorted_and_binds_current_image_hashes(self):
        manifest = build_intake_manifest(**self.options())

        self.assertEqual(manifest["schema_version"], "VISUAL-QC-INTAKE-BATCH-V1")
        self.assertEqual(manifest["batch_id"], "km4-physical-001")
        self.assertEqual(
            [entry["side_id"] for entry in manifest["entries"]],
            ["main_page_1", "main_page_2"],
        )
        front_entry = manifest["entries"][0]
        self.assertEqual(front_entry["entry_id"], "km4-unit-001-main_page_1")
        self.assertEqual(front_entry["file_path"], str(self.front.resolve()))
        self.assertEqual(
            front_entry["expected_sha256"],
            hashlib.sha256(self.front.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            front_entry["capture_checklist"],
            {
                "board_and_side_confirmed": True,
                "focus_and_lens_confirmed": True,
                "lighting_and_occlusion_confirmed": True,
            },
        )

    def test_builder_requires_explicit_checklist_confirmation(self):
        with self.assertRaisesRegex(IntakeValidationError, "confirmation is required"):
            build_intake_manifest(
                **self.options(capture_checklist_confirmed=False)
            )

    def test_builder_rejects_duplicate_sides_and_resolved_paths(self):
        with self.assertRaisesRegex(IntakeValidationError, "duplicate side_id"):
            build_intake_manifest(
                **self.options(
                    image_assignments=[
                        ("main_page_1", self.front),
                        ("main_page_1", self.back),
                    ]
                )
            )

        with self.assertRaisesRegex(IntakeValidationError, "duplicate resolved image path"):
            build_intake_manifest(
                **self.options(
                    image_assignments=[
                        ("main_page_1", self.front),
                        ("main_page_2", self.root / "." / "front.jpg"),
                    ]
                )
            )

    def test_builder_rejects_unknown_side_and_invalid_image(self):
        with self.assertRaisesRegex(IntakeValidationError, "does not belong"):
            build_intake_manifest(
                **self.options(image_assignments=[("unknown_side", self.front)])
            )

        broken = self.root / "broken.jpg"
        broken.write_bytes(b"not-an-image")
        with self.assertRaisesRegex(IntakeValidationError, "image signature"):
            build_intake_manifest(
                **self.options(image_assignments=[("main_page_1", broken)])
            )

    def test_builder_rejects_repository_proxy_material(self):
        proxy = ROOT / "assets" / "board-atlas" / "km4-f151" / "main-point-map-page-1.png"
        copied_proxy = self.root / "renamed-reference.png"
        copied_proxy.write_bytes(proxy.read_bytes())

        for path in (proxy, copied_proxy):
            with self.subTest(path=path):
                with self.assertRaisesRegex(
                    IntakeValidationError, "reference or proxy image"
                ):
                    build_intake_manifest(
                        **self.options(image_assignments=[("main_page_1", path)])
                    )

    def test_create_manifest_writes_a_validator_compatible_file(self):
        output = self.root / "batch.intake.json"

        result = create_validated_intake_manifest(
            output_path=output,
            **self.options(),
        )

        persisted = json.loads(output.read_text(encoding="utf-8"))
        validated = validate_intake_batch(output, ROOT)
        self.assertEqual(persisted, result["manifest"])
        self.assertEqual(len(validated["entries"]), 2)
        self.assertEqual(result["output_path"], output.resolve())
        self.assertEqual(result["validated_batch"]["batch_id"], "km4-physical-001")

    def test_create_manifest_protects_existing_output_unless_forced(self):
        output = self.root / "batch.intake.json"
        output.write_text('{"keep": true}\n', encoding="utf-8")

        with self.assertRaisesRegex(IntakeValidationError, "already exists"):
            create_validated_intake_manifest(output_path=output, **self.options())
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"keep": True})

        result = create_validated_intake_manifest(
            output_path=output,
            force=True,
            **self.options(),
        )
        self.assertEqual(result["manifest"]["batch_id"], "km4-physical-001")

    def test_force_cannot_replace_a_source_image(self):
        original = self.front.read_bytes()

        with self.assertRaisesRegex(
            IntakeValidationError, "cannot replace a source image"
        ):
            create_validated_intake_manifest(
                output_path=self.front,
                force=True,
                **self.options(image_assignments=[("main_page_1", self.front)]),
            )

        self.assertEqual(self.front.read_bytes(), original)

    def test_non_force_publish_never_overwrites_a_concurrently_created_file(self):
        output = self.root / "race.intake.json"
        real_validate = validate_intake_batch

        def validate_after_competing_create(manifest_path, project_root):
            validated = real_validate(manifest_path, project_root)
            output.write_text("PROTECTED\n", encoding="utf-8")
            return validated

        with patch(
            "scripts.visual_qc.intake_builder.validate_intake_batch",
            side_effect=validate_after_competing_create,
        ):
            with self.assertRaisesRegex(
                IntakeValidationError, "appeared while the manifest was being validated"
            ):
                create_validated_intake_manifest(
                    output_path=output,
                    **self.options(),
                )

        self.assertEqual(output.read_text(encoding="utf-8"), "PROTECTED\n")


class VisualQcIntakeBuilderCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.front = self.root / "front.jpg"
        self.front.write_bytes(encode_jpeg(value=160))
        self.script = ROOT / "scripts" / "create_visual_qc_intake_batch.py"

    def tearDown(self):
        self.temp_dir.cleanup()

    def command(self, *extra):
        return [
            sys.executable,
            str(self.script),
            "--batch-id",
            "km4-cli-batch",
            "--board-key",
            "km4-f151",
            "--capture-session-id",
            "km4-cli-unit",
            "--capture-stage",
            "before_repair",
            "--image",
            f"main_page_1={self.front}",
            *extra,
        ]

    def run_cli(self, *extra):
        return subprocess.run(
            self.command(*extra),
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_direct_invocation_writes_default_manifest_and_json_summary(self):
        result = self.run_cli("--confirm-capture-checklist")

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        summary = json.loads(result.stdout)
        output = self.root / "km4-cli-batch.intake.json"
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(summary["batch_id"], "km4-cli-batch")
        self.assertEqual(summary["manifest"], str(output.resolve()))
        self.assertEqual(summary["entry_count"], 1)
        self.assertEqual(summary["entries"][0]["side_id"], "main_page_1")
        self.assertEqual(summary["entries"][0]["width"], 180)
        self.assertEqual(summary["entries"][0]["height"], 120)
        self.assertEqual(
            summary["entries"][0]["sha256"],
            hashlib.sha256(self.front.read_bytes()).hexdigest(),
        )
        self.assertTrue(output.is_file())

    def test_cli_requires_explicit_checklist_confirmation(self):
        result = self.run_cli()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "validation_failed")
        self.assertIn("confirmation is required", result.stdout)
        self.assertFalse((self.root / "km4-cli-batch.intake.json").exists())

    def test_cli_reports_bad_assignment_unknown_side_and_invalid_image(self):
        cases = [
            (["--image", "not-an-assignment"], "side_id=path"),
            (
                ["--image", f"unknown_side={self.front}"],
                "does not belong",
            ),
        ]
        broken = self.root / "broken.jpg"
        broken.write_bytes(b"bad-image")
        cases.append(
            (["--image", f"main_page_2={broken}"], "image signature")
        )

        for replacement, message in cases:
            with self.subTest(message=message):
                command = self.command("--confirm-capture-checklist")
                image_index = command.index("--image")
                command[image_index : image_index + 2] = replacement
                result = subprocess.run(
                    command,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, json.loads(result.stdout)["message"])

    def test_cli_reports_missing_image_as_validation_failure(self):
        missing = self.root / "missing.jpg"
        command = self.command("--confirm-capture-checklist")
        image_index = command.index("--image")
        command[image_index + 1] = f"main_page_1={missing}"

        result = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "validation_failed")
        self.assertIn("does not exist", payload["message"])

    def test_argparse_errors_are_machine_readable_validation_failures(self):
        cases = [
            [sys.executable, str(self.script)],
            [
                *self.command("--confirm-capture-checklist"),
                "--capture-stage",
                "not-a-stage",
            ],
        ]

        for command in cases:
            with self.subTest(command=command):
                result = subprocess.run(
                    command,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "validation_failed")
                self.assertEqual(result.stderr, "")

    def test_cli_protects_existing_output_and_force_replaces_it(self):
        output = self.root / "custom.json"
        output.write_text('{"keep": true}\n', encoding="utf-8")

        blocked = self.run_cli(
            "--confirm-capture-checklist", "--output", str(output)
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"keep": True})

        replaced = self.run_cli(
            "--confirm-capture-checklist",
            "--output",
            str(output),
            "--force",
        )
        self.assertEqual(replaced.returncode, 0, replaced.stderr or replaced.stdout)
        self.assertEqual(
            json.loads(output.read_text(encoding="utf-8"))["batch_id"],
            "km4-cli-batch",
        )


if __name__ == "__main__":
    unittest.main()
