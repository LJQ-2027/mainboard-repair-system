import json
import unittest
from pathlib import Path

from scripts.compile_km4_board import SIDE_CONFIGS, build_side_manifest


ROOT = Path(__file__).resolve().parents[1]


class CompiledKm4BoardTests(unittest.TestCase):
    def test_side_configs_keep_each_pdf_page_and_texture_explicit(self):
        self.assertEqual(set(SIDE_CONFIGS), {"main_page_1", "main_page_2"})
        self.assertEqual(SIDE_CONFIGS["main_page_1"]["page"], 1)
        self.assertEqual(SIDE_CONFIGS["main_page_2"]["page"], 2)
        self.assertNotEqual(SIDE_CONFIGS["main_page_1"]["image"], SIDE_CONFIGS["main_page_2"]["image"])

    def test_side_manifest_uses_reviewed_source_labels(self):
        manifest = build_side_manifest(ROOT)
        self.assertEqual(manifest["default_side_id"], "main_page_2")
        self.assertEqual([side["label"] for side in manifest["sides"]], ["第1面", "第2面"])
        self.assertEqual([side["side_id"] for side in manifest["sides"]], ["main_page_1", "main_page_2"])

    def test_page_one_output_is_compiled_from_its_own_source(self):
        data = json.loads((ROOT / "knowledge-base/km4-board-compiled-page-1.json").read_text(encoding="utf-8"))
        self.assertEqual(data["side_id"], "main_page_1")
        self.assertEqual(data["source"]["page"], 1)
        self.assertTrue(data["board_outline_source"]["image"].endswith("main-point-map-page-1.png"))
        self.assertGreater(data["audit"]["accepted_designators"], 0)
        self.assertGreater(data["audit"]["outline_points"], 20)
        self.assertEqual(len(data["components"]), data["audit"]["accepted_designators"])

    def test_compiled_dataset_recovers_reviewed_entities(self):
        data = json.loads((ROOT / "knowledge-base/km4-board-compiled.json").read_text(encoding="utf-8"))
        self.assertTrue(data["audit"]["required_recovery_complete"])
        self.assertGreaterEqual(data["audit"]["accepted_designators"], 800)
        self.assertGreater(data["audit"]["outline_points"], 20)
        self.assertGreaterEqual(data["audit"]["footprint_confidence"]["high"], 100)
        self.assertLess(data["audit"]["footprint_confidence"]["low"], 50)
        self.assertEqual(len(data["components"]), data["audit"]["accepted_designators"])

    def test_components_use_normalized_coordinates_and_source_evidence(self):
        data = json.loads((ROOT / "knowledge-base/km4-board-compiled.json").read_text(encoding="utf-8"))
        for component in data["components"]:
            self.assertLessEqual(0, component["center"]["x"])
            self.assertLessEqual(component["center"]["x"], 1)
            self.assertLessEqual(0, component["center"]["y"])
            self.assertLessEqual(component["center"]["y"], 1)
            self.assertEqual(component["source_status"], "decoded_pdf_text")


if __name__ == "__main__":
    unittest.main()
