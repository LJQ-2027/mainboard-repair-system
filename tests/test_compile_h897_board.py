import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CompiledH897BoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_one = json.loads(
            (ROOT / "knowledge-base/h897-board-compiled-page-1.json").read_text(
                encoding="utf-8"
            )
        )
        cls.page_two = json.loads(
            (ROOT / "knowledge-base/h897-board-compiled-page-2.json").read_text(
                encoding="utf-8"
            )
        )
        cls.manifest = json.loads(
            (ROOT / "knowledge-base/h897-board-sides.json").read_text(encoding="utf-8")
        )
        cls.schematic = json.loads(
            (ROOT / "knowledge-base/h897-schematic-compiled.json").read_text(
                encoding="utf-8"
            )
        )

    def test_compiles_both_placement_pages_with_normalized_outlines(self):
        self.assertGreater(self.page_one["audit"]["accepted_designators"], 200)
        self.assertGreater(self.page_two["audit"]["accepted_designators"], 300)
        self.assertGreater(len(self.page_one["board_outline"]), 20)
        self.assertGreater(len(self.page_two["board_outline"]), 20)
        self.assertEqual(
            [side["side_id"] for side in self.manifest["sides"]],
            ["main_page_1", "main_page_2"],
        )

    def test_keeps_reviewed_designators_on_their_source_side(self):
        page_one = {item["designator"] for item in self.page_one["components"]}
        page_two = {item["designator"] for item in self.page_two["components"]}

        self.assertTrue(
            {"U3101", "U6000", "U6601", "J6210", "J6202", "U1001", "U4101"}.issubset(
                page_one
            )
        )
        self.assertTrue(
            {"U5003", "J6204", "U2001", "X2101", "U3001", "U3201", "U4102", "J6101"}.issubset(
                page_two
            )
        )

    def test_schematic_recovers_reviewed_designators_from_28_pages(self):
        audit = self.schematic["audit"]

        self.assertEqual(self.schematic["source"]["pages"], 28)
        self.assertTrue(audit["reviewed_recovery_complete"])
        self.assertEqual(len(audit["reviewed_designators"]), 15)
        self.assertGreater(audit["linked_designators"], 100)

    def test_compiled_identity_is_exact_h897_v12(self):
        for payload in (self.page_one, self.page_two, self.schematic):
            self.assertEqual(payload["board_id"], "BOARD-H897-MAIN-V1.2")


if __name__ == "__main__":
    unittest.main()
