from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.intake import CAPTURE_STAGES, IntakeValidationError
from scripts.visual_qc.intake_builder import parse_image_assignment
from scripts.visual_qc.source_library import stage_source_package


class ValidationArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise IntakeValidationError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = ValidationArgumentParser(
        description=(
            "Preserve Milo-supplied physical photos and create a Visual-QC "
            "intake batch. HEIC originals are retained with manifest-bound "
            "JPEG working derivatives."
        )
    )
    parser.add_argument("--library-root", required=True, type=Path)
    parser.add_argument("--package-id", required=True)
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
        help="Explicit board-side source assignment; repeat for each side.",
    )
    parser.add_argument("--confirm-milo-physical-source", action="store_true")
    parser.add_argument("--confirm-capture-checklist", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        assignments = [parse_image_assignment(raw) for raw in arguments.image]
        result = stage_source_package(
            project_root=PROJECT_ROOT,
            library_root=arguments.library_root,
            package_id=arguments.package_id,
            batch_id=arguments.batch_id,
            board_key=arguments.board_key,
            capture_session_id=arguments.capture_session_id,
            capture_stage=arguments.capture_stage,
            capture_setup_id=arguments.capture_setup_id,
            image_assignments=assignments,
            milo_physical_source_confirmed=arguments.confirm_milo_physical_source,
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
    except Exception as exc:
        print(
            json.dumps(
                {"status": "failed", "message": str(exc)},
                ensure_ascii=False,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "state": result["state"],
                "package_id": result["package_id"],
                "batch_id": result["batch_id"],
                "entry_count": result["entry_count"],
                "schema_version": result["schema_version"],
                "derived_entry_count": result["derived_entry_count"],
                "source_package": str(result["source_package_path"]),
                "intake_manifest": str(result["intake_manifest_path"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
