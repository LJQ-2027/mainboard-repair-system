import json
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class CompiledH8918BoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_one = json.loads((ROOT / "knowledge-base/h8918-board-compiled-page-1.json").read_text(encoding="utf-8"))
        cls.page_two = json.loads((ROOT / "knowledge-base/h8918-board-compiled.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / "knowledge-base/h8918-board-sides.json").read_text(encoding="utf-8"))
        cls.schematic = json.loads((ROOT / "knowledge-base/h8918-schematic-compiled.json").read_text(encoding="utf-8"))

    def test_compiles_direct_page_content_on_both_board_sides(self):
        self.assertEqual(self.page_one["board_id"], "BOARD-H8918-MAIN-V1.2")
        self.assertEqual(self.page_two["board_id"], self.page_one["board_id"])
        self.assertEqual(self.page_one["source"]["form_xobject"], "/PageContents")
        self.assertEqual(self.page_two["source"]["form_xobject"], "/PageContents")
        self.assertGreaterEqual(self.page_one["audit"]["accepted_designators"], 550)
        self.assertGreaterEqual(self.page_two["audit"]["accepted_designators"], 630)
        self.assertTrue(self.page_one["audit"]["required_recovery_complete"])
        self.assertTrue(self.page_two["audit"]["required_recovery_complete"])

    def test_reviewed_identities_remain_on_their_source_side(self):
        page_one = {item["designator"] for item in self.page_one["components"]}
        page_two = {item["designator"] for item in self.page_two["components"]}
        self.assertIn("U1001", page_one)
        for designator in ("U2001", "X2101", "J6102", "U5007", "VBAT1"):
            self.assertIn(designator, page_two)

    def test_manifest_and_textures_preserve_source_order(self):
        self.assertEqual(self.manifest["default_side_id"], "main_page_2")
        self.assertEqual([item["source_pdf_page"] for item in self.manifest["sides"]], [1, 2])
        for side in self.manifest["sides"]:
            texture = ROOT / side["engineering_texture"]
            self.assertTrue(texture.is_file())
            with Image.open(texture) as image:
                self.assertGreater(image.width, 7000)
                self.assertGreater(image.height, 4500)

    def test_schematic_recovers_only_the_explicit_exact_subset(self):
        expected_pages = {
            "U1001": [2, 2, 3, 3, 4, 4, 5, 5],
            "U2001": [6, 6, 7, 7, 7, 7, 7, 7],
            "X2101": [7],
            "U5007": [17],
        }
        self.assertTrue(self.schematic["audit"]["reviewed_recovery_complete"])
        self.assertEqual(self.schematic["audit"]["reviewed_designators"], sorted(expected_pages))
        for designator, pages in expected_pages.items():
            self.assertEqual([item["page"] for item in self.schematic["components"][designator]], pages)

    def test_outline_is_normalized_and_source_bounded(self):
        for dataset in (self.page_one, self.page_two):
            self.assertGreater(len(dataset["board_outline"]), 40)
            self.assertGreater(dataset["audit"]["outline_mask_area_ratio"], 0.75)
            self.assertLess(dataset["audit"]["outline_mask_area_ratio"], 0.9)
            for point in dataset["board_outline"]:
                self.assertLessEqual(0, point["x"])
                self.assertLessEqual(point["x"], 1)
                self.assertLessEqual(0, point["y"])
                self.assertLessEqual(point["y"], 1)


if __name__ == "__main__":
    unittest.main()
