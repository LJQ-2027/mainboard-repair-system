#!/usr/bin/env python3
"""Validate the static internal vision-recognition demo and its references."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / "assets" / "vision-recognition-demo"
GALLERY_MANIFEST = ROOT / "knowledge-base" / "vision-reference-gallery.json"
FORBIDDEN_CLAIMS = (
    "fault detected",
    "defect confirmed",
    "board is normal",
    "production confidence",
    "repair decision",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    index = (DEMO_ROOT / "index.html").read_text(encoding="utf-8")
    styles = (DEMO_ROOT / "styles.css").read_text(encoding="utf-8")
    app = (DEMO_ROOT / "app.js").read_text(encoding="utf-8")
    core = (DEMO_ROOT / "vision-core.js").read_text(encoding="utf-8")
    manifest = json.loads(GALLERY_MANIFEST.read_text(encoding="utf-8"))

    require('href="styles.css"' in index, "index.html must load styles.css")
    require('src="app.js"' in index, "index.html must load app.js")
    require("vision-reference-gallery.json" in app, "app.js must load the reviewed gallery manifest")
    require("rankModelCandidates" in app, "app.js must rank unique model candidates")
    require("analyzeImageQuality" in core, "vision-core.js must expose image quality analysis")
    require("@media (max-width: 500px)" in styles, "mobile layout breakpoint is missing")
    require("http://" not in index + styles + app + core, "demo must not load remote HTTP resources")
    require("https://" not in index + styles + app + core, "demo must not load remote HTTPS resources")

    approved = []
    model_counts = Counter()
    roles = Counter()
    for model in manifest["models"]:
        for page in model["candidate_pages"]:
            for asset in page["embedded_images"]:
                if asset.get("review_status") != "approved":
                    continue
                path = ROOT / asset["asset_path"]
                require(path.is_file() and path.stat().st_size > 0, f"missing approved reference: {path}")
                approved.append(asset)
                model_counts[model["model"]] += 1
                roles[asset["reference_role"]] += 1

    require(len(approved) == 21, f"expected 21 approved references, found {len(approved)}")
    require(len(model_counts) == 7, f"expected 7 models, found {len(model_counts)}")
    require(all(count == 3 for count in model_counts.values()), f"each model needs 3 references: {model_counts}")
    require(
        roles == {"exploded_structure": 7, "installed_mainboard": 7, "installed_subboard": 7},
        f"unexpected approved reference roles: {roles}",
    )

    visible_text = " ".join((index + app).lower().split())
    for claim in FORBIDDEN_CLAIMS:
        require(claim not in visible_text, f"prohibited production claim found: {claim}")
    require("not a production model" in visible_text, "internal-demo boundary must be visible")

    print("Vision recognition demo validation passed")
    print(f"  models: {len(model_counts)}")
    print(f"  approved references: {len(approved)}")
    print(f"  roles: {dict(roles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
