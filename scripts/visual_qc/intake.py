from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import cv2
import numpy as np

from scripts.visual_qc.server.catalog import BoardCatalog, CatalogError
from scripts.visual_qc.proxy_inventory import known_proxy_hashes
from scripts.visual_qc.server.storage import MIME_EXTENSIONS, detect_image_mime_type


BATCH_SCHEMA_VERSION = "VISUAL-QC-INTAKE-BATCH-V1"
RECEIPT_SCHEMA_VERSION = "VISUAL-QC-INTAKE-RECEIPT-V1"
CAPTURE_STAGES = {"golden_reference", "before_repair", "after_repair"}
CHECKLIST_ITEMS = {
    "board_and_side_confirmed",
    "focus_and_lens_confirmed",
    "lighting_and_occlusion_confirmed",
}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
RECEIPT_FIELDS = {"schema_version", "batch_id", "entries"}
RECEIPT_ENTRY_FIELDS = {
    "entry_id",
    "sha256",
    "idempotency_key",
    "mime_type",
    "width",
    "height",
    "byte_size",
    "state",
    "server_case_id",
    "server_job_id",
    "error",
}
RECEIPT_STATES = {
    "validated",
    "uploading",
    "uploaded",
    "processing",
    "completed",
    "failed",
}
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL", "CLOCK$",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
EXTENSION_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
MIN_IMAGE_DIMENSION = 64
MAX_IMAGE_DIMENSION = 20_000
MAX_IMAGE_BYTES = 100 * 1024 * 1024


class IntakeValidationError(ValueError):
    pass


def _require_safe_id(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not SAFE_ID.fullmatch(value)
        or value.endswith(".")
        or value.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES
    ):
        raise IntakeValidationError(f"unsafe {field}")
    return value


def _resolve_input_path(raw_path: object, manifest_dir: Path) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise IntakeValidationError("file_path must be a non-empty string")
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = manifest_dir / candidate
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise IntakeValidationError(f"image file does not exist: {raw_path}")
    return resolved


