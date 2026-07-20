from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile


class StorageError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def detect_image_mime_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


class LocalObjectStorage:
    def __init__(self, data_root: Path, minimum_free_bytes: int):
        self.data_root = data_root.resolve()
        self.minimum_free_bytes = minimum_free_bytes
        self.originals_root = self.data_root / "objects" / "originals"
        self.artifacts_root = self.data_root / "objects" / "artifacts"
        self.originals_root.mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)

    def put_original(self, content: bytes, sha256: str, mime_type: str) -> Path:
        extension = MIME_EXTENSIONS.get(mime_type)
        if not extension:
            raise StorageError("unsupported_mime_type", f"Unsupported MIME type: {mime_type}")

        self._ensure_capacity(len(content))

        destination = self.originals_root / sha256[:2] / f"{sha256}{extension}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            return destination

        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{sha256}.",
            suffix=".upload",
            dir=destination.parent,
        )
        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return destination

    def put_artifact(self, content: bytes, sha256: str, extension: str) -> Path:
        if extension not in {".png", ".json"}:
            raise StorageError("unsupported_artifact_type", "Unsupported artifact type.")
        self._ensure_capacity(len(content))
        destination = self.artifacts_root / sha256[:2] / f"{sha256}{extension}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            return destination
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{sha256}.",
            suffix=".artifact",
            dir=destination.parent,
        )
        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return destination

    def _ensure_capacity(self, incoming_bytes: int):
        free_bytes = shutil.disk_usage(self.data_root).free
        if free_bytes - incoming_bytes < self.minimum_free_bytes:
            raise StorageError(
                "insufficient_storage",
                "Server free-space reserve would be exceeded by this write.",
            )
