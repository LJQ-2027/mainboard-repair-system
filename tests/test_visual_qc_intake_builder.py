import hashlib
import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