def _image_evidence(path: Path) -> dict:
    content = path.read_bytes()
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise IntakeValidationError("image byte size is outside supported limits")
    mime_type = detect_image_mime_type(content)
    if mime_type not in MIME_EXTENSIONS:
        raise IntakeValidationError("unsupported or invalid image signature")
    expected_mime = EXTENSION_MIME.get(path.suffix.lower())
    if expected_mime != mime_type:
        raise IntakeValidationError("extension does not match detected MIME")
    decoded = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if decoded is None or decoded.size == 0:
        raise IntakeValidationError("image cannot be decoded")
    height, width = decoded.shape[:2]
    if (
        min(width, height) < MIN_IMAGE_DIMENSION
        or max(width, height) > MAX_IMAGE_DIMENSION
    ):
        raise IntakeValidationError("image dimensions are outside supported limits")
    return {
        "mime_type": mime_type,
        "width": int(width),
        "height": int(height),
        "byte_size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def validate_intake_batch(
    manifest_path: Path, project_root: Path, *, manifest_bytes: bytes | None = None
) -> dict:
    manifest_path = Path(manifest_path).resolve()
    try:
        raw = manifest_path.read_bytes() if manifest_bytes is None else manifest_bytes
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeValidationError(f"invalid intake manifest: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != BATCH_SCHEMA_VERSION:
        raise IntakeValidationError(f"schema_version must be {BATCH_SCHEMA_VERSION}")
    batch_id = _require_safe_id(payload.get("batch_id"), "batch_id")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise IntakeValidationError("entries must be a non-empty array")
    if len(entries) > 500:
        raise IntakeValidationError("entries exceeds the batch limit")

    catalog = BoardCatalog(Path(project_root))
    try:
        proxy_hashes = known_proxy_hashes(project_root)
    except (OSError, ValueError, KeyError) as exc:
        raise IntakeValidationError(f"invalid proxy inventory: {exc}") from exc
    normalized_entries = []
    entry_ids: set[str] = set()
    paths: set[Path] = set()
    session_sides: set[tuple[str, str]] = set()
    session_identity: dict[str, tuple[str, str]] = {}

    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            raise IntakeValidationError(f"entries[{index}] must be an object")
        entry_id = _require_safe_id(raw_entry.get("entry_id"), "entry_id")
        if entry_id in entry_ids:
            raise IntakeValidationError(f"duplicate entry_id: {entry_id}")
        entry_ids.add(entry_id)

        path = _resolve_input_path(raw_entry.get("file_path"), manifest_path.parent)
        if path in paths:
            raise IntakeValidationError(f"duplicate resolved file path: {path}")
        paths.add(path)

        board_key = _require_safe_id(raw_entry.get("board_key"), "board_key")
        side_id = _require_safe_id(raw_entry.get("side_id"), "side_id")
        try:
            side = catalog.resolve_side(board_key, side_id)
        except CatalogError as exc:
            raise IntakeValidationError(str(exc)) from exc

        capture_stage = raw_entry.get("capture_stage")
        if capture_stage not in CAPTURE_STAGES:
            raise IntakeValidationError(f"invalid capture_stage: {capture_stage}")
        session_id = _require_safe_id(
            raw_entry.get("capture_session_id"), "capture_session_id"
        )
        setup_id = _require_safe_id(raw_entry.get("capture_setup_id"), "capture_setup_id")
        identity = (board_key, setup_id)
        if session_id in session_identity and session_identity[session_id] != identity:
            raise IntakeValidationError(f"mixed capture session identity: {session_id}")
        session_identity[session_id] = identity
        session_side = (session_id, side_id)
        if session_side in session_sides:
            raise IntakeValidationError(
                f"duplicate capture session side: {session_id}/{side_id}"
            )
        session_sides.add(session_side)

        checklist = raw_entry.get("capture_checklist")
        if (
            not isinstance(checklist, dict)
            or set(checklist) != CHECKLIST_ITEMS
            or not all(checklist.get(item) is True for item in CHECKLIST_ITEMS)
        ):
            raise IntakeValidationError(f"incomplete capture checklist: {entry_id}")

        evidence = _image_evidence(path)
        if evidence["sha256"] in proxy_hashes:
            raise IntakeValidationError(
                f"known reference or proxy image cannot enter physical intake: {entry_id}"
            )
        expected_sha256 = raw_entry.get("expected_sha256")
        if expected_sha256 is not None:
            if not isinstance(expected_sha256, str) or not SHA256.fullmatch(expected_sha256):
                raise IntakeValidationError("expected_sha256 must be null or 64 hex characters")
            if expected_sha256.lower() != evidence["sha256"]:
                raise IntakeValidationError(f"expected SHA-256 does not match: {entry_id}")

        normalized_entries.append(
            {
                "entry_id": entry_id,
                "file_path": path,
                "board_key": board_key,
                "board_id": side["board_id"],
                "side_id": side_id,
                "capture_stage": capture_stage,
                "capture_session_id": session_id,
                "capture_setup_id": setup_id,
                "capture_checklist": copy.deepcopy(checklist),
                **evidence,
            }
        )
    return {
        "schema_version": BATCH_SCHEMA_VERSION,
        "batch_id": batch_id,
        "entries": normalized_entries,
    }


def intake_idempotency_key(batch_id: str, entry_id: str, sha256: str) -> str:
    digest = hashlib.sha256(f"{batch_id}:{entry_id}:{sha256}".encode("utf-8")).hexdigest()
    return f"intake:{digest[:48]}"


def create_intake_receipt(validated_batch: dict) -> dict:
    rows = []
    for entry in validated_batch["entries"]:
        rows.append(
            {
                "entry_id": entry["entry_id"],
                "sha256": entry["sha256"],
                "idempotency_key": intake_idempotency_key(
                    validated_batch["batch_id"], entry["entry_id"], entry["sha256"]
                ),
                "mime_type": entry["mime_type"],
                "width": entry["width"],
                "height": entry["height"],
                "byte_size": entry["byte_size"],
                "state": "validated",
                "server_case_id": None,
                "server_job_id": None,
                "error": None,
            }
        )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "batch_id": validated_batch["batch_id"],
        "entries": rows,
    }


