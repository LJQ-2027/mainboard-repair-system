import unittest
from pathlib import Path

from scripts.board_compiler.pdf_primitives import (
    decode_cid_text,
    extract_form_primitives,
    multiply_matrix,
    parse_to_unicode,
    transform_rectangle,
)


ROOT = Path(__file__).resolve().parents[1]


class PdfPrimitiveTests(unittest.TestCase):
    def test_parses_bfchar_cmap_and_decodes_two_byte_cids(self):
        cmap = b"2 beginbfchar\n<0014><0031>\n<0024><0041>\nendbfchar"
        mapping = parse_to_unicode(cmap)
        self.assertEqual(decode_cid_text(bytes.fromhex("00240014"), mapping), "A1")

    def test_matrix_multiplication_keeps_translation(self):
        result = multiply_matrix([1, 0, 0, 1, 10, 20], [2, 0, 0, 3, 5, 7])
        self.assertEqual(result, [2, 0, 0, 3, 15, 27])

    def test_rectangle_is_transformed_to_source_bounds(self):
        bounds = transform_rectangle([2, 0, 0, 3, 10, 20], [1, 2, 4, 5])
        self.assertEqual(bounds, {"x": 12, "y": 26, "width": 8, "height": 15})

    def test_extracts_direct_page_content_without_a_form_xobject(self):
        package = ROOT / "source-materials/manufacturing-center/top20-model-board-assets/2026-07-02-inhouse-top20/packages/CM6-H8918"
        source = next(package.glob("H8918_MAIN_PCB_V1.2*.pdf"))

        primitives = extract_form_primitives(source, 2)
        labels = {item["text"] for item in primitives["labels"]}

        self.assertEqual(primitives["form_name"], "/PageContents")
        self.assertIn("U2001", labels)
        self.assertIn("X2101", labels)
        self.assertGreater(len(primitives["rectangles"]), 5000)

    def test_falls_back_to_standard_pdf_text_for_xk67j_page_content(self):
        source = (
            ROOT
            / "source-materials/owner-supplied/2026-07-31-km5-xk67j/packages"
            / "KM5-KM4N-XK67J-SHARED/XK67J_KM5_MAIN_PCB_V1.0B_PLACEMENT.pdf"
        )

        page_one = extract_form_primitives(source, 1)
        page_two = extract_form_primitives(source, 2)

        self.assertEqual(page_one["label_method"], "pypdf_visitor_fallback")
        self.assertEqual(page_two["label_method"], "pypdf_visitor_fallback")
        self.assertTrue(
            {"U1001", "U4001", "U5007", "J6501"}.issubset(
                {item["text"] for item in page_one["labels"]}
            )
        )
        self.assertTrue(
            {"U2001", "U3001", "U3101", "U4002", "J6402", "X2101"}.issubset(
                {item["text"] for item in page_two["labels"]}
            )
        )

    def test_rotated_xk67j_page_uses_display_coordinates(self):
        source = (
            ROOT
            / "source-materials/owner-supplied/2026-07-31-km5-xk67j/packages"
            / "KM5-KM4N-XK67J-SHARED/XK67J_KM5_MAIN_PCB_V1.0B_PLACEMENT.pdf"
        )

        primitives = extract_form_primitives(source, 2)
        u2001 = next(item for item in primitives["labels"] if item["text"] == "U2001")

        self.assertEqual(primitives["bounds"], [0.0, 0.0, 842.0, 595.22])
        self.assertAlmostEqual(u2001["x"], 492.16, places=2)
        self.assertAlmostEqual(u2001["y"], 287.69, places=2)


if __name__ == "__main__":
    unittest.main()
