import unittest

import numpy as np

from scripts.extract_point_map_geometry import connected_regions, normalize_regions


class PointMapGeometryTests(unittest.TestCase):
    def test_connected_regions_returns_separate_shapes(self):
        mask = np.zeros((20, 30), dtype=bool)
        mask[2:7, 3:10] = True
        mask[10:18, 18:27] = True
        regions = connected_regions(mask, minimum_pixels=4)
        self.assertEqual([(r["x"], r["y"], r["width"], r["height"]) for r in regions], [(18, 10, 9, 8), (3, 2, 7, 5)])

    def test_normalized_regions_filters_lines_and_full_board_clusters(self):
        regions = [
            {"pixels": 80, "x": 10, "y": 10, "width": 20, "height": 10},
            {"pixels": 100, "x": 0, "y": 40, "width": 100, "height": 1},
            {"pixels": 5000, "x": 0, "y": 0, "width": 100, "height": 100},
        ]
        result = normalize_regions(regions, image_width=100, image_height=100)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["center"], {"x": 0.2, "y": 0.15})


if __name__ == "__main__":
    unittest.main()
