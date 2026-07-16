import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.board_compiler.pipeline import (
    build_schematic_payload,
    build_side_manifest,
    compile_geometry,
    compile_side,
)


def sample_profile():
    return {
        "profile_id": "sample-board",
        "model": "SAMPLE",
        "board_id": "BOARD-SAMPLE-MAIN-V1",
        "board_version": "SAMPLE_MAIN_V1",
        "component_prefix": "SAMPLE-MAIN",
        "point_map_source": "source.pdf",
        "schematic_source": "schematic.pdf",
        "default_side_id": "side_2",
        "schematic_geometry_side_id": "side_2",
        "side_manifest_output": "out/sides.json",
        "schematic_output": "out/schematic.json",
        "cross_source_output": "out/registration.json",
        "reviewed_designators": ["U2001"],
        "sides": [
            {
                "side_id": "side_1",
                "label": "第1面",
                "source_pdf_page": 1,
                "engineering_texture": "assets/page-1.png",
                "compiled_data": "out/page-1.json",
                "source_crop": {"x": 0, "y": 0, "width": 1, "height": 1},
                "required_designators": [],
            },
            {
                "side_id": "side_2",
                "label": "第2面",
                "source_pdf_page": 2,
                "engineering_texture": "assets/page-2.png",
                "compiled_data": "out/page-2.json",
                "source_crop": {"x": 0, "y": 0, "width": 1, "height": 1},
                "required_designators": ["U2001"],
            },
        ],
    }


def sample_primitives(designator="U2001"):
    return {
        "form_name": "/I1",
        "bounds": [0, 0, 100, 50],
        "visible_bounds": [0, 0, 100, 50],
        "labels": [{"text": designator, "x": 50, "y": 25}],
        "rectangles": [{"x": 45, "y": 20, "width": 10, "height": 10}],
    }


def sample_outline():
    return {
        "outline": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9}],
        "mask_area_ratio": 0.64,
        "image_size": {"width": 100, "height": 50},
    }


class BoardPipelineTests(unittest.TestCase):
    def test_compile_side_uses_profile_identity_and_prefix(self):
        profile = sample_profile()
        side = profile["sides"][1]
        result = compile_side(Path("."), profile, side, primitives=sample_primitives(), outline=sample_outline())

        self.assertEqual(result["board_id"], "BOARD-SAMPLE-MAIN-V1")
        self.assertEqual(result["side_id"], "side_2")
        self.assertEqual(result["components"][0]["component_id"], "SAMPLE-MAIN-P2-U2001")
        self.assertTrue(result["audit"]["required_recovery_complete"])

    def test_compile_side_reports_missing_required_designators(self):
        profile = sample_profile()
        side = profile["sides"][1]
        result = compile_side(Path("."), profile, side, primitives=sample_primitives("U3001"), outline=sample_outline())

        self.assertFalse(result["audit"]["required_recovery_complete"])
        self.assertEqual(result["audit"]["missing_required_designators"], ["U2001"])

    def test_compile_side_separates_physical_source_page_from_logical_component_page(self):
        profile = sample_profile()
        side = profile["sides"][1]
        side["point_map_source"] = "side-two.pdf"
        side["source_pdf_page"] = 1
        side["component_page"] = 2

        result = compile_side(Path("."), profile, side, primitives=sample_primitives(), outline=sample_outline())

        self.assertEqual(result["source"]["path"], "side-two.pdf")
        self.assertEqual(result["source"]["page"], 1)
        self.assertEqual(result["components"][0]["component_id"], "SAMPLE-MAIN-P2-U2001")

    def test_side_manifest_preserves_profile_order(self):
        manifest = build_side_manifest(sample_profile())

        self.assertEqual(manifest["default_side_id"], "side_2")
        self.assertEqual([side["side_id"] for side in manifest["sides"]], ["side_1", "side_2"])
        self.assertEqual(manifest["sides"][1]["compiled_data"], "out/page-2.json")

    def test_failed_batch_does_not_publish_partial_geometry(self):
        profile = sample_profile()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            for name in ("page-1.png", "page-2.png"):
                Image.new("RGB", (100, 50), "white").save(root / "assets" / name)

            def primitive_extractor(_source, page):
                return sample_primitives("U3001" if page == 2 else "U1001")

            with self.assertRaisesRegex(ValueError, "U2001"):
                compile_geometry(
                    root,
                    profile,
                    render_textures=False,
                    primitive_extractor=primitive_extractor,
                    outline_extractor=lambda _path, **_options: sample_outline(),
                )

            self.assertFalse((root / "out/page-1.json").exists())
            self.assertFalse((root / "out/page-2.json").exists())
            self.assertFalse((root / "out/sides.json").exists())

    def test_schematic_payload_links_only_exact_reviewed_identities(self):
        profile = sample_profile()
        pages = {
            1: [
                {"text": "U2001", "x": 50, "y": 25, "font_size": 10},
                {"text": "replace U2001", "x": 10, "y": 10, "font_size": 10},
            ]
        }
        page_sizes = {1: {"width": 100, "height": 50}}

        payload = build_schematic_payload(profile, {"U2001", "U3001"}, pages, page_sizes)

        self.assertEqual(payload["board_id"], profile["board_id"])
        self.assertEqual(payload["audit"]["linked_designators"], 1)
        self.assertTrue(payload["audit"]["reviewed_recovery_complete"])
        self.assertEqual(payload["components"]["U2001"][0]["text_origin"], {"x": 0.5, "y": 0.5})

    def test_schematic_payload_reports_missing_reviewed_identity(self):
        payload = build_schematic_payload(
            sample_profile(),
            {"U3001"},
            {1: [{"text": "U3001", "x": 20, "y": 10, "font_size": 10}]},
            {1: {"width": 100, "height": 50}},
        )

        self.assertFalse(payload["audit"]["reviewed_recovery_complete"])
        self.assertEqual(payload["audit"]["missing_reviewed_designators"], ["U2001"])

    def test_schematic_payload_uses_an_explicit_schematic_review_subset(self):
        profile = sample_profile()
        profile["reviewed_designators"] = ["U2001", "VBAT1"]
        profile["schematic_reviewed_designators"] = ["U2001"]

        payload = build_schematic_payload(
            profile,
            {"U2001", "VBAT1"},
            {1: [{"text": "U2001", "x": 50, "y": 25, "font_size": 10}]},
            {1: {"width": 100, "height": 50}},
        )

        self.assertTrue(payload["audit"]["reviewed_recovery_complete"])
        self.assertEqual(payload["audit"]["reviewed_designators"], ["U2001"])


if __name__ == "__main__":
    unittest.main()
