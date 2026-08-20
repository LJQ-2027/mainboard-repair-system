from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from scripts.visual_qc.server.catalog import BoardCatalog


INVENTORY_SCHEMA_VERSION = "VISUAL-QC-PROXY-INVENTORY-V1"
INVENTORY_PATH = Path("knowledge-base/visual-qc-proxy-inventory-v1.json")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _configured_path(project_root: Path, raw_path: str) -> Path:
    candidate = (project_root / raw_path).resolve()
    if candidate == project_root or project_root not in candidate.parents:
        raise ValueError(f"configured proxy path escapes project root: {raw_path}")
    return candidate


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_proxy_paths(value: object, project_root: Path, result: set[Path]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "assets" and isinstance(item, dict):
                for asset_path, annotation in item.items():
                    if (
                        isinstance(asset_path, str)
                        and isinstance(annotation, dict)
                        and annotation.get("review_status") == "approved"
                    ):
                        result.add(_configured_path(project_root, asset_path))
            elif key in {"asset_path", "proxy_image"} and isinstance(item, str):
                result.add(_configured_path(project_root, item))
            else:
                _collect_proxy_paths(item, project_root, result)
    elif isinstance(value, list):
        for item in value:
            _collect_proxy_paths(item, project_root, result)


def _configured_proxy_paths(project_root: Path) -> set[Path]:
    catalog = BoardCatalog(project_root)
    paths: set[Path] = set()
    for board_key in catalog.catalog.get("boards", {}):
        board = catalog.resolve_board(board_key)
        for side_id in board["side_ids"]:
            paths.add(catalog.resolve_side(board_key, side_id)["reference_path"])

    review_path = project_root / "knowledge-base" / "vision-reference-review.json"
    if review_path.is_file():
        _collect_proxy_paths(
            json.loads(review_path.read_text(encoding="utf-8")), project_root, paths
        )
    for registration_path in (project_root / "knowledge-base").glob(
        "*-cross-source-registration.json"
    ):
        _collect_proxy_paths(
            json.loads(registration_path.read_text(encoding="utf-8")),
            project_root,
            paths,
        )
    return paths


def known_proxy_hashes(project_root: Path) -> frozenset[str]:
    project_root = Path(project_root).resolve()
    inventory_path = project_root / INVENTORY_PATH
    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid proxy inventory: {exc}") from exc
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "entries"}
        or payload.get("schema_version") != INVENTORY_SCHEMA_VERSION
        or not isinstance(payload.get("entries"), list)
    ):
        raise ValueError("invalid proxy inventory contract")

    expected_paths = {path.resolve() for path in _configured_proxy_paths(project_root)}
    inventory_paths: set[Path] = set()
    hashes: set[str] = set()
    for index, entry in enumerate(payload["entries"]):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ValueError(f"invalid proxy inventory entry: {index}")
        raw_path = entry.get("path")
        sha256 = entry.get("sha256")
        if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute():
            raise ValueError(f"invalid proxy inventory path: {index}")
        if not isinstance(sha256, str) or not LOWER_SHA256.fullmatch(sha256):
            raise ValueError(f"invalid proxy inventory sha256: {index}")
        path = (project_root / raw_path).resolve()
        if project_root not in path.parents or path in inventory_paths:
            raise ValueError(f"invalid proxy inventory path: {raw_path}")
        inventory_paths.add(path)
        hashes.add(sha256)
        if not path.is_file():
            raise ValueError(f"proxy inventory source is missing: {raw_path}")
        if _hash_file(path) != sha256:
            raise ValueError(f"proxy inventory hash mismatch: {raw_path}")

    if inventory_paths != expected_paths:
        raise ValueError("proxy inventory does not match configured proxy sources")
    return frozenset(hashes)


def proxy_inventory_sha256(project_root: Path) -> str:
    serialized = "\n".join(sorted(known_proxy_hashes(project_root))).encode("ascii")
    return hashlib.sha256(serialized).hexdigest()
