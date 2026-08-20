from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.intake import IntakeValidationError, _require_safe_id
from scripts.visual_qc.repair_evidence_link_library import (
    RepairEvidenceLinkLibraryError,
    _read_safe_json,
    build_repair_evidence_link_revision,
    publish_repair_evidence_link_revision,
)


class ValidationArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise RepairEvidenceLinkLibraryError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = ValidationArgumentParser(
        description="Publish an immutable Visual-QC repair-evidence link.",
        allow_abbrev=False,
    )
    parser.add_argument("--library-root", required=True, type=Path)
    parser.add_argument("--link-set-id", required=True)
    parser.add_argument(
        "--repair-case-manifest",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--physical-evidence",
        action="append",
        required=True,
        type=Path,
    )
    parser.add_argument("--binding-record", required=True, type=Path)
    parser.add_argument("--previous-manifest", type=Path)
    return parser


def _silence_broken_stdout() -> None:
    original = sys.stdout
    try:
        stdout_fd = original.fileno()
    except (AttributeError, OSError, ValueError):
        stdout_fd = None

    if stdout_fd is not None:
        devnull_fd = None
        try:
            devnull_fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull_fd, stdout_fd)
        except OSError:
            pass
        finally:
            if devnull_fd is not None and devnull_fd != stdout_fd:
                try:
                    os.close(devnull_fd)
                except OSError:
                    pass

    try:
        sys.stdout = open(
            os.devnull,
            "w",
            encoding="ascii",
            errors="strict",
        )
    except OSError:
        pass


def _emit(payload: dict) -> bool:
    try:
        serialized = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
        )
        sys.stdout.write(serialized + "\n")
        sys.stdout.flush()
    except (BrokenPipeError, OSError):
        _silence_broken_stdout()
        return False
    except (TypeError, UnicodeError, ValueError):
        return False
    return True


def _typed_error(status: str, message: str) -> bool:
    return _emit(
        {"status": status, "message": message},
    )


def _expected_receipt(
    *,
    manifest: dict,
    library_root: Path,
    link_set_id: str,
) -> dict:
    if (
        manifest["link_set_id"] != link_set_id
        or type(manifest["revision"]) is not int
        or manifest["revision"] < 1
        or not isinstance(manifest["bindings"], list)
        or not isinstance(manifest["physical_evidence"], list)
    ):
        raise ValueError("preflight receipt fields are invalid")
    return {
        "link_set_id": link_set_id,
        "revision": manifest["revision"],
        "binding_count": len(manifest["bindings"]),
        "physical_evidence_count": len(manifest["physical_evidence"]),
        "manifest_path": (
            Path(library_root).expanduser().resolve()
            / "repair-evidence-links"
            / link_set_id
            / "revisions"
            / f"{manifest['revision']:04d}"
            / "repair-evidence-link.json"
        ),
    }


def _validated_receipt(result: dict, expected: dict) -> dict:
    if not isinstance(result, dict):
        raise TypeError("publication result is invalid")
    state = result["state"]
    manifest_sha256 = result["manifest_sha256"]
    manifest_path = Path(result["manifest_path"]).expanduser().resolve()
    if (
        state not in {"created", "existing"}
        or result["link_set_id"] != expected["link_set_id"]
        or result["revision"] != expected["revision"]
        or result["binding_count"] != expected["binding_count"]
        or result["physical_evidence_count"]
        != expected["physical_evidence_count"]
        or not isinstance(manifest_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) is None
        or manifest_path != expected["manifest_path"]
    ):
        raise ValueError("publication receipt does not match preflight")
    return {
        "status": "ok",
        "state": state,
        "link_set_id": expected["link_set_id"],
        "revision": expected["revision"],
        "binding_count": expected["binding_count"],
        "physical_evidence_count": expected["physical_evidence_count"],
        "manifest_sha256": manifest_sha256,
        "manifest_path": str(manifest_path),
    }


def _receipt_delivery_failed() -> int:
    _typed_error(
        "receipt_delivery_failed",
        "publication outcome is indeterminate; replay safely",
    )
    return 3


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        try:
            link_set_id = _require_safe_id(
                arguments.link_set_id,
                "link_set_id",
            )
        except IntakeValidationError as exc:
            raise RepairEvidenceLinkLibraryError(str(exc)) from exc

        binding_record, _binding_record_sha256 = _read_safe_json(
            arguments.binding_record,
            "binding record",
        )
        preflight_manifest = build_repair_evidence_link_revision(
            project_root=PROJECT_ROOT,
            library_root=arguments.library_root,
            link_set_id=link_set_id,
            repair_case_manifest_path=arguments.repair_case_manifest,
            physical_evidence_paths=arguments.physical_evidence,
            binding_record=binding_record,
            previous_manifest_path=arguments.previous_manifest,
        )
        expected_receipt = _expected_receipt(
            manifest=preflight_manifest,
            library_root=arguments.library_root,
            link_set_id=link_set_id,
        )
    except (RepairEvidenceLinkLibraryError, IntakeValidationError):
        _typed_error(
            "validation_failed",
            "repair evidence link input failed validation",
        )
        return 2
    except (KeyError, OSError, TypeError, UnicodeError, ValueError):
        _typed_error(
            "failed",
            "repair evidence link staging failed",
        )
        return 1
    except Exception:
        _typed_error(
            "failed",
            "repair evidence link staging failed",
        )
        return 1

    try:
        result = publish_repair_evidence_link_revision(
            project_root=PROJECT_ROOT,
            library_root=arguments.library_root,
            link_set_id=link_set_id,
            repair_case_manifest_path=arguments.repair_case_manifest,
            physical_evidence_paths=arguments.physical_evidence,
            binding_record_path=arguments.binding_record,
            previous_manifest_path=arguments.previous_manifest,
        )
    except (RepairEvidenceLinkLibraryError, IntakeValidationError):
        _typed_error(
            "validation_failed",
            "repair evidence link input failed validation",
        )
        return 2
    except Exception:
        _typed_error(
            "failed",
            "repair evidence link staging failed",
        )
        return 1

    try:
        receipt = _validated_receipt(result, expected_receipt)
    except Exception:
        return _receipt_delivery_failed()
    if not _emit(receipt):
        return _receipt_delivery_failed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
