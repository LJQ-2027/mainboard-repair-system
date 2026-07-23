from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import threading

if os.name == "nt":
    import msvcrt
else:
    import fcntl

import cv2
import numpy as np

from scripts.visual_qc.registration import RegistrationConfig, register_board_image
from scripts.visual_qc.server.catalog import BoardCatalog
from scripts.visual_qc.server.quality import analyze_image_quality
from scripts.visual_qc.source_library import (
    _assert_controlled_path,
    _fsync_directory as _source_fsync_directory,
    validate_source_package,
)


RUN_SCHEMA_VERSION = "VISUAL-QC-PHYSICAL-REGISTRATION-RUN-V1"
OVERLAY_MAX_DIMENSION = 1600
_OUTPUT_THREAD_LOCKS: dict[str, threading.Lock] = {}
_OUTPUT_THREAD_LOCKS_GUARD = threading.Lock()


def derive_next_action(quality_status: str, registration_status: str) -> str:
    if quality_status == "retake":
        return "image_retake_required"
    if registration_status == "manual_required":
        return "manual_registration_required"
    if registration_status == "candidate":
        return "automatic_candidate_review_required"
    return "processing_issue"


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


def _prepare_output_root(
    output_root: Path,
    library_root: Path,
    *,
    precreated_empty: bool = False,
) -> Path:
    supplied_output_root = Path(output_root).expanduser()
    if precreated_empty:
        lexical_output_root = Path(os.path.abspath(supplied_output_root))
        output_root = _assert_controlled_path(
            lexical_output_root.parent.resolve(),
            lexical_output_root,
            "acceptance publishing directory",
        )
    else:
        output_root = supplied_output_root.resolve()
    library_root = Path(library_root).expanduser().resolve()
    if _paths_overlap(output_root, library_root):
        raise ValueError("acceptance output must be outside the controlled source library")
    if precreated_empty:
        if not output_root.is_dir() or any(output_root.iterdir()):
            raise ValueError("acceptance publishing directory is not empty")
    else:
        if output_root.exists():
            raise ValueError("acceptance output already exists")
        output_root.mkdir(parents=True)
    (output_root / "artifacts").mkdir()
    return output_root


