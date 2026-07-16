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


if __name__ == "__main__":
    unittest.main()
