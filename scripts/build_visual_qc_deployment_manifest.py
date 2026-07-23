from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.deployment_manifest import build_deployment_manifest
from scripts.visual_qc.source_library import _fsync_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a byte-bound Visual-QC deployment manifest."
    )
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--runtime-manifest", required=True, type=Path)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def publish_manifest(output: Path, manifest: dict) -> None:
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Output deployment manifest already exists.")
    output.parent.mkdir(parents=True, exist_ok=True)
    content = (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, output)
        except FileExistsError as exc:
            raise ValueError(
                "Output deployment manifest appeared during publication."
            ) from exc
        temporary_path.unlink()
        _fsync_directory(output.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        manifest = build_deployment_manifest(
            archive=arguments.archive,
            runtime_manifest=arguments.runtime_manifest,
            commit_sha=arguments.commit_sha,
        )
        publish_manifest(arguments.output, manifest)
    except (OSError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "validation_failed", "message": str(exc)},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 2
    print(json.dumps(manifest, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
