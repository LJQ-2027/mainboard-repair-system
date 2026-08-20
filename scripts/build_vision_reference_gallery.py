#!/usr/bin/env python3
"""Extract board-reference candidates from model service manuals."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader


DEFAULT_MODELS = ["KM4", "KL4", "CLA5", "KJ5", "CM5", "CM6", "X6880"]
PAGE_TERMS = {
    "motherboard": 8,
    "mainboard": 8,
    "main board": 8,
    "main pcba": 7,
    "pcba": 6,
    "printed circuit board": 5,
    "pcb": 4,
    "auxiliary board": 4,
    "sub board": 4,
    "exploded": 2,
    "disassemble": 1,
    "remove": 1,
}


def score_candidate_page(text: str) -> int:
    normalized = " ".join(text.lower().split())
    return sum(weight for term, weight in PAGE_TERMS.items() if term in normalized)


def infer_board_side(text: str) -> str:
    normalized = " ".join(text.lower().split())
    subject = r"(?:main\s*board|motherboard|pcba|pcb)"
    if re.search(rf"top\s+(?:and|/)\s+bottom\s+side\s+of\s+(?:the\s+)?{subject}", normalized):
        return "both"
    top_patterns = [
        rf"{subject}\s+(?:on\s+the\s+)?top\s+side",
        rf"top\s+side\s+(?:of\s+)?(?:the\s+)?{subject}",
        rf"top\s+of\s+(?:the\s+)?{subject}",
    ]
    bottom_patterns = [
        rf"{subject}\s+(?:on\s+the\s+)?bottom\s+side",
        rf"bottom\s+side\s+(?:of\s+)?(?:the\s+)?{subject}",
        rf"bottom\s+of\s+(?:the\s+)?{subject}",
    ]
    has_top = any(re.search(pattern, normalized) for pattern in top_patterns)
    has_bottom = any(re.search(pattern, normalized) for pattern in bottom_patterns)
    if has_top and has_bottom:
        return "both"
    if has_top:
        return "top"
    if has_bottom:
        return "bottom"
    return "unknown"


def is_reference_image_candidate(width: int, height: int, size_bytes: int) -> bool:
    if width < 600 or height < 350 or size_bytes < 12000:
        return False
    aspect_ratio = width / height
    return 0.55 <= aspect_ratio <= 2.5


def select_manual_records(records: list[dict], models: list[str]) -> dict[str, list[dict]]:
    selected: dict[str, list[dict]] = {model: [] for model in models}
    seen: dict[str, set[str]] = {model: set() for model in models}
    for record in records:
        if record.get("extension") != ".pdf":
            continue
        stored_path = record.get("stored_path", "")
        for model in models:
            if model not in record.get("models", []) or stored_path in seen[model]:
                continue
            selected[model].append(record)
            seen[model].add(stored_path)
    for model in models:
        selected[model].sort(key=lambda item: item["stored_path"].lower())
    return selected


def classify_board_versions(versions: list[str]) -> dict[str, list[str]]:
    result = {"main": [], "sub": [], "other": []}
    for version in versions:
        upper = version.upper()
        if "MAIN" in upper:
            result["main"].append(version)
        elif "SUB" in upper:
            result["sub"].append(version)
        else:
            result["other"].append(version)
    return result


def apply_review_annotations(model_record: dict, review: dict) -> None:
    annotations = review.get("assets", {})
    for page in model_record.get("candidate_pages", []):
        for asset in page.get("embedded_images", []):
            asset["review_status"] = "not_selected"
            annotation = annotations.get(asset["asset_path"])
            if annotation:
                asset.update(annotation)
    model_record["coverage"] = review.get("coverage", {})
    model_record["review_notes"] = review.get("notes", "")


def board_version_label(model_record: dict, asset: dict) -> str:
    versions = model_record.get("board_versions", {})
    scope = asset.get("board_scope")
    if scope == "main":
        selected = versions.get("main", [])
    elif scope == "sub":
        selected = versions.get("sub", [])
    elif scope == "mixed_phone_components":
        selected = versions.get("main", []) + versions.get("sub", [])
    else:
        selected = versions.get("main", []) + versions.get("sub", []) + versions.get("other", [])
    return " + ".join(selected) or "board version unresolved"


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_pdftoppm(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return str(path)
        raise FileNotFoundError(f"pdftoppm not found: {path}")
    discovered = shutil.which("pdftoppm")
    if discovered:
        return discovered
    raise FileNotFoundError("pdftoppm is required; pass --pdftoppm with its executable path")


def reset_output_root(output_root: Path, project_root: Path) -> None:
    resolved_project = project_root.resolve()
    resolved_output = output_root.resolve()
    if resolved_output == resolved_project or resolved_project not in resolved_output.parents:
        raise ValueError(f"Unsafe gallery output path: {resolved_output}")
    if resolved_output.name != "vision-reference-gallery":
        raise ValueError(f"Refusing to reset unowned output directory: {resolved_output}")
    if resolved_output.exists():
        shutil.rmtree(resolved_output)
    resolved_output.mkdir(parents=True, exist_ok=True)


def render_pdf_page(pdftoppm: str, pdf: Path, page_number: int, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    output_prefix = destination.with_suffix("")
    subprocess.run(
        [
            pdftoppm,
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            "-r",
            "150",
            "-png",
            "-singlefile",
            str(pdf),
            str(output_prefix),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def extract_page_images(
    page,
    page_number: int,
    output_dir: Path,
    project_root: Path,
    seen_hashes: set[str],
) -> list[dict]:
    assets = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for image_index, image_file in enumerate(page.images, start=1):
        width, height = image_file.image.size
        data = image_file.data
        if not is_reference_image_candidate(width, height, len(data)):
            continue
        digest = file_sha256(data)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        extension = Path(image_file.name).suffix.lower() or ".bin"
        destination = output_dir / f"page-{page_number:03d}-image-{image_index:02d}{extension}"
        destination.write_bytes(data)
        assets.append(
            {
                "asset_path": destination.relative_to(project_root).as_posix(),
                "source_object": image_file.name,
                "source_page": page_number,
                "width": width,
                "height": height,
                "size_bytes": len(data),
                "sha256": digest,
                "review_status": "pending",
                "reference_role": "candidate",
                "board_side": "unknown",
            }
        )
    return assets


def load_board_model_index(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {record["model_name"]: record for record in data["models"]}


def generate_gallery_html(manifest: dict, destination: Path) -> None:
    cards = []
    for model in manifest["models"]:
        for page in model["candidate_pages"]:
            for asset in page["embedded_images"]:
                cards.append(
                    f"""
                    <article class="asset" data-model="{html.escape(model['model'])}" data-status="{asset['review_status']}"{' hidden' if asset['review_status'] != 'approved' else ''}>
                      <div class="asset-image"><img src="../../{html.escape(asset['asset_path'])}" alt="{html.escape(model['model'])} page {page['page_number']} candidate"></div>
                      <div class="asset-meta">
                        <div><strong>{html.escape(model['model'])}</strong><span>Page {page['page_number']} · {html.escape(asset['review_status'])}</span></div>
                        <p>{asset['width']} x {asset['height']} · {html.escape(asset['board_side'])} · {html.escape(asset['reference_role'])}</p>
                        <code>{html.escape(board_version_label(model, asset))}</code>
                      </div>
                    </article>
                    """
                )
    buttons = "".join(
        f'<button type="button" data-filter="{html.escape(model["model"])}">{html.escape(model["model"])}</button>'
        for model in manifest["models"]
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Board Vision Reference Gallery</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, "Segoe UI", Arial, sans-serif; color: #192126; background: #eef1f2; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; }}
    header {{ position: sticky; top: 0; z-index: 2; background: #ffffff; border-bottom: 1px solid #cbd2d5; padding: 14px 20px 12px; }}
    .title-row {{ display: flex; align-items: baseline; justify-content: space-between; gap: 16px; }}
    h1 {{ margin: 0; font-size: 20px; letter-spacing: 0; }}
    .summary {{ margin: 0; color: #526168; font-size: 13px; }}
    nav {{ display: flex; gap: 6px; overflow-x: auto; margin-top: 12px; padding-bottom: 2px; }}
    button {{ border: 1px solid #aeb9bd; background: #f8faf9; color: #263238; height: 34px; padding: 0 12px; border-radius: 4px; cursor: pointer; white-space: nowrap; }}
    button[aria-pressed="true"] {{ background: #123c35; border-color: #123c35; color: #ffffff; }}
    .show-all {{ margin-left: auto; border-color: #b66a2c; color: #7c4217; }}
    .show-all[aria-pressed="true"] {{ background: #8a4a1b; border-color: #8a4a1b; color: #ffffff; }}
    main {{ padding: 18px 20px 32px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }}
    .asset {{ min-width: 0; background: #ffffff; border: 1px solid #cbd2d5; border-radius: 6px; overflow: hidden; }}
    .asset[hidden] {{ display: none; }}
    .asset-image {{ aspect-ratio: 4 / 3; background: #dfe5e7; display: grid; place-items: center; overflow: hidden; }}
    .asset-image img {{ width: 100%; height: 100%; object-fit: contain; }}
    .asset-meta {{ padding: 10px 11px 12px; }}
    .asset-meta div {{ display: flex; justify-content: space-between; gap: 8px; }}
    .asset-meta span, .asset-meta p {{ color: #617077; font-size: 12px; }}
    .asset-meta p {{ margin: 7px 0; }}
    code {{ display: block; overflow: hidden; text-overflow: ellipsis; color: #874c16; font-size: 11px; white-space: nowrap; }}
    @media (max-width: 600px) {{ header, main {{ padding-left: 12px; padding-right: 12px; }} .title-row {{ display: block; }} .summary {{ margin-top: 4px; }} .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <div class="title-row"><h1>Board Vision Reference Gallery</h1><p class="summary">{len(manifest['models'])} models · {manifest['statistics']['approved_image_count']} curated · {manifest['statistics']['embedded_image_count']} candidates</p></div>
    <nav aria-label="Model filter"><button type="button" data-filter="all" aria-pressed="true">All</button>{buttons}<button class="show-all" type="button" id="showAll" aria-pressed="false">Show all candidates</button></nav>
  </header>
  <main><section class="grid" aria-live="polite">{''.join(cards)}</section></main>
  <script>
    const buttons = [...document.querySelectorAll('[data-filter]')];
    const assets = [...document.querySelectorAll('.asset')];
    const showAllButton = document.getElementById('showAll');
    let activeFilter = 'all';
    let showAll = false;
    function applyFilters() {{
      assets.forEach(asset => {{
        const modelMatches = activeFilter === 'all' || asset.dataset.model === activeFilter;
        const statusMatches = showAll || asset.dataset.status === 'approved';
        asset.hidden = !modelMatches || !statusMatches;
      }});
    }}
    buttons.forEach(button => button.addEventListener('click', () => {{
      activeFilter = button.dataset.filter;
      buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      applyFilters();
    }}));
    showAllButton.addEventListener('click', () => {{
      showAll = !showAll;
      showAllButton.setAttribute('aria-pressed', String(showAll));
      applyFilters();
    }});
  </script>
</body>
</html>
"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = "\n".join(line.rstrip() for line in document.splitlines()) + "\n"
    destination.write_text(document, encoding="utf-8", newline="\n")


def build_gallery(args) -> dict:
    project_root = args.project_root.resolve()
    service_manifest = json.loads((project_root / args.service_manifest).read_text(encoding="utf-8"))
    board_models = load_board_model_index(project_root / args.board_models)
    review_path = project_root / args.review
    review_data = json.loads(review_path.read_text(encoding="utf-8")) if review_path.is_file() else {"models": {}}
    selected = select_manual_records(service_manifest["files"], args.models)
    pdftoppm = find_pdftoppm(args.pdftoppm)
    output_root = project_root / args.output_root
    reset_output_root(output_root, project_root)

    gallery_models = []
    total_pages = 0
    total_images = 0
    for model in args.models:
        if not selected[model]:
            gallery_models.append(
                {
                    "model": model,
                    "status": "manual_missing",
                    "board_versions": classify_board_versions(board_models.get(model, {}).get("board_versions", [])),
                    "manuals": [],
                    "candidate_pages": [],
                }
            )
            continue

        record = selected[model][0]
        pdf = project_root / record["stored_path"]
        reader = PdfReader(str(pdf), strict=False)
        scored_pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = " ".join((page.extract_text() or "").split())
            score = score_candidate_page(page_text)
            if score >= args.minimum_page_score:
                scored_pages.append((page_number, score, page_text))
        scored_pages = sorted(scored_pages, key=lambda item: (-item[1], item[0]))[: args.max_pages]
        scored_pages.sort(key=lambda item: item[0])

        model_dir = output_root / model.lower()
        seen_image_hashes: set[str] = set()
        candidate_pages = []
        for page_number, score, page_text in scored_pages:
            rendered = model_dir / "source-pages" / f"page-{page_number:03d}.png"
            render_pdf_page(pdftoppm, pdf, page_number, rendered)
            images = extract_page_images(
                reader.pages[page_number - 1],
                page_number,
                model_dir / "embedded",
                project_root,
                seen_image_hashes,
            )
            side = infer_board_side(page_text)
            for image in images:
                image["board_side"] = side
            candidate_pages.append(
                {
                    "page_number": page_number,
                    "score": score,
                    "board_side_evidence": side,
                    "rendered_page": rendered.relative_to(project_root).as_posix(),
                    "text_excerpt": page_text[:600],
                    "embedded_images": images,
                }
            )
            total_pages += 1
            total_images += len(images)

        model_record = board_models.get(model, {})
        gallery_model = {
                "model": model,
                "aliases": model_record.get("aliases", []),
                "status": "candidates_extracted" if candidate_pages else "no_candidate_pages",
                "board_versions": classify_board_versions(model_record.get("board_versions", [])),
                "main_point_map": model_record.get("assets", {}).get("main_point_map", ""),
                "manuals": [record["stored_path"]],
                "candidate_pages": candidate_pages,
            }
        apply_review_annotations(gallery_model, review_data.get("models", {}).get(model, {}))
        gallery_models.append(gallery_model)

    approved_images = sum(
        1
        for model in gallery_models
        for page in model.get("candidate_pages", [])
        for asset in page.get("embedded_images", [])
        if asset.get("review_status") == "approved"
    )

    manifest = {
        "gallery_id": "VISION-REFERENCE-GALLERY-20260710",
        "title": "Service-manual board vision reference candidates",
        "source_inventory_id": service_manifest["inventory_id"],
        "scope": args.models,
        "review_policy": "Candidate extraction is automatic. Board side and reference role remain unknown until visual review provides explicit evidence.",
        "statistics": {
            "model_count": len(gallery_models),
            "candidate_page_count": total_pages,
            "embedded_image_count": total_images,
            "approved_image_count": approved_images,
        },
        "models": gallery_models,
    }
    manifest_path = project_root / args.output_manifest
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    generate_gallery_html(manifest, project_root / args.output_html)
    return manifest


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--service-manifest", type=Path, default=Path("knowledge-base/service-manual-library-2026-07-10.json"))
    parser.add_argument("--board-models", type=Path, default=Path("knowledge-base/model-board-assets.json"))
    parser.add_argument("--output-root", type=Path, default=Path("assets/vision-reference-gallery"))
    parser.add_argument("--output-manifest", type=Path, default=Path("knowledge-base/vision-reference-gallery.json"))
    parser.add_argument("--output-html", type=Path, default=Path("assets/vision-reference-gallery/index.html"))
    parser.add_argument("--review", type=Path, default=Path("knowledge-base/vision-reference-review.json"))
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--minimum-page-score", type=int, default=4)
    parser.add_argument("--max-pages", type=int, default=7)
    parser.add_argument("--pdftoppm")
    return parser.parse_args()


def main() -> int:
    manifest = build_gallery(parse_args())
    print(json.dumps(manifest["statistics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
