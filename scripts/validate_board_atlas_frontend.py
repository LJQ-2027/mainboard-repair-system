from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "mainboard_repair_system_v7.4_updated.html"
ATLAS_JSON = ROOT / "knowledge-base" / "board-atlas-mvp.json"


def require_contains(text: str, needle: str) -> None:
    if needle not in text:
        raise AssertionError(f"Missing expected frontend marker: {needle}")


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")

    required_markers = [
        "data-tab=\"board-atlas-guide\"",
        "id=\"board-atlas-guide-tab\"",
        "boardAtlas: 'knowledge-base/board-atlas-mvp.json'",
        "boardAtlas: null",
        "renderBoardAtlasGuide()",
        "function renderBoardAtlasGuide()",
        "function setBoardAtlasSide(",
        "function setBoardAtlasFault(",
        "function selectBoardAtlasModule(",
        "function selectBoardAtlasTestPoint(",
        "class=\"board-atlas-shell\"",
        "class=\"board-atlas-canvas\"",
        "class=\"board-atlas-overlay\"",
    ]
    for marker in required_markers:
        require_contains(html, marker)

    if not ATLAS_JSON.exists():
        raise AssertionError("Board atlas JSON is missing")

    print("Board atlas frontend markers found.")


if __name__ == "__main__":
    main()