def validate_intake_receipt(receipt: dict) -> None:
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        raise IntakeValidationError("receipt root fields are invalid")
    batch_id = _require_safe_id(receipt.get("batch_id"), "receipt batch_id")
    entries = receipt.get("entries")
    if (
        receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION
        or not isinstance(entries, list)
        or not entries
        or len(entries) > 500
    ):
        raise IntakeValidationError("receipt root is invalid")
    identifiers = []
    for row in entries:
        if not isinstance(row, dict) or set(row) != RECEIPT_ENTRY_FIELDS:
            raise IntakeValidationError("receipt entry fields are invalid")
        entry_id = _require_safe_id(row.get("entry_id"), "receipt entry_id")
        sha256 = row.get("sha256")
        state = row.get("state")
        case_id = row.get("server_case_id")
        job_id = row.get("server_job_id")
        error = row.get("error")
        valid_error = error is None or (
            isinstance(error, dict)
            and set(error) == {"code", "message"}
            and isinstance(error.get("code"), str)
            and bool(error["code"])
            and isinstance(error.get("message"), str)
            and bool(error["message"])
        )
        if (
            not isinstance(sha256, str)
            or not LOWER_SHA256.fullmatch(sha256)
            or row.get("idempotency_key")
            != intake_idempotency_key(batch_id, entry_id, sha256)
            or row.get("mime_type") not in MIME_EXTENSIONS
            or not isinstance(row.get("width"), int)
            or isinstance(row.get("width"), bool)
            or row["width"] < MIN_IMAGE_DIMENSION
            or not isinstance(row.get("height"), int)
            or isinstance(row.get("height"), bool)
            or row["height"] < MIN_IMAGE_DIMENSION
            or not isinstance(row.get("byte_size"), int)
            or isinstance(row.get("byte_size"), bool)
            or row["byte_size"] <= 0
            or state not in RECEIPT_STATES
            or (case_id is None) != (job_id is None)
            or (case_id is not None and (not isinstance(case_id, str) or not case_id))
            or (job_id is not None and (not isinstance(job_id, str) or not job_id))
            or (state in {"uploaded", "processing", "completed"} and case_id is None)
            or (state in {"validated", "uploading"} and case_id is not None)
            or (state == "failed" and error is None)
            or (state != "failed" and error is not None)
            or not valid_error
        ):
            raise IntakeValidationError("receipt entry is invalid")
        identifiers.append(entry_id)
    if len(set(identifiers)) != len(identifiers):
        raise IntakeValidationError("receipt entries are duplicated")


def merge_receipt(previous: dict | None, validated_batch: dict) -> dict:
    current = create_intake_receipt(validated_batch)
    if not isinstance(previous, dict):
        return current
    validate_intake_receipt(previous)
    if (
        previous.get("schema_version") != RECEIPT_SCHEMA_VERSION
        or previous.get("batch_id") != current["batch_id"]
    ):
        return current
    prior_rows = {
        row.get("entry_id"): row
        for row in previous.get("entries", [])
        if isinstance(row, dict)
    }
    for row in current["entries"]:
        prior = prior_rows.get(row["entry_id"])
        if prior and prior.get("sha256") == row["sha256"]:
            row["server_case_id"] = prior["server_case_id"]
            row["server_job_id"] = prior["server_job_id"]
            if prior["server_case_id"] is not None:
                row.update({"state": "uploaded", "error": None})
            elif prior["state"] == "failed":
                row.update({"state": "failed", "error": copy.deepcopy(prior["error"])})
    return current


def write_json_atomic(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise
