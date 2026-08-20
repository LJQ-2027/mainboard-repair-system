from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import threading
from collections import Counter
from contextlib import contextmanager

if os.name == "nt":
    import msvcrt
else:
    import fcntl

import cv2
import numpy as np

from scripts.import_visual_qc_batch import run_intake
from scripts.visual_qc.intake import (
    IntakeValidationError,
    validate_intake_batch,
    write_json_atomic,
)
from scripts.visual_qc.physical_acceptance import (
    validate_physical_registration_report,
)
from scripts.visual_qc.server.provenance import normalize_qualified_handoff
from scripts.visual_qc.source_library import (
    _assert_controlled_path,
    _build_archived_intake,
    _fsync_directory,
    validate_source_package,
)


HANDOFF_SCHEMA_VERSION = "VISUAL-QC-PHYSICAL-HANDOFF-V1"
ALLOWED_HANDOFF_ACTIONS = {
    "automatic_candidate_review_required",
    "manual_registration_required",
}
REPORT_FIELDS = {
    "schema_version",
    "status",
    "evidence_role",
    "physical_source_confirmed",
    "field_accuracy_claim_allowed",
    "source_package",
    "board",
    "capture",
    "summary",
    "entries",
}
SOURCE_PACKAGE_FIELDS = {
    "package_id",
    "batch_id",
    "manifest_sha256",
    "proxy_inventory_sha256",
}
BOARD_FIELDS = {"board_key", "board_id"}
CAPTURE_FIELDS = {"stage", "session_id", "setup_id"}
ENTRY_FIELDS = {
    "entry_id",
    "side_id",
    "image",
    "quality",
    "registration",
    "registration_review_status",
    "next_action",
    "overlay",
    "processing_issue",
}
IMAGE_FIELDS = {
    "original_filename",
    "mime_type",
    "width",
    "height",
    "byte_size",
    "sha256",
}
OVERLAY_FIELDS = {"path", "mime_type", "width", "height", "byte_size", "sha256"}
REPORT_SUMMARY_FIELDS = {
    "entry_count",
    "automatic_candidate_count",
    "manual_registration_count",
    "image_retake_count",
    "processing_issue_count",
    "action_counts",
}
HANDOFF_FIELDS = {
    "schema_version",
    "status",
    "field_accuracy_claim_allowed",
    "registration_review_required",
    "source_package",
    "acceptance",
    "archived_intake",
    "board",
    "capture",
    "summary",
    "entries",
}
HANDOFF_SOURCE_FIELDS = {"package_id", "batch_id", "manifest_sha256"}
HANDOFF_ACCEPTANCE_FIELDS = {"report_sha256", "source_status"}
HANDOFF_INTAKE_FIELDS = {"manifest_sha256"}
HANDOFF_SUMMARY_FIELDS = {"entry_count", "state_counts", "action_counts"}
HANDOFF_ENTRY_FIELDS = {
    "entry_id",
    "side_id",
    "image_sha256",
    "acceptance_action",
    "registration_review_required",
    "transfer_state",
    "server_case_id",
    "server_job_id",
    "error",
}
_HANDOFF_THREAD_LOCKS: dict[str, threading.Lock] = {}
_HANDOFF_THREAD_LOCKS_GUARD = threading.Lock()
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
TRANSFER_STATES = {
    "validated",
    "uploading",
    "uploaded",
    "processing",
    "completed",
    "failed",
}


class PhysicalHandoffError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _expect_fields(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise PhysicalHandoffError(
            "invalid_acceptance_report", f"Acceptance {label} fields are invalid."
        )
    return value


def _read_acceptance_report(path: Path) -> tuple[dict, str, Path]:
    supplied = Path(path).expanduser()
    root = supplied.parent.resolve()
    try:
        controlled = _assert_controlled_path(root, supplied, "acceptance report")
        if controlled.name != "physical-registration-run.json" or not controlled.is_file():
            raise PhysicalHandoffError(
                "invalid_acceptance_report", "Physical acceptance report is missing."
            )
        content = controlled.read_bytes()
        report = json.loads(content.decode("utf-8"))
    except PhysicalHandoffError:
        raise
    except (IntakeValidationError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PhysicalHandoffError(
            "invalid_acceptance_report", "Physical acceptance report is invalid."
        ) from exc
    if not isinstance(report, dict):
        raise PhysicalHandoffError(
            "invalid_acceptance_report", "Physical acceptance report is invalid."
        )
    return report, hashlib.sha256(content).hexdigest(), root


def _strict_report_shape(report: dict) -> None:
    _expect_fields(report, REPORT_FIELDS, "report")
    _expect_fields(report.get("source_package"), SOURCE_PACKAGE_FIELDS, "source package")
    _expect_fields(report.get("board"), BOARD_FIELDS, "board")
    _expect_fields(report.get("capture"), CAPTURE_FIELDS, "capture")
    _expect_fields(report.get("summary"), REPORT_SUMMARY_FIELDS, "summary")
    entries = report.get("entries")
    if not isinstance(entries, list) or not entries:
        raise PhysicalHandoffError(
            "invalid_acceptance_report", "Acceptance entries are invalid."
        )
    for entry in entries:
        _expect_fields(entry, ENTRY_FIELDS, "entry")
        _expect_fields(entry.get("image"), IMAGE_FIELDS, "image")
        overlay = entry.get("overlay")
        if overlay is not None:
            _expect_fields(overlay, OVERLAY_FIELDS, "overlay")
        elif entry.get("next_action") != "processing_issue":
            raise PhysicalHandoffError(
                "invalid_acceptance_report", "Acceptance overlay fields are invalid."
            )


def _verify_overlay(root: Path, metadata: dict) -> None:
    relative = metadata.get("path")
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise PhysicalHandoffError(
            "invalid_acceptance_overlay", "Acceptance overlay path is invalid."
        )
    try:
        path = _assert_controlled_path(root, root / relative, "acceptance overlay")
        content = path.read_bytes()
    except (IntakeValidationError, OSError) as exc:
        raise PhysicalHandoffError(
            "invalid_acceptance_overlay", "Acceptance overlay is missing or unsafe."
        ) from exc
    digest = hashlib.sha256(content).hexdigest()
    if (
        metadata.get("mime_type") != "image/png"
        or len(content) != metadata.get("byte_size")
        or digest != metadata.get("sha256")
        or not content.startswith(b"\x89PNG\r\n\x1a\n")
    ):
        raise PhysicalHandoffError(
            "invalid_acceptance_overlay", "Acceptance overlay integrity is invalid."
        )
    decoded = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if decoded is None or decoded.size == 0:
        raise PhysicalHandoffError(
            "invalid_acceptance_overlay", "Acceptance overlay cannot be decoded."
        )
    height, width = decoded.shape[:2]
    if width != metadata.get("width") or height != metadata.get("height"):
        raise PhysicalHandoffError(
            "invalid_acceptance_overlay", "Acceptance overlay dimensions are invalid."
        )


def _image_identity(entry: dict) -> dict:
    return {field: entry[field] for field in IMAGE_FIELDS}


def _validate_intake_identity(package: dict, intake: dict) -> None:
    if intake.get("batch_id") != package["batch_id"]:
        raise PhysicalHandoffError(
            "intake_identity_mismatch", "Archived intake batch does not match the package."
        )
    package_entries = {entry["entry_id"]: entry for entry in package["entries"]}
    intake_entries = {entry["entry_id"]: entry for entry in intake["entries"]}
    if set(package_entries) != set(intake_entries):
        raise PhysicalHandoffError(
            "intake_identity_mismatch", "Archived intake entries do not match the package."
        )
    for entry_id, package_entry in package_entries.items():
        intake_entry = intake_entries[entry_id]
        if any(
            intake_entry.get(field) != package_entry.get(field)
            for field in (
                "side_id",
                "mime_type",
                "width",
                "height",
                "byte_size",
                "sha256",
            )
        ) or any(
            intake_entry.get(field) != package.get(package_field)
            for field, package_field in (
                ("board_key", "board_key"),
                ("board_id", "board_id"),
                ("capture_stage", "capture_stage"),
                ("capture_session_id", "capture_session_id"),
                ("capture_setup_id", "capture_setup_id"),
                ("capture_checklist", "capture_checklist"),
            )
        ) or Path(intake_entry.get("file_path", "")).resolve() != Path(
            package_entry["object_file"]
        ).resolve():
            raise PhysicalHandoffError(
                "intake_identity_mismatch",
                "Archived intake identity does not match the package.",
            )


def validate_physical_handoff_evidence(
    *,
    package_path: Path,
    acceptance_report_path: Path,
    project_root: Path,
    library_root: Path,
) -> dict:
    try:
        package = validate_source_package(package_path, project_root, library_root)
    except (IntakeValidationError, OSError, ValueError) as exc:
        raise PhysicalHandoffError(
            "invalid_source_package", "Controlled source package is invalid or revoked."
        ) from exc

    report, report_sha256, acceptance_root = _read_acceptance_report(
        acceptance_report_path
    )
    try:
        _strict_report_shape(report)
        validate_physical_registration_report(report)
    except PhysicalHandoffError:
        raise
    except (TypeError, ValueError) as exc:
        raise PhysicalHandoffError(
            "invalid_acceptance_report", "Physical acceptance report is inconsistent."
        ) from exc

    expected_top_level = {
        "schema_version": "VISUAL-QC-PHYSICAL-REGISTRATION-RUN-V1",
        "evidence_role": "physical_capture",
        "physical_source_confirmed": True,
        "field_accuracy_claim_allowed": False,
    }
    if any(report.get(key) != value for key, value in expected_top_level.items()):
        raise PhysicalHandoffError(
            "invalid_acceptance_report", "Physical acceptance evidence boundary is invalid."
        )

    expected_source = {
        "package_id": package["package_id"],
        "batch_id": package["batch_id"],
        "manifest_sha256": package["manifest_sha256"],
        "proxy_inventory_sha256": package["proxy_inventory_sha256"],
    }
    expected_board = {
        "board_key": package["board_key"],
        "board_id": package["board_id"],
    }
    expected_capture = {
        "stage": package["capture_stage"],
        "session_id": package["capture_session_id"],
        "setup_id": package["capture_setup_id"],
    }
    if report["source_package"] != expected_source:
        raise PhysicalHandoffError(
            "package_identity_mismatch", "Acceptance package identity does not match."
        )
    if report["board"] != expected_board or report["capture"] != expected_capture:
        raise PhysicalHandoffError(
            "capture_identity_mismatch", "Acceptance board or capture identity does not match."
        )

    package_entries = {entry["entry_id"]: entry for entry in package["entries"]}
    report_entries = {entry["entry_id"]: entry for entry in report["entries"]}
    if len(report_entries) != len(report["entries"]) or set(report_entries) != set(
        package_entries
    ):
        raise PhysicalHandoffError(
            "entry_identity_mismatch", "Acceptance entries do not match the package."
        )

    normalized_entries = []
    for entry_id in sorted(package_entries):
        package_entry = package_entries[entry_id]
        report_entry = report_entries[entry_id]
        if (
            report_entry.get("side_id") != package_entry["side_id"]
            or report_entry.get("image") != _image_identity(package_entry)
        ):
            raise PhysicalHandoffError(
                "image_identity_mismatch",
                "Acceptance image evidence does not match the package.",
            )
        action = report_entry.get("next_action")
        if action == "image_retake_required":
            raise PhysicalHandoffError(
                "image_retake_required", "Physical image retake is required before handoff."
            )
        if action == "processing_issue":
            raise PhysicalHandoffError(
                "acceptance_processing_issue",
                "Physical acceptance processing must be resolved before handoff.",
            )
        if action not in ALLOWED_HANDOFF_ACTIONS:
            raise PhysicalHandoffError(
                "invalid_acceptance_action", "Acceptance action is not handoff eligible."
            )
        expected_overlay_path = f"artifacts/{entry_id}.registration-overlay.png"
        if report_entry["overlay"].get("path") != expected_overlay_path:
            raise PhysicalHandoffError(
                "invalid_acceptance_overlay",
                "Acceptance overlay does not match its entry identity.",
            )
        _verify_overlay(acceptance_root, report_entry["overlay"])
        normalized_entries.append(
            {
                "entry_id": entry_id,
                "side_id": package_entry["side_id"],
                "image_sha256": package_entry["sha256"],
                "acceptance_action": action,
            }
        )

    intake_path = Path(package["package_path"]).parent / f"{package['batch_id']}.intake.json"
    try:
        intake_path = _assert_controlled_path(
            Path(library_root).resolve(), intake_path, "archived intake manifest"
        )
        if not intake_path.is_file():
            raise IntakeValidationError("archived intake manifest is not a regular file")
    except (IntakeValidationError, OSError) as exc:
        raise PhysicalHandoffError(
            "unsafe_archived_intake", "Archived intake manifest path is unsafe."
        ) from exc
    try:
        intake_bytes = intake_path.read_bytes()
        archived_intake = json.loads(intake_bytes.decode("utf-8"))
        expected_intake = _build_archived_intake(
            package, Path(project_root).resolve(), Path(library_root).resolve()
        )
        if archived_intake != expected_intake:
            raise PhysicalHandoffError(
                "intake_identity_mismatch",
                "Archived intake identity is not deterministic for the source package.",
            )
        intake = validate_intake_batch(
            intake_path, project_root, manifest_bytes=intake_bytes
        )
    except PhysicalHandoffError:
        raise
    except (
        IntakeValidationError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise PhysicalHandoffError(
            "invalid_archived_intake", "Archived intake manifest is invalid."
        ) from exc
    _validate_intake_identity(package, intake)

    return {
        "package": expected_source,
        "acceptance": {
            "sha256": report_sha256,
            "status": report["status"],
            "field_accuracy_claim_allowed": False,
        },
        "archived_intake": {
            "manifest_sha256": hashlib.sha256(intake_bytes).hexdigest(),
        },
        "board": expected_board,
        "capture": expected_capture,
        "entries": normalized_entries,
    }


def _paths_overlap(first: Path, second: Path) -> bool:
    try:
        first.relative_to(second)
        return True
    except ValueError:
        pass
    try:
        second.relative_to(first)
        return True
    except ValueError:
        return False


@contextmanager
def _handoff_lock(handoff_root: Path):
    lexical = Path(os.path.abspath(Path(handoff_root).expanduser()))
    lexical.parent.mkdir(parents=True, exist_ok=True)
    lock_key = str(lexical).casefold() if os.name == "nt" else str(lexical)
    with _HANDOFF_THREAD_LOCKS_GUARD:
        thread_lock = _HANDOFF_THREAD_LOCKS.setdefault(lock_key, threading.Lock())
    with thread_lock:
        locks_root = _assert_controlled_path(
            lexical.parent.resolve(),
            lexical.parent / ".visual-qc-handoff-locks",
            "physical handoff lock directory",
        )
        locks_root.mkdir(parents=True, exist_ok=True)
        _assert_controlled_path(
            lexical.parent.resolve(), locks_root, "physical handoff lock directory"
        )
        lock_path = _assert_controlled_path(
            lexical.parent.resolve(),
            locks_root / f"{hashlib.sha256(lock_key.encode('utf-8')).hexdigest()}.lock",
            "physical handoff lock path",
        )
        with lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _prepare_handoff_root(
    handoff_root: Path, project_root: Path, library_root: Path
) -> Path:
    lexical = Path(os.path.abspath(Path(handoff_root).expanduser()))
    project_root = Path(project_root).resolve()
    library_root = Path(library_root).resolve()
    _assert_handoff_root_scope(lexical, project_root, library_root)
    try:
        controlled = _assert_controlled_path(
            lexical.parent.resolve(), lexical, "physical handoff working directory"
        )
        if controlled.exists() and not controlled.is_dir():
            raise PhysicalHandoffError(
                "unsafe_handoff_root", "Physical handoff working path is not a directory."
            )
        created = not controlled.exists()
        controlled.mkdir(parents=False, exist_ok=True)
        _assert_controlled_path(
            lexical.parent.resolve(), controlled, "physical handoff working directory"
        )
        if created:
            _fsync_directory(controlled)
            _fsync_directory(controlled.parent)
    except PhysicalHandoffError:
        raise
    except (IntakeValidationError, OSError) as exc:
        raise PhysicalHandoffError(
            "unsafe_handoff_root", "Physical handoff working directory is unsafe."
        ) from exc
    allowed = {"physical-handoff.json", "intake-receipt.json"}
    if any(path.name not in allowed for path in controlled.iterdir()):
        raise PhysicalHandoffError(
            "unsafe_handoff_root", "Physical handoff working directory has unknown files."
        )
    return controlled


def _controlled_receipt_path(root: Path, name: str) -> Path:
    try:
        path = _assert_controlled_path(root.resolve(), root / name, name)
    except (IntakeValidationError, OSError) as exc:
        raise PhysicalHandoffError(
            "unsafe_handoff_root", "Physical handoff receipt path is unsafe."
        ) from exc
    if path.exists() and not path.is_file():
        raise PhysicalHandoffError(
            "unsafe_handoff_root", "Physical handoff receipt path is unsafe."
        )
    return path


def _assert_handoff_root_scope(
    handoff_root: Path, project_root: Path, library_root: Path
) -> None:
    lexical = Path(os.path.abspath(Path(handoff_root).expanduser()))
    if _paths_overlap(lexical, Path(project_root).resolve()) or _paths_overlap(
        lexical, Path(library_root).resolve()
    ):
        raise PhysicalHandoffError(
            "unsafe_handoff_root",
            "Physical handoff working directory must be outside project and source roots.",
        )
    try:
        _assert_controlled_path(
            lexical.parent.resolve(), lexical, "physical handoff working directory"
        )
    except (IntakeValidationError, OSError) as exc:
        raise PhysicalHandoffError(
            "unsafe_handoff_root", "Physical handoff working directory is unsafe."
        ) from exc


def _derive_handoff_status(entries: list[dict]) -> str:
    states = [entry["transfer_state"] for entry in entries]
    if states and all(state == "validated" for state in states):
        return "validated"
    if states and all(state == "completed" for state in states):
        return "transferred"
    if "failed" in states:
        reached = any(
            entry["transfer_state"] != "failed"
            and entry["server_case_id"] is not None
            and entry["server_job_id"] is not None
            for entry in entries
        )
        return "partial_failure" if reached else "failed"
    return "processing"


def _build_handoff_receipt(evidence: dict, intake_receipt: dict) -> dict:
    intake_rows = {row["entry_id"]: row for row in intake_receipt["entries"]}
    expected_hashes = {
        entry["entry_id"]: entry["image_sha256"] for entry in evidence["entries"]
    }
    if set(intake_rows) != set(expected_hashes) or any(
        intake_rows[entry_id].get("sha256") != image_sha256
        for entry_id, image_sha256 in expected_hashes.items()
    ):
        raise PhysicalHandoffError(
            "intake_receipt_identity_mismatch",
            "Intake receipt does not match the validated physical evidence.",
        )
    entries = []
    for evidence_entry in evidence["entries"]:
        row = intake_rows[evidence_entry["entry_id"]]
        entries.append(
            {
                **evidence_entry,
                "registration_review_required": True,
                "transfer_state": row["state"],
                "server_case_id": row["server_case_id"],
                "server_job_id": row["server_job_id"],
                "error": row["error"],
            }
        )
    state_counts = Counter(entry["transfer_state"] for entry in entries)
    action_counts = Counter(entry["acceptance_action"] for entry in entries)
    receipt = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "status": _derive_handoff_status(entries),
        "field_accuracy_claim_allowed": False,
        "registration_review_required": True,
        "source_package": {
            key: evidence["package"][key]
            for key in ("package_id", "batch_id", "manifest_sha256")
        },
        "acceptance": {
            "report_sha256": evidence["acceptance"]["sha256"],
            "source_status": evidence["acceptance"]["status"],
        },
        "archived_intake": evidence["archived_intake"],
        "board": evidence["board"],
        "capture": evidence["capture"],
        "summary": {
            "entry_count": len(entries),
            "state_counts": dict(sorted(state_counts.items())),
            "action_counts": dict(sorted(action_counts.items())),
        },
        "entries": entries,
    }
    validate_physical_handoff_receipt(receipt)
    return receipt


def validate_physical_handoff_receipt(receipt: dict) -> None:
    _expect_fields(receipt, HANDOFF_FIELDS, "handoff receipt")
    _expect_fields(receipt.get("source_package"), HANDOFF_SOURCE_FIELDS, "handoff source")
    _expect_fields(receipt.get("acceptance"), HANDOFF_ACCEPTANCE_FIELDS, "handoff acceptance")
    _expect_fields(
        receipt.get("archived_intake"), HANDOFF_INTAKE_FIELDS, "handoff intake"
    )
    _expect_fields(receipt.get("board"), BOARD_FIELDS, "handoff board")
    _expect_fields(receipt.get("capture"), CAPTURE_FIELDS, "handoff capture")
    summary = _expect_fields(receipt.get("summary"), HANDOFF_SUMMARY_FIELDS, "handoff summary")
    entries = receipt.get("entries")
    if (
        receipt.get("schema_version") != HANDOFF_SCHEMA_VERSION
        or receipt.get("field_accuracy_claim_allowed") is not False
        or receipt.get("registration_review_required") is not True
        or not isinstance(entries, list)
        or not entries
    ):
        raise PhysicalHandoffError("invalid_handoff_receipt", "Physical handoff receipt is invalid.")
    source = receipt["source_package"]
    acceptance = receipt["acceptance"]
    archived_intake = receipt["archived_intake"]
    board = receipt["board"]
    capture = receipt["capture"]
    if (
        not all(
            SAFE_ID.fullmatch(str(source.get(key, "")))
            for key in ("package_id", "batch_id")
        )
        or not LOWER_SHA256.fullmatch(str(source.get("manifest_sha256", "")))
        or not LOWER_SHA256.fullmatch(str(acceptance.get("report_sha256", "")))
        or not LOWER_SHA256.fullmatch(
            str(archived_intake.get("manifest_sha256", ""))
        )
        or acceptance.get("source_status") not in {"review_required", "attention"}
        or not SAFE_ID.fullmatch(str(board.get("board_key", "")))
        or not isinstance(board.get("board_id"), str)
        or not board["board_id"]
        or capture.get("stage")
        not in {"golden_reference", "before_repair", "after_repair"}
        or not all(
            SAFE_ID.fullmatch(str(capture.get(key, "")))
            for key in ("session_id", "setup_id")
        )
    ):
        raise PhysicalHandoffError(
            "invalid_handoff_receipt", "Physical handoff receipt identity is invalid."
        )
    identifiers = []
    for entry in entries:
        _expect_fields(entry, HANDOFF_ENTRY_FIELDS, "handoff entry")
        identifiers.append(entry.get("entry_id"))
        state = entry.get("transfer_state")
        case_id = entry.get("server_case_id")
        job_id = entry.get("server_job_id")
        error = entry.get("error")
        valid_error = error is None or (
            isinstance(error, dict)
            and set(error) == {"code", "message"}
            and isinstance(error.get("code"), str)
            and bool(error["code"])
            and isinstance(error.get("message"), str)
            and bool(error["message"])
        )
        if (
            not SAFE_ID.fullmatch(str(entry.get("entry_id", "")))
            or not SAFE_ID.fullmatch(str(entry.get("side_id", "")))
            or not LOWER_SHA256.fullmatch(str(entry.get("image_sha256", "")))
            or entry.get("registration_review_required") is not True
            or entry.get("acceptance_action") not in ALLOWED_HANDOFF_ACTIONS
            or state not in TRANSFER_STATES
            or (case_id is None) != (job_id is None)
            or (case_id is not None and (not isinstance(case_id, str) or not case_id))
            or (job_id is not None and (not isinstance(job_id, str) or not job_id))
            or (
                state in {"uploaded", "processing", "completed"}
                and (case_id is None or job_id is None)
            )
            or (state != "failed" and error is not None)
            or (state == "failed" and error is None)
            or not valid_error
        ):
            raise PhysicalHandoffError(
                "invalid_handoff_receipt", "Physical handoff entry is invalid."
            )
    if len(set(identifiers)) != len(identifiers):
        raise PhysicalHandoffError(
            "invalid_handoff_receipt", "Physical handoff entries are duplicated."
        )
    expected_summary = {
        "entry_count": len(entries),
        "state_counts": dict(
            sorted(Counter(entry["transfer_state"] for entry in entries).items())
        ),
        "action_counts": dict(
            sorted(Counter(entry["acceptance_action"] for entry in entries).items())
        ),
    }
    if summary != expected_summary or receipt.get("status") != _derive_handoff_status(entries):
        raise PhysicalHandoffError(
            "invalid_handoff_receipt", "Physical handoff receipt summary is inconsistent."
        )


def _read_existing_handoff(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        validate_physical_handoff_receipt(receipt)
        return receipt
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, PhysicalHandoffError) as exc:
        raise PhysicalHandoffError(
            "invalid_handoff_receipt", "Existing physical handoff receipt is invalid."
        ) from exc


def _assert_receipt_identity(existing: dict, evidence: dict) -> None:
    expected_source = {
        key: evidence["package"][key]
        for key in ("package_id", "batch_id", "manifest_sha256")
    }
    expected_acceptance = {
        "report_sha256": evidence["acceptance"]["sha256"],
        "source_status": evidence["acceptance"]["status"],
    }
    expected_intake = evidence["archived_intake"]
    expected_entries = [
        {
            key: entry[key]
            for key in ("entry_id", "side_id", "image_sha256", "acceptance_action")
        }
        for entry in evidence["entries"]
    ]
    actual_entries = [
        {
            key: entry[key]
            for key in ("entry_id", "side_id", "image_sha256", "acceptance_action")
        }
        for entry in existing["entries"]
    ]
    if (
        existing["source_package"] != expected_source
        or existing["acceptance"] != expected_acceptance
        or existing["archived_intake"] != expected_intake
        or existing["board"] != evidence["board"]
        or existing["capture"] != evidence["capture"]
        or actual_entries != expected_entries
    ):
        raise PhysicalHandoffError(
            "handoff_receipt_conflict",
            "Existing physical handoff receipt conflicts with current evidence.",
        )


def _write_handoff_receipt(path: Path, receipt: dict) -> None:
    write_json_atomic(path, receipt)
    _fsync_directory(path.parent)


def _run_bound_intake(evidence: dict, *args, **kwargs) -> dict:
    kwargs["expected_manifest_sha256"] = evidence["archived_intake"][
        "manifest_sha256"
    ]
    kwargs["qualified_handoff_by_entry"] = _qualified_handoff_by_entry(
        evidence
    )
    try:
        return run_intake(*args, **kwargs)
    except IntakeValidationError as exc:
        if "manifest changed after validation" in str(exc):
            raise PhysicalHandoffError(
                "intake_changed_after_validation",
                "Archived intake changed after physical evidence validation.",
            ) from exc
        raise PhysicalHandoffError(
            "invalid_intake_receipt", "Physical handoff intake state is invalid."
        ) from exc


def _qualified_handoff_by_entry(evidence: dict) -> dict[str, dict]:
    common = {
        "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "source_package_manifest_sha256": evidence["package"]["manifest_sha256"],
        "archived_intake_manifest_sha256": evidence["archived_intake"][
            "manifest_sha256"
        ],
        "acceptance_report_sha256": evidence["acceptance"]["sha256"],
        "registration_review_required": True,
        "field_accuracy_claim_allowed": False,
    }
    return {
        entry["entry_id"]: normalize_qualified_handoff(
            {
                **common,
                "acceptance_action": entry["acceptance_action"],
            }
        )
        for entry in evidence["entries"]
    }


def run_physical_handoff(
    *,
    package_path: Path,
    acceptance_report_path: Path,
    project_root: Path,
    library_root: Path,
    handoff_root: Path,
    transport,
    dry_run: bool = False,
    wait_for_jobs: bool = False,
    continue_on_error: bool = False,
    poll_interval_seconds: float = 1,
    maximum_job_polls: int = 300,
) -> dict:
    evidence = validate_physical_handoff_evidence(
        package_path=package_path,
        acceptance_report_path=acceptance_report_path,
        project_root=project_root,
        library_root=library_root,
    )
    _assert_handoff_root_scope(handoff_root, project_root, library_root)
    with _handoff_lock(handoff_root):
        root = _prepare_handoff_root(handoff_root, project_root, library_root)
        evidence = validate_physical_handoff_evidence(
            package_path=package_path,
            acceptance_report_path=acceptance_report_path,
            project_root=project_root,
            library_root=library_root,
        )
        handoff_path = _controlled_receipt_path(root, "physical-handoff.json")
        intake_receipt_path = _controlled_receipt_path(root, "intake-receipt.json")
        existing = _read_existing_handoff(handoff_path)
        if existing is not None:
            _assert_receipt_identity(existing, evidence)
        elif intake_receipt_path.is_file():
            try:
                orphaned = json.loads(intake_receipt_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PhysicalHandoffError(
                    "orphaned_intake_receipt", "Orphaned intake receipt is invalid."
                ) from exc
            if any(
                row.get("server_case_id") or row.get("server_job_id")
                for row in orphaned.get("entries", [])
                if isinstance(row, dict)
            ):
                raise PhysicalHandoffError(
                    "orphaned_intake_receipt",
                    "Orphaned intake receipt with server ids cannot be rebound.",
                )

        package_dir = Path(package_path).expanduser().resolve().parent
        intake_manifest_path = package_dir / f"{evidence['package']['batch_id']}.intake.json"
        if existing is None:
            preflight = _run_bound_intake(
                evidence,
                intake_manifest_path,
                intake_receipt_path,
                None,
                dry_run=True,
                project_root=project_root,
            )
            existing = _build_handoff_receipt(evidence, preflight)
            _write_handoff_receipt(handoff_path, existing)
        if dry_run:
            return existing

        intake_receipt = _run_bound_intake(
            evidence,
            intake_manifest_path,
            intake_receipt_path,
            transport,
            wait_for_jobs=wait_for_jobs,
            continue_on_error=continue_on_error,
            project_root=project_root,
            poll_interval_seconds=poll_interval_seconds,
            maximum_job_polls=maximum_job_polls,
        )
        receipt = _build_handoff_receipt(evidence, intake_receipt)
        _write_handoff_receipt(handoff_path, receipt)
        return receipt
