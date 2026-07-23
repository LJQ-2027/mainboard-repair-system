from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.intake import IntakeValidationError
from scripts.visual_qc.physical_acceptance import publish_physical_registration_run


class ValidationArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise IntakeValidationError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = ValidationArgumentParser(
        description="Build deterministic review evidence for a controlled physical photo package."
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        report = publish_physical_registration_run(
            package_path=arguments.package,
            project_root=arguments.project_root,
            library_root=arguments.library_root,
            output_root=arguments.output,
        )
    except (IntakeValidationError, OSError, ValueError):
        print(
            json.dumps(
                {
                    "error": {
                        "code": "invalid_acceptance_input",
                        "message": "Physical registration acceptance input is invalid.",
                    }
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception:
        print(
            json.dumps(
                {
                    "error": {
                        "code": "acceptance_run_failed",
                        "message": "Physical registration acceptance failed.",
                    }
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "entry_count": report["summary"]["entry_count"],
                "schema_version": report["schema_version"],
                "status": report["status"],
            },
            sort_keys=True,
        )
    )
    return 1 if report["status"] == "issues" else 0


if __name__ == "__main__":
    raise SystemExit(main())
