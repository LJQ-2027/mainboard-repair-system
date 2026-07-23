from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_visual_qc_batch import (  # noqa: E402
    VisualQcIntakeTransport,
    _load_credentials,
)
from scripts.visual_qc.physical_handoff import (  # noqa: E402
    PhysicalHandoffError,
    run_physical_handoff,
)


class PathFreeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _emit(
            {
                "status": "validation_failed",
                "code": "invalid_arguments",
                "message": "Physical handoff arguments are invalid.",
            },
            error=True,
        )
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = PathFreeArgumentParser(
        description=(
            "Run an acceptance-qualified handoff of one controlled physical "
            "mainboard photo package."
        )
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("acceptance_report", type=Path)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--handoff-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--api-base")
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--actor-id")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--allow-http-localhost", action="store_true")
    return parser


def _emit(payload: dict, *, error: bool = False) -> None:
    print(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        file=sys.stderr if error else sys.stdout,
    )


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        transport = None
        if not arguments.dry_run:
            credentials = _load_credentials(arguments.credential_file)
            api_base = arguments.api_base
            if not api_base:
                raise PhysicalHandoffError(
                    "api_base_required", "API base is required for physical handoff."
                )
            actor_id = arguments.actor_id or credentials["actor_id"] or credentials["username"]
            try:
                transport = VisualQcIntakeTransport(
                    api_base,
                    actor_id=actor_id or "",
                    username=credentials["username"] or "",
                    password=credentials["password"] or "",
                    allow_http_localhost=arguments.allow_http_localhost,
                )
            except ValueError as exc:
                raise PhysicalHandoffError(
                    "invalid_transport_configuration",
                    "Physical handoff transport configuration is invalid.",
                ) from exc
        receipt = run_physical_handoff(
            package_path=arguments.package,
            acceptance_report_path=arguments.acceptance_report,
            project_root=PROJECT_ROOT,
            library_root=arguments.library_root,
            handoff_root=arguments.handoff_root,
            transport=transport,
            dry_run=arguments.dry_run,
            wait_for_jobs=arguments.wait,
            continue_on_error=arguments.continue_on_error,
        )
    except PhysicalHandoffError as exc:
        _emit(
            {
                "status": "validation_failed",
                "code": exc.code,
                "message": str(exc),
            },
            error=True,
        )
        return 2
    except Exception:
        _emit(
            {
                "status": "failed",
                "code": "handoff_failed",
                "message": "Physical handoff could not be completed.",
            },
            error=True,
        )
        return 1

    _emit(
        {
            "status": receipt["status"],
            "batch_id": receipt["source_package"]["batch_id"],
            "counts": receipt["summary"]["state_counts"],
        }
    )
    return 1 if receipt["status"] in {"partial_failure", "failed"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
