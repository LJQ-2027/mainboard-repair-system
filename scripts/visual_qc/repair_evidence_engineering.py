"""Deterministic board-asset and engineering-target resolution."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat

from scripts.visual_qc.repair_evidence_link_contract import canonical_sha256
from scripts.visual_qc.source_library import _is_reparse_or_symlink


CATALOG_PATH = "knowledge-base/repair-workbench-boards.json"
MAX_ASSET_BYTES = 128 * 1024 * 1024
MAX_POLYGON_POINTS = 256


class RepairEvidenceEngineeringError(ValueError):
    pass


def _error(message: str):
    raise RepairEvidenceEngineeringError(message)


def _strict_json_bytes(content: bytes, label: str) -> dict:
    def object_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _error(f"{label} contains duplicate field: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=object_hook,
            parse_constant=lambda token: _error(
                f"{label} contains non-finite number: {token}"
            ),
        )
    except RepairEvidenceEngineeringError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepairEvidenceEngineeringError(
            f"{label} is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        _error(f"{label} root must be an object")
    return value


def _repository_path(project_root: Path, raw_path: str, label: str) -> tuple[str, Path]:
    if not isinstance(raw_path, str) or not raw_path:
        _error(f"{label} is invalid")
    normalized = raw_path.replace("\\", "/")
    if normalized.startswith("../../knowledge-base/"):
        normalized = normalized[6:]
    pure = PurePosixPath(normalized)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        _error(f"{label} escapes project root")
    repository_path = pure.as_posix()
    candidate = project_root.joinpath(*pure.parts).absolute()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise RepairEvidenceEngineeringError(
            f"{label} escapes project root"
        ) from exc
    current = project_root
    for part in pure.parts:
        current = current / part
        if _is_reparse_or_symlink(current):
            _error(f"{label} contains a reparse point or symlink")
    return repository_path, candidate


def _read_stable_file(path: Path, label: str) -> bytes:
    if _is_reparse_or_symlink(path):
        _error(f"{label} contains a reparse point or symlink")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RepairEvidenceEngineeringError(f"{label} is missing") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > MAX_ASSET_BYTES
        ):
            _error(f"{label} is not one safe regular file")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_ASSET_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_ASSET_BYTES:
                _error(f"{label} exceeds the byte limit")
        after = os.fstat(descriptor)
        identity = lambda item: (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_nlink,
            getattr(item, "st_mtime_ns", None),
        )
        if identity(before) != identity(after) or total != after.st_size:
            _error(f"{label} changed while reading")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _load_asset(
    project_root: Path, raw_path: str, label: str
) -> tuple[str, dict, str]:
    repository_path, path = _repository_path(project_root, raw_path, label)
    content = _read_stable_file(path, label)
    return (
        repository_path,
        _strict_json_bytes(content, label),
        hashlib.sha256(content).hexdigest(),
    )


def _finite(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _error(f"{label} must be finite")
    number = float(value)
    if not math.isfinite(number):
        _error(f"{label} must be finite")
    return number


def _point(value: dict, label: str) -> dict:
    if not isinstance(value, dict) or set(value) != {"x", "y"}:
        _error(f"{label} is invalid")
    x = _finite(value["x"], f"{label}.x")
    y = _finite(value["y"], f"{label}.y")
    if not (0 <= x <= 1 and 0 <= y <= 1):
        _error(f"{label} is outside normalized bounds")
    return {"x": value["x"], "y": value["y"]}


def _orientation(a: dict, b: dict, c: dict) -> float:
    return (b["x"] - a["x"]) * (c["y"] - a["y"]) - (
        b["y"] - a["y"]
    ) * (c["x"] - a["x"])


def _on_segment(a: dict, b: dict, point: dict) -> bool:
    return (
        min(a["x"], b["x"]) - 1e-12
        <= point["x"]
        <= max(a["x"], b["x"]) + 1e-12
        and min(a["y"], b["y"]) - 1e-12
        <= point["y"]
        <= max(a["y"], b["y"]) + 1e-12
        and abs(_orientation(a, b, point)) <= 1e-12
    )


def _segments_intersect(a: dict, b: dict, c: dict, d: dict) -> bool:
    values = (
        _orientation(a, b, c),
        _orientation(a, b, d),
        _orientation(c, d, a),
        _orientation(c, d, b),
    )
    if (
        (values[0] > 0 > values[1] or values[1] > 0 > values[0])
        and (values[2] > 0 > values[3] or values[3] > 0 > values[2])
    ):
        return True
    return any(
        abs(value) <= 1e-12 and _on_segment(*segment)
        for value, segment in zip(
            values,
            ((a, b, c), (a, b, d), (c, d, a), (c, d, b)),
        )
    )


def _validate_region(region: dict) -> dict:
    if not isinstance(region, dict):
        _error("board region is invalid")
    if region.get("kind") == "normalized_rectangle":
        if set(region) != {"kind", "x", "y", "width", "height"}:
            _error("board rectangle fields are invalid")
        x = _finite(region["x"], "rectangle.x")
        y = _finite(region["y"], "rectangle.y")
        width = _finite(region["width"], "rectangle.width")
        height = _finite(region["height"], "rectangle.height")
        if (
            x < 0
            or y < 0
            or width <= 0
            or height <= 0
            or x + width > 1
            or y + height > 1
        ):
            _error("board rectangle is outside normalized bounds")
        return copy.deepcopy(region)
    if region.get("kind") != "normalized_polygon" or set(region) != {
        "kind",
        "points",
    }:
        _error("board region kind is invalid")
    points = region["points"]
    if (
        not isinstance(points, list)
        or len(points) < 3
        or len(points) > MAX_POLYGON_POINTS
    ):
        _error("board polygon point count is invalid")
    normalized = [_point(item, "polygon point") for item in points]
    area = abs(
        sum(
            normalized[index]["x"] * normalized[(index + 1) % len(normalized)]["y"]
            - normalized[(index + 1) % len(normalized)]["x"]
            * normalized[index]["y"]
            for index in range(len(normalized))
        )
        / 2
    )
    if area <= 1e-12:
        _error("board polygon is degenerate")
    count = len(normalized)
    for left in range(count):
        a, b = normalized[left], normalized[(left + 1) % count]
        for right in range(left + 1, count):
            if right in {left, (left + 1) % count} or (
                left == 0 and right == count - 1
            ):
                continue
            c, d = normalized[right], normalized[(right + 1) % count]
            if _segments_intersect(a, b, c, d):
                _error("board polygon is self-intersecting")
    return copy.deepcopy(region)


def _load_board_assets(project_root: Path, board_key: str) -> dict:
    project_root = Path(project_root).expanduser().absolute()
    catalog_path, catalog_file = _repository_path(
        project_root, CATALOG_PATH, "board catalog"
    )
    catalog_bytes = _read_stable_file(catalog_file, "board catalog")
    catalog = _strict_json_bytes(catalog_bytes, "board catalog")
    boards = catalog.get("boards")
    entry = boards.get(board_key) if isinstance(boards, dict) else None
    if not isinstance(entry, dict):
        _error(f"unknown board: {board_key}")

    side_path, side_manifest, side_sha = _load_asset(
        project_root, entry.get("side_manifest"), "side manifest"
    )
    board_id = side_manifest.get("board_id")
    sides = side_manifest.get("sides")
    if (
        side_manifest.get("profile_id") != board_key
        or not isinstance(board_id, str)
        or not isinstance(sides, list)
        or not sides
    ):
        _error("side manifest board identity is invalid")
    side_by_id = {}
    for side in sides:
        side_id = side.get("side_id") if isinstance(side, dict) else None
        if not isinstance(side_id, str) or side_id in side_by_id:
            _error("side manifest contains an invalid or duplicate side")
        side_by_id[side_id] = side

    cross_path, cross_source, cross_sha = _load_asset(
        project_root, entry.get("data"), "cross-source registration"
    )
    if (
        cross_source.get("board_id") != board_id
        or cross_source.get("side_id") not in side_by_id
        or not isinstance(cross_source.get("entities"), list)
    ):
        _error("cross-source board identity is invalid")

    compiled_sources = [
        {"kind": "side_manifest", "path": side_path, "sha256": side_sha},
        {
            "kind": "cross_source_registration",
            "path": cross_path,
            "sha256": cross_sha,
        },
    ]
    geometry_by_side = entry.get("geometry_by_side")
    if (
        not isinstance(geometry_by_side, dict)
        or set(geometry_by_side) != set(side_by_id)
    ):
        _error("catalog geometry sides do not match side manifest")
    geometry = {}
    for side_id in sorted(geometry_by_side):
        path, payload, digest = _load_asset(
            project_root,
            geometry_by_side[side_id],
            f"compiled geometry {side_id}",
        )
        if payload.get("board_id") != board_id or payload.get("side_id") != side_id:
            _error("compiled geometry board identity is invalid")
        manifest_compiled_path, _ = _repository_path(
            project_root,
            side_by_id[side_id].get("compiled_data"),
            f"side compiled geometry {side_id}",
        )
        if manifest_compiled_path != path:
            _error("side manifest compiled geometry path does not match catalog")
        geometry[side_id] = payload
        compiled_sources.append(
            {
                "kind": f"compiled_geometry_{side_id}",
                "path": path,
                "sha256": digest,
            }
        )

    return {
        "project_root": project_root,
        "entry": copy.deepcopy(entry),
        "board_id": board_id,
        "side_by_id": side_by_id,
        "cross_source": cross_source,
        "geometry": geometry,
        "snapshot": {
            "board_key": board_key,
            "board_id": board_id,
            "catalog_asset": {
                "path": catalog_path,
                "sha256": hashlib.sha256(catalog_bytes).hexdigest(),
                "entry_sha256": canonical_sha256(entry),
            },
            "compiled_sources": compiled_sources,
            "board_snapshot_sha256": "",
        },
    }


def load_board_asset_context(project_root: Path, board_key: str) -> dict:
    return _load_board_assets(project_root, board_key)


def board_asset_snapshot_from_context(assets: dict) -> dict:
    snapshot = assets["snapshot"]
    snapshot["board_snapshot_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in snapshot.items()
            if key != "board_snapshot_sha256"
        }
    )
    return copy.deepcopy(snapshot)


def resolve_board_asset_snapshot(project_root: Path, board_key: str) -> dict:
    return board_asset_snapshot_from_context(
        load_board_asset_context(project_root, board_key)
    )


def _engineering_descriptors(entity: dict) -> list[str]:
    descriptors = []
    links = entity.get("schematic_links")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            source = link.get("source")
            page = link.get("page")
            facts = link.get("facts")
            if (
                isinstance(source, str)
                and isinstance(page, str)
                and isinstance(facts, list)
            ):
                for fact in facts:
                    if isinstance(fact, str) and fact.strip():
                        descriptors.append(f"{source} · page {page} · {fact}")
    if not descriptors:
        _error("designator lacks reviewed engineering evidence")
    if len(descriptors) != len(set(descriptors)):
        _error("engineering evidence descriptors are duplicated")
    return descriptors


def resolve_engineering_target_from_context(
    assets: dict, *, target: dict
) -> dict:
    if not isinstance(target, dict):
        _error("engineering target is invalid")
    side_id = target.get("side_id")
    if side_id not in assets["side_by_id"]:
        _error("target board side is unknown")
    kind = target.get("kind")
    if kind == "whole_board":
        if set(target) != {"kind", "side_id"}:
            _error("whole-board target fields are invalid")
        return copy.deepcopy(target)
    if kind == "board_region":
        if set(target) != {"kind", "side_id", "region"}:
            _error("board-region target fields are invalid")
        return {
            "kind": "board_region",
            "side_id": side_id,
            "region": _validate_region(target["region"]),
        }
    if kind != "designator" or set(target) != {
        "kind",
        "side_id",
        "designator",
    }:
        _error("engineering target kind or fields are invalid")
    designator = target["designator"]
    if not isinstance(designator, str) or not designator:
        _error("designator is invalid")
    matches = [
        entity
        for entity in assets["cross_source"]["entities"]
        if isinstance(entity, dict) and entity.get("designator") == designator
    ]
    if len(matches) != 1:
        _error("designator is missing or duplicated")
    entity = matches[0]
    if entity.get("side_id") != side_id:
        _error("designator belongs to another board side")
    compiled_matches = [
        item
        for item in assets["geometry"][side_id].get("components", [])
        if isinstance(item, dict) and item.get("designator") == designator
    ]
    if len(compiled_matches) != 1:
        _error("compiled designator geometry is missing or duplicated")
    compiled = compiled_matches[0]
    component_id = entity.get("component_id")
    category = entity.get("category")
    geometry = entity.get("geometry")
    if (
        not isinstance(component_id, str)
        or not component_id
        or not isinstance(category, str)
        or not category
        or not isinstance(geometry, dict)
    ):
        _error("designator engineering identity is invalid")
    status = geometry.get("source_status")
    if status not in {"high", "medium", "low"}:
        _error("designator geometry source status is invalid")
    center = _point(geometry.get("center"), "designator center")
    compiled_center = _point(compiled.get("center"), "compiled designator center")
    if compiled_center != center:
        _error("reviewed and compiled designator locations disagree")
    compiled_footprint = compiled.get("footprint")
    if (
        status == "low"
        and isinstance(compiled_footprint, dict)
        and compiled_footprint.get("confidence") not in {None, "low"}
    ):
        _error("low-confidence designator has contradictory footprint status")
    if status == "low":
        location = {"kind": "normalized_point", "point": center}
    else:
        size = geometry.get("size")
        if not isinstance(size, dict) or set(size) != {"x", "y"}:
            _error("designator footprint size is invalid")
        width = _finite(size["x"], "designator width")
        height = _finite(size["y"], "designator height")
        rectangle = {
            "kind": "normalized_rectangle",
            "x": center["x"] - width / 2,
            "y": center["y"] - height / 2,
            "width": width,
            "height": height,
        }
        _validate_region(rectangle)
        location = {
            "kind": "normalized_footprint",
            "rectangle": {
                key: value for key, value in rectangle.items() if key != "kind"
            },
        }
    descriptors = _engineering_descriptors(entity)
    semantic_evidence = entity.get("semantic_identity_evidence")
    semantic_identity_proven = (
        isinstance(semantic_evidence, list)
        and bool(semantic_evidence)
        and all(isinstance(item, str) and item.strip() for item in semantic_evidence)
    )
    snapshot = {
        "component_id": component_id,
        "designator": designator,
        "side_id": side_id,
        "technician_category": category,
        "location": location,
        "evidence_descriptors": descriptors,
        "geometry_source_status": status,
        "semantic_identity_proven": semantic_identity_proven,
        "engineering_snapshot_sha256": "",
    }
    snapshot["engineering_snapshot_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in snapshot.items()
            if key not in {"side_id", "engineering_snapshot_sha256"}
        }
    )
    return snapshot


def resolve_engineering_target(
    *, project_root: Path, board_key: str, target: dict
) -> dict:
    return resolve_engineering_target_from_context(
        load_board_asset_context(project_root, board_key),
        target=target,
    )
