import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.build_h897_photo_navigation import (
    build_navigation_manifest,
    validate_navigation_manifest,
)
from scripts.visual_qc.proxy_inventory import known_proxy_hashes


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reviewed_image(sha256, side_id, source_dimensions, transform, registration_dimensions):
    return {
        "sha256": sha256,
        "side_id": side_id,
        "source_dimensions": source_dimensions,
        "registration_transform": transform,
        "registration_dimensions": registration_dimensions,
        "capture_geometry_id": f"H897-{side_id}",
        "view_scope": "full_board_repair_case",
        "source_annotation_present": False,
        "source_annotation_role": None,
        "registration_status": "reviewed_manual_registration",
        "registration_review": {
            "review_status": "reviewed",
            "board_to_image_matrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
            "error": {"unit": "normalized_image_plane", "rms": 0.01},
            "field_accuracy_claim_allowed": False,
        },
    }


class H897PhotoNavigationBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_root = self.root / "controlled"
        self.derivative_root = self.root / "site" / "assets" / "physical"
        self.source_root.mkdir(parents=True)

        page_one = self.source_root / "nested" / "page-one.jpg"
        page_one.parent.mkdir()
        Image.new("RGB", (80, 120), "#31584d").save(page_one, quality=95)
        page_two = self.source_root / "page-two.jpg"
        Image.new("RGB", (120, 80), "#4b6250").save(page_two, quality=95)
        self.sources = [page_one, page_two]
        hashes = [_sha256(path) for path in self.sources]
        self.reviewed = {
            "board_key": "kj6-h897",
            "board_id": "BOARD-H897-MAIN-V1.2",
            "physical_board_revision": "H897 V1.2",
            "engineering_board_revision": "H897_MAIN_PCB_V1.2",
            "images": [
                _reviewed_image(
                    hashes[0],
                    "main_page_1",
                    {"width": 80, "height": 120},
                    "rotate_90_counterclockwise",
                    {"width": 120, "height": 80},
                ),
                _reviewed_image(
                    hashes[1],
                    "main_page_2",
                    {"width": 120, "height": 80},
                    "none",
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

    def test_builds_hash_bound_metadata_stripped_derivatives(self):
        manifest = self._build()

        self.assertEqual(manifest["schema_version"], "H897-PHOTO-NAVIGATION-V1")
        self.assertEqual(manifest["board_key"], "kj6-h897")
        self.assertEqual(len(manifest["photos"]), 2)
        self.assertEqual(
            [item["side_id"] for item in manifest["photos"]],
            ["main_page_1", "main_page_2"],
        )
        self.assertEqual(validate_navigation_manifest(manifest, self.root / "site"), [])
        for item in manifest["photos"]:
            derivative = self.root / "site" / item["asset_path"]
            self.assertEqual(_sha256(derivative), item["derivative_sha256"])
            with Image.open(derivative) as image:
                self.assertEqual(image.size, (60, 40))
                self.assertEqual(image.format, "WEBP")
                self.assertFalse(image.getexif())
                self.assertNotIn("icc_profile", image.info)
                self.assertNotIn("xmp", image.info)

    def test_manifest_excludes_controlled_paths_and_rejects_tampering(self):
        manifest = self._build()
        serialized = json.dumps(manifest, ensure_ascii=False)

        self.assertNotIn(str(self.source_root), serialized)
        self.assertNotIn("page-one.jpg", serialized)
        self.assertTrue(
            all(
                item["source_scope"] == "owner_authorized_feishu_case_library"
                for item in manifest["photos"]
            )
        )

        self.sources[0].write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "source hash"):
            self._build()


class H897PublishedPhotoNavigationTests(unittest.TestCase):
    def test_published_derivatives_are_protected_by_the_proxy_inventory(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads(
            (root / "knowledge-base/h897-photo-navigation.json").read_text(encoding="utf-8")
        )
        protected_hashes = known_proxy_hashes(root)

        self.assertTrue(
            {item["derivative_sha256"] for item in manifest["photos"]}.issubset(
                protected_hashes
            )
        )


if __name__ == "__main__":
    unittest.main()
