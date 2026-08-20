import json
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class CompiledKl4BoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_one = json.loads((ROOT / "knowledge-base/kl4-board-compiled-page-1.json").read_text(encoding="utf-8"))
        cls.page_two = json.loads((ROOT / "knowledge-base/kl4-board-compiled.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / "knowledge-base/kl4-board-sides.json").read_text(encoding="utf-8"))
        cls.schematic = json.loads((ROOT / "knowledge-base/kl4-schematic-compiled.json").read_text(encoding="utf-8"))

    def test_compiles_two_source_pages_with_one_board_identity(self):
        self.assertEqual(self.page_one["board_id"], "BOARD-KL4-F201-MAIN-V1.2")
        self.assertEqual(self.page_two["board_id"], self.page_one["board_id"])
        self.assertEqual(self.page_one["source"]["page"], 1)
        self.assertEqual(self.page_two["source"]["page"], 2)
        self.assertGreaterEqual(self.page_one["audit"]["accepted_designators"], 350)
        self.assertGreaterEqual(self.page_two["audit"]["accepted_designators"], 800)
        self.assertTrue(self.page_one["audit"]["required_recovery_complete"])
        self.assertTrue(self.page_two["audit"]["required_recovery_complete"])

    def test_reviewed_geometry_stays_on_its_source_side(self):
        page_one = {item["designator"] for item in self.page_one["components"]}
        page_two = {item["designator"] for item in self.page_two["components"]}
        self.assertIn("U1001", page_one)
        self.assertIn("U2001", page_two)
        self.assertIn("X2100", page_two)

    def test_manifest_and_textures_preserve_source_order(self):
        self.assertEqual(self.manifest["default_side_id"], "main_page_2")
        self.assertEqual([item["source_pdf_page"] for item in self.manifest["sides"]], [1, 2])
        for side in self.manifest["sides"]:
            texture = ROOT / side["engineering_texture"]
            self.assertTrue(texture.is_file())
            with Image.open(texture) as image:
                self.assertGreater(image.width, 3000)
                self.assertGreater(image.height, 2500)

    def test_schematic_recovers_reviewed_components_and_rails(self):
        expected_pages = {
            "U1001": [3, 3, 3, 3, 4, 4, 5],
            "U2001": [6, 7],
            "X2100": [7],
            "VDDCORE": [3, 3, 3, 3, 6, 15],
            "VDDEMMCCORE": [6, 6, 14, 14],
        }
        self.assertTrue(self.schematic["audit"]["reviewed_recovery_complete"])
        for designator, pages in expected_pages.items():
            self.assertEqual([item["page"] for item in self.schematic["components"][designator]], pages)

    def test_all_compiled_geometry_is_normalized(self):
        for dataset in (self.page_one, self.page_two):
            self.assertGreater(len(dataset["board_outline"]), 20)
            for point in dataset["board_outline"]:
                self.assertLessEqual(0, point["x"])
                self.assertLessEqual(point["x"], 1)
                self.assertLessEqual(0, point["y"])
                self.assertLessEqual(point["y"], 1)
            for component in dataset["components"]:
                self.assertLessEqual(0, component["center"]["x"])
                self.assertLessEqual(component["center"]["x"], 1)
                self.assertLessEqual(0, component["center"]["y"])
                self.assertLessEqual(component["center"]["y"], 1)


if __name__ == "__main__":
    unittest.main()
