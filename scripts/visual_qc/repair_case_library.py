from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import stat
import tempfile
import zipfile

from scripts.visual_qc.intake import IntakeValidationError, _require_safe_id
from scripts.visual_qc.repair_case_contract import (
    MAX_SUPPORTING_FILE_BYTES,
    MAX_SUPPORTING_FILES,
    MIME_EXTENSIONS,
)
from scripts.visual_qc.server.storage import detect_image_mime_type
from scripts.visual_qc.source_library import (
    _assert_controlled_path,
    _ensure_directory_durable,
    _fsync_directory,
    _is_reparse_or_symlink,
    _resolve_library_root,
    validate_source_package,
)


ROLE_CAPTURE_STAGE = {
    "before_repair": "before_repair",
    "after_repair": "after_repair",
    "golden_reference": "golden_reference",
}


def resolve_package_links(
    *,
    project_root: Path,
    library_root: Path,
    assignments: list[tuple[str, Path]],
    board_key: str,
) -> list[dict]:
    if not isinstance(assignments, list) or not assignments:
        raise IntakeValidationError("at least one source package is required")
    board_key = _require_safe_id(board_key, "board_key")
    links = []
    seen_packages: set[str] = set()
    for role, package_path in assignments:
        if role not in {*ROLE_CAPTURE_STAGE, "supplemental"}:
            raise IntakeValidationError(f"invalid repair case package role: {role}")
        package = validate_source_package(
            Path(package_path), Path(project_root), Path(library_root)
        )
        package_id = package["package_id"]
        if package_id in seen_packages:
            raise IntakeValidationError(
                f"duplicate repair case source package: {package_id}"
            )
        seen_packages.add(package_id)
        if package["board_key"] != board_key:
            raise IntakeValidationError(
                f"source package board does not match repair case: {package_id}"
            )
        expected_stage = ROLE_CAPTURE_STAGE.get(role)
        if expected_stage is not None and package["capture_stage"] != expected_stage:
            raise IntakeValidationError(
                f"source package role does not match capture stage: {package_id}"
            )
        links.append(
            {
                "package_id": package_id,
                "source_package_manifest_sha256": package["manifest_sha256"],
                "capture_stage": package["capture_stage"],
                "role": role,
                "entry_ids": [entry["entry_id"] for entry in package["entries"]],
            }
        )
    return links


def _assert_regular_source(path: Path) -> Path:
    path = Path(path).expanduser().absolute()
    current = path
    while current != current.parent:
        if _is_reparse_or_symlink(current):
            raise IntakeValidationError(
                f"supporting source contains a reparse point or symlink: {current}"
            )
        current = current.parent
    return path


