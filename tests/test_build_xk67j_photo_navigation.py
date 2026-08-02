import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.build_xk67j_photo_navigation import (
    build_navigation_manifest,
    validate_navigation_manifest,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reviewed_image(sha256, side_id, source_dimensions, transform, registration_dimensions):
    return {
        "sha256": sha256,
        "side_id": side_id,
        "source_dimensions": source_dimensions,
        "registration_transform": transform,
        "registration_dimensions": registration_dimensions,
        "view_scope": "full_board_repair_case",
        "source_annotation_present": side_id == "main_page_2",
        "source_annotation_role": (
            "source_component_callout_not_system_label"
            if side_id == "main_page_2"
            else None
        ),
        "registration_status": "reviewed_manual_registration",
        "registration_review": {
            "review_status": "reviewed",
            "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
            "error": {"unit": "normalized_image_plane", "rms": 0.01},
            "field_accuracy_claim_allowed": False,
        },
    }


class Xk67jPhotoNavigationBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_root = self.root / "controlled"
        self.derivative_root = self.root / "site" / "assets" / "physical"
        self.source_root.mkdir(parents=True)

        page_two_a = self.source_root / "nested" / "page-two-a.jpg"
        page_two_a.parent.mkdir()
        Image.new("RGB", (120, 80), "#164c42").save(page_two_a, quality=95)

        page_two_b = self.source_root / "page-two-b.jpg"
        Image.new("RGB", (120, 80), "#53613f").save(page_two_b, quality=95)

        page_one = self.source_root / "page-one.jpg"
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (120, 80), "#2f4645").save(page_one, quality=95, exif=exif)

        self.sources = [page_two_a, page_two_b, page_one]
        hashes = [_sha256(path) for path in self.sources]
        self.reviewed = {
            "board_key": "xk67j-shared",
            "board_id": "BOARD-XK67J-MAIN-V1.0B",
            "physical_board_revision": "XK67J_MAIN V1.0",
            "engineering_board_revision": "XK67J_MAIN_PCB V1.0B",
            "status": "reviewed_board_coordinate_registration",
            "images": [
                _reviewed_image(
                    hashes[0],
                    "main_page_2",
                    {"width": 120, "height": 80},
                    "none",
                    {"width": 120, "height": 80},
                ),
                _reviewed_image(
                    hashes[1],
                    "main_page_2",
                    {"width": 120, "height": 80},
                    "none",
                    {"width": 120, "height": 80},
                ),
                _reviewed_image(
                    hashes[2],
                    "main_page_1",
                    {"width": 80, "height": 120},
                    "rotate_90_counterclockwise",
                    {"width": 120, "height": 80},
                ),
            ],
        }

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _build(self):
        return build_navigation_manifest(
            self.source_root,
            self.derivative_root,
            self.reviewed,
            asset_prefix="assets/physical",
            max_dimension=60,
        )

    def test_builds_one_side_one_and_two_side_two_photos_from_exact_hashes(self):
        manifest = self._build()

        self.assertEqual(manifest["schema_version"], "XK67J-PHOTO-NAVIGATION-V1")
        self.assertEqual(manifest["board_key"], "xk67j-shared")
        self.assertEqual(len(manifest["photos"]), 3)
        self.assertEqual(len({item["source_sha256"] for item in manifest["photos"]}), 3)
        self.assertEqual(
            [item["side_id"] for item in manifest["photos"]],
            ["main_page_1", "main_page_2", "main_page_2"],
        )
        self.assertEqual(
            [item["label"] for item in manifest["photos"]],
            ["第1面实拍", "第2面实拍 A", "第2面实拍 B"],
        )
        self.assertEqual(validate_navigation_manifest(manifest, self.root / "site"), [])

    def test_normalizes_orientation_resizes_and_strips_metadata(self):
        manifest = self._build()

        for item in manifest["photos"]:
            derivative = self.root / "site" / item["asset_path"]
            self.assertEqual(_sha256(derivative), item["derivative_sha256"])
            with Image.open(derivative) as image:
                self.assertEqual(max(image.size), 60)
                self.assertEqual(image.size, (60, 40))
                self.assertEqual(image.format, "WEBP")
                self.assertFalse(image.getexif())
                self.assertNotIn("icc_profile", image.info)
                self.assertNotIn("xmp", image.info)
            self.assertEqual(item["registration_dimensions"], {"width": 120, "height": 80})
            self.assertEqual(item["derivative_dimensions"], {"width": 60, "height": 40})
            self.assertEqual(len(item["board_to_image_matrix"]), 9)

    def test_manifest_contains_no_controlled_source_path(self):
        manifest = self._build()
        serialized = json.dumps(manifest, ensure_ascii=False)

        self.assertNotIn(str(self.source_root), serialized)
        self.assertNotIn("page-two-a.jpg", serialized)
        self.assertNotIn("page-one.jpg", serialized)
        self.assertTrue(all(item["source_scope"] == "owner_authorized_feishu_case_library" for item in manifest["photos"]))

    def test_rejects_missing_or_tampered_sources(self):
        self.sources[0].write_bytes(b"tampered")

        with self.assertRaisesRegex(ValueError, "source hash"):
            self._build()

    def test_rejects_unreviewed_or_duplicate_photo_contracts(self):
        self.reviewed["images"][0]["registration_review"]["review_status"] = "draft"
        with self.assertRaisesRegex(ValueError, "reviewed registration"):
            self._build()

        self.reviewed["images"][0]["registration_review"]["review_status"] = "reviewed"
        self.reviewed["images"][1]["sha256"] = self.reviewed["images"][0]["sha256"]
        with self.assertRaisesRegex(ValueError, "unique source hashes"):
            self._build()


if __name__ == "__main__":
    unittest.main()
