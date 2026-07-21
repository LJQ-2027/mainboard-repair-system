import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_visual_qc_dataset import DEFECT_CATEGORIES, validate_visual_qc_case


def _pixel_points(geometry, width, height):
    return [
        (round(point["x"] * width, 6), round(point["y"] * height, 6))
        for point in geometry["points"]
    ]


def _coco_geometry(geometry, width, height):
    points = _pixel_points(geometry, width, height)
    if geometry["type"] == "rectangle":
        left, right = sorted((points[0][0], points[1][0]))
        top, bottom = sorted((points[0][1], points[1][1]))
        polygon = [left, top, right, top, right, bottom, left, bottom]
    else:
        left = min(point[0] for point in points)
        right = max(point[0] for point in points)
        top = min(point[1] for point in points)
        bottom = max(point[1] for point in points)
        polygon = [coordinate for point in points for coordinate in point]
    bbox = [left, top, right - left, bottom - top]
    polygon_area = abs(sum(
        point[0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * point[1]
        for index, point in enumerate(points)
    ) / 2)
    return {
        "bbox": [round(value, 6) for value in bbox],
        "area": round(bbox[2] * bbox[3] if geometry["type"] == "rectangle" else polygon_area, 6),
        "segmentation": [polygon],
    }


def _categories():
    return [
        {"id": index + 1, "name": category, "supercategory": "visible_mainboard_defect"}
        for index, category in enumerate(DEFECT_CATEGORIES)
    ]


def build_coco_from_training_manifest(manifest):
    if manifest.get("schema_version") != "VISUAL-QC-TRAINING-MANIFEST-V1":
        raise ValueError("Training manifest schema version is unsupported")
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Training manifest cases must be an array")
    case_ids = [case.get("case_id") for case in cases]
    if any(not case_id for case_id in case_ids) or len(case_ids) != len(set(case_ids)):
        raise ValueError("Training manifest contains missing or duplicate case ids")

    categories = _categories()
    category_ids = {category["name"]: category["id"] for category in categories}
    images = []
    annotations = []
    annotation_id = 1
    for image_id, case in enumerate(sorted(cases, key=lambda item: item["case_id"]), start=1):
        image = case["image"]
        review = case["qc_review"]
        images.append({
            "id": image_id,
            "case_id": case["case_id"],
            "image_id": image["image_id"],
            "file_name": image["file_name"],
            "width": image["width"],
            "height": image["height"],
            "sha256": image["sha256"],
            "board_key": case["board_key"],
            "board_id": case["board_id"],
            "side_id": case["side_id"],
            "capture_stage": case["capture_stage"],
            "qc_status": review["qc_result"],
            "qc_review_id": review["qc_review_id"],
            "qc_review_version": review["version"],
        })
        for annotation in sorted(
            review.get("annotations", []),
            key=lambda item: item["annotation_id"],
        ):
            if annotation["review_status"] != "confirmed":
                continue
            category = annotation["category"]
            if category not in category_ids:
                raise ValueError(f"Unsupported training annotation category: {category}")
            geometry = _coco_geometry(
                annotation["image_geometry"],
                image["width"],
                image["height"],
            )
            annotations.append({
                "id": annotation_id,
                "image_id": image_id,
                "category_id": category_ids[category],
                **geometry,
                "iscrowd": 0,
                "attributes": {
                    "annotation_id": annotation["annotation_id"],
                    "source": annotation["source"],
                    "designator": (annotation.get("component") or {}).get("designator"),
                    "board_geometry": annotation["board_geometry"],
                },
            })
            annotation_id += 1
    return {
        "info": {
            "description": "Human-reviewed mainboard visual QC dataset",
            "version": "VISUAL-QC-COCO-V1",
            "source_manifest": "VISUAL-QC-TRAINING-MANIFEST-V1",
        },
        "licenses": [],
        "images": images,
        "annotations": annotations,
        "categories": categories,
    }


def build_coco_dataset(cases, root):
    case_ids = [visual_case.get("case_id") for visual_case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Visual QC dataset contains duplicate case_id values")
    ordered_cases = sorted(cases, key=lambda visual_case: visual_case["case_id"])
    errors = []
    for visual_case in ordered_cases:
        errors.extend(
            f"{visual_case.get('case_id', 'unknown')}: {error}"
            for error in validate_visual_qc_case(visual_case, root, training_ready=True)
        )
    if errors:
        raise ValueError("Visual QC dataset is not training ready:\n" + "\n".join(errors))

    categories = _categories()
    category_ids = {category["name"]: category["id"] for category in categories}
    images = []
    annotations = []
    annotation_id = 1
    for image_id, visual_case in enumerate(ordered_cases, start=1):
        image = visual_case["image"]
        images.append({
            "id": image_id,
            "file_name": image["file_name"],
            "width": image["width"],
            "height": image["height"],
            "sha256": image["sha256"],
            "board_key": visual_case["board_key"],
            "board_id": visual_case["board_id"],
            "side_id": visual_case["side_id"],
            "capture_stage": visual_case["capture_stage"],
            "qc_status": visual_case["qc_result"]["status"],
        })
        for annotation in sorted(
            visual_case.get("annotations", []),
            key=lambda item: item["annotation_id"],
        ):
            if annotation["review_status"] != "confirmed":
                continue
            geometry = _coco_geometry(
                annotation["image_geometry"],
                image["width"],
                image["height"],
            )
            annotations.append({
                "id": annotation_id,
                "image_id": image_id,
                "category_id": category_ids[annotation["category"]],
                **geometry,
                "iscrowd": 0,
                "attributes": {
                    "annotation_id": annotation["annotation_id"],
                    "source": annotation["source"],
                    "designator": (annotation.get("component") or {}).get("designator"),
                    "board_geometry": annotation["board_geometry"],
                },
            })
            annotation_id += 1
    return {
        "info": {
            "description": "Human-reviewed mainboard visual QC dataset",
            "version": "VISUAL-QC-CASE-V1",
        },
        "licenses": [],
        "images": images,
        "annotations": annotations,
        "categories": categories,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export reviewed visual QC cases to COCO")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    cases = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        cases = [cases]
    coco = build_coco_dataset(cases, root)
    Path(args.output).write_text(
        json.dumps(coco, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
