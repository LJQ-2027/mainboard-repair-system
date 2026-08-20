import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CompiledF069BoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_one = json.loads(
            (ROOT / "knowledge-base/f069-board-compiled-page-1.json").read_text(encoding="utf-8")
        )
        cls.page_two = json.loads(
            (ROOT / "knowledge-base/f069-board-compiled-page-2.json").read_text(encoding="utf-8")
        )
        cls.manifest = json.loads(
            (ROOT / "knowledge-base/f069-board-sides.json").read_text(encoding="utf-8")
        )
        cls.schematic = json.loads(
            (ROOT / "knowledge-base/f069-schematic-compiled.json").read_text(encoding="utf-8")
        )

    def test_compiles_both_f069_v12_point_map_pages(self):
        self.assertEqual(self.page_one["board_id"], "BOARD-F069-MAIN-V1.2")
        self.assertEqual(self.page_two["board_id"], "BOARD-F069-MAIN-V1.2")
        self.assertGreater(self.page_one["audit"]["accepted_designators"], 350)
        self.assertGreater(self.page_two["audit"]["accepted_designators"], 700)
        self.assertEqual(
            [side["side_id"] for side in self.manifest["sides"]],
            ["main_page_1", "main_page_2"],
        )

    def test_reviewed_designators_remain_on_their_source_side(self):
        page_one = {item["designator"] for item in self.page_one["components"]}
        page_two = {item["designator"] for item in self.page_two["components"]}
        self.assertTrue(
            {"U1001", "U4001", "U5002", "J6202", "J6250"}.issubset(page_one)
        )
        self.assertTrue(
            {"U2001", "U4000", "U0600", "J6101", "X2100", "VBAT1", "VBUS1"}.issubset(page_two)
        )

    def test_schematic_recovers_the_declared_exact_identities(self):
        self.assertTrue(self.schematic["audit"]["reviewed_recovery_complete"])
        self.assertNotIn("VBAT1", self.schematic["audit"]["reviewed_designators"])
        self.assertEqual(
            set(self.schematic["audit"]["reviewed_designators"]),
            {
                "U1001",
                "U2001",
                "U4000",
                "U4001",
                "U5002",
                "U0600",
                "J6101",
                "J6202",
                "J6250",
                "X2100",
                "VBUS1",
            },
        )

    def test_outline_and_footprints_preserve_source_boundaries(self):
        self.assertGreater(len(self.page_one["board_outline"]), 20)
        self.assertGreater(len(self.page_two["board_outline"]), 20)
        u1001 = next(item for item in self.page_one["components"] if item["designator"] == "U1001")
        vbus1 = next(item for item in self.page_two["components"] if item["designator"] == "VBUS1")
        self.assertEqual(u1001["footprint"]["confidence"], "low")
        self.assertEqual(vbus1["footprint"]["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
