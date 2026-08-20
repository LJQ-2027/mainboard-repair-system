from collections import defaultdict, deque
import math

import numpy as np
from PIL import Image


def dilate(mask, radius):
    result = mask.copy()
    for _ in range(radius):
        source = result
        expanded = source.copy()
        expanded[1:] |= source[:-1]
        expanded[:-1] |= source[1:]
        expanded[:, 1:] |= source[:, :-1]
        expanded[:, :-1] |= source[:, 1:]
        result = expanded
    return result


def erode(mask, radius):
    return ~dilate(~mask, radius)


def largest_component(mask):
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    best = []
    for y, x in zip(*np.where(mask)):
        if seen[y, x]:
            continue
        stack = [(int(y), int(x))]
        seen[y, x] = True
        points = []
        while stack:
            current_y, current_x = stack.pop()
            points.append((current_y, current_x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                next_y, next_x = current_y + dy, current_x + dx
                if 0 <= next_y < height and 0 <= next_x < width and mask[next_y, next_x] and not seen[next_y, next_x]:
                    seen[next_y, next_x] = True
                    stack.append((next_y, next_x))
        if len(points) > len(best):
            best = points
    result = np.zeros_like(mask, dtype=bool)
    for y, x in best:
        result[y, x] = True
    return result


def fill_holes(mask):
    height, width = mask.shape
    outside = np.zeros_like(mask, dtype=bool)
    queue = deque()
    for x in range(width):
        for y in (0, height - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
    while queue:
        current_y, current_x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            next_y, next_x = current_y + dy, current_x + dx
            if 0 <= next_y < height and 0 <= next_x < width and not mask[next_y, next_x] and not outside[next_y, next_x]:
                outside[next_y, next_x] = True
                queue.append((next_y, next_x))
    return ~outside


def _signed_area(polygon):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1])) / 2


def mask_outer_polygon(mask):
    edges = defaultdict(list)
    height, width = mask.shape
    for y, x in zip(*np.where(mask)):
        if y == 0 or not mask[y - 1, x]:
            edges[(x, y)].append((x + 1, y))
        if x == width - 1 or not mask[y, x + 1]:
            edges[(x + 1, y)].append((x + 1, y + 1))
        if y == height - 1 or not mask[y + 1, x]:
            edges[(x + 1, y + 1)].append((x, y + 1))
        if x == 0 or not mask[y, x - 1]:
            edges[(x, y + 1)].append((x, y))

    loops = []
    remaining = {(start, end) for start, ends in edges.items() for end in ends}
    while remaining:
        start, next_point = next(iter(remaining))
        loop = [start]
        current = start
        while True:
            edge = (current, next_point)
            if edge not in remaining:
                break
            remaining.remove(edge)
            current = next_point
            loop.append(current)
            if current == start:
                break
            candidates = [end for end in edges.get(current, []) if (current, end) in remaining]
            if not candidates:
                break
            next_point = candidates[0]
        if len(loop) > 3 and loop[-1] == start:
            loops.append(loop[:-1])
    if not loops:
        raise ValueError("Mask contains no closed outer boundary.")
    return max(loops, key=lambda polygon: abs(_signed_area(polygon)))


def _point_line_distance(point, start, end):
    if start == end:
        return math.dist(point, start)
    x, y = point
    x1, y1 = start
    x2, y2 = end
    numerator = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1)
    return numerator / math.hypot(y2 - y1, x2 - x1)


def _rdp(points, tolerance):
    if len(points) <= 2:
        return points
    distances = [_point_line_distance(point, points[0], points[-1]) for point in points[1:-1]]
    if not distances or max(distances) <= tolerance:
        return [points[0], points[-1]]
    index = distances.index(max(distances)) + 1
    return _rdp(points[:index + 1], tolerance)[:-1] + _rdp(points[index:], tolerance)


def simplify_polygon(polygon, tolerance=2.0):
    if polygon[0] == polygon[-1]:
        polygon = polygon[:-1]
    anchor = min(range(len(polygon)), key=lambda index: polygon[index])
    rotated = polygon[anchor:] + polygon[:anchor] + [polygon[anchor]]
    simplified = _rdp(rotated, tolerance)
    return simplified[:-1] if simplified[-1] == simplified[0] else simplified


def extract_board_outline(image_path, closing_radius=8, tolerance=2.5, method="engineering_marks", max_alpha_dimension=1600):
    source = Image.open(image_path)
    source_width, source_height = source.size
    if method == "engineering_marks":
        image = np.asarray(source.convert("RGB"))
        engineering_marks = image.min(axis=2) < 235
        closed = dilate(engineering_marks, closing_radius)
        board = erode(fill_holes(largest_component(closed)), closing_radius)
    elif method == "alpha_silhouette":
        working = source.convert("RGBA")
        if max(working.size) > max_alpha_dimension:
            scale = max_alpha_dimension / max(working.size)
            working = working.resize(
                (max(1, round(working.width * scale)), max(1, round(working.height * scale))),
                Image.Resampling.NEAREST,
            )
        image = np.asarray(working)
        board = fill_holes(largest_component(image[:, :, 3] > 32))
    else:
        raise ValueError(f"Unsupported board outline method: {method}")
    polygon = simplify_polygon(mask_outer_polygon(board), tolerance)
    height, width = board.shape
    normalized = [{"x": round(x / width, 6), "y": round(y / height, 6)} for x, y in polygon]
    return {
        "outline": normalized,
        "mask_area_ratio": round(float(board.mean()), 6),
        "image_size": {"width": source_width, "height": source_height},
        "working_image_size": {"width": width, "height": height},
    }
