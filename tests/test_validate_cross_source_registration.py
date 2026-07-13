import json
import unittest
from pathlib import Path

from scripts.validate_cross_source_registration import validate_dataset


ROOT = Path(__file__).resolve().parents[1]


class CrossSourceRegistrationTests(unittest.TestCase):
    def test_committed_dataset_is_valid(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_dataset(data, ROOT), [])

    def test_rejects_out_of_range_geometry(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        data["entities"][0]["geometry"]["center"]["x"] = 1.2
        self.assertTrue(any("normalized" in error for error in validate_dataset(data, ROOT)))

    def test_rejects_missing_source_links(self):
        data = json.loads((ROOT / "knowledge-base/km4-cross-source-registration.json").read_text(encoding="utf-8"))
        data["entities"][0]["schematic_links"] = []
        data["entities"][0]["repair_links"] = []
        self.assertTrue(any("source link" in error for error in validate_dataset(data, ROOT)))


if __name__ == "__main__":
    unittest.main()
