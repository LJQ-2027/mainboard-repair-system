from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.intake import CAPTURE_STAGES, IntakeValidationError
from scripts.visual_qc.intake_builder import (
    create_validated_intake_manifest,
    parse_image_assignment,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a validated owner-managed Visual-QC intake batch."
    )
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--board-key", required=True)
    parser.add_argument("--capture-session-id", required=True)
    parser.add_argument(
        "--capture-stage", required=True, choices=sorted(CAPTURE_STAGES)
    )
    parser.add_argument("--capture-setup-id", default="standard-bench")
    parser.add_argument(
        "--image",
        action="append",
        required=True,
        metavar="SIDE_ID=PATH",
        help="Explicit board-side image assignment; repeat for each side.",
    )
    parser.add_argument("--confirm-capture-checklist", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    output_path = arguments.output or Path.cwd() / f"{arguments.batch_id}.intake.json"
    try:
        assignments = [parse_image_assignment(raw) for raw in arguments.image]
        result = create_validated_intake_manifest(
            output_path=output_path,
            force=arguments.force,
            project_root=PROJECT_ROOT,
            batch_id=arguments.batch_id,
            board_key=arguments.board_key,
            capture_session_id=arguments.capture_session_id,
            capture_stage=arguments.capture_stage,
            capture_setup_id=arguments.capture_setup_id,
            image_assignments=assignments,
            capture_checklist_confirmed=arguments.confirm_capture_checklist,
        )
    except IntakeValidationError as exc:
        print(
            json.dumps(
                {"status": "validation_failed", "message": str(exc)},
                ensure_ascii=False,
            )
        )
        return 2
    except OSError as exc:
        print(
            json.dumps(
                {"status": "failed", "message": str(exc)},
                ensure_ascii=False,
            )
        )
        return 1

    validated = result["validated_batch"]
    entries = [
        {
            key: entry[key]
            for key in (
                "entry_id",
                "side_id",
                "mime_type",
                "width",
                "height",
                "byte_size",
                "sha256",
            )
        }
        for entry in validated["entries"]
    ]
    print(
        json.dumps(
            {
                "status": "ok",
                "batch_id": validated["batch_id"],
                "manifest": str(result["output_path"]),
                "entry_count": len(entries),
                "entries": entries,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
