from __future__ import annotations

import json
from pathlib import Path


class CatalogError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class BoardCatalog:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        catalog_path = self.project_root / "knowledge-base" / "repair-workbench-boards.json"
        self.catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    def resolve_board(self, board_key: str) -> dict:
        board = self.catalog.get("boards", {}).get(board_key)
        if not board:
            raise CatalogError("unknown_board", f"Unknown board_key: {board_key}")

        manifest_name = Path(board["side_manifest"]).name
        manifest_path = self.project_root / "knowledge-base" / manifest_name
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "board_key": board_key,
            "board_id": manifest["board_id"],
            "side_ids": [side["side_id"] for side in manifest.get("sides", [])],
            "manifest": manifest,
        }

    def resolve_side(self, board_key: str, side_id: str) -> dict:
        resolved_board = self.resolve_board(board_key)
        manifest = resolved_board["manifest"]
        side = next(
            (candidate for candidate in manifest.get("sides", []) if candidate["side_id"] == side_id),
            None,
        )
        if not side:
            raise CatalogError(
                "unknown_board_side",
                f"side_id {side_id} does not belong to board_key {board_key}",
            )

        reference_path = (self.project_root / side["engineering_texture"]).resolve()
        try:
            reference_path.relative_to(self.project_root)
        except ValueError as exc:
            raise CatalogError("invalid_reference_path", "Reference path escapes project root") from exc
        if not reference_path.is_file():
            raise CatalogError("missing_reference", f"Missing board reference: {reference_path}")

        return {
            "board_key": board_key,
            "board_id": resolved_board["board_id"],
            "side_id": side_id,
            "expected_side_ids": resolved_board["side_ids"],
            "reference_path": reference_path,
        }
