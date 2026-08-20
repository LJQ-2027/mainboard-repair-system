import copy
import json
import unittest
from pathlib import Path

from scripts.board_compiler.profiles import load_profile
from scripts.validate_repair_board_dataset import validate_dataset_package, validate_dataset_path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "knowledge-base/kl4-cross-source-registration.json"
H8918_DATASET_PATH = ROOT / "knowledge-base/h8918-cross-source-registration.json"


class RepairBoardDatasetValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.profile = load_profile(ROOT, "kl4-f201")

    def test_validates_compiled_kl4_package(self):
        self.assertEqual(validate_dataset_path(DATASET_PATH, ROOT), [])

    def test_allows_point_map_entities_without_claimed_schematic_links(self):
        self.assertEqual(validate_dataset_path(H8918_DATASET_PATH, ROOT), [])

    def test_rejects_board_identity_drift(self):
        data = copy.deepcopy(self.data)
        data["board_id"] = "BOARD-WRONG"
        errors = validate_dataset_package(data, ROOT, self.profile)
        self.assertIn("dataset board_id does not match board profile", errors)

    def test_rejects_entity_on_wrong_source_side(self):
        data = copy.deepcopy(self.data)
        entity = next(item for item in data["entities"] if item["designator"] == "U1001")
        entity["side_id"] = "main_page_2"
        errors = validate_dataset_package(data, ROOT, self.profile)
        self.assertIn("KL4-MAIN-U1001 does not resolve in declared-side geometry", errors)


if __name__ == "__main__":
    unittest.main()
