from pypdf import PdfReader


def crop_box_from_origin(origin, image_width, image_height, width_ratio=0.24, height_ratio=0.22, y_offset_ratio=0.08):
    crop_width = round(image_width * width_ratio)
    crop_height = round(image_height * height_ratio)
    center_x = round(origin["x"] * image_width)
    center_y = round((origin["y"] + y_offset_ratio) * image_height)
    left = min(max(center_x - crop_width // 2, 0), image_width - crop_width)
    top = min(max(center_y - crop_height // 2, 0), image_height - crop_height)
    return left, top, left + crop_width, top + crop_height


def _same_baseline(left, right):
    tolerance = max(left["font_size"], right["font_size"]) * 0.22
    return abs(left["y"] - right["y"]) <= tolerance


def _may_join(left, right):
    estimated_right = left["x"] + len(left["text"]) * left["font_size"] * 0.65
    gap = right["x"] - estimated_right
    return -left["font_size"] <= gap <= max(left["font_size"], right["font_size"]) * 1.25


def coalesce_text_fragments(fragments):
    usable = [fragment for fragment in fragments if fragment["text"].strip() and (fragment["x"] or fragment["y"])]
    rows = []
    for fragment in sorted(usable, key=lambda item: (-item["y"], item["x"])):
        row = next((candidate for candidate in rows if _same_baseline(candidate[0], fragment)), None)
        if row is None:
            rows.append([fragment])
        else:
            row.append(fragment)

    runs = []
    for row in rows:
        current = None
        for fragment in sorted(row, key=lambda item: item["x"]):
            if current is None or not _may_join(current, fragment):
                if current is not None:
                    runs.append(current)
                current = {**fragment, "text": fragment["text"].strip(), "_count": 1}
                continue
            count = current["_count"] + 1
            current["text"] += fragment["text"].strip()
            current["y"] = (current["y"] * current["_count"] + fragment["y"]) / count
            current["font_size"] = (current["font_size"] * current["_count"] + fragment["font_size"]) / count
            current["_count"] = count
        if current is not None:
            runs.append(current)
    return [
        {
            "text": run["text"],
            "x": round(run["x"], 3),
            "y": round(run["y"], 3),
            "font_size": round(run["font_size"], 3),
        }
        for run in sorted(runs, key=lambda item: (-item["y"], item["x"]))
    ]


def extract_schematic_pages(pdf_path):
    reader = PdfReader(str(pdf_path))
    pages = {}
    page_sizes = {}
    for page_number, page in enumerate(reader.pages, 1):
        fragments = []

        def visitor(text, _cm, tm, _font, font_size):
            if text.strip():
                fragments.append({
                    "text": text,
                    "x": float(tm[4]),
                    "y": float(tm[5]),
                    "font_size": float(font_size),
                })

        page.extract_text(visitor_text=visitor)
        pages[page_number] = coalesce_text_fragments(fragments)
        page_sizes[page_number] = {"width": float(page.mediabox.width), "height": float(page.mediabox.height)}
    return pages, page_sizes


def index_component_pages(pages, designators):
    result = {designator: [] for designator in sorted(designators)}
    for page_number, runs in pages.items():
        for run in runs:
            source_text = run["text"].strip()
            designator = source_text.upper()
            if designator not in result:
                continue
            result[designator].append({
                "page": page_number,
                "source_text": source_text,
                "x": run["x"],
                "y": run["y"],
                "match_method": "exact_text_run",
            })
    return result
