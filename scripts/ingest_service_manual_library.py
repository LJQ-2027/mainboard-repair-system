#!/usr/bin/env python3
"""Ingest a local service-manual folder into the project material library."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional verification dependency
    Image = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional verification dependency
    PdfReader = None


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"}
MODEL_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?:X\d{3,5}[A-Z]?|[A-Z]{1,4}\d{1,5}[A-Z]*|7C(?:_PRO)?|8H)(?![A-Z0-9])",
    re.IGNORECASE,
)
MODEL_STOPWORDS = {"V1", "V2", "V10", "V20"}
MAINBOARD_TERMS = (
    "mainboard",
    "main board",
    "motherboard",
    "pcb",
    "schematic",
    "circuit",
    "block diagram",
    "board layout",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_models(relative_path: str) -> list[str]:
    normalized = relative_path.upper().replace("SERVICE MANUAL", "")
    models = []
    for candidate in MODEL_PATTERN.findall(normalized):
        candidate = candidate.upper()
        if candidate not in MODEL_STOPWORDS and candidate not in models:
            models.append(candidate)
    return models


def inspect_pdf(path: Path) -> dict:
    if PdfReader is None:
        return {"parse_status": "dependency_missing", "parser": "pypdf"}
    try:
        reader = PdfReader(str(path), strict=False)
        text_parts = []
        for page in reader.pages[: min(12, len(reader.pages))]:
            text_parts.append(page.extract_text() or "")
        sample = " ".join(text_parts)
        sample_lower = sample.lower()
        return {
            "parse_status": "ok",
            "page_count": len(reader.pages),
            "sample_text_chars": len(sample),
            "mainboard_terms": [term for term in MAINBOARD_TERMS if term in sample_lower],
        }
    except Exception as exc:  # pragma: no cover - source-dependent corruption
        return {"parse_status": "error", "error": f"{type(exc).__name__}: {exc}"}


def inspect_docx(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            names = set(archive.namelist())
            document_xml = archive.read("word/document.xml") if "word/document.xml" in names else b""
        sample = document_xml[: 2 * 1024 * 1024].decode("utf-8", errors="ignore").lower()
        return {
            "parse_status": "ok" if bad_member is None and document_xml else "error",
            "zip_bad_member": bad_member,
            "document_xml_bytes": len(document_xml),
            "mainboard_terms": [term for term in MAINBOARD_TERMS if term in sample],
        }
    except Exception as exc:
        return {"parse_status": "error", "error": f"{type(exc).__name__}: {exc}"}


def inspect_doc(path: Path) -> dict:
    with path.open("rb") as stream:
        signature = stream.read(8)
    ole_signature = bytes.fromhex("D0CF11E0A1B11AE1")
    return {
        "parse_status": "ok" if signature == ole_signature else "error",
        "format": "ole_compound_document",
    }


def inspect_image(path: Path) -> dict:
    if Image is None:
        return {"parse_status": "dependency_missing", "parser": "Pillow"}
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            image_format = image.format
        return {
            "parse_status": "ok",
            "width": width,
            "height": height,
            "format": image_format,
        }
    except Exception as exc:
        return {"parse_status": "error", "error": f"{type(exc).__name__}: {exc}"}


def inspect_file(path: Path) -> dict:
    extension = path.suffix.lower()
    if extension == ".pdf":
        return inspect_pdf(path)
    if extension == ".docx":
        return inspect_docx(path)
    if extension == ".doc":
        return inspect_doc(path)
    if extension in {".jpg", ".jpeg", ".png"}:
        return inspect_image(path)
    return {"parse_status": "unsupported"}


def preferred_source(paths: list[Path], source_root: Path) -> Path:
    return sorted(
        paths,
        key=lambda path: (
            len(path.relative_to(source_root).parts),
            str(path.relative_to(source_root)).lower(),
        ),
    )[0]


def write_intake_doc(path: Path, manifest: dict) -> None:
    stats = manifest["statistics"]
    overlaps = manifest["project_overlap_models"]
    lines = [
        "# Service Manual Library Intake - 2026-07-10",
        "",
        "## Source",
        "",
        f"- Original folder: `{manifest['source_root']}`",
        f"- Project-local binary library: `{manifest['storage_root']}`",
        "- Binary policy: local project copy, excluded from Git history",
        "- Integrity: SHA-256 recorded for every source and stored file",
        "",
        "## Inventory",
        "",
        f"- Source entries: {stats['source_file_count']}",
        f"- Unique files stored: {stats['unique_file_count']}",
        f"- Exact duplicate groups: {stats['duplicate_group_count']}",
        f"- Unique size: {stats['unique_size_bytes'] / 1024 / 1024 / 1024:.3f} GB",
        f"- Parseable files: {stats['parse_status_counts'].get('ok', 0)}",
        f"- Parse errors: {stats['parse_status_counts'].get('error', 0)}",
        "",
        "## Project Overlap",
        "",
        "These manuals overlap models already present in the repair project:",
        "",
        *[f"- `{model}`" for model in overlaps],
        "",
        "## Use In The Project",
        "",
        "The library is a new service-manual source layer. It can contribute:",
        "",
        "- board and sub-board photographs embedded in service manuals;",
        "- disassembly order and connector locations;",
        "- module names and parts-placement context;",
        "- model aliases and visual references for board-photo recognition;",
        "- training and repair-context material complementary to schematics and point maps.",
        "",
        "Service manuals do not replace placement drawings or schematics. Extracted claims must retain the source file and page reference.",
        "",
        "## Next Extraction Priority",
        "",
        "1. KM4, KL4, CLA5, KJ5, CM5, CM6, and X6880 overlap with existing structured models.",
        "2. Extract board-photo pages and model/board identifiers from those manuals first.",
        "3. Build reference-image candidates for the visual-recognition demo.",
        "4. Add newly covered models only after their model aliases and board versions are identified.",
        "",
        "The complete per-file inventory, hashes, duplicate mappings, model tags, and parse checks are stored in `knowledge-base/service-manual-library-2026-07-10.json`.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--batch-id", default="2026-07-10-desktop-manual")
    parser.add_argument("--received-date", default="2026-07-10")
    args = parser.parse_args()

    source_root = args.source.resolve()
    project_root = args.project_root.resolve()
    storage_root = project_root / "source-materials" / "service-manual-library" / args.batch_id / "files"
    manifest_path = project_root / "knowledge-base" / "service-manual-library-2026-07-10.json"
    intake_path = project_root / "docs" / "service-manual-library-intake-2026-07-10.md"

    if not source_root.is_dir():
        raise SystemExit(f"Source folder does not exist: {source_root}")

    source_files = sorted(
        (path for path in source_root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=lambda path: str(path.relative_to(source_root)).lower(),
    )
    if not source_files:
        raise SystemExit("No supported files found")

    by_hash: dict[str, list[Path]] = defaultdict(list)
    file_hashes: dict[Path, str] = {}
    for path in source_files:
        digest = sha256(path)
        file_hashes[path] = digest
        by_hash[digest].append(path)

    storage_root.mkdir(parents=True, exist_ok=True)
    stored_by_hash: dict[str, str] = {}
    for digest, paths in sorted(by_hash.items()):
        source_path = preferred_source(paths, source_root)
        relative_path = source_path.relative_to(source_root)
        destination = storage_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or sha256(destination) != digest:
            shutil.copy2(source_path, destination)
        if sha256(destination) != digest:
            raise RuntimeError(f"Stored file hash mismatch: {destination}")
        stored_by_hash[digest] = destination.relative_to(project_root).as_posix()

    records = []
    for path in source_files:
        digest = file_hashes[path]
        relative_path = path.relative_to(source_root).as_posix()
        inspection = inspect_file(path)
        records.append(
            {
                "source_relative_path": relative_path,
                "stored_path": stored_by_hash[digest],
                "file_name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "sha256": digest,
                "is_exact_duplicate": len(by_hash[digest]) > 1,
                "duplicate_source_paths": [
                    item.relative_to(source_root).as_posix() for item in by_hash[digest] if item != path
                ],
                "models": extract_models(relative_path),
                "inspection": inspection,
            }
        )

    model_counts = Counter(model for record in records for model in record["models"])
    parse_counts = Counter(record["inspection"].get("parse_status", "unknown") for record in records)
    extension_counts = Counter(record["extension"] for record in records)
    current_models = {"KJ5", "KL4", "CLA5", "X6880", "CM5", "CM6", "KM4"}
    overlaps = sorted(current_models.intersection(model_counts))

    manifest = {
        "inventory_id": "SERVICE-MANUAL-LIBRARY-20260710",
        "title": "Desktop service manual library intake",
        "received_date": args.received_date,
        "source_root": str(source_root),
        "storage_root": storage_root.relative_to(project_root).as_posix(),
        "binary_policy": "project-local copy excluded from Git; manifest and intake record are Git-tracked",
        "statistics": {
            "source_file_count": len(records),
            "unique_file_count": len(by_hash),
            "duplicate_group_count": sum(1 for paths in by_hash.values() if len(paths) > 1),
            "unique_size_bytes": sum(paths[0].stat().st_size for paths in by_hash.values()),
            "extension_counts": dict(sorted(extension_counts.items())),
            "parse_status_counts": dict(sorted(parse_counts.items())),
        },
        "project_overlap_models": overlaps,
        "model_counts": dict(sorted(model_counts.items())),
        "files": records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_intake_doc(intake_path, manifest)

    print(json.dumps(manifest["statistics"], ensure_ascii=False, indent=2))
    print(f"Project overlap: {', '.join(overlaps)}")
    print(f"Manifest: {manifest_path}")
    print(f"Intake record: {intake_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
