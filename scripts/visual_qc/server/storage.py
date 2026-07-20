from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import tempfile
import threading

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class StorageError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class StorageCleanupError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        deleted_objects: int,
        deleted_bytes: int,
    ):
        super().__init__(message)
        self.deleted_objects = deleted_objects
        self.deleted_bytes = deleted_bytes


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
        self._lock = threading.RLock()
        self.reference_lock_path = self.data_root / ".storage-reference.lock"
        self.originals_root = self.data_root / "objects" / "originals"
        self.artifacts_root = self.data_root / "objects" / "artifacts"
        self.originals_root.mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def reference_transaction(self):
        with self._lock:
            self.reference_lock_path.parent.mkdir(parents=True, exist_ok=True)
            with self.reference_lock_path.open("a+b") as handle:
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                self._lock_reference_file(handle)
                try:
                    yield
                finally:
                    handle.seek(0)
                    self._unlock_reference_file(handle)

    def put_original(self, content: bytes, sha256: str, mime_type: str) -> Path:
        extension = MIME_EXTENSIONS.get(mime_type)
        if not extension:
            raise StorageError("unsupported_mime_type", f"Unsupported MIME type: {mime_type}")

        with self._lock:
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
        with self._lock:
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

    def health(self, warning_free_bytes: int) -> dict:
        usage = shutil.disk_usage(self.data_root)
        warning_threshold = max(self.minimum_free_bytes, warning_free_bytes)
        if usage.free < self.minimum_free_bytes:
            pressure = "critical"
        elif usage.free < warning_threshold:
            pressure = "warning"
        else:
            pressure = "normal"
        return {
            "pressure": pressure,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "minimum_free_bytes": self.minimum_free_bytes,
            "warning_free_bytes": warning_threshold,
            "objects": self._object_usage(),
        }

    def delete_unreferenced(self, paths: list[str], is_referenced) -> dict:
        deleted_objects = 0
        deleted_bytes = 0
        try:
            for value in sorted(set(paths)):
                path = Path(value).resolve()
                if not self._is_managed(path) or is_referenced(str(path)) or not path.is_file():
                    continue
                byte_size = path.stat().st_size
                path.unlink()
                deleted_objects += 1
                deleted_bytes += byte_size
                if path.parent != self.originals_root and path.parent != self.artifacts_root:
                    try:
                        path.parent.rmdir()
                    except OSError:
                        pass
        except Exception as exc:
            raise StorageCleanupError(
                str(exc),
                deleted_objects=deleted_objects,
                deleted_bytes=deleted_bytes,
            ) from exc
        return {
            "deleted_objects": deleted_objects,
            "deleted_bytes": deleted_bytes,
        }

    def _object_usage(self) -> dict:
        result = {}
        for name, root in (
            ("originals", self.originals_root),
            ("artifacts", self.artifacts_root),
        ):
            files = [path for path in root.rglob("*") if path.is_file()]
            result[name] = {
                "files": len(files),
                "bytes": sum(path.stat().st_size for path in files),
            }
        return result

    def _is_managed(self, path: Path) -> bool:
        return any(
            path == root or root in path.parents
            for root in (self.originals_root, self.artifacts_root)
        )

    @staticmethod
    def _lock_reference_file(handle):
        if os.name == "nt":
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    @staticmethod
    def _unlock_reference_file(handle):
        if os.name == "nt":
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _ensure_capacity(self, incoming_bytes: int):
        free_bytes = shutil.disk_usage(self.data_root).free
        if free_bytes - incoming_bytes < self.minimum_free_bytes:
            raise StorageError(
                "insufficient_storage",
                "Server free-space reserve would be exceeded by this write.",
            )
