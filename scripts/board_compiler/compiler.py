import math
import re


PREFIX_TYPES = {
    "U": "ic", "J": "connector", "X": "crystal", "R": "resistor", "C": "capacitor",
    "L": "inductor", "PL": "inductor", "D": "diode", "Q": "transistor", "F": "fuse",
    "ANT": "antenna", "LED": "led", "TP": "test_point",
}


def classify_designator(value):
    text = value.strip().upper()
    if re.fullmatch(r"VB(?:AT|US)\d+", text):
        return "test_point"
    match = re.fullmatch(r"([A-Z]{1,4})(\d{3,5})", text)
    if not match:
        return None
    return PREFIX_TYPES.get(match.group(1))


def normalize_point(point, bounds):
    x0, y0, x1, y1 = bounds
    return {
        "x": round((point["x"] - x0) / (x1 - x0), 6),
        "y": round(1 - (point["y"] - y0) / (y1 - y0), 6),
    }


def _candidate_footprint(label, rectangles, bounds, category):
    board_width, board_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    plausible = []
    for rectangle in rectangles:
        width, height = rectangle["width"], rectangle["height"]
        if width <= 8 or height <= 8 or width > board_width * 0.18 or height > board_height * 0.18:
            continue
        if category == "test_point" and (width > board_width * 0.03 or height > board_height * 0.03):
            continue
        center_x = rectangle["x"] + width / 2
        center_y = rectangle["y"] + height / 2
        contains = rectangle["x"] <= label["x"] <= rectangle["x"] + width and rectangle["y"] <= label["y"] <= rectangle["y"] + height
        distance = math.hypot(center_x - label["x"], center_y - label["y"])
        scale = max(width, height)
        score = distance / scale - (2 if contains else 0)
        if contains or distance <= scale * 2.5:
            plausible.append((score, rectangle, contains, distance / scale))
    if not plausible:
        return None
    score, rectangle, contains, distance_ratio = min(plausible, key=lambda item: item[0])
    if contains and distance_ratio <= 0.35:
        confidence = "high"
    elif contains or distance_ratio <= 0.75:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "rectangle": rectangle,
        "confidence": confidence,
        "match_method": "label_inside_vector_rectangle" if contains else "nearest_vector_rectangle",
        "distance_ratio": round(distance_ratio, 4),
        "score": round(score, 4),
    }


def compile_designators(labels, rectangles, bounds, component_prefix="KM4-F151-P2"):
    compiled = {}
    for label in labels:
        category = classify_designator(label["text"])
        if not category:
            continue
        key = (label["text"].upper(), round(label["x"], 3), round(label["y"], 3))
        if key in compiled:
            continue
        footprint_match = _candidate_footprint(label, rectangles, bounds, category)
        item = {
            "component_id": f"{component_prefix}-{label['text'].upper()}",
            "designator": label["text"].upper(),
            "category": category,
            "source_point": {"x": round(label["x"], 3), "y": round(label["y"], 3)},
            "center": normalize_point(label, bounds),
            "source_status": "decoded_pdf_text",
        }
        if footprint_match:
            footprint = footprint_match["rectangle"]
            item["footprint"] = {
                "center": normalize_point({"x": footprint["x"] + footprint["width"] / 2, "y": footprint["y"] + footprint["height"] / 2}, bounds),
                "size": {
                    "x": round(footprint["width"] / (bounds[2] - bounds[0]), 6),
                    "y": round(footprint["height"] / (bounds[3] - bounds[1]), 6),
                },
                "confidence": footprint_match["confidence"],
                "match_method": footprint_match["match_method"],
                "distance_ratio": footprint_match["distance_ratio"],
            }
        compiled[key] = item
    return sorted(compiled.values(), key=lambda item: (item["designator"], item["center"]["y"], item["center"]["x"]))
