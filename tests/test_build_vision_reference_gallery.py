import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_vision_reference_gallery import (  # noqa: E402
    apply_review_annotations,
    board_version_label,
    classify_board_versions,
    infer_board_side,
    is_reference_image_candidate,
    score_candidate_page,
    select_manual_records,
    generate_gallery_html,
    reset_output_root,
)


class VisionReferenceGalleryTests(unittest.TestCase):
    def test_mainboard_page_scores_above_generic_disassembly_page(self):
        board_score = score_candidate_page(
            "Remove the mainboard PCBA and disconnect the motherboard FPC."
        )
        generic_score = score_candidate_page(
            "Disassemble the battery cover and remove the side key."
        )
        self.assertGreater(board_score, generic_score)
        self.assertGreaterEqual(board_score, 8)

    def test_board_side_requires_explicit_evidence(self):
        self.assertEqual(infer_board_side("Mainboard top side reference"), "top")
        self.assertEqual(infer_board_side("Bottom side of the PCBA"), "bottom")
        self.assertEqual(infer_board_side("Top and bottom side of motherboard"), "both")
        self.assertEqual(infer_board_side("Remove the motherboard"), "unknown")

    def test_image_candidate_rejects_small_or_extreme_assets(self):
        self.assertTrue(is_reference_image_candidate(1087, 663, 72000))
        self.assertFalse(is_reference_image_candidate(240, 180, 40000))
        self.assertFalse(is_reference_image_candidate(2400, 120, 80000))
        self.assertFalse(is_reference_image_candidate(900, 600, 5000))

    def test_manual_selection_prefers_unique_pdf_records(self):
        records = [
            {"models": ["KM4"], "extension": ".pdf", "stored_path": "a.pdf"},
            {"models": ["KM4"], "extension": ".pdf", "stored_path": "a.pdf"},
            {"models": ["KM4"], "extension": ".docx", "stored_path": "a.docx"},
            {"models": ["KL4"], "extension": ".pdf", "stored_path": "b.pdf"},
        ]
        selected = select_manual_records(records, ["KM4", "KL4"])
        self.assertEqual([item["stored_path"] for item in selected["KM4"]], ["a.pdf"])
        self.assertEqual([item["stored_path"] for item in selected["KL4"]], ["b.pdf"])

    def test_board_versions_are_split_into_main_and_sub(self):
        result = classify_board_versions(
            ["F151_MAIN_PCB_V1.2", "F151_SUB_PCB_1_V1.1", "UNKNOWN"]
        )
        self.assertEqual(result["main"], ["F151_MAIN_PCB_V1.2"])
        self.assertEqual(result["sub"], ["F151_SUB_PCB_1_V1.1"])
        self.assertEqual(result["other"], ["UNKNOWN"])

    def test_review_annotations_promote_only_selected_assets(self):
        model = {
            "model": "KM4",
            "candidate_pages": [
                {
                    "embedded_images": [
                        {"asset_path": "a.jpg", "review_status": "pending"},
                        {"asset_path": "b.jpg", "review_status": "pending"},
                    ]
                }
            ],
        }
        review = {
            "coverage": {"main_board_top": "missing"},
            "assets": {
                "a.jpg": {
                    "review_status": "approved",
                    "reference_role": "installed_mainboard",
                    "board_side": "unknown",
                }
            },
        }
        apply_review_annotations(model, review)
        assets = model["candidate_pages"][0]["embedded_images"]
        self.assertEqual(assets[0]["review_status"], "approved")
        self.assertEqual(assets[1]["review_status"], "not_selected")
        self.assertEqual(model["coverage"]["main_board_top"], "missing")

    def test_gallery_html_uses_embedded_favicon_to_avoid_404(self):
        manifest = {
            "statistics": {"embedded_image_count": 1, "approved_image_count": 1},
            "models": [
                {
                    "model": "KM4",
                    "board_versions": {"main": ["F151_MAIN_PCB_V1.2"], "sub": [], "other": []},
                    "candidate_pages": [
                        {
                            "page_number": 3,
                            "embedded_images": [
                                {
                                    "asset_path": "assets/a.jpg",
                                    "review_status": "approved",
                                    "width": 800,
                                    "height": 600,
                                    "board_side": "unknown",
                                    "reference_role": "candidate",
                                    "board_scope": "main",
                                },
                                {
                                    "asset_path": "assets/b.jpg",
                                    "review_status": "approved",
                                    "width": 800,
                                    "height": 600,
                                    "board_side": "unknown",
                                    "reference_role": "candidate",
                                    "board_scope": "main",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.html"
            generate_gallery_html(manifest, output)
            document = output.read_text(encoding="utf-8")
        self.assertIn('rel="icon" href="data:,"', document)
        self.assertFalse(any(line.endswith((" ", "\t")) for line in document.splitlines()))

    def test_board_version_label_follows_asset_scope(self):
        model = {
            "board_versions": {
                "main": ["F151_MAIN_PCB_V1.2"],
                "sub": ["F151_SUB_PCB_1_V1.1"],
                "other": [],
            }
        }
        self.assertEqual(
            board_version_label(model, {"board_scope": "main"}),
            "F151_MAIN_PCB_V1.2",
        )
        self.assertEqual(
            board_version_label(model, {"board_scope": "sub"}),
            "F151_SUB_PCB_1_V1.1",
        )
        self.assertIn("F151_SUB_PCB_1_V1.1", board_version_label(model, {"board_scope": "mixed_phone_components"}))

    def test_output_reset_removes_only_owned_gallery_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            output_root = project_root / "assets" / "vision-reference-gallery"
            output_root.mkdir(parents=True)
            (output_root / "stale.jpg").write_bytes(b"stale")
            reset_output_root(output_root, project_root)
            self.assertTrue(output_root.is_dir())
            self.assertFalse((output_root / "stale.jpg").exists())
            with self.assertRaises(ValueError):
                reset_output_root(project_root, project_root)


if __name__ == "__main__":
    unittest.main()
