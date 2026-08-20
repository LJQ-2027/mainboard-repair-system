import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CompiledXk67jBoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_one = json.loads(
            (ROOT / "knowledge-base/xk67j-board-compiled-page-1.json").read_text(
                encoding="utf-8"
            )
        )
        cls.page_two = json.loads(
            (ROOT / "knowledge-base/xk67j-board-compiled-page-2.json").read_text(
                encoding="utf-8"
            )
        )
        cls.manifest = json.loads(
            (ROOT / "knowledge-base/xk67j-board-sides.json").read_text(encoding="utf-8")
        )
        cls.schematic = json.loads(
            (ROOT / "knowledge-base/xk67j-schematic-compiled.json").read_text(
                encoding="utf-8"
            )
        )

    def test_compiles_both_placement_pages_with_normalized_outlines(self):
        self.assertGreater(self.page_one["audit"]["accepted_designators"], 100)
        self.assertGreater(self.page_two["audit"]["accepted_designators"], 200)
        self.assertGreater(len(self.page_one["board_outline"]), 20)
        self.assertGreater(len(self.page_two["board_outline"]), 20)
        self.assertEqual(
            [side["side_id"] for side in self.manifest["sides"]],
            ["main_page_1", "main_page_2"],
        )

    def test_keeps_reviewed_designators_on_their_source_side(self):
        page_one = {item["designator"] for item in self.page_one["components"]}
        page_two = {item["designator"] for item in self.page_two["components"]}
        self.assertTrue({"U1001", "U4001", "U5007", "J6501"}.issubset(page_one))
        self.assertTrue(
            {
                "U2001",
                "U3001",
                "U3101",
                "U4002",
                "J6102",
                "J6402",
                "J2810",
                "X2101",
            }.issubset(page_two)
        )

    def test_schematic_recovers_all_reviewed_designators_from_28_pages(self):
        audit = self.schematic["audit"]
        self.assertEqual(self.schematic["source"]["pages"], 28)
        self.assertTrue(audit["reviewed_recovery_complete"])
        self.assertEqual(len(audit["reviewed_designators"]), 12)
        self.assertGreater(audit["linked_designators"], 100)

    def test_component_centers_share_the_cropped_texture_coordinate_plane(self):
        u2001 = next(
            item for item in self.page_two["components"] if item["designator"] == "U2001"
        )

        self.assertGreater(u2001["center"]["x"], 0.52)
        self.assertLess(u2001["center"]["x"], 0.54)
        self.assertGreater(u2001["center"]["y"], 0.53)
        self.assertLess(u2001["center"]["y"], 0.56)


if __name__ == "__main__":
    unittest.main()
