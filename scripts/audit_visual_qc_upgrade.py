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

from scripts.visual_qc.source_library import (
    _absolute_lexical_path,
    _fsync_directory,
    _is_reparse_or_symlink,
)
from scripts.visual_qc.upgrade_preflight import audit_visual_qc_upgrade


class UpgradePreflightInputError(ValueError):
    pass


class ValidationArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UpgradePreflightInputError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = ValidationArgumentParser(
        description=(
            "Rehearse a Visual-QC SQLite and runtime upgrade on temporary copies."
        )
    )
    parser.add_argument("--source-database", required=True, type=Path)
    parser.add_argument("--source-data-root", required=True, type=Path)
    parser.add_argument("--source-app-root", required=True, type=Path)
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _is_within(path: Path, root: Path) -> bool:
    path = _absolute_lexical_path(path)
    root = _absolute_lexical_path(root)
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _assert_safe_output(output: Path, source_data_root: Path) -> Path:
    output = _absolute_lexical_path(output)
    source_data_root = _absolute_lexical_path(source_data_root)
    if _is_within(output, source_data_root):
        raise UpgradePreflightInputError(
            "Output must remain outside the source data root."
        )
    if output.exists():
        raise UpgradePreflightInputError("Output report already exists.")
    existing = output.parent
    pending = []
    while not existing.exists() and existing != existing.parent:
        pending.append(existing)
        existing = existing.parent
    if _is_reparse_or_symlink(existing):
        raise UpgradePreflightInputError(
            "Output path contains a symlink or reparse point."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    for path in reversed(pending):
        if _is_reparse_or_symlink(path):
            raise UpgradePreflightInputError(
                "Output path contains a symlink or reparse point."
            )
    return output


def publish_report(output: Path, report: dict) -> None:
    content = (
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".preflight.json",
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
            raise UpgradePreflightInputError(
                "Output report appeared during publication."
            ) from exc
        temporary_path.unlink()
        _fsync_directory(output.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def _failure_payload(message: str) -> dict:
    return {"status": "validation_failed", "message": message}


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        output = _assert_safe_output(
            arguments.output,
            arguments.source_data_root,
        )
        report = audit_visual_qc_upgrade(
            project_root=PROJECT_ROOT,
            source_database=arguments.source_database,
            source_data_root=arguments.source_data_root,
            source_app_root=arguments.source_app_root,
            target_version=arguments.target_version,
        )
        publish_report(output, report)
    except (UpgradePreflightInputError, ValueError, OSError) as exc:
        print(
            json.dumps(
                _failure_payload(str(exc)),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 2
    except Exception:
        print(
            json.dumps(
                _failure_payload("Unexpected upgrade preflight failure."),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 2

    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
