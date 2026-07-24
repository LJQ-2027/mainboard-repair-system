from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.intake import IntakeValidationError, _require_safe_id
from scripts.visual_qc.repair_case_library import stage_repair_case_revision


class ValidationArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise IntakeValidationError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = ValidationArgumentParser(
        description="Create or extend a Milo-supplied Visual-QC repair case."
    )
    parser.add_argument("--library-root", required=True, type=Path)
    parser.add_argument("--repair-case-id", required=True)
    parser.add_argument("--board-key", required=True)
    parser.add_argument("--case-record", required=True, type=Path)
    parser.add_argument(
        "--source-package",
        action="append",
        required=True,
        metavar="ROLE=PATH",
    )
    parser.add_argument(
        "--supporting-file",
        action="append",
        default=[],
        metavar="EVIDENCE_ID=PATH",
    )
    parser.add_argument("--previous-manifest", type=Path)
    return parser


def _parse_assignment(raw: str, id_label: str) -> tuple[str, Path]:
    identifier, separator, path = raw.partition("=")
    if not separator or not path:
        raise IntakeValidationError(
            f"{id_label} assignment must use {id_label.upper()}=PATH"
        )
    return _require_safe_id(identifier, id_label), Path(path)


def _load_case_record(path: Path) -> dict:
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise IntakeValidationError(
                    f"case record contains duplicate JSON key: {key}"
                )
            result[key] = value
        return result

    try:
        content = Path(path).read_bytes()
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except IntakeValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntakeValidationError(f"invalid case record JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise IntakeValidationError("case record JSON root must be an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        package_assignments = [
            _parse_assignment(raw, "role")
            for raw in arguments.source_package
        ]
        supporting_assignments = [
            _parse_assignment(raw, "evidence_id")
            for raw in arguments.supporting_file
        ]
        result = stage_repair_case_revision(
            project_root=PROJECT_ROOT,
            library_root=arguments.library_root,
            repair_case_id=arguments.repair_case_id,
            board_key=arguments.board_key,
            package_assignments=package_assignments,
            case_record=_load_case_record(arguments.case_record),
            supporting_assignments=supporting_assignments,
            previous_manifest_path=arguments.previous_manifest,
        )
    except IntakeValidationError as exc:
        print(
            json.dumps(
                {"status": "validation_failed", "message": str(exc)},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {"status": "failed", "message": str(exc)},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "state": result["state"],
                "repair_case_id": result["repair_case_id"],
                "revision": result["revision"],
                "completeness": result["completeness"],
                "manifest_sha256": result["manifest_sha256"],
                "manifest_path": str(result["manifest_path"]),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
