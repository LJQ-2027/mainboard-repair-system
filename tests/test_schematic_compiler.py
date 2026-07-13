import unittest
import json
from pathlib import Path

from scripts.board_compiler.schematic import coalesce_text_fragments, index_component_pages


class SchematicCompilerTests(unittest.TestCase):
    def test_coalesces_adjacent_characters_on_the_same_baseline(self):
        fragments = [
            {"text": "U", "x": 100, "y": 200, "font_size": 10},
            {"text": "2", "x": 106, "y": 200.2, "font_size": 10},
            {"text": "0", "x": 112, "y": 200, "font_size": 10},
            {"text": "0", "x": 118, "y": 200, "font_size": 10},
            {"text": "1", "x": 124, "y": 200, "font_size": 10},
        ]
        runs = coalesce_text_fragments(fragments)
        self.assertEqual(runs, [{"text": "U2001", "x": 100, "y": 200.04, "font_size": 10.0}])

    def test_keeps_distant_labels_separate(self):
        fragments = [
            {"text": "U2001", "x": 100, "y": 200, "font_size": 10},
            {"text": "VDDCORE", "x": 220, "y": 200, "font_size": 10},
        ]
        runs = coalesce_text_fragments(fragments)
        self.assertEqual([run["text"] for run in runs], ["U2001", "VDDCORE"])

    def test_indexes_exact_component_designators_by_page(self):
        pages = {
            6: [{"text": "U2001", "x": 100, "y": 200, "font_size": 10}],
            7: [{"text": "X2100", "x": 300, "y": 400, "font_size": 10}],
        }
        result = index_component_pages(pages, {"U2001", "X2100", "U4000"})
        self.assertEqual(result["U2001"][0]["page"], 6)
        self.assertEqual(result["X2100"][0]["page"], 7)
        self.assertEqual(result["U4000"], [])

    def test_ignores_designators_embedded_in_notes_or_merged_runs(self):
        pages = {
            8: [
                {"text": "place R2715/R2725 close to IC", "x": 100, "y": 200, "font_size": 10},
                {"text": "C1026C1027", "x": 100, "y": 180, "font_size": 10},
            ],
        }
        result = index_component_pages(pages, {"R2715", "R2725", "C1026", "C1027"})
        self.assertTrue(all(not occurrences for occurrences in result.values()))

    def test_compiled_km4_schematic_recovers_reviewed_entities(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "knowledge-base/km4-schematic-compiled.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(data["audit"]["linked_designators"], 650)
        self.assertEqual(data["audit"]["reviewed_recovery_complete"], True)
        expected_pages = {
            "U2001": [6, 7], "X2100": [7], "VBAT1": [9], "U0600": [10],
            "U4000": [13], "J6101": [16], "VBUS1": [16],
        }
        for designator, pages in expected_pages.items():
            self.assertEqual([item["page"] for item in data["components"][designator]], pages)
        self.assertTrue(data["audit"]["quality_gate_complete"])
        for occurrences in data["components"].values():
            for occurrence in occurrences:
                self.assertLessEqual(0, occurrence["text_origin"]["x"])
                self.assertLessEqual(occurrence["text_origin"]["x"], 1)
                self.assertLessEqual(0, occurrence["text_origin"]["y"])
                self.assertLessEqual(occurrence["text_origin"]["y"], 1)


if __name__ == "__main__":
    unittest.main()
