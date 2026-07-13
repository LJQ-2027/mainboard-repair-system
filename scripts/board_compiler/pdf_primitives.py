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
    if not forms:
        raise ValueError("Point-map page contains no Form XObject.")
    return max(forms, key=lambda entry: entry[0])[1:]


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


def extract_form_primitives(pdf_path, page_number):
    reader = PdfReader(str(pdf_path))
    page = reader.pages[page_number - 1]
    form_name, form = _largest_form(page)
    bounds = [float(value) for value in form["/BBox"]]
    visible_bounds = _xobject_clip_bounds(page, reader, form_name) or bounds
    fonts = form["/Resources"].get("/Font", {})
    font_maps = {}
    for name, reference in fonts.items():
        font = reference.get_object()
        if font.get("/ToUnicode"):
            font_maps[str(name)] = parse_to_unicode(font["/ToUnicode"].get_object().get_data())

    stream = ContentStream(form, reader)
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

    return {
        "form_name": form_name,
        "bounds": bounds,
        "visible_bounds": visible_bounds,
        "labels": labels,
        "rectangles": rectangles,
        "operator_counts": operator_counts,
    }
