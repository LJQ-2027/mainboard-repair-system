from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.service import VisualQcService


EXECUTION_CONFIRMATION = "DELETE-EXPIRED-DRAFTS"


def validate_execution_confirmation(execute: bool, confirmation: str | None) -> bool:
    if not execute:
        return False
    if confirmation != EXECUTION_CONFIRMATION:
        raise ValueError(
            f"Execution requires --confirm {EXECUTION_CONFIRMATION}."
        )
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute bounded Visual-QC retention. Only terminal, "
            "unreviewed drafts outside the retention window are eligible."
        )
    )
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--retention-days", type=int)
    parser.add_argument("--batch-limit", type=int)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the plan. Without this flag the command is always a dry run.",
    )
    parser.add_argument(
        "--confirm",
        help=f"Required with --execute: {EXECUTION_CONFIRMATION}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        execute = validate_execution_confirmation(
            arguments.execute,
            arguments.confirm,
        )
    except ValueError as exc:
        parser.error(str(exc))

    settings = VisualQcServerSettings.from_environment()
    updates = {"worker_count": 0}
    if arguments.data_root:
        updates["data_root"] = arguments.data_root.resolve()
    if arguments.retention_days is not None:
        if arguments.retention_days < 1:
            parser.error("--retention-days must be at least 1.")
        updates["retention_days"] = arguments.retention_days
    if arguments.batch_limit is not None:
        if not 1 <= arguments.batch_limit <= 1000:
            parser.error("--batch-limit must be between 1 and 1000.")
        updates["retention_batch_limit"] = arguments.batch_limit

    service = VisualQcService(
        replace(settings, **updates),
        recover_interrupted_jobs=False,
    )
    result = service.run_retention(dry_run=not execute)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
