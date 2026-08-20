from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.intake import IntakeValidationError
from scripts.visual_qc.source_audit import audit_source_library


class ValidationArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise IntakeValidationError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = ValidationArgumentParser(
        description="Read-only integrity audit for a controlled Visual-QC source library."
    )
    parser.add_argument("--library-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        report = audit_source_library(PROJECT_ROOT, arguments.library_root)
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
                {
                    "status": "failed",
                    "message": "Unexpected source library audit failure.",
                },
                ensure_ascii=False,
            )
        )
        return 1

    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["status"] == "issues" else 0


if __name__ == "__main__":
    raise SystemExit(main())
