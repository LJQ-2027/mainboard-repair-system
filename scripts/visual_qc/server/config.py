from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class VisualQcServerSettings:
    project_root: Path
    data_root: Path
    maximum_upload_bytes: int = 20 * 1024 * 1024
    minimum_image_dimension: int = 480
    minimum_free_bytes: int = 2 * 1024 * 1024 * 1024
    warning_free_bytes: int = 4 * 1024 * 1024 * 1024
    retention_days: int = 90
    retention_batch_limit: int = 100
    worker_count: int = 1
    allowed_origins: tuple[str, ...] = ()

    @classmethod
    def from_environment(cls) -> "VisualQcServerSettings":
        project_root = Path(__file__).resolve().parents[3]
        return cls(
            project_root=Path(os.environ.get("VISUAL_QC_PROJECT_ROOT", project_root)).resolve(),
            data_root=Path(
                os.environ.get("VISUAL_QC_DATA_ROOT", project_root / ".local" / "visual-qc-server")
            ).resolve(),
            maximum_upload_bytes=int(
                os.environ.get("VISUAL_QC_MAX_UPLOAD_BYTES", 20 * 1024 * 1024)
            ),
            minimum_image_dimension=int(
                os.environ.get("VISUAL_QC_MIN_IMAGE_DIMENSION", 480)
            ),
            minimum_free_bytes=int(
                os.environ.get("VISUAL_QC_MIN_FREE_BYTES", 2 * 1024 * 1024 * 1024)
            ),
            warning_free_bytes=int(
                os.environ.get("VISUAL_QC_WARNING_FREE_BYTES", 4 * 1024 * 1024 * 1024)
            ),
            retention_days=max(1, int(os.environ.get("VISUAL_QC_RETENTION_DAYS", "90"))),
            retention_batch_limit=max(
                1,
                min(1000, int(os.environ.get("VISUAL_QC_RETENTION_BATCH_LIMIT", "100"))),
            ),
            worker_count=max(0, min(2, int(os.environ.get("VISUAL_QC_WORKERS", "1")))),
            allowed_origins=tuple(
                origin.strip()
                for origin in os.environ.get("VISUAL_QC_ALLOWED_ORIGINS", "").split(",")
                if origin.strip()
            ),
        )
