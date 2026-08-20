import re

from pypdf import PdfReader
from pypdf.generic import ContentStream


def parse_to_unicode(data):
    text = data.decode("latin1") if isinstance(data, bytes) else data
    return {int(source, 16): chr(int(target, 16)) for source, target in re.findall(r"<([0-9A-Fa-f]{4})><([0-9A-Fa-f]{4})>", text)}


def decode_cid_text(data, mapping):
    return "".join(mapping.get(int.from_bytes(data[index:index + 2], "big"), "") for index in range(0, len(data) - 1, 2))


def multiply_matrix(left, right):
    a, b, c, d, e, f = left
    A, B, C, D, E, F = right
    return [
        a * A + c * B,
        b * A + d * B,
        a * C + c * D,
        b * C + d * D,
        a * E + c * F + e,
        b * E + d * F + f,
    ]


def transform_point(matrix, x, y):
    a, b, c, d, e, f = matrix
    return {"x": a * x + c * y + e, "y": b * x + d * y + f}


def transform_rectangle(matrix, rectangle):
    x, y, width, height = [float(value) for value in rectangle]
    points = [
        transform_point(matrix, x, y),
        transform_point(matrix, x + width, y),
        transform_point(matrix, x + width, y + height),
        transform_point(matrix, x, y + height),
    ]
    xs, ys = [point["x"] for point in points], [point["y"] for point in points]
    return {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)}


def _largest_form(page):
    forms = []
    for name, reference in page["/Resources"].get("/XObject", {}).items():
        item = reference.get_object()
        if item.get("/Subtype") == "/Form":
            forms.append((len(item.get_data()), str(name), item))
    return max(forms, key=lambda entry: entry[0])[1:] if forms else None


def _primitive_source(page):
    form = _largest_form(page)
    if form:
        form_name, stream = form
        return {
            "name": form_name,
            "stream": stream,
            "resources": stream["/Resources"],
            "bounds": [float(value) for value in stream["/BBox"]],
            "is_form": True,
        }
    media_box = page.mediabox
    return {
        "name": "/PageContents",
        "stream": page.get_contents(),
        "resources": page["/Resources"],
        "bounds": [float(media_box.left), float(media_box.bottom), float(media_box.right), float(media_box.top)],
        "is_form": False,
    }


def _xobject_clip_bounds(page, reader, form_name):
    stream = ContentStream(page.get_contents(), reader)
    last_rectangle = None
    for operands, operator in stream.operations:
        if operator == b"re":
            x, y, width, height = [float(value) for value in operands]
            last_rectangle = [x, y, x + width, y + height]
        elif operator == b"Do" and str(operands[0]) == form_name:
            return last_rectangle
    return None


def _extract_visitor_labels(page):
    labels = []

    def visit_text(text, current_matrix, text_matrix, font, _font_size):
        value = text.strip()
        if not value:
            return
        matrix = multiply_matrix(current_matrix, text_matrix)
        point = transform_point(matrix, 0, 0)
        labels.append({
            "text": value,
            "x": point["x"],
            "y": point["y"],
            "font": str(font.get("/BaseFont", "")) if font else "",
        })

    page.extract_text(visitor_text=visit_text)
    return labels


def _page_display_matrix(page):
    rotation = int(page.get("/Rotate", 0)) % 360
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    if rotation == 90:
        return [0, -1, 1, 0, 0, width]
    if rotation == 180:
        return [-1, 0, 0, -1, width, height]
    if rotation == 270:
        return [0, 1, -1, 0, height, 0]
    return None


def _transform_bounds(matrix, bounds):
    rectangle = transform_rectangle(
        matrix,
        [bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]],
    )
    return [
        rectangle["x"],
        rectangle["y"],
        rectangle["x"] + rectangle["width"],
        rectangle["y"] + rectangle["height"],
    ]


def extract_form_primitives(pdf_path, page_number):
    reader = PdfReader(str(pdf_path))
    page = reader.pages[page_number - 1]
    source = _primitive_source(page)
    form_name = source["name"]
    bounds = source["bounds"]
    visible_bounds = (_xobject_clip_bounds(page, reader, form_name) if source["is_form"] else None) or bounds
    fonts = source["resources"].get("/Font", {})
    font_maps = {}
    for name, reference in fonts.items():
        font = reference.get_object()
        if font.get("/ToUnicode"):
            font_maps[str(name)] = parse_to_unicode(font["/ToUnicode"].get_object().get_data())

    stream = ContentStream(source["stream"], reader)
    matrix = [1, 0, 0, 1, 0, 0]
    stack = []
    active_font = None
    labels, rectangles = [], []
    operator_counts = {}
    for operands, operator in stream.operations:
        name = operator.decode("latin1")
        operator_counts[name] = operator_counts.get(name, 0) + 1
        if operator == b"q":
            stack.append(matrix[:])
        elif operator == b"Q":
            matrix = stack.pop()
        elif operator == b"cm":
            matrix = multiply_matrix(matrix, [float(value) for value in operands])
        elif operator == b"Tf":
            active_font = str(operands[0])
        elif operator == b"re":
            rectangles.append(transform_rectangle(matrix, operands))
        elif operator == b"Tj" and active_font in font_maps:
            raw = getattr(operands[0], "original_bytes", b"")
            text = decode_cid_text(raw, font_maps[active_font])
            if text:
                labels.append({"text": text, "x": matrix[4], "y": matrix[5], "font": active_font})

    label_method = "embedded_cmap"
    if not labels:
        labels = _extract_visitor_labels(page)
        label_method = "pypdf_visitor_fallback"

    display_matrix = _page_display_matrix(page) if not source["is_form"] else None
    if display_matrix:
        labels = [
            {**label, **transform_point(display_matrix, label["x"], label["y"])}
            for label in labels
        ]
        rectangles = [
            transform_rectangle(
                display_matrix,
                [rectangle["x"], rectangle["y"], rectangle["width"], rectangle["height"]],
            )
            for rectangle in rectangles
        ]
        bounds = _transform_bounds(display_matrix, bounds)
        visible_bounds = _transform_bounds(display_matrix, visible_bounds)

    return {
        "form_name": form_name,
        "bounds": bounds,
        "visible_bounds": visible_bounds,
        "labels": labels,
        "label_method": label_method,
        "rectangles": rectangles,
        "operator_counts": operator_counts,
    }
