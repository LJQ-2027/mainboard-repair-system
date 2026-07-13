import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def connected_regions(mask, minimum_pixels=20):
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    regions = []
    for y, x in zip(*np.where(mask)):
        if seen[y, x]:
            continue
        stack = [(int(y), int(x))]
        seen[y, x] = True
        xs, ys = [], []
        while stack:
            current_y, current_x = stack.pop()
            xs.append(current_x)
            ys.append(current_y)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                next_y, next_x = current_y + dy, current_x + dx
                if 0 <= next_y < height and 0 <= next_x < width and mask[next_y, next_x] and not seen[next_y, next_x]:
                    seen[next_y, next_x] = True
                    stack.append((next_y, next_x))
        if len(xs) >= minimum_pixels:
            regions.append({
                "pixels": len(xs),
                "x": min(xs),
                "y": min(ys),
                "width": max(xs) - min(xs) + 1,
                "height": max(ys) - min(ys) + 1,
            })
    return sorted(regions, key=lambda region: region["pixels"], reverse=True)


def normalize_regions(regions, image_width, image_height):
    normalized = []
    for region in regions:
        width_ratio = region["width"] / image_width
        height_ratio = region["height"] / image_height
        area_ratio = width_ratio * height_ratio
        aspect = max(region["width"] / region["height"], region["height"] / region["width"])
        occupancy = region["pixels"] / (region["width"] * region["height"])
        if region["width"] < 4 or region["height"] < 4 or area_ratio > 0.20 or aspect > 18 or occupancy < 0.025:
            continue
        category = "shield_region" if area_ratio > 0.015 else "source_geometry"
        normalized.append({
            "geometry_id": f"PM2-GEO-{len(normalized) + 1:03d}",
            "category": category,
            "center": {
                "x": round((region["x"] + region["width"] / 2) / image_width, 6),
                "y": round((region["y"] + region["height"] / 2) / image_height, 6),
            },
            "size": {
                "x": round(width_ratio, 6),
                "y": round(height_ratio, 6),
            },
            "source_pixels": region["pixels"],
            "source": "point_map_red_engineering_layer",
            "semantic_status": "unresolved_geometry",
        })
    return normalized


def extract(image_path):
    image = np.asarray(Image.open(image_path).convert("RGB"))
    red = (image[:, :, 0] > 210) & (image[:, :, 1] < 170) & (image[:, :, 2] < 170) & ((image[:, :, 0] - image[:, :, 1]) > 70)
    regions = connected_regions(red)
    return normalize_regions(regions, image.shape[1], image.shape[0])


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "assets/board-atlas/km4-f151/main-point-map-page-2.png"
    target = root / "knowledge-base/km4-point-map-geometry.json"
    geometry = extract(source)
    payload = {
        "geometry_set_id": "KM4-F151-MAIN-PAGE2-RASTER-GEOMETRY-20260713",
        "coordinate_system": "normalized_board_plane",
        "source_image": str(source.relative_to(root)).replace("\\", "/"),
        "method": "red_engineering_layer_connected_regions",
        "limitations": "Geometry only. Designators remain unresolved unless linked by reviewed source evidence.",
        "regions": geometry,
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Extracted {len(geometry)} source geometry regions to {target.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
