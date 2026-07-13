import unittest

from scripts.board_compiler.compiler import classify_designator, compile_designators, normalize_point


class BoardCompilerTests(unittest.TestCase):
    def test_accepts_board_designators_and_rejects_bga_grid_labels(self):
        self.assertEqual(classify_designator("U2001"), "ic")
        self.assertEqual(classify_designator("VBAT1"), "test_point")
        self.assertIsNone(classify_designator("A13"))
        self.assertIsNone(classify_designator("1"))

    def test_normalizes_pdf_coordinates_and_flips_vertical_axis(self):
        self.assertEqual(normalize_point({"x": 50, "y": 25}, [0, 0, 100, 50]), {"x": 0.5, "y": 0.5})

    def test_compilation_is_deterministic_and_deduplicated(self):
        labels = [
            {"text": "U2001", "x": 40, "y": 20},
            {"text": "C1001", "x": 10, "y": 30},
            {"text": "U2001", "x": 40, "y": 20},
            {"text": "A13", "x": 90, "y": 10},
        ]
        result = compile_designators(labels, [], [0, 0, 100, 50])
        self.assertEqual([item["designator"] for item in result], ["C1001", "U2001"])

    def test_test_point_does_not_claim_a_large_connector_rectangle(self):
        labels = [{"text": "VBUS1", "x": 500, "y": 200}]
        rectangles = [{"x": 430, "y": 190, "width": 140, "height": 20}]
        result = compile_designators(labels, rectangles, [0, 0, 1000, 500])
        self.assertNotIn("footprint", result[0])


if __name__ == "__main__":
    unittest.main()
