import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class CompiledH6929BoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.top = read_json("knowledge-base/h6929-board-compiled-top.json")
        cls.bot = read_json("knowledge-base/h6929-board-compiled-bot.json")
        cls.manifest = read_json("knowledge-base/h6929-board-sides.json")
        cls.schematic = read_json("knowledge-base/h6929-schematic-compiled.json")

    def test_compiles_two_independent_page_one_sources(self):
        self.assertEqual(self.top["source"]["page"], 1)
        self.assertEqual(self.bot["source"]["page"], 1)
        self.assertNotEqual(self.top["source"]["path"], self.bot["source"]["path"])
        self.assertGreaterEqual(self.top["audit"]["accepted_designators"], 570)
        self.assertGreaterEqual(self.bot["audit"]["accepted_designators"], 600)

    def test_logical_component_pages_remain_unique(self):
        top_u1001 = next(item for item in self.top["components"] if item["designator"] == "U1001")
        bot_u2001 = next(item for item in self.bot["components"] if item["designator"] == "U2001")
        self.assertEqual(top_u1001["component_id"], "H6929-MAIN-P1-U1001")
        self.assertEqual(bot_u2001["component_id"], "H6929-MAIN-P2-U2001")

    def test_reviewed_identities_remain_on_source_named_sides(self):
        top_ids = {item["designator"] for item in self.top["components"]}
        bot_ids = {item["designator"] for item in self.bot["components"]}
        self.assertTrue({"U1001", "U2304", "U2305"}.issubset(top_ids))
        self.assertTrue({"U2001", "X2101", "J2101", "U5003", "J6101", "U2404", "VBAT1"}.issubset(bot_ids))
        self.assertEqual([item["label"] for item in self.manifest["sides"]], ["TOP 面", "BOT 面"])

    def test_schematic_recovers_the_explicit_exact_subset(self):
        expected = {"U1001", "U2001", "X2101", "U2304", "U2305", "J2101", "U5003", "J6101", "U2404"}
        self.assertEqual(set(self.schematic["audit"]["reviewed_designators"]), expected)
        self.assertTrue(self.schematic["audit"]["reviewed_recovery_complete"])
        self.assertEqual(sorted({item["page"] for item in self.schematic["components"]["U2304"]}), [9])
        self.assertEqual(sorted({item["page"] for item in self.schematic["components"]["J6101"]}), [19])

    def test_outline_is_normalized_and_nontrivial(self):
        for payload in (self.top, self.bot):
            outline = payload["board_outline"]
            self.assertGreater(len(outline), 80)
            self.assertTrue(all(0 <= point["x"] <= 1 and 0 <= point["y"] <= 1 for point in outline))
            self.assertGreater(payload["audit"]["outline_mask_area_ratio"], 0.78)


if __name__ == "__main__":
    unittest.main()