@contextmanager
def _output_lock(output_root: Path):
    output_root = Path(output_root).expanduser().resolve()
    lock_key = str(output_root).casefold() if os.name == "nt" else str(output_root)
    with _OUTPUT_THREAD_LOCKS_GUARD:
        thread_lock = _OUTPUT_THREAD_LOCKS.setdefault(lock_key, threading.Lock())
    with thread_lock:
        locks_root = output_root.parent / ".visual-qc-acceptance-locks"
        _assert_controlled_path(
            output_root.parent,
            locks_root,
            "acceptance output lock directory",
        )
        locks_root.mkdir(parents=True, exist_ok=True)
        _assert_controlled_path(
            output_root.parent,
            locks_root,
            "acceptance output lock directory",
        )
        lock_name = hashlib.sha256(lock_key.encode("utf-8")).hexdigest() + ".lock"
        lock_path = locks_root / lock_name
        _assert_controlled_path(
            output_root.parent,
            lock_path,
            "acceptance output lock path",
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


def _normalization_matrix(width: int, height: int) -> np.ndarray:
    return np.array(
        [[max(1, width - 1), 0, 0], [0, max(1, height - 1), 0], [0, 0, 1]],
        dtype=np.float64,
    )


def _resize_capture(capture: np.ndarray) -> np.ndarray:
    height, width = capture.shape[:2]
    scale = min(1.0, OVERLAY_MAX_DIMENSION / max(width, height))
    if scale == 1.0:
        return capture.copy()
    return cv2.resize(
        capture,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )


def _candidate_overlay(
    reference: np.ndarray,
    capture: np.ndarray,
    normalized_matrix: list[float],
) -> np.ndarray:
    overlay = _resize_capture(capture)
    target_height, target_width = overlay.shape[:2]
    reference_height, reference_width = reference.shape[:2]
    matrix = np.asarray(normalized_matrix, dtype=np.float64).reshape(3, 3)
    pixel_matrix = (
        _normalization_matrix(target_width, target_height)
        @ matrix
        @ np.linalg.inv(_normalization_matrix(reference_width, reference_height))
    )
    warped = cv2.warpPerspective(
        reference,
        pixel_matrix,
        (target_width, target_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    source_mask = np.full((reference_height, reference_width), 255, dtype=np.uint8)
    mask = cv2.warpPerspective(
        source_mask,
        pixel_matrix,
        (target_width, target_height),
        flags=cv2.INTER_NEAREST,
    )
    blended = cv2.addWeighted(overlay, 0.68, warped, 0.32, 0)
    overlay[mask > 0] = blended[mask > 0]
    corners = np.array(
        [[0, 0], [reference_width - 1, 0], [reference_width - 1, reference_height - 1], [0, reference_height - 1]],
        dtype=np.float32,
    )
    projected = cv2.perspectiveTransform(
        corners.reshape(-1, 1, 2), pixel_matrix
    ).reshape(-1, 2)
    cv2.polylines(
        overlay,
        [np.rint(projected).astype(np.int32)],
        True,
        (0, 176, 255),
        max(2, round(min(target_width, target_height) / 450)),
        cv2.LINE_AA,
    )
    return overlay


def _manual_overlay(capture: np.ndarray) -> np.ndarray:
    overlay = _resize_capture(capture)
    height, width = overlay.shape[:2]
    thickness = max(2, round(min(width, height) / 320))
    cv2.rectangle(
        overlay,
        (thickness, thickness),
        (width - thickness - 1, height - thickness - 1),
        (0, 176, 255),
        thickness,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        "MANUAL REGISTRATION REQUIRED",
        (max(12, thickness * 3), max(34, thickness * 9)),
        cv2.FONT_HERSHEY_SIMPLEX,
        max(0.55, min(width, height) / 1100),
        (0, 92, 204),
        max(1, thickness // 2),
        cv2.LINE_AA,
    )
    return overlay


def _write_overlay(path: Path, image: np.ndarray) -> dict:
    encoded, payload = cv2.imencode(
        ".png",
        image,
        [cv2.IMWRITE_PNG_COMPRESSION, 6],
    )
    if not encoded:
        raise RuntimeError("registration overlay could not be encoded")
    content = payload.tobytes()
    _write_durable(path, content)
    height, width = image.shape[:2]
    return {
        "path": f"artifacts/{path.name}",
        "mime_type": "image/png",
        "width": int(width),
        "height": int(height),
        "byte_size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _entry_image(entry: dict) -> dict:
    return {
        "original_filename": entry["original_filename"],
        "mime_type": entry["mime_type"],
        "width": entry["width"],
        "height": entry["height"],
        "byte_size": entry["byte_size"],
        "sha256": entry["sha256"],
    }


def _read_verified_image(path: Path, expected_sha256: str) -> np.ndarray:
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise RuntimeError("source object changed after validation")
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise RuntimeError("verified source object could not be decoded")
    return image


def validate_physical_registration_report(report: dict) -> None:
    entries = report.get("entries")
    summary = report.get("summary")
    if not isinstance(entries, list) or not entries or not isinstance(summary, dict):
        raise ValueError("physical registration report summary is invalid")
    actions = Counter(entry.get("next_action") for entry in entries)
    expected = {
        "entry_count": len(entries),
        "automatic_candidate_count": sum(
            (entry.get("registration") or {}).get("status") == "candidate"
            for entry in entries
        ),
        "manual_registration_count": sum(
            (entry.get("registration") or {}).get("status") == "manual_required"
            for entry in entries
        ),
        "image_retake_count": actions["image_retake_required"],
        "processing_issue_count": actions["processing_issue"],
        "action_counts": dict(sorted(actions.items())),
    }
    if any(summary.get(key) != value for key, value in expected.items()):
        raise ValueError("physical registration report summary is inconsistent")
    attention = actions["image_retake_required"] + actions["manual_registration_required"]
    expected_status = (
        "issues"
        if actions["processing_issue"]
        else "attention"
        if attention
        else "review_required"
    )
    if report.get("status") != expected_status:
        raise ValueError("physical registration report status is inconsistent")
    for entry in entries:
        if entry.get("registration_review_status") != "pending":
            raise ValueError("physical registration report bypasses human review")
        action = entry.get("next_action")
        quality = entry.get("quality")
        registration = entry.get("registration")
        issue = entry.get("processing_issue")
        if registration is not None and not _valid_registration_contract(registration):
            raise ValueError("physical registration report registration is invalid")
        if action == "processing_issue":
            valid = quality is None and registration is None and issue is not None
        else:
            valid = (
                quality is not None
                and registration is not None
                and issue is None
                and action
                == derive_next_action(quality.get("status"), registration.get("status"))
            )
        if not valid:
            raise ValueError("physical registration report entry state is inconsistent")


def _valid_registration_contract(registration: dict) -> bool:
    if (
        not isinstance(registration, dict)
        or registration.get("schema_version")
        != "VISUAL-QC-REGISTRATION-CANDIDATE-V1"
        or not isinstance(registration.get("evidence"), dict)
    ):
        return False
    fallback = registration.get("fallback")
    if not isinstance(fallback, dict) or fallback.get("method") != "reviewed_manual_four_point":
        return False
    if registration.get("status") == "candidate":
        matrix = registration.get("board_to_image_matrix")
        return (
            registration.get("method") == "automatic_feature_homography"
            and registration.get("review_status") == "draft"
            and registration.get("requires_human_review") is True
            and registration.get("requires_manual_registration") is False
            and isinstance(matrix, list)
            and len(matrix) == 9
            and all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in matrix
            )
            and registration.get("failure") is None
            and fallback.get("reason_code") is None
        )
    failure = registration.get("failure")
    return (
        registration.get("status") == "manual_required"
        and registration.get("method") is None
        and registration.get("review_status") is None
        and registration.get("requires_human_review") is False
        and registration.get("requires_manual_registration") is True
        and registration.get("board_to_image_matrix") is None
        and isinstance(failure, dict)
        and isinstance(failure.get("code"), str)
        and bool(failure["code"])
        and fallback.get("reason_code") == failure["code"]
    )


def build_physical_registration_run(
    *,
    package_path: Path,
    project_root: Path,
    library_root: Path,
    output_root: Path,
    _precreated_output_root: bool = False,
) -> dict:
    project_root = Path(project_root).resolve()
    library_root = Path(library_root).resolve()
    package = validate_source_package(package_path, project_root, library_root)
    output_root = _prepare_output_root(
        output_root,
        library_root,
        precreated_empty=_precreated_output_root,
    )
    catalog = BoardCatalog(project_root)
    results = []

    for entry in sorted(package["entries"], key=lambda item: item["entry_id"]):
        overlay_path = (
            output_root
            / "artifacts"
            / f"{entry['entry_id']}.registration-overlay.png"
        )
        try:
            side = catalog.resolve_side(package["board_key"], entry["side_id"])
            capture = _read_verified_image(entry["object_file"], entry["sha256"])
            reference = cv2.imread(str(side["reference_path"]), cv2.IMREAD_COLOR)
            if reference is None:
                raise RuntimeError("validated registration image could not be decoded")
            quality = analyze_image_quality(capture)
            registration = register_board_image(
                reference,
                capture,
                RegistrationConfig(max_dimension=1600),
            )
            next_action = derive_next_action(
                quality["status"], registration["status"]
            )
            if registration["status"] == "candidate":
                overlay_image = _candidate_overlay(
                    reference,
                    capture,
                    registration["board_to_image_matrix"],
                )
            else:
                overlay_image = _manual_overlay(capture)
            overlay = _write_overlay(
                overlay_path,
                overlay_image,
            )
            processing_issue = None
        except Exception:
            overlay_path.unlink(missing_ok=True)
            quality = None
            registration = None
            next_action = "processing_issue"
            overlay = None
            processing_issue = {
                "code": "processing_failed",
                "message": "The validated entry could not be processed.",
            }
        results.append(
            {
                "entry_id": entry["entry_id"],
                "side_id": entry["side_id"],
                "image": _entry_image(entry),
                "quality": quality,
                "registration": registration,
                "registration_review_status": "pending",
                "next_action": next_action,
                "overlay": overlay,
                "processing_issue": processing_issue,
            }
        )

    action_counts = Counter(item["next_action"] for item in results)
    processing_issues = action_counts["processing_issue"]
    attention = (
        action_counts["image_retake_required"]
        + action_counts["manual_registration_required"]
    )
    status = "issues" if processing_issues else "attention" if attention else "review_required"
    report = {
        "schema_version": RUN_SCHEMA_VERSION,
        "status": status,
        "evidence_role": "physical_capture",
        "physical_source_confirmed": True,
        "field_accuracy_claim_allowed": False,
        "source_package": {
            "package_id": package["package_id"],
            "batch_id": package["batch_id"],
            "manifest_sha256": package["manifest_sha256"],
            "proxy_inventory_sha256": package["proxy_inventory_sha256"],
        },
        "board": {
            "board_key": package["board_key"],
            "board_id": package["board_id"],
        },
        "capture": {
            "stage": package["capture_stage"],
            "session_id": package["capture_session_id"],
            "setup_id": package["capture_setup_id"],
        },
        "summary": {
            "entry_count": len(results),
            "automatic_candidate_count": sum(
                item["registration"] is not None
                and item["registration"]["status"] == "candidate"
                for item in results
            ),
            "manual_registration_count": sum(
                item["registration"] is not None
                and item["registration"]["status"] == "manual_required"
                for item in results
            ),
            "image_retake_count": action_counts["image_retake_required"],
            "processing_issue_count": processing_issues,
            "action_counts": dict(sorted(action_counts.items())),
        },
        "entries": results,
    }
    validate_physical_registration_report(report)
    return report


def render_physical_acceptance_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Physical Registration Acceptance Run",
        "",
        "This run uses Milo-supplied physical capture evidence. It does not establish field registration accuracy.",
        "",
        "## Run Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Board: `{report['board']['board_key']}` / `{report['board']['board_id']}`",
        f"- Source package: `{report['source_package']['package_id']}`",
        f"- Entries: {summary['entry_count']}",
        f"- Automatic candidates awaiting review: {summary['automatic_candidate_count']}",
        f"- Manual registration required: {summary['manual_registration_count']}",
        f"- Image retakes required: {summary['image_retake_count']}",
        f"- Processing issues: {summary['processing_issue_count']}",
        "",
        "## Entry Actions",
        "",
        "| Entry | Side | Quality | Registration | Required action |",
        "|---|---|---|---|---|",
    ]
    for entry in report["entries"]:
        quality = entry["quality"]["status"] if entry["quality"] else "unavailable"
        registration = (
            entry["registration"]["status"]
            if entry["registration"]
            else "unavailable"
        )
        lines.append(
            f"| `{entry['entry_id']}` | `{entry['side_id']}` | `{quality}` | "
            f"`{registration}` | `{entry['next_action']}` |"
        )
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            "- Every automatic result remains a draft candidate pending human review.",
            "- Manual fallback and retake actions are not defect findings.",
            "- No registration, defect, Golden Sample, or repair decision is approved by this run.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_durable(path: Path, content: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    _source_fsync_directory(Path(path))


def publish_physical_registration_run(
    *,
    package_path: Path,
    project_root: Path,
    library_root: Path,
    output_root: Path,
) -> dict:
    output_root = Path(output_root).expanduser().resolve()
    library_root = Path(library_root).expanduser().resolve()
    if _paths_overlap(output_root, library_root):
        raise ValueError("acceptance output must be outside the controlled source library")
    with _output_lock(output_root):
        return _publish_physical_registration_run_locked(
            package_path=package_path,
            project_root=project_root,
            library_root=library_root,
            output_root=output_root,
        )


def _publish_physical_registration_run_locked(
    *,
    package_path: Path,
    project_root: Path,
    library_root: Path,
    output_root: Path,
) -> dict:
    if output_root.exists():
        raise ValueError("acceptance output already exists")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    published = False
    try:
        temporary = Path(
            tempfile.mkdtemp(
                prefix=f".{output_root.name}.publishing-",
                dir=output_root.parent,
            )
        )
        report = build_physical_registration_run(
            package_path=package_path,
            project_root=project_root,
            library_root=library_root,
            output_root=temporary,
            _precreated_output_root=True,
        )
        json_bytes = (
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        markdown_bytes = render_physical_acceptance_markdown(report).encode("utf-8")
        _write_durable(temporary / "physical-registration-run.json", json_bytes)
        _write_durable(temporary / "physical-registration-run.md", markdown_bytes)
        _fsync_directory(temporary / "artifacts")
        _fsync_directory(temporary)
        temporary.rename(output_root)
        published = True
        _fsync_directory(output_root.parent)
        return report
    except Exception:
        if published and output_root.exists():
            try:
                output_root.rename(temporary)
            except OSError:
                shutil.rmtree(output_root, ignore_errors=True)
        if temporary is not None:
            shutil.rmtree(temporary, ignore_errors=True)
        raise
