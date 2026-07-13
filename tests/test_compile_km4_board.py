import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CompiledKm4BoardTests(unittest.TestCase):
    def test_compiled_dataset_recovers_reviewed_entities(self):
        data = json.loads((ROOT / "knowledge-base/km4-board-compiled.json").read_text(encoding="utf-8"))
        self.assertTrue(data["audit"]["required_recovery_complete"])
        self.assertGreaterEqual(data["audit"]["accepted_designators"], 800)
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
