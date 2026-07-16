import unittest
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from scripts.board_compiler.outline import extract_board_outline, largest_component, mask_outer_polygon, simplify_polygon


class BoardOutlineTests(unittest.TestCase):
    def test_largest_component_ignores_detached_noise(self):
        mask = np.zeros((12, 16), dtype=bool)
        mask[2:10, 3:13] = True
        mask[0, 0] = True
        result = largest_component(mask)
        self.assertEqual(int(result.sum()), 80)
        self.assertFalse(result[0, 0])

    def test_outer_polygon_preserves_a_rectangular_notch(self):
        mask = np.zeros((12, 16), dtype=bool)
        mask[2:10, 2:14] = True
        mask[2:6, 6:10] = False
        polygon = mask_outer_polygon(mask)
        self.assertGreater(len(polygon), 8)
        self.assertIn((6, 6), polygon)
        self.assertIn((10, 6), polygon)

    def test_polygon_simplification_removes_collinear_points(self):
        polygon = [(0, 0), (1, 0), (2, 0), (3, 0), (3, 3), (0, 3), (0, 0)]
        simplified = simplify_polygon(polygon, tolerance=0.1)
        self.assertLess(len(simplified), len(polygon))
        self.assertIn((3, 3), simplified)

    def test_alpha_silhouette_uses_transparency_instead_of_internal_marks(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "board.png"
            image = Image.new("RGBA", (100, 80), (255, 255, 255, 0))
            draw = ImageDraw.Draw(image)
            draw.polygon([(10, 10), (90, 10), (90, 70), (60, 70), (60, 50), (40, 50), (40, 70), (10, 70)], fill=(255, 255, 255, 255))
            draw.rectangle((45, 20, 55, 30), fill=(0, 0, 0, 255))
            image.save(path)

            result = extract_board_outline(path, method="alpha_silhouette", closing_radius=0, tolerance=0.5)

            self.assertGreater(result["mask_area_ratio"], 0.5)
            self.assertLess(result["mask_area_ratio"], 0.6)
            self.assertTrue(any(point["y"] > 0.6 for point in result["outline"]))


if __name__ == "__main__":
    unittest.main()
