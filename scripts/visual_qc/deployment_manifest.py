from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import tarfile


DEPLOYMENT_MANIFEST_SCHEMA_VERSION = "VISUAL-QC-DEPLOYMENT-MANIFEST-V1"
FULL_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "commit_sha",
        "archive_sha256",
        "archive_bytes",
        "runtime_manifest_sha256",
        "runtime_path_count",
    }
)
RUNTIME_MANIFEST_ARCHIVE_PATH = "deploy/visual-qc-runtime-files.txt"


def _hash_regular_file(path: Path) -> dict:
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"Expected a regular file: {path}")
        digest = hashlib.sha256()
        byte_size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            byte_size += len(chunk)
        after = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            getattr(before, "st_mtime_ns", None),
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            getattr(after, "st_mtime_ns", None),
        )
        if before_identity != after_identity or byte_size != after.st_size:
            raise ValueError(f"File changed while hashing: {path}")
        return {"sha256": digest.hexdigest(), "byte_size": byte_size}
    finally:
        os.close(descriptor)


def _read_regular_file(path: Path) -> bytes:
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"Expected a regular file: {path}")
        chunks = []
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            getattr(before, "st_mtime_ns", None),
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            getattr(after, "st_mtime_ns", None),
        ):
            raise ValueError(f"File changed while reading: {path}")
        content = b"".join(chunks)
        if len(content) != after.st_size:
            raise ValueError(f"File changed while reading: {path}")
        return content
    finally:
        os.close(descriptor)


def _parse_runtime_paths(content: bytes) -> list[str]:
    if not content:
        raise ValueError("Runtime manifest must not be empty.")
    try:
        text = content.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Runtime manifest must be valid UTF-8.") from exc
    paths = []
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if (
            RUNTIME_PATH_PATTERN.fullmatch(value) is None
            or value.startswith("/")
            or "\\" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
        ):
            raise ValueError(f"Unsafe runtime path: {value}")
        paths.append(value)
    if not paths:
        raise ValueError("Runtime manifest contains no runtime paths.")
    if len(set(paths)) != len(paths):
        raise ValueError("Runtime manifest contains duplicate paths.")
    return paths


def normalized_runtime_paths(runtime_manifest: Path) -> list[str]:
    return _parse_runtime_paths(_read_regular_file(runtime_manifest))


def _read_archived_runtime_manifest(archive: Path) -> bytes:
    matches = []
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            for member in bundle:
                if member.name == RUNTIME_MANIFEST_ARCHIVE_PATH:
                    matches.append(member)
            if len(matches) != 1 or not matches[0].isfile():
                raise ValueError(
                    "Runtime archive must contain one regular path manifest."
                )
            source = bundle.extractfile(matches[0])
            if source is None:
                raise ValueError(
                    "Runtime archive path manifest cannot be read."
                )
            content = source.read()
    except (OSError, tarfile.TarError) as exc:
        raise ValueError("Runtime archive must be a valid gzip tar file.") from exc
    if len(content) != matches[0].size:
        raise ValueError("Runtime archive path manifest changed while reading.")
    return content


def validate_deployment_manifest(manifest: dict) -> dict:
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        raise ValueError("Deployment manifest must contain the exact V1 fields.")
    if manifest["schema_version"] != DEPLOYMENT_MANIFEST_SCHEMA_VERSION:
        raise ValueError("Deployment manifest schema version is invalid.")
    if (
        not isinstance(manifest["commit_sha"], str)
        or FULL_COMMIT_PATTERN.fullmatch(manifest["commit_sha"]) is None
    ):
        raise ValueError("Commit SHA must be 40-character lowercase hexadecimal.")
    for field in ("archive_sha256", "runtime_manifest_sha256"):
        value = manifest[field]
        if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(f"{field} must be lowercase SHA-256.")
    for field in ("archive_bytes", "runtime_path_count"):
        value = manifest[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{field} must be a positive integer.")
    return dict(manifest)


def build_deployment_manifest(
    *,
    archive: Path,
    runtime_manifest: Path,
    commit_sha: str,
) -> dict:
    if not isinstance(commit_sha, str) or FULL_COMMIT_PATTERN.fullmatch(
        commit_sha
    ) is None:
        raise ValueError("Commit SHA must be 40-character lowercase hexadecimal.")
    archive_evidence = _hash_regular_file(archive)
    if archive_evidence["byte_size"] == 0:
        raise ValueError("Runtime archive must not be empty.")
    local_runtime_content = _read_regular_file(runtime_manifest)
    local_runtime_paths = _parse_runtime_paths(local_runtime_content)
    archived_runtime_content = _read_archived_runtime_manifest(archive)
    archived_runtime_paths = _parse_runtime_paths(archived_runtime_content)
    if archived_runtime_paths != local_runtime_paths:
        raise ValueError(
            "Archived runtime path list does not match the local manifest."
        )
    return validate_deployment_manifest(
        {
            "schema_version": DEPLOYMENT_MANIFEST_SCHEMA_VERSION,
            "commit_sha": commit_sha,
            "archive_sha256": archive_evidence["sha256"],
            "archive_bytes": archive_evidence["byte_size"],
            "runtime_manifest_sha256": hashlib.sha256(
                archived_runtime_content
            ).hexdigest(),
            "runtime_path_count": len(archived_runtime_paths),
        }
    )