def _read_stable_supporting_file(path: Path) -> bytes:
    path = _assert_regular_source(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise IntakeValidationError(
            f"unable to open supporting source: {path}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise IntakeValidationError(
                f"supporting source must be one regular non-hard-linked file: {path}"
            )
        if before.st_size < 1 or before.st_size > MAX_SUPPORTING_FILE_BYTES:
            raise IntakeValidationError(
                f"supporting source size is invalid: {path}"
            )
        chunks = []
        byte_size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            byte_size += len(chunk)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            getattr(before, "st_mtime_ns", None),
            before.st_nlink,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            getattr(after, "st_mtime_ns", None),
            after.st_nlink,
        )
        if identity_before != identity_after or byte_size != after.st_size:
            raise IntakeValidationError(
                f"supporting source changed while reading: {path}"
            )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _detect_supporting_mime(path: Path, content: bytes) -> str:
    extension = path.suffix.lower()
    image_mime = detect_image_mime_type(content)
    if extension == ".pdf" and content.startswith(b"%PDF-"):
        return "application/pdf"
    if extension in {".txt", ".csv"}:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IntakeValidationError(
                f"supporting text must be UTF-8: {path}"
            ) from exc
        if b"\x00" in content:
            raise IntakeValidationError(
                f"supporting text contains null bytes: {path}"
            )
        return "text/csv" if extension == ".csv" else "text/plain"
    if extension == ".xls" and content.startswith(
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    ):
        return "application/vnd.ms-excel"
    if extension == ".xlsx" and content.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as workbook:
                names = set(workbook.namelist())
        except (OSError, zipfile.BadZipFile) as exc:
            raise IntakeValidationError(
                f"supporting XLSX container is invalid: {path}"
            ) from exc
        if {
            "[Content_Types].xml",
            "xl/workbook.xml",
        }.issubset(names):
            return (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
    if extension == ".png" and image_mime == "image/png":
        return "image/png"
    if extension in {".jpg", ".jpeg"} and image_mime == "image/jpeg":
        return "image/jpeg"
    raise IntakeValidationError(f"unsupported supporting evidence format: {path}")


def inspect_supporting_evidence(
    assignments: list[tuple[str, Path]],
    descriptions: dict[str, str],
) -> list[dict]:
    if not isinstance(assignments, list) or len(assignments) > MAX_SUPPORTING_FILES:
        raise IntakeValidationError(
            f"supporting files may contain at most {MAX_SUPPORTING_FILES} records"
        )
    if not isinstance(descriptions, dict):
        raise IntakeValidationError("supporting evidence descriptions are invalid")
    inspected = []
    seen_ids: set[str] = set()
    for evidence_id, raw_path in assignments:
        evidence_id = _require_safe_id(evidence_id, "evidence_id")
        if evidence_id in seen_ids:
            raise IntakeValidationError(
                f"duplicate supporting evidence_id: {evidence_id}"
            )
        seen_ids.add(evidence_id)
        description = descriptions.get(evidence_id)
        if not isinstance(description, str) or not description.strip():
            raise IntakeValidationError(
                f"supporting evidence description is required: {evidence_id}"
            )
        path = Path(raw_path).expanduser()
        content = _read_stable_supporting_file(path)
        mime_type = _detect_supporting_mime(path, content)
        digest = hashlib.sha256(content).hexdigest()
        extension = MIME_EXTENSIONS[mime_type]
        inspected.append(
            {
                "record": {
                    "evidence_id": evidence_id,
                    "original_filename": path.name,
                    "object_path": (
                        f"objects/case-evidence/{digest[:2]}/"
                        f"{digest}{extension}"
                    ),
                    "mime_type": mime_type,
                    "byte_size": len(content),
                    "sha256": digest,
                    "description": description,
                },
                "content": content,
            }
        )
    extra_descriptions = set(descriptions) - seen_ids
    if extra_descriptions:
        raise IntakeValidationError(
            "supporting evidence descriptions contain unknown IDs"
        )
    return inspected


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_stored_object(path: Path, expected_sha256: str) -> None:
    if _is_reparse_or_symlink(path):
        raise IntakeValidationError(
            f"supporting evidence object is a reparse point or symlink: {path}"
        )
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise IntakeValidationError(
            f"supporting evidence object is missing: {path}"
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise IntakeValidationError(
            f"supporting evidence object is not a regular file: {path}"
        )
    if _hash_file(path) != expected_sha256:
        raise IntakeValidationError(
            f"supporting evidence object integrity mismatch: {path}"
        )


def store_supporting_evidence(
    *,
    library_root: Path,
    inspected: list[dict],
) -> None:
    project_placeholder = Path.cwd()
    library_root = _resolve_library_root(project_placeholder, library_root)
    _ensure_directory_durable(library_root)
    for item in inspected:
        record = item["record"]
        content = item["content"]
        destination = _assert_controlled_path(
            library_root,
            library_root / record["object_path"],
            "supporting evidence object path",
        )
        if destination.exists():
            _assert_stored_object(destination, record["sha256"])
            continue
        _ensure_directory_durable(destination.parent)
        _assert_controlled_path(
            library_root, destination, "supporting evidence object path"
        )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{record['sha256']}.",
            suffix=".staging",
            dir=destination.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            if _hash_file(temporary_path) != record["sha256"]:
                raise IntakeValidationError(
                    "supporting evidence changed before publication"
                )
            try:
                os.link(temporary_path, destination)
            except FileExistsError:
                _assert_stored_object(destination, record["sha256"])
            temporary_path.unlink(missing_ok=True)
            _assert_controlled_path(
                library_root, destination, "supporting evidence object path"
            )
            _assert_stored_object(destination, record["sha256"])
            _fsync_directory(destination.parent)
        finally:
            temporary_path.unlink(missing_ok=True)
