import copy
import unittest
from pathlib import Path

from scripts.board_compiler.profiles import load_profile, validate_profile


ROOT = Path(__file__).resolve().parents[1]


class BoardProfileTests(unittest.TestCase):
    def test_loads_source_profiles_including_f069_and_incomplete_bg6m_package(self):
        km4 = load_profile(ROOT, "km4-f151")
        kl4 = load_profile(ROOT, "kl4-f201")
        h8918 = load_profile(ROOT, "h8918-main-v1.2")
        h6929 = load_profile(ROOT, "h6929-main-v1.1")
        f069m = load_profile(ROOT, "f069m-main-v1.0")
        f069 = load_profile(ROOT, "bg6h-f069")

        self.assertEqual(km4["board_id"], "BOARD-KM4-F151-MAIN-V1.2")
        self.assertEqual(kl4["board_id"], "BOARD-KL4-F201-MAIN-V1.2")
        self.assertEqual([side["source_pdf_page"] for side in kl4["sides"]], [1, 2])
        self.assertEqual(kl4["default_side_id"], "main_page_2")
        self.assertTrue((ROOT / kl4["point_map_source"]).is_file())
        self.assertTrue((ROOT / kl4["schematic_source"]).is_file())
        self.assertEqual(h8918["board_id"], "BOARD-H8918-MAIN-V1.2")
        self.assertEqual(h8918["models"], ["CM6", "CM5"])
        self.assertEqual([side["source_pdf_page"] for side in h8918["sides"]], [1, 2])
        self.assertTrue((ROOT / h8918["point_map_source"]).is_file())
        self.assertTrue((ROOT / h8918["schematic_source"]).is_file())
        self.assertTrue((ROOT / h8918["repair_guide_source"]).is_file())
        self.assertEqual(h6929["board_id"], "BOARD-H6929-MAIN-V1.1")
        self.assertEqual([side["source_pdf_page"] for side in h6929["sides"]], [1, 1])
        self.assertEqual([side["component_page"] for side in h6929["sides"]], [1, 2])
        self.assertNotEqual(h6929["sides"][0].get("point_map_source", h6929["point_map_source"]), h6929["sides"][1]["point_map_source"])
        self.assertEqual(f069m["board_id"], "BOARD-F069M-MAIN-V1.0")
        self.assertEqual([side["source_pdf_page"] for side in f069m["sides"]], [1, 2])
        self.assertNotIn("repair_guide_source", f069m)
        self.assertEqual(f069["board_id"], "BOARD-F069-MAIN-V1.2")
        self.assertEqual(f069["model"], "BG6H")
        self.assertEqual(f069["models"], ["BG6H", "BG6h"])
        self.assertEqual([side["source_pdf_page"] for side in f069["sides"]], [1, 2])
        self.assertTrue((ROOT / f069["point_map_source"]).is_file())
        self.assertTrue((ROOT / f069["schematic_source"]).is_file())
        self.assertTrue((ROOT / f069["repair_guide_source"]).is_file())
        self.assertNotEqual(f069["board_id"], f069m["board_id"])

    def test_rejects_an_unknown_profile(self):
        with self.assertRaisesRegex(ValueError, "Unknown board profile"):
            load_profile(ROOT, "missing-board")

    def test_loads_xk67j_with_evidence_tiered_sales_model_aliases(self):
        profile = load_profile(ROOT, "xk67j-main-v1.0b")

        self.assertEqual(profile["board_id"], "BOARD-XK67J-MAIN-V1.0B")
        self.assertEqual(
            profile["models"],
            ["KM4n", "KM4k", "KM5", "KM5n", "KM5s"],
        )
        self.assertEqual(
            profile["model_evidence"],
            {
                "KM4n": "photo_verified_shared_platform",
                "KM4k": "owner_confirmed_alias",
                "KM5": "engineering_source",
                "KM5n": "owner_confirmed_alias",
                "KM5s": "owner_confirmed_alias",
            },
        )
        self.assertEqual([side["source_pdf_page"] for side in profile["sides"]], [1, 2])
        self.assertTrue((ROOT / profile["point_map_source"]).is_file())
        self.assertTrue((ROOT / profile["schematic_source"]).is_file())

    def test_rejects_model_evidence_that_does_not_cover_every_alias(self):
        profile = copy.deepcopy(load_profile(ROOT, "xk67j-main-v1.0b"))
        del profile["model_evidence"]["KM5s"]

        with self.assertRaisesRegex(ValueError, "model_evidence"):
            validate_profile(ROOT, profile)

    def test_rejects_duplicate_side_identities(self):
        profile = copy.deepcopy(load_profile(ROOT, "kl4-f201"))
        profile["sides"][1]["side_id"] = profile["sides"][0]["side_id"]

        with self.assertRaisesRegex(ValueError, "duplicate side_id"):
            validate_profile(ROOT, profile)

    def test_rejects_invalid_normalized_crop(self):
        profile = copy.deepcopy(load_profile(ROOT, "kl4-f201"))
        profile["sides"][0]["source_crop"]["width"] = 2

        with self.assertRaisesRegex(ValueError, "source_crop"):
            validate_profile(ROOT, profile)

    def test_rejects_default_side_outside_profile(self):
        profile = copy.deepcopy(load_profile(ROOT, "kl4-f201"))
        profile["default_side_id"] = "missing_side"

        with self.assertRaisesRegex(ValueError, "default_side_id"):
            validate_profile(ROOT, profile)

    def test_rejects_schematic_geometry_side_outside_profile(self):
        profile = copy.deepcopy(load_profile(ROOT, "kl4-f201"))
        profile["schematic_geometry_side_id"] = "missing_side"

        with self.assertRaisesRegex(ValueError, "schematic_geometry_side_id"):
            validate_profile(ROOT, profile)

    def test_rejects_outputs_outside_repository(self):
        profile = copy.deepcopy(load_profile(ROOT, "kl4-f201"))
        profile["sides"][0]["compiled_data"] = "../outside.json"

        with self.assertRaisesRegex(ValueError, "inside the repository"):
            validate_profile(ROOT, profile)

    def test_accepts_same_page_number_from_distinct_side_sources(self):
        profile = copy.deepcopy(load_profile(ROOT, "kl4-f201"))
        profile["sides"][1]["point_map_source"] = profile["schematic_source"]
        profile["sides"][1]["source_pdf_page"] = 1
        profile["sides"][1]["component_page"] = 2

        validated = validate_profile(ROOT, profile)

        self.assertEqual(validated["sides"][1]["component_page"], 2)

    def test_rejects_duplicate_page_from_the_same_effective_source(self):
        profile = copy.deepcopy(load_profile(ROOT, "kl4-f201"))
        profile["sides"][1]["source_pdf_page"] = 1
        profile["sides"][1]["component_page"] = 2

        with self.assertRaisesRegex(ValueError, "duplicate point-map source page"):
            validate_profile(ROOT, profile)


if __name__ == "__main__":
    unittest.main()
