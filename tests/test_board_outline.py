import unittest

import numpy as np

from scripts.board_compiler.outline import largest_component, mask_outer_polygon, simplify_polygon


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


if __name__ == "__main__":
    unittest.main()
