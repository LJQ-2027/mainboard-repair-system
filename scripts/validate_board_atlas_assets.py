from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ATLAS_JSON = ROOT / "knowledge-base" / "board-atlas-mvp.json"


def map_to_crop(value: float, start: float, end: float) -> float:
    return (value - start) / (end - start)


def main() -> None:
    atlas = json.loads(ATLAS_JSON.read_text(encoding="utf-8"))
    board = atlas["boards"][0]
    sides = {side["side_id"]: side for side in board["sides"]}

    for side in sides.values():
        crop = side.get("source_crop")
        if not crop or set(crop) != {"x", "y", "width", "height"}:
            raise AssertionError(f"Missing source_crop metadata for {side['side_id']}")

        image_path = ROOT / side["image"]
        image = Image.open(image_path)
        if image.mode != "RGBA":
            raise AssertionError(f"Atlas asset must preserve board silhouette alpha: {image_path}")

        alpha = image.getchannel("A")
        if alpha.getextrema() != (0, 255):
            raise AssertionError(f"Atlas asset must contain transparent and opaque pixels: {image_path}")

        alpha_box = alpha.getbbox()
        if alpha_box is None:
            raise AssertionError(f"Atlas asset is blank: {image_path}")
        visible_width = (alpha_box[2] - alpha_box[0]) / image.width
        visible_height = (alpha_box[3] - alpha_box[1]) / image.height
        if visible_width < 0.9 or visible_height < 0.85:
            raise AssertionError(f"Board does not fill atlas asset: {image_path}")

    expected_module_sides = {
        "cpu_baseband": "main_page_1",
        "memory_ddr": "main_page_1",
        "memory_emmc": "main_page_2",
        "power_pmu": "main_page_2",
        "charging_usb": "main_page_1",
        "usb_power_connector": "main_page_2",
    }
    module_by_id = {module["module_id"]: module for module in board["modules"]}
    for module_id, side_id in expected_module_sides.items():
        module = module_by_id.get(module_id)
        if not module:
            raise AssertionError(f"Missing source-based module: {module_id}")
        if module["side_id"] != side_id:
            raise AssertionError(f"Module {module_id} must be on {side_id}")
        if not module.get("designators"):
            raise AssertionError(f"Module {module_id} must name its source designators")

    for module in board["modules"]:
        crop = sides[module["side_id"]]["source_crop"]
        x_end = crop["x"] + crop["width"]
        y_end = crop["y"] + crop["height"]
        regions = module.get("regions") or [module["polygon"]]
        for region in regions:
            for x, y in region:
                mapped_x = map_to_crop(x, crop["x"], x_end)
                mapped_y = map_to_crop(y, crop["y"], y_end)
                if not (0 <= mapped_x <= 1 and 0 <= mapped_y <= 1):
                    raise AssertionError(
                        f"Module {module['module_id']} falls outside cropped source image"
                    )

    for point in board["test_points"]:
        crop = sides[point["side_id"]]["source_crop"]
        mapped_x = map_to_crop(point["x"], crop["x"], crop["x"] + crop["width"])
        mapped_y = map_to_crop(point["y"], crop["y"], crop["y"] + crop["height"])
        if not (0 <= mapped_x <= 1 and 0 <= mapped_y <= 1):
            raise AssertionError(f"Test point {point['point_id']} falls outside cropped source image")

    expected_points = {
        "tp_basic_vbat": ("main_page_2", 0.70758, 0.84525),
        "tp_basic_vbus": ("main_page_2", 0.69321, 0.82425),
    }
    point_by_id = {point["point_id"]: point for point in board["test_points"]}
    for point_id, (side_id, x, y) in expected_points.items():
        point = point_by_id.get(point_id)
        if not point:
            raise AssertionError(f"Missing source-based test point: {point_id}")
        if point["side_id"] != side_id or abs(point["x"] - x) > 0.0001 or abs(point["y"] - y) > 0.0001:
            raise AssertionError(f"Test point {point_id} does not match the point-map label position")

    print("Board atlas assets and crop coordinates are valid.")


if __name__ == "__main__":
    main()
