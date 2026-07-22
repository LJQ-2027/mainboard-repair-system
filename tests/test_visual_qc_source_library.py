import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import cv2
import numpy as np

from scripts.visual_qc.intake import (
    IntakeValidationError,
    validate_intake_batch,
    write_json_atomic,
)
from scripts.visual_qc.source_library import (
    SOURCE_PACKAGE_SCHEMA_VERSION,
    build_source_package,
    stage_source_package,
    validate_source_package,
)


ROOT = Path(__file__).resolve().parents[1]


def encode_image(extension, *, width=180, height=120, value=170):
    image = np.full((height, width, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(extension, image)
    if not ok:
        raise RuntimeError(f"Unable to encode test image: {extension}")
    return encoded.tobytes()


class VisualQcSourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.library = self.root / "controlled-library"
        self.front = self.root / "incoming-front.jpeg"
        self.back = self.root / "incoming-back.png"
        self.front.write_bytes(encode_image(".jpg", value=180))
        self.back.write_bytes(encode_image(".png", value=120))

    def tearDown(self):
        self.temp_dir.cleanup()

    def options(self, **overrides):
        options = {
            "project_root": ROOT,
            "library_root": self.library,
            "package_id": "km4-unit-001-source",
            "batch_id": "km4-unit-001-batch",
            "board_key": "km4-f151",
            "capture_session_id": "km4-unit-001",
            "capture_stage": "before_repair",
            "capture_setup_id": "standard-bench",
            "image_assignments": [
                ("main_page_2", self.back),
                ("main_page_1", self.front),
            ],
            "milo_physical_source_confirmed": True,
            "capture_checklist_confirmed": True,
        }
        options.update(overrides)
        return options

    def test_build_source_package_is_deterministic_and_content_addressed(self):
        first = build_source_package(**self.options())
        second = build_source_package(**self.options())

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], SOURCE_PACKAGE_SCHEMA_VERSION)
        self.assertEqual(first["source_origin"], "milo_supplied")
        self.assertIs(first["physical_source_confirmed"], True)
        self.assertEqual(first["board_key"], "km4-f151")
        self.assertEqual(first["board_id"], "BOARD-KM4-F151-MAIN-V1.2")
        self.assertEqual(first["capture_stage"], "before_repair")
        self.assertEqual(
            [entry["side_id"] for entry in first["entries"]],
            ["main_page_1", "main_page_2"],
        )

        front = first["entries"][0]
        front_hash = hashlib.sha256(self.front.read_bytes()).hexdigest()
        self.assertEqual(front["original_filename"], "incoming-front.jpeg")
        self.assertEqual(front["mime_type"], "image/jpeg")
        self.assertEqual(front["width"], 180)
        self.assertEqual(front["height"], 120)
        self.assertEqual(front["byte_size"], len(self.front.read_bytes()))
        self.assertEqual(front["sha256"], front_hash)
        self.assertEqual(
            front["object_path"],
            f"objects/originals/{front_hash[:2]}/{front_hash}.jpg",
        )
        self.assertNotIn("source_path", json.dumps(first))
        self.assertNotIn("created_at", first)

    def test_package_requires_explicit_physical_source_confirmation(self):
        with self.assertRaisesRegex(
            IntakeValidationError, "Milo-supplied physical source confirmation"
        ):
            build_source_package(
                **self.options(milo_physical_source_confirmed=False)
            )

    def test_library_root_must_be_outside_the_repository(self):
        with self.assertRaisesRegex(IntakeValidationError, "outside the project repository"):
            build_source_package(
                **self.options(library_root=ROOT / ".local" / "visual-source-library")
            )
        self.assertFalse((ROOT / ".local" / "visual-source-library").exists())

    def test_existing_intake_validation_rejects_duplicates_and_invalid_images(self):
        with self.assertRaisesRegex(IntakeValidationError, "duplicate side_id"):
            build_source_package(
                **self.options(
                    image_assignments=[
                        ("main_page_1", self.front),
                        ("main_page_1", self.back),
                    ]
                )
            )

        with self.assertRaisesRegex(IntakeValidationError, "duplicate resolved image path"):
            build_source_package(
                **self.options(
                    image_assignments=[
                        ("main_page_1", self.front),
                        ("main_page_2", self.root / "." / self.front.name),
                    ]
                )
            )

        broken = self.root / "broken.jpg"
        broken.write_bytes(b"not-an-image")
        with self.assertRaisesRegex(IntakeValidationError, "image signature"):
            build_source_package(
                **self.options(image_assignments=[("main_page_1", broken)])
            )

    def test_known_proxy_bytes_remain_blocked_after_external_copy(self):
        proxy = (
            ROOT
            / "assets"
            / "vision-reference-gallery"
            / "km4"
            / "embedded"
            / "page-003-image-02.jpg"
        )
        copied = self.root / "renamed-photo.jpg"
        copied.write_bytes(proxy.read_bytes())

        with self.assertRaisesRegex(
            IntakeValidationError, "known reference or proxy image"
        ):
            build_source_package(
                **self.options(image_assignments=[("main_page_1", copied)])
            )

    def materialize_package(self, payload):
        package_dir = self.library / "packages" / payload["package_id"]
        package_dir.mkdir(parents=True)
        source_by_side = {
            "main_page_1": self.front,
            "main_page_2": self.back,
        }
        for entry in payload["entries"]:
            destination = self.library / entry["object_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_by_side[entry["side_id"]].read_bytes())
        manifest_path = package_dir / "source-package.json"
        write_json_atomic(manifest_path, payload)
        return manifest_path

    def test_validate_source_package_verifies_objects_and_board_identity(self):
        payload = build_source_package(**self.options())
        manifest_path = self.materialize_package(payload)

        validated = validate_source_package(manifest_path, ROOT, self.library)

        self.assertEqual(validated["package_id"], payload["package_id"])
        self.assertEqual(len(validated["entries"]), 2)
        self.assertEqual(
            validated["entries"][0]["object_file"],
            (self.library / payload["entries"][0]["object_path"]).resolve(),
        )

    def test_validate_source_package_rejects_path_escape_and_corruption(self):
        payload = build_source_package(**self.options())
        manifest_path = self.materialize_package(payload)

        escaped = json.loads(manifest_path.read_text(encoding="utf-8"))
        escaped["entries"][0]["object_path"] = "../outside.jpg"
        write_json_atomic(manifest_path, escaped)
        with self.assertRaisesRegex(IntakeValidationError, "object_path"):
            validate_source_package(manifest_path, ROOT, self.library)

        write_json_atomic(manifest_path, payload)
        object_path = self.library / payload["entries"][0]["object_path"]
        object_path.write_bytes(b"corrupted")
        with self.assertRaisesRegex(IntakeValidationError, "object integrity"):
            validate_source_package(manifest_path, ROOT, self.library)

    def test_stage_preserves_exact_bytes_and_creates_compatible_manifests(self):
        original_front = self.front.read_bytes()
        original_back = self.back.read_bytes()

        result = stage_source_package(**self.options())

        self.assertEqual(result["state"], "created")
        self.assertEqual(result["entry_count"], 2)
        self.assertEqual(
            result["source_package_path"],
            (
                self.library
                / "packages"
                / "km4-unit-001-source"
                / "source-package.json"
            ).resolve(),
        )
        self.assertEqual(
            result["intake_manifest_path"],
            (
                self.library
                / "packages"
                / "km4-unit-001-source"
                / "km4-unit-001-batch.intake.json"
            ).resolve(),
        )
        validated_source = validate_source_package(
            result["source_package_path"], ROOT, self.library
        )
        validated_intake = validate_intake_batch(result["intake_manifest_path"], ROOT)
        self.assertEqual(len(validated_source["entries"]), 2)
        self.assertEqual(len(validated_intake["entries"]), 2)
        by_side = {entry["side_id"]: entry for entry in validated_source["entries"]}
        self.assertEqual(
            by_side["main_page_1"]["object_file"].read_bytes(), original_front
        )
        self.assertEqual(
            by_side["main_page_2"]["object_file"].read_bytes(), original_back
        )
        self.assertEqual(self.front.read_bytes(), original_front)
        self.assertEqual(self.back.read_bytes(), original_back)

    def test_identical_stage_is_idempotently_reused(self):
        created = stage_source_package(**self.options())
        first_source_bytes = created["source_package_path"].read_bytes()
        first_intake_bytes = created["intake_manifest_path"].read_bytes()

        reused = stage_source_package(**self.options())

        self.assertEqual(reused["state"], "reused")
        self.assertEqual(reused["source_package_path"].read_bytes(), first_source_bytes)
        self.assertEqual(reused["intake_manifest_path"].read_bytes(), first_intake_bytes)

    def test_existing_package_rejects_changed_content_or_metadata(self):
        created = stage_source_package(**self.options())
        committed = created["source_package_path"].read_bytes()

        changed = self.root / "changed-front.jpeg"
        changed.write_bytes(encode_image(".jpg", value=40))
        with self.assertRaisesRegex(IntakeValidationError, "package conflict"):
            stage_source_package(
                **self.options(
                    image_assignments=[
                        ("main_page_1", changed),
                        ("main_page_2", self.back),
                    ]
                )
            )
        with self.assertRaisesRegex(IntakeValidationError, "package conflict"):
            stage_source_package(
                **self.options(capture_stage="after_repair")
            )
        self.assertEqual(created["source_package_path"].read_bytes(), committed)

    def test_corrupted_existing_object_fails_closed(self):
        result = stage_source_package(**self.options())
        payload = json.loads(result["source_package_path"].read_text(encoding="utf-8"))
        object_file = self.library / payload["entries"][0]["object_path"]
        object_file.write_bytes(b"corrupted")

        with self.assertRaisesRegex(IntakeValidationError, "object integrity"):
            stage_source_package(**self.options())

    def test_conflicting_preexisting_object_is_not_replaced(self):
        payload = build_source_package(**self.options())
        object_file = self.library / payload["entries"][0]["object_path"]
        object_file.parent.mkdir(parents=True)
        object_file.write_bytes(b"PROTECTED")

        with self.assertRaisesRegex(IntakeValidationError, "object integrity"):
            stage_source_package(**self.options())

        self.assertEqual(object_file.read_bytes(), b"PROTECTED")
        self.assertFalse(
            (self.library / "packages" / payload["package_id"]).exists()
        )

    def test_intake_failure_does_not_publish_partial_package(self):
        with patch(
            "scripts.visual_qc.source_library.create_validated_intake_manifest",
            side_effect=IntakeValidationError("injected intake failure"),
        ):
            with self.assertRaisesRegex(IntakeValidationError, "injected intake failure"):
                stage_source_package(**self.options())

        self.assertFalse(
            (self.library / "packages" / "km4-unit-001-source").exists()
        )


if __name__ == "__main__":
    unittest.main()
