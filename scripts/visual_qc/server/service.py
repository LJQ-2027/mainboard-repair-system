from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import signal
import shutil
import sqlite3
import stat
import struct
import sys
import tempfile
import threading
import uuid
import zipfile

import cv2
from jsonschema.validators import Draft202012Validator
import numpy as np

from scripts.visual_qc.registration import RegistrationConfig, register_board_image
from scripts.export_visual_qc_coco import build_coco_from_training_manifest
from scripts.validate_visual_qc_dataset import validate_visual_qc_case
from scripts.visual_qc.repair_evidence_engineering import (
    RepairEvidenceEngineeringError,
    resolve_board_asset_snapshot,
)
from scripts.visual_qc.repair_evidence_link_contract import (
    RepairEvidenceLinkContractError,
    canonical_sha256,
    validate_repair_evidence_link_manifest,
)
from scripts.visual_qc.repair_evidence_link_library import (
    RepairEvidenceLinkLibraryError,
    _reference_authorities,
    validate_repair_evidence_link_revision_on_disk,
)
from scripts.visual_qc.source_library import _is_reparse_or_symlink
from scripts.visual_qc.server.catalog import BoardCatalog, CatalogError
from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.difference import generate_difference_candidates
from scripts.visual_qc.server.quality import analyze_image_quality
from scripts.visual_qc.server.provenance import (
    QualifiedHandoffError,
    normalize_qualified_handoff,
    serialize_qualified_handoff,
)
from scripts.visual_qc.server.storage import (
    LocalObjectStorage,
    MIME_EXTENSIONS,
    StorageCleanupError,
    StorageError,
    detect_image_mime_type,
)
from scripts.visual_qc.server.store import (
    CaptureSessionIdentityConflict,
    RepairEvidenceProjectionCorrupt,
    RepairEvidenceProjectionResultLimitExceeded,
    VisualQcStore,
    utc_now,
)


CAPTURE_STAGES = {"golden_reference", "before_repair", "after_repair"}
ADMIN_CASE_STATES = {
    "processing",
    "processing_failed",
    "manual_registration_required",
    "registration_review_required",
    "ready_for_human_qc",
    "completed",
}
EVIDENCE_ROLES = {"physical_capture", "synthetic_proxy", "service_manual_proxy"}
DEFECT_CATEGORIES = {
    "burn_or_thermal_damage",
    "corrosion_or_oxidation",
    "missing_component",
    "displaced_component",
    "connector_damage",
    "shield_or_structural_damage",
    "solder_appearance_anomaly",
    "foreign_material_or_contamination",
    "unclassified_visible_anomaly",
}
CANDIDATE_REVIEW_DECISIONS = {"confirmed", "rejected", "needs_review"}
CAPTURE_CHECKLIST_ITEMS = {
    "board_and_side_confirmed",
    "focus_and_lens_confirmed",
    "lighting_and_occlusion_confirmed",
}
HUMAN_DEFECT_CATEGORIES = {
    "burn_or_heat_damage",
    "corrosion_or_oxidation",
    "missing_component",
    "displaced_component",
    "connector_damage",
    "shield_or_structure_damage",
    "solder_anomaly",
    "foreign_material",
    "unknown_visible_anomaly",
}


class VisualQcServiceError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class RepairEvidenceProjectionDrift(RuntimeError):
    pass


class _LinuxImageLeaseGuard:
    _F_OWNER_TID = 0

    def __init__(
        self,
        descriptors,
        previous_signal_mask,
        owner_thread_id,
        *,
        fcntl_module,
    ):
        self.descriptors = tuple(descriptors)
        self.previous_signal_mask = previous_signal_mask
        self.owner_thread_id = owner_thread_id
        self.fcntl_module = fcntl_module

    @classmethod
    def acquire(cls, descriptors):
        import fcntl

        descriptors = tuple(descriptors)
        if not descriptors:
            raise RuntimeError("No verified image descriptors were provided.")
        if not all(
            hasattr(fcntl, name)
            for name in ("F_SETLEASE", "F_RDLCK", "F_UNLCK")
        ):
            raise RuntimeError("Linux file leases are unavailable.")
        if not all(
            hasattr(signal, name)
            for name in ("pthread_sigmask", "sigtimedwait", "SIG_BLOCK", "SIG_SETMASK")
        ):
            raise RuntimeError("Thread-scoped SIGIO handling is unavailable.")

        owner_thread_id = threading.get_native_id()
        previous_signal_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK,
            {signal.SIGIO},
        )
        leased = []
        try:
            # F_SETOWN_EX is Linux ABI command 15. Targeting SIGIO at this
            # blocked thread keeps the kernel lease safe in a multithreaded server.
            set_owner_ex = getattr(fcntl, "F_SETOWN_EX", 15)
            owner = struct.pack("ii", cls._F_OWNER_TID, owner_thread_id)
            for descriptor in descriptors:
                fcntl.fcntl(descriptor, set_owner_ex, owner)
                fcntl.fcntl(
                    descriptor,
                    fcntl.F_SETLEASE,
                    fcntl.F_RDLCK,
                )
                leased.append(descriptor)
        except BaseException as exc:
            cleanup_errors = cls._release_leases(leased, fcntl)
            try:
                cls._drain_sigio()
            except BaseException as cleanup_exc:
                cleanup_errors.append(cleanup_exc)
            try:
                signal.pthread_sigmask(
                    signal.SIG_SETMASK,
                    previous_signal_mask,
                )
            except BaseException as cleanup_exc:
                cleanup_errors.append(cleanup_exc)
            if cleanup_errors and hasattr(exc, "add_note"):
                exc.add_note(
                    f"{len(cleanup_errors)} lease-acquisition cleanup "
                    "operation(s) also failed."
                )
            raise
        return cls(
            leased,
            previous_signal_mask,
            owner_thread_id,
            fcntl_module=fcntl,
        )

    @staticmethod
    def _release_leases(descriptors, fcntl_module):
        errors = []
        for descriptor in reversed(tuple(descriptors)):
            try:
                fcntl_module.fcntl(
                    descriptor,
                    fcntl_module.F_SETLEASE,
                    fcntl_module.F_UNLCK,
                )
            except BaseException as exc:
                errors.append(exc)
        return errors

    @staticmethod
    def _drain_sigio():
        while signal.sigtimedwait({signal.SIGIO}, 0) is not None:
            pass

    def release(self):
        if not self.descriptors:
            return []
        errors = []
        if threading.get_native_id() != self.owner_thread_id:
            errors.append(
                RuntimeError(
                    "Linux image leases must be released by their acquiring thread."
                )
            )
        descriptors, self.descriptors = self.descriptors, ()
        try:
            errors.extend(
                self._release_leases(descriptors, self.fcntl_module)
            )
        except BaseException as exc:
            errors.append(exc)
        try:
            self._drain_sigio()
        except BaseException as exc:
            errors.append(exc)
        try:
            signal.pthread_sigmask(
                signal.SIG_SETMASK,
                self.previous_signal_mask,
            )
        except BaseException as exc:
            errors.append(exc)
        return errors


class VisualQcService:
    def __init__(
        self,
        settings: VisualQcServerSettings,
        *,
        recover_interrupted_jobs: bool = True,
    ):
        self.settings = settings
        self.settings.data_root.mkdir(parents=True, exist_ok=True)
        self.catalog = BoardCatalog(settings.project_root)
        link_schema_path = (
            settings.project_root
            / "knowledge-base"
            / "visual-qc-repair-evidence-link-v1-schema.json"
        )
        self.repair_evidence_link_validator = Draft202012Validator(
            json.loads(link_schema_path.read_text(encoding="utf-8"))
        )
        self.storage = LocalObjectStorage(settings.data_root, settings.minimum_free_bytes)
        self.store = VisualQcStore(
            settings.data_root / "visual-qc.sqlite3",
            recover_interrupted_jobs=recover_interrupted_jobs,
        )
        self._stop_event = threading.Event()
        self._workers: list[threading.Thread] = []

    def health(self) -> dict:
        storage = self.storage.health(self.settings.warning_free_bytes)
        counts = self.store.operational_counts()
        return {
            "status": "ok" if storage["pressure"] == "normal" else "degraded",
            "service": "visual-qc",
            "schema_version": "VISUAL-QC-SERVER-HEALTH-V2",
            "workers": self.settings.worker_count,
            "storage": storage,
            **counts,
        }

    def run_retention(
        self,
        *,
        dry_run: bool = True,
        now: datetime | None = None,
    ) -> dict:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("Retention clock must be timezone-aware.")
        cutoff = current_time.astimezone(timezone.utc) - timedelta(
            days=self.settings.retention_days
        )
        cutoff_at = cutoff.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        protected_cases = self.store.list_retention_link_protections(cutoff_at)
        candidates = self.store.list_retention_candidates(
            cutoff_at,
            self.settings.retention_batch_limit,
            protected_case_ids=[
                item["case_id"] for item in protected_cases
            ],
        )
        result = {
            "schema_version": "VISUAL-QC-RETENTION-RUN-V1",
            "dry_run": dry_run,
            "cutoff_at": cutoff_at,
            "retention_days": self.settings.retention_days,
            "candidate_case_ids": [item["case_id"] for item in candidates],
            "candidate_count": len(candidates),
            "deleted_cases": 0,
            "deleted_objects": 0,
            "deleted_bytes": 0,
            "excluded_cases": protected_cases,
        }
        if dry_run:
            return result

        timestamp = current_time.astimezone(timezone.utc).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")
        run_id = f"retention_{uuid.uuid4().hex}"
        self.store.create_retention_run(
            {
                "run_id": run_id,
                "status": "running",
                "cutoff_at": cutoff_at,
                "candidate_count": len(candidates),
                "payload": {
                    "candidate_case_ids": result["candidate_case_ids"],
                    "retention_days": self.settings.retention_days,
                    "excluded_cases": protected_cases,
                },
                "created_at": timestamp,
            }
        )
        deletion_outcome = {
            "candidate_case_ids": result["candidate_case_ids"],
            "excluded_cases": protected_cases,
            "deleted_case_ids": [],
        }
        object_result = {"deleted_objects": 0, "deleted_bytes": 0}
        try:
            with self.storage.reference_transaction():
                deletion_outcome = self.store.delete_retention_candidates(
                    candidates,
                    cutoff_at,
                )
                result["candidate_case_ids"] = deletion_outcome[
                    "candidate_case_ids"
                ]
                result["candidate_count"] = len(
                    deletion_outcome["candidate_case_ids"]
                )
                result["excluded_cases"] = deletion_outcome["excluded_cases"]
                self.store.update_retention_run_audit(
                    run_id,
                    result["candidate_case_ids"],
                    result["excluded_cases"],
                    self.settings.retention_days,
                )
                deleted_paths = [
                    path
                    for candidate in candidates
                    if candidate["case_id"]
                    in deletion_outcome["deleted_case_ids"]
                    for path in candidate["storage_paths"]
                ]
                object_result = self.storage.delete_unreferenced(
                    deleted_paths,
                    self.store.storage_path_is_referenced,
                )
            self.store.complete_retention_run(
                run_id,
                len(deletion_outcome["deleted_case_ids"]),
                object_result["deleted_objects"],
                object_result["deleted_bytes"],
                utc_now(),
            )
        except Exception as exc:
            if isinstance(exc, StorageCleanupError):
                object_result = {
                    "deleted_objects": exc.deleted_objects,
                    "deleted_bytes": exc.deleted_bytes,
                }
            self.store.fail_retention_run(
                run_id,
                len(deletion_outcome["deleted_case_ids"]),
                object_result["deleted_objects"],
                object_result["deleted_bytes"],
                str(exc),
                utc_now(),
            )
            raise
        result.update(
            {
                "run_id": run_id,
                "deleted_cases": len(deletion_outcome["deleted_case_ids"]),
                **object_result,
            }
        )
        return result

    def create_case(
        self,
        *,
        actor_id: str,
        idempotency_key: str,
        board_key: str,
        side_id: str,
        capture_stage: str,
        evidence_role: str,
        claimed_sha256: str,
        original_filename: str,
        mime_type: str,
        content: bytes,
        capture_session_id: str | None = None,
        capture_setup_id: str = "standard-bench",
        capture_checklist: str = "{}",
        intake_batch_id: str | None = None,
        intake_entry_id: str | None = None,
        qualified_handoff: str | None = None,
    ) -> dict:
        if capture_stage not in CAPTURE_STAGES:
            raise VisualQcServiceError(
                "invalid_capture_stage",
                f"Unsupported capture_stage: {capture_stage}",
            )
        if evidence_role not in EVIDENCE_ROLES:
            raise VisualQcServiceError(
                "invalid_evidence_role",
                f"Unsupported evidence_role: {evidence_role}",
            )
        if not idempotency_key or len(idempotency_key) > 128:
            raise VisualQcServiceError("invalid_idempotency_key", "Idempotency-Key is required.")
        if not content:
            raise VisualQcServiceError("empty_upload", "Uploaded image is empty.")
        if len(content) > self.settings.maximum_upload_bytes:
            raise VisualQcServiceError("upload_too_large", "Uploaded image exceeds the size limit.", 413)
        detected_mime_type = detect_image_mime_type(content)
        if not detected_mime_type:
            raise VisualQcServiceError(
                "unsupported_image_content",
                "Uploaded bytes are not a supported JPEG, PNG, or WebP image.",
                415,
            )
        if detected_mime_type != mime_type:
            raise VisualQcServiceError(
                "mime_content_mismatch",
                "Declared MIME type does not match the uploaded image bytes.",
                415,
            )

        actual_sha256 = hashlib.sha256(content).hexdigest()
        if claimed_sha256.lower() != actual_sha256:
            raise VisualQcServiceError(
                "sha256_mismatch",
                "Declared SHA-256 does not match the uploaded bytes.",
            )
        try:
            side = self.catalog.resolve_side(board_key, side_id)
        except CatalogError as exc:
            raise VisualQcServiceError(exc.code, str(exc)) from exc
        capture_session_id = self._normalized_capture_session_id(
            capture_session_id,
            actor_id,
            idempotency_key,
        )
        capture_setup_id = self._normalized_capture_setup_id(capture_setup_id)
        normalized_checklist = self._normalized_capture_checklist(
            capture_checklist,
            evidence_role,
        )
        intake_batch_id, intake_entry_id = self._normalized_intake_provenance(
            intake_batch_id,
            intake_entry_id,
        )
        normalized_handoff = self._normalized_qualified_handoff(
            evidence_role=evidence_role,
            raw=qualified_handoff,
            intake_batch_id=intake_batch_id,
            intake_entry_id=intake_entry_id,
        )
        session_records = self.store.list_capture_session(actor_id, capture_session_id)
        if session_records:
            identity = session_records[0]
            requested_identity = (
                board_key,
                side["board_id"],
                capture_stage,
                evidence_role,
                capture_setup_id,
            )
            stored_identity = (
                identity["board_key"],
                identity["board_id"],
                identity["capture_stage"],
                identity["evidence_role"],
                identity["capture_setup_id"],
            )
            if requested_identity != stored_identity:
                raise VisualQcServiceError(
                    "capture_session_identity_conflict",
                    "Capture session already belongs to a different board, stage, evidence role, or setup.",
                    409,
                )

        image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise VisualQcServiceError("invalid_image", "Uploaded bytes are not a decodable image.")
        height, width = image.shape[:2]
        if min(width, height) < self.settings.minimum_image_dimension:
            raise VisualQcServiceError(
                "image_too_small",
                f"Image dimensions must both be at least {self.settings.minimum_image_dimension}px.",
            )

        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "board_key": board_key,
                    "side_id": side_id,
                    "capture_stage": capture_stage,
                    "evidence_role": evidence_role,
                    "capture_session_id": capture_session_id,
                    "capture_setup_id": capture_setup_id,
                    "capture_checklist": normalized_checklist,
                    "intake_batch_id": intake_batch_id,
                    "intake_entry_id": intake_entry_id,
                    "qualified_handoff": normalized_handoff,
                    "sha256": actual_sha256,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        existing = self.store.get_case_for_idempotency(actor_id, idempotency_key)
        if existing:
            if existing["request_fingerprint"] != fingerprint:
                raise VisualQcServiceError(
                    "idempotency_conflict",
                    "Idempotency-Key was already used for different content.",
                    409,
                )
            return self.get_case(existing["case_id"], actor_id)
        existing_intake = self.store.get_case_for_intake(
            actor_id,
            intake_batch_id,
            intake_entry_id,
        )
        if existing_intake:
            if existing_intake["request_fingerprint"] != fingerprint:
                raise VisualQcServiceError(
                    "intake_provenance_conflict",
                    "Intake entry was already admitted with different provenance.",
                    409,
                )
            return self.get_case(existing_intake["case_id"], actor_id)

        timestamp = utc_now()
        case_id = f"vqc_{uuid.uuid4().hex}"
        image_id = f"img_{uuid.uuid4().hex}"
        job_id = f"job_{uuid.uuid4().hex}"
        case_record = {
            "case_id": case_id,
            "actor_id": actor_id,
            "idempotency_key": idempotency_key,
            "request_fingerprint": fingerprint,
            "board_key": board_key,
            "board_id": side["board_id"],
            "side_id": side_id,
            "capture_stage": capture_stage,
            "evidence_role": evidence_role,
            "capture_session_id": capture_session_id,
            "capture_setup_id": capture_setup_id,
            "capture_checklist_json": json.dumps(
                normalized_checklist,
                sort_keys=True,
                separators=(",", ":"),
            ),
            "intake_batch_id": intake_batch_id,
            "intake_entry_id": intake_entry_id,
            "qualified_handoff_json": serialize_qualified_handoff(
                normalized_handoff
            ),
            "reference_path": str(side["reference_path"]),
            "created_at": timestamp,
        }
        image_record = {
            "image_id": image_id,
            "case_id": case_id,
            "original_filename": Path(original_filename or "upload").name,
            "mime_type": mime_type,
            "byte_size": len(content),
            "width": width,
            "height": height,
            "sha256": actual_sha256,
            "created_at": timestamp,
        }
        job_record = {
            "job_id": job_id,
            "case_id": case_id,
            "image_id": image_id,
            "job_type": "automatic_registration",
            "status": "queued",
            "attempt_count": 0,
            "input_json": "{}",
            "dedupe_key": f"registration:{case_id}",
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        with self.storage.reference_transaction():
            try:
                storage_path = self.storage.put_original(
                    content,
                    actual_sha256,
                    mime_type,
                )
            except StorageError as exc:
                status_code = 507 if exc.code == "insufficient_storage" else 415
                raise VisualQcServiceError(exc.code, str(exc), status_code) from exc
            image_record["storage_path"] = str(storage_path)
            try:
                self.store.create_case(case_record, image_record, job_record)
            except CaptureSessionIdentityConflict as exc:
                raise VisualQcServiceError(
                    "capture_session_identity_conflict",
                    "Capture session already belongs to a different board, stage, evidence role, or setup.",
                    409,
                ) from exc
            except Exception:
                existing = self.store.get_case_for_idempotency(actor_id, idempotency_key)
                if existing and existing["request_fingerprint"] == fingerprint:
                    return self.get_case(existing["case_id"], actor_id)
                existing_intake = self.store.get_case_for_intake(
                    actor_id,
                    intake_batch_id,
                    intake_entry_id,
                )
                if existing_intake:
                    if existing_intake["request_fingerprint"] != fingerprint:
                        raise VisualQcServiceError(
                            "intake_provenance_conflict",
                            "Intake entry was already admitted with different provenance.",
                            409,
                        )
                    return self.get_case(existing_intake["case_id"], actor_id)
                raise
        return self.get_case(case_id, actor_id)

    def get_case(self, case_id: str, actor_id: str) -> dict:
        record = self.store.get_case(case_id)
        if not record or record["case"]["actor_id"] != actor_id:
            raise VisualQcServiceError("case_not_found", "Visual-QC case was not found.", 404)
        case = record["case"]
        image = record["image"]
        job = record["job"]
        response = {
            "schema_version": "VISUAL-QC-SERVER-CASE-V2",
            "case_id": case["case_id"],
            "board_key": case["board_key"],
            "board_id": case["board_id"],
            "side_id": case["side_id"],
            "capture_stage": case["capture_stage"],
            "evidence_role": case["evidence_role"],
            "intake": {
                "batch_id": case["intake_batch_id"],
                "entry_id": case["intake_entry_id"],
            },
            "qualified_handoff": self._stored_qualified_handoff(
                case.get("qualified_handoff_json")
            ),
            "capture_session": self._capture_session_payload(
                case["capture_session_id"],
                actor_id,
                case["case_id"],
            ),
            "created_at": case["created_at"],
            "image": {
                key: image[key]
                for key in (
                    "image_id", "original_filename", "mime_type", "byte_size",
                    "width", "height", "sha256", "created_at",
                )
            },
            "job": self._public_job(job),
        }
        qc_review = self.store.get_latest_case_qc_review(case_id)
        if qc_review:
            response["server_qc_review"] = qc_review
        return response

    def list_admin_cases(
        self,
        actor_id: str,
        *,
        board_key: str | None,
        side_id: str | None,
        capture_stage: str | None,
        state: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        if state is not None and state not in ADMIN_CASE_STATES:
            raise VisualQcServiceError(
                "invalid_admin_case_state",
                f"Unsupported admin case state: {state}",
            )
        if capture_stage is not None and capture_stage not in CAPTURE_STAGES:
            raise VisualQcServiceError(
                "invalid_capture_stage",
                f"Unsupported capture_stage: {capture_stage}",
            )
        if board_key is not None:
            try:
                if side_id is None:
                    self.catalog.resolve_board(board_key)
                else:
                    self.catalog.resolve_side(board_key, side_id)
            except CatalogError as exc:
                raise VisualQcServiceError(exc.code, str(exc)) from exc
        rows, total = self.store.list_admin_cases(
            actor_id,
            board_key=board_key,
            side_id=side_id,
            capture_stage=capture_stage,
            state=state,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        cases = []
        for row in rows:
            cases.append(
                {
                    "case_id": row["case_id"],
                    "board_key": row["board_key"],
                    "board_id": row["board_id"],
                    "side_id": row["side_id"],
                    "capture_stage": row["capture_stage"],
                    "evidence_role": row["evidence_role"],
                    "capture_session_id": row["capture_session_id"],
                    "capture_setup_id": row["capture_setup_id"],
                    "intake": {
                        "batch_id": row["intake_batch_id"],
                        "entry_id": row["intake_entry_id"],
                    },
                    "qualified_handoff": self._stored_qualified_handoff(
                        row.get("qualified_handoff_json")
                    ),
                    "state": row["state"],
                    "created_at": row["created_at"],
                    "image": {
                        key: row[key]
                        for key in (
                            "image_id", "original_filename", "mime_type", "byte_size",
                            "width", "height", "sha256",
                        )
                    },
                    "job": {
                        "job_id": row["job_id"],
                        "status": row["job_status"],
                    },
                }
            )
        return {
            "schema_version": "VISUAL-QC-ADMIN-CASE-LIST-V2",
            "page": page,
            "page_size": page_size,
            "total": total,
            "cases": cases,
        }

    def get_admin_case(self, case_id: str, actor_id: str) -> dict:
        response = self.get_case(case_id, actor_id)
        response["schema_version"] = "VISUAL-QC-SERVER-CASE-V3"
        registration_review = self.store.get_latest_registration_review(case_id)
        if registration_review:
            response["server_registration_review"] = registration_review
        return response

    @staticmethod
    def _registration_snapshot(review: dict) -> dict:
        def contract_point(pair: dict) -> dict:
            board = pair["board"]
            image = pair["image"]
            if isinstance(board, list):
                board = {"x": board[0], "y": board[1]}
            if isinstance(image, list):
                image = {"x": image[0], "y": image[1]}
            return {"board": board, "image": image}

        return {
            "method": review["method"],
            "board_to_image_matrix": review["board_to_image_matrix"],
            "solve_anchors": [contract_point(pair) for pair in review["anchors"]],
            "independent_check_points": [
                contract_point(pair) for pair in review["check_points"]
            ],
            "error": review["error"],
        }

    def _case_identity(self, case_id: str, connection=None):
        if connection is None:
            return self.store.get_case_identity(case_id)
        row = connection.execute(
            "SELECT * FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
        return dict(row) if row else None

    def _image_identity(self, image_id: str, connection=None):
        if connection is None:
            return self.store.get_image(image_id)
        row = connection.execute(
            "SELECT * FROM images WHERE image_id = ?", (image_id,)
        ).fetchone()
        return dict(row) if row else None

    def _job_identity(self, job_id: str, connection=None):
        if connection is None:
            return self.store.get_job(job_id)
        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return dict(row) if row else None

    def _review_identity(self, review_id: str, connection=None):
        if connection is None:
            return self.store.get_registration_review(review_id)
        row = connection.execute(
            "SELECT * FROM registration_reviews WHERE review_id = ?",
            (review_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["board_to_image_matrix"] = json.loads(result.pop("matrix_json"))
        result["anchors"] = json.loads(result.pop("anchors_json"))
        result["check_points"] = json.loads(
            result.pop("check_points_json")
        )
        result["error"] = json.loads(result.pop("error_json"))
        return result

    @staticmethod
    def _file_identity(metadata):
        # Windows denies write/delete while this handle is held. POSIX permits
        # writes, so descriptor ctime catches same-inode rewrites with restored mtime.
        return (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_nlink,
            getattr(metadata, "st_mtime_ns", None),
            getattr(metadata, "st_ctime_ns", None),
        )

    @staticmethod
    def _file_locator_identity(metadata):
        return (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_nlink,
            getattr(metadata, "st_mtime_ns", None),
        )

    @staticmethod
    def _image_file_cache_key(image: dict, evidence: dict):
        return (
            evidence["image_id"],
            evidence["image_sha256"],
            image["storage_path"],
            image["sha256"],
            image["byte_size"],
            image["mime_type"],
        )

    @staticmethod
    def _open_stable_image_descriptor(candidate: Path) -> int:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if os.name != "nt":
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            return os.open(candidate, flags)

        import ctypes
        import msvcrt

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
        handle = create_file(
            str(candidate),
            0x80000000,  # GENERIC_READ
            0x00000001,  # FILE_SHARE_READ; deny write and delete
            None,
            3,  # OPEN_EXISTING
            0x00200000 | 0x08000000,  # OPEN_REPARSE_POINT | SEQUENTIAL_SCAN
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle == invalid_handle:
            raise OSError(
                ctypes.get_last_error(),
                "Unable to open stable image descriptor.",
            )
        try:
            return msvcrt.open_osfhandle(int(handle), flags)
        except Exception:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            raise

    def _hash_image_descriptor(self, descriptor: int):
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(
                descriptor,
                min(
                    1024 * 1024,
                    self.settings.maximum_upload_bytes + 1 - total,
                ),
            )
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
            if total > self.settings.maximum_upload_bytes:
                break
        return digest.hexdigest(), total

    def _stored_image_file_proof(
        self, image: dict, evidence: dict, *, keep_open: bool
    ):
        extension = MIME_EXTENSIONS.get(image["mime_type"])
        if extension is None:
            return "image_identity_mismatch", None
        expected = (
            self.storage.originals_root
            / evidence["image_sha256"][:2]
            / f"{evidence['image_sha256']}{extension}"
        ).absolute()
        candidate = Path(os.path.abspath(image["storage_path"]))
        if candidate != expected:
            return "image_identity_mismatch", None
        try:
            relative = candidate.relative_to(self.storage.data_root)
        except ValueError:
            return "image_identity_mismatch", None
        current = self.storage.data_root
        if _is_reparse_or_symlink(current):
            return "image_identity_mismatch", None
        for part in relative.parts:
            current = current / part
            if _is_reparse_or_symlink(current):
                return "image_identity_mismatch", None
        try:
            metadata = candidate.lstat()
        except (FileNotFoundError, PermissionError, OSError):
            return "image_missing", None
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size < 1
            or metadata.st_size > self.settings.maximum_upload_bytes
            or metadata.st_size != image["byte_size"]
        ):
            return "image_identity_mismatch", None
        try:
            descriptor = self._open_stable_image_descriptor(candidate)
        except (FileNotFoundError, PermissionError, OSError):
            return "image_missing", None
        try:
            before = os.fstat(descriptor)
            if _is_reparse_or_symlink(candidate):
                return "image_identity_mismatch", None
            digest, total = self._hash_image_descriptor(descriptor)
            after = os.fstat(descriptor)
            if (
                self._file_locator_identity(metadata)
                != self._file_locator_identity(before)
                or _is_reparse_or_symlink(candidate)
                or self._file_identity(before) != self._file_identity(after)
                or total != after.st_size
                or digest != evidence["image_sha256"]
                or digest != image["sha256"]
            ):
                return "image_identity_mismatch", None
            proof = {
                "descriptor": descriptor,
                "path": candidate,
                "identity": self._file_identity(after),
                "path_identity": self._file_locator_identity(after),
                "image_id": image["image_id"],
                "image_snapshot": {
                    key: image[key]
                    for key in (
                        "image_id",
                        "case_id",
                        "mime_type",
                        "byte_size",
                        "sha256",
                        "storage_path",
                    )
                },
            }
            if keep_open:
                descriptor = None
                return None, proof
            return None, None
        except OSError:
            return "image_missing", None
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def _stored_image_file_reason(self, image: dict, evidence: dict):
        reason, _proof = self._stored_image_file_proof(
            image, evidence, keep_open=False
        )
        return reason

    def _stable_image_proofs_are_current(
        self, proofs: dict, connection
    ) -> bool:
        for proof in proofs.values():
            row = connection.execute(
                "SELECT * FROM images WHERE image_id = ?",
                (proof["image_id"],),
            ).fetchone()
            if row is None:
                return False
            current_image = dict(row)
            if any(
                current_image.get(key) != value
                for key, value in proof["image_snapshot"].items()
            ):
                return False
            try:
                path_metadata = proof["path"].lstat()
                descriptor_metadata = os.fstat(proof["descriptor"])
            except (FileNotFoundError, PermissionError, OSError):
                return False
            if (
                _is_reparse_or_symlink(proof["path"])
                or not stat.S_ISREG(path_metadata.st_mode)
                or self._file_locator_identity(path_metadata)
                != proof["path_identity"]
                or self._file_identity(descriptor_metadata)
                != proof["identity"]
            ):
                return False
        return True

    def _acquire_kernel_image_exclusion(self, proofs: dict):
        if sys.platform.startswith("win"):
            return None
        if not sys.platform.startswith("linux"):
            raise VisualQcServiceError(
                "repair_evidence_link_file_exclusion_unavailable",
                "Kernel image exclusion is unavailable on this platform.",
                503,
            )
        try:
            return _LinuxImageLeaseGuard.acquire(
                proof["descriptor"] for proof in proofs.values()
            )
        except Exception as exc:
            raise VisualQcServiceError(
                "repair_evidence_link_file_exclusion_unavailable",
                "Kernel image exclusion is unavailable.",
                503,
            ) from exc

    @staticmethod
    def _cleanup_image_proofs(kernel_exclusion, stable_image_proofs):
        errors = []
        if kernel_exclusion is not None:
            try:
                lease_errors = kernel_exclusion.release()
                if lease_errors:
                    errors.extend(lease_errors)
            except BaseException as exc:
                errors.append(exc)
        for proof in stable_image_proofs.values():
            descriptor = proof.get("descriptor")
            if descriptor is None:
                continue
            proof["descriptor"] = None
            try:
                os.close(descriptor)
            except BaseException as exc:
                errors.append(exc)
        return errors

    def _repair_evidence_link_health(
        self,
        manifest: dict,
        *,
        connection=None,
        verification_cache=None,
        stable_image_proofs=None,
        verify_files=True,
        verify_board=True,
    ) -> dict:
        verification_cache = (
            verification_cache if verification_cache is not None else {}
        )
        reasons = []
        authority_reason = self._controlled_repair_evidence_link_reason(
            manifest, verification_cache=verification_cache
        )
        if authority_reason is not None:
            reasons.append(authority_reason)
        for evidence in manifest["physical_evidence"]:
            case = self._case_identity(
                evidence["server_case_id"], connection
            )
            if case is None:
                reasons.append("server_case_missing")
                continue
            expected_case = {
                "board_key": evidence["board_key"],
                "board_id": evidence["board_id"],
                "side_id": evidence["side_id"],
                "capture_stage": evidence["capture_stage"],
                "evidence_role": evidence["evidence_role"],
                "intake_batch_id": evidence["intake"]["batch_id"],
                "intake_entry_id": evidence["intake"]["entry_id"],
            }
            if any(case.get(key) != value for key, value in expected_case.items()):
                reasons.append("server_case_identity_mismatch")

            image = self._image_identity(evidence["image_id"], connection)
            if image is None:
                reasons.append("image_missing")
            elif (
                image["case_id"] != evidence["server_case_id"]
                or image["sha256"] != evidence["image_sha256"]
            ):
                reasons.append("image_identity_mismatch")
            elif verify_files:
                file_key = self._image_file_cache_key(image, evidence)
                image_cache = verification_cache.setdefault("images", {})
                if file_key not in image_cache:
                    if stable_image_proofs is None:
                        image_cache[file_key] = (
                            self._stored_image_file_reason(image, evidence)
                        )
                    else:
                        reason, proof = self._stored_image_file_proof(
                            image, evidence, keep_open=True
                        )
                        image_cache[file_key] = reason
                        if proof is not None:
                            stable_image_proofs[file_key] = proof
                file_reason = image_cache[file_key]
                if file_reason is not None:
                    reasons.append(file_reason)

            try:
                stored_handoff = json.loads(case["qualified_handoff_json"] or "null")
            except json.JSONDecodeError:
                stored_handoff = None
            if (
                stored_handoff != evidence["qualified_handoff"]
                or canonical_sha256(stored_handoff)
                != evidence["qualified_handoff_sha256"]
            ):
                reasons.append("qualified_handoff_mismatch")

            job = self._job_identity(evidence["job_id"], connection)
            if job is None:
                reasons.append("registration_job_missing")
            elif (
                job["case_id"] != evidence["server_case_id"]
                or job["image_id"] != evidence["image_id"]
                or job["job_type"] != "automatic_registration"
                or job["status"] != "succeeded"
            ):
                reasons.append("registration_job_mismatch")

            review = self._review_identity(
                evidence["registration_review_id"], connection
            )
            if review is None:
                reasons.append("registration_review_missing")
            elif (
                review["case_id"] != evidence["server_case_id"]
                or review["job_id"] != evidence["job_id"]
                or review["decision"] != "accept_manual"
                or self._registration_snapshot(review) != evidence["registration"]
            ):
                reasons.append("registration_review_mismatch")

        if verify_board:
            board_key = manifest["board"]["board_key"]
            board_cache = verification_cache.setdefault("boards", {})
            if board_key not in board_cache:
                try:
                    board_cache[board_key] = (
                        "ok",
                        resolve_board_asset_snapshot(
                            self.settings.project_root, board_key
                        ),
                    )
                except (OSError, RepairEvidenceEngineeringError):
                    board_cache[board_key] = ("missing", None)
            board_state, current_board = board_cache[board_key]
            if board_state == "missing":
                reasons.append("board_asset_missing")
            elif current_board != manifest["board"]:
                reasons.append("board_asset_mismatch")

        ordered = [
            reason
            for reason in (
                "link_authority_missing",
                "server_case_missing",
                "image_missing",
                "registration_job_missing",
                "registration_review_missing",
                "board_asset_missing",
                "link_authority_mismatch",
                "server_case_identity_mismatch",
                "image_identity_mismatch",
                "qualified_handoff_mismatch",
                "registration_job_mismatch",
                "registration_review_mismatch",
                "board_asset_mismatch",
            )
            if reason in reasons
        ]
        unavailable = any(reason.endswith("_missing") for reason in ordered)
        return {
            "state": "unavailable" if unavailable else ("stale" if ordered else "active"),
            "reasons": ordered,
        }

    def _controlled_library_root(self) -> Path | None:
        for candidate in (
            self.settings.data_root / "library",
            self.settings.data_root.parent / "library",
        ):
            if (
                candidate.is_dir()
                and not _is_reparse_or_symlink(candidate)
                and candidate.resolve() != self.settings.project_root.resolve()
            ):
                return candidate.resolve()
        return None

    def _controlled_repair_evidence_link_reason(
        self, manifest: dict, *, verification_cache=None
    ) -> str | None:
        verification_cache = (
            verification_cache if verification_cache is not None else {}
        )
        authority_cache = verification_cache.setdefault(
            "link_authorities", {}
        )
        key = (
            manifest["link_set_id"],
            manifest["revision"],
            canonical_sha256(manifest),
        )
        if key in authority_cache:
            return authority_cache[key]
        library_root = self._controlled_library_root()
        if library_root is None:
            authority_cache[key] = "link_authority_missing"
            return authority_cache[key]
        authority_path = (
            library_root
            / "repair-evidence-links"
            / manifest["link_set_id"]
            / "revisions"
            / f"{manifest['revision']:04d}"
            / "repair-evidence-link.json"
        )
        if not authority_path.is_file():
            authority_cache[key] = "link_authority_missing"
            return authority_cache[key]
        try:
            authority = validate_repair_evidence_link_revision_on_disk(
                authority_path,
                project_root=self.settings.project_root,
                library_root=library_root,
            )
        except (
            OSError,
            UnicodeError,
            RepairEvidenceLinkContractError,
            RepairEvidenceLinkLibraryError,
        ):
            authority_cache[key] = "link_authority_mismatch"
            return authority_cache[key]
        authority_cache[key] = (
            None
            if canonical_sha256(authority) == key[2]
            else "link_authority_mismatch"
        )
        return authority_cache[key]

    def _validate_controlled_repair_evidence_link(
        self,
        manifest: dict,
        manifest_sha256: str,
        *,
        verification_cache=None,
    ) -> dict:
        reason = self._controlled_repair_evidence_link_reason(
            manifest, verification_cache=verification_cache
        )
        if reason == "link_authority_missing":
            raise VisualQcServiceError(
                "repair_evidence_link_authority_unavailable",
                "Controlled repair-evidence link authority is unavailable.",
                503,
            )
        if reason is not None or canonical_sha256(manifest) != manifest_sha256:
            raise VisualQcServiceError(
                "repair_evidence_link_authority_mismatch",
                "Repair-evidence link does not match controlled authority.",
                409,
            )
        return manifest

    @staticmethod
    def _terminal_replacement(
        start: str, replacements: dict[str, str]
    ) -> str | None:
        current = start
        seen = {start}
        while current in replacements:
            current = replacements[current]
            if current in seen:
                raise VisualQcServiceError(
                    "repair_evidence_link_authority_unavailable",
                    "Repair-case correction authority is unavailable.",
                    503,
                )
            seen.add(current)
        return None if current == start else current

    def _repair_evidence_link_binding_states(
        self, manifest: dict, *, verification_cache=None
    ) -> list[dict]:
        verification_cache = (
            verification_cache if verification_cache is not None else {}
        )
        authority_key = tuple(
            (
                item["repair_case_reference_id"],
                item["manifest_sha256"],
            )
            for item in manifest["repair_case_references"]
        )
        authority_cache = verification_cache.setdefault("authorities", {})
        if authority_key in authority_cache:
            source_replacements = authority_cache[authority_key]
        else:
            source_replacements = {}
            library_root = self._controlled_library_root()
            if library_root is None:
                raise VisualQcServiceError(
                    "repair_evidence_link_authority_unavailable",
                    "Repair-case correction authority is unavailable.",
                    503,
                )
            try:
                authorities = _reference_authorities(
                    manifest["repair_case_references"],
                    project_root=self.settings.project_root,
                    library_root=library_root,
                )
                corrections = {}
                for reference in sorted(
                    manifest["repair_case_references"],
                    key=lambda item: item["revision"],
                ):
                    case = authorities[
                        reference["repair_case_reference_id"]
                    ]
                    for correction in case["corrections"]:
                        correction_id = correction["correction_id"]
                        if (
                            correction_id in corrections
                            and corrections[correction_id] != correction
                        ):
                            raise ValueError(
                                "repair case correction drift"
                            )
                        corrections[correction_id] = correction
                        current = source_replacements.get(
                            correction["corrects_fact_id"]
                        )
                        if (
                            current is not None
                            and current
                            != correction["replacement_fact_id"]
                        ):
                            raise ValueError(
                                "multiple active source corrections"
                            )
                        source_replacements[
                            correction["corrects_fact_id"]
                        ] = correction["replacement_fact_id"]
            except (OSError, ValueError) as exc:
                raise VisualQcServiceError(
                    "repair_evidence_link_authority_unavailable",
                    "Repair-case correction authority is unavailable.",
                    503,
                ) from exc
            authority_cache[authority_key] = source_replacements

        binding_replacements = {}
        for item in manifest["bindings"]:
            parent = item["supersedes_binding_id"]
            if parent is not None:
                binding_replacements[parent] = item["binding_id"]

        states = []
        for item in manifest["bindings"]:
            replacement_fact_id = self._terminal_replacement(
                item["source_fact"]["fact_id"], source_replacements
            )
            replacement_binding_id = self._terminal_replacement(
                item["binding_id"], binding_replacements
            )
            states.append(
                {
                    "binding_id": item["binding_id"],
                    "source_fact_superseded": replacement_fact_id is not None,
                    "replacement_fact_id": replacement_fact_id,
                    "binding_superseded": (
                        replacement_binding_id is not None
                    ),
                    "replacement_binding_id": replacement_binding_id,
                }
            )
        return states

    @staticmethod
    def _repair_evidence_link_counts(
        manifest: dict, binding_states: list[dict]
    ) -> dict:
        association = {
            name: 0
            for name in (
                "related",
                "possibly_related",
                "not_related",
                "insufficient_evidence",
            )
        }
        visibility = {
            name: 0
            for name in ("not_assessed", "visible", "not_visible", "occluded")
        }
        for item in manifest["bindings"]:
            association[item["association_status"]] += 1
            visibility[item["visibility_status"]] += 1
        return {
            "association": association,
            "visibility": visibility,
            "source_fact_superseded": sum(
                item["source_fact_superseded"] for item in binding_states
            ),
            "binding_superseded": sum(
                item["binding_superseded"] for item in binding_states
            ),
        }

    def _repair_evidence_link_summary(
        self,
        row: dict,
        binding_states: list[dict] | None = None,
        *,
        verification_cache=None,
    ) -> dict:
        manifest = row["manifest"]
        binding_states = (
            binding_states
            if binding_states is not None
            else self._repair_evidence_link_binding_states(
                manifest, verification_cache=verification_cache
            )
        )
        return {
            "link_set_id": row["link_set_id"],
            "revision": row["revision"],
            "manifest_sha256": row["manifest_sha256"],
            "repair_case_id": row["repair_case_id"],
            "board": {
                "board_key": row["board_key"],
                "board_id": row["board_id"],
            },
            "server_case_ids": row["server_case_ids"],
            "counts": self._repair_evidence_link_counts(
                manifest, binding_states
            ),
            "health": self._repair_evidence_link_health(
                manifest, verification_cache=verification_cache
            ),
            "imported_at": row["imported_at"],
        }

    def import_repair_evidence_link(
        self, *, manifest: dict, manifest_sha256: str, actor_id: str
    ) -> dict:
        if next(self.repair_evidence_link_validator.iter_errors(manifest), None):
            raise VisualQcServiceError(
                "repair_evidence_link_invalid",
                "Repair-evidence link manifest does not match its schema.",
            )
        try:
            validated = validate_repair_evidence_link_manifest(manifest)
        except RepairEvidenceLinkContractError as exc:
            raise VisualQcServiceError(
                "repair_evidence_link_invalid", str(exc)
            ) from exc
        if canonical_sha256(validated) != manifest_sha256:
            raise VisualQcServiceError(
                "repair_evidence_link_hash_mismatch",
                "Repair-evidence link manifest hash does not match.",
            )
        verification_cache = {}
        validated = self._validate_controlled_repair_evidence_link(
            validated,
            manifest_sha256,
            verification_cache=verification_cache,
        )
        stable_image_proofs = {}
        kernel_exclusion = None
        projection_committed = False
        result = None
        failure = None
        try:
            self._repair_evidence_link_binding_states(
                validated, verification_cache=verification_cache
            )
            health = self._repair_evidence_link_health(
                validated,
                verification_cache=verification_cache,
                stable_image_proofs=stable_image_proofs,
            )
            if health["state"] != "active":
                raise VisualQcServiceError(
                    "repair_evidence_link_not_active",
                    "Repair-evidence link projection is not active.",
                    409,
                )
            kernel_exclusion = self._acquire_kernel_image_exclusion(
                stable_image_proofs
            )
            with self.store.connect() as proof_connection:
                if not self._stable_image_proofs_are_current(
                    stable_image_proofs, proof_connection
                ):
                    raise RepairEvidenceProjectionDrift(health)

            def validate_stable_current(connection):
                current = self._repair_evidence_link_health(
                    validated,
                    connection=connection,
                    verification_cache=verification_cache,
                    verify_files=False,
                    verify_board=False,
                )
                if (
                    current["state"] != "active"
                    or not self._stable_image_proofs_are_current(
                        stable_image_proofs, connection
                    )
                ):
                    raise RepairEvidenceProjectionDrift(current)

            def mark_projection_committed():
                nonlocal projection_committed
                projection_committed = True

            row = self.store.import_repair_evidence_link_revision(
                manifest=validated,
                manifest_sha256=manifest_sha256,
                actor_id=actor_id,
                imported_at=utc_now(),
                validate_current=validate_stable_current,
                validate_after=validate_stable_current,
                on_committed=mark_projection_committed,
            )
            result = self._repair_evidence_link_detail(
                row, verification_cache=verification_cache
            )
        except RepairEvidenceProjectionDrift as exc:
            failure = VisualQcServiceError(
                "repair_evidence_link_not_active",
                "Repair-evidence link projection is not active.",
                409,
            )
            failure.__cause__ = exc
        except RepairEvidenceProjectionCorrupt as exc:
            failure = VisualQcServiceError(
                "repair_evidence_link_projection_corrupt",
                "Stored repair-evidence link projection is corrupt.",
                503,
            )
            failure.__cause__ = exc
        except VisualQcServiceError as exc:
            failure = exc
        except (ValueError, sqlite3.IntegrityError) as exc:
            failure = VisualQcServiceError(
                "repair_evidence_link_conflict",
                "Repair-evidence link projection conflicts with stored data.",
                409,
            )
            failure.__cause__ = exc
        except BaseException as exc:
            failure = exc

        cleanup_errors = self._cleanup_image_proofs(
            kernel_exclusion,
            stable_image_proofs,
        )
        if cleanup_errors:
            if projection_committed:
                raise VisualQcServiceError(
                    "repair_evidence_link_cleanup_uncertain",
                    "Projection may already exist; caller must replay the exact import.",
                    503,
                )
            raise VisualQcServiceError(
                "repair_evidence_link_cleanup_failed",
                "Import failed before commit and resource cleanup was incomplete.",
                503,
            )
        if failure is not None:
            raise failure
        return result

    def list_repair_evidence_links(
        self,
        *,
        server_case_id: str | None = None,
        repair_case_id: str | None = None,
    ) -> dict:
        try:
            rows = self.store.list_repair_evidence_link_revisions(
                server_case_id=server_case_id,
                repair_case_id=repair_case_id,
            )
        except RepairEvidenceProjectionResultLimitExceeded as exc:
            raise VisualQcServiceError(
                "repair_evidence_link_result_limit_exceeded",
                "Repair-evidence link query exceeds the result limit.",
                422,
            ) from exc
        except RepairEvidenceProjectionCorrupt as exc:
            raise VisualQcServiceError(
                "repair_evidence_link_projection_corrupt",
                "Stored repair-evidence link projection is corrupt.",
                503,
            ) from exc
        verification_cache = {}
        return {
            "schema_version": "VISUAL-QC-REPAIR-EVIDENCE-LINK-LIST-V1",
            "links": [
                self._repair_evidence_link_summary(
                    row, verification_cache=verification_cache
                )
                for row in rows
            ],
        }

    def _repair_evidence_link_detail(
        self, row: dict, *, verification_cache=None
    ) -> dict:
        verification_cache = (
            verification_cache if verification_cache is not None else {}
        )
        binding_states = self._repair_evidence_link_binding_states(
            row["manifest"], verification_cache=verification_cache
        )
        return {
            "schema_version": "VISUAL-QC-REPAIR-EVIDENCE-LINK-DETAIL-V1",
            **self._repair_evidence_link_summary(
                row,
                binding_states,
                verification_cache=verification_cache,
            ),
            "binding_states": binding_states,
            "manifest": row["manifest"],
        }

    def get_repair_evidence_link(self, link_set_id: str, revision: int) -> dict:
        try:
            row = self.store.get_repair_evidence_link_revision(
                link_set_id, revision
            )
        except RepairEvidenceProjectionCorrupt as exc:
            raise VisualQcServiceError(
                "repair_evidence_link_projection_corrupt",
                "Stored repair-evidence link projection is corrupt.",
                503,
            ) from exc
        if row is None:
            raise VisualQcServiceError(
                "repair_evidence_link_not_found",
                "Repair-evidence link projection was not found.",
                404,
            )
        return self._repair_evidence_link_detail(row)

    def get_admin_case_original(self, case_id: str, actor_id: str) -> dict:
        record = self.store.get_case(case_id)
        if not record or record["case"]["actor_id"] != actor_id:
            raise VisualQcServiceError("case_not_found", "Visual-QC case was not found.", 404)
        image = record["image"]
        storage_path = Path(image["storage_path"]).resolve()
        try:
            storage_path.relative_to(self.storage.originals_root.resolve())
        except ValueError as exc:
            raise VisualQcServiceError(
                "invalid_original_storage_path",
                "The case original is outside managed storage.",
                500,
            ) from exc
        if not storage_path.is_file():
            raise VisualQcServiceError(
                "original_not_found", "The case original is unavailable.", 404
            )
        actual_sha256 = hashlib.sha256(storage_path.read_bytes()).hexdigest()
        if actual_sha256 != image["sha256"]:
            raise VisualQcServiceError(
                "original_integrity_failure",
                "The case original failed its integrity check.",
                409,
            )
        return {
            "storage_path": storage_path,
            "mime_type": image["mime_type"],
            "original_filename": image["original_filename"],
        }

    def get_capture_session(self, capture_session_id: str, actor_id: str) -> dict:
        normalized_id = self._normalized_capture_session_id(
            capture_session_id,
            actor_id,
            "lookup",
        )
        records = self.store.list_capture_session(actor_id, normalized_id)
        if not records:
            raise VisualQcServiceError(
                "capture_session_not_found",
                "Capture session was not found.",
                404,
            )
        return self._capture_session_payload(normalized_id, actor_id)

    def review_case_qc(
        self,
        case_id: str,
        actor_id: str,
        qc_result: str,
        annotations: list[dict],
        notes: str,
    ) -> dict:
        record = self.store.get_case(case_id)
        if not record or record["case"]["actor_id"] != actor_id:
            raise VisualQcServiceError(
                "case_not_found",
                "Visual-QC case was not found.",
                404,
            )
        case = record["case"]
        image = record["image"]
        job = record["job"]
        if case["evidence_role"] != "physical_capture":
            raise VisualQcServiceError(
                "physical_capture_required",
                "Final QC review for training requires a physical capture.",
                409,
            )
        checklist = json.loads(case["capture_checklist_json"] or "{}")
        if checklist.get("status") != "confirmed":
            raise VisualQcServiceError(
                "capture_checklist_confirmation_required",
                "Final QC review requires a confirmed physical capture checklist.",
                409,
            )
        registration_review = self.store.get_latest_registration_review(case_id)
        if not registration_review:
            raise VisualQcServiceError(
                "registration_review_required",
                "Final QC review requires reviewed registration.",
                409,
            )
        quality = (job.get("result") or {}).get("quality") or {}
        if job.get("status") != "succeeded" or quality.get("status") == "retake":
            raise VisualQcServiceError(
                "acceptable_image_quality_required",
                "Final QC review requires a completed image-quality result that is not retake.",
                409,
            )
        if qc_result not in {"no_visible_anomaly", "confirmed_anomaly"}:
            raise VisualQcServiceError(
                "invalid_final_qc_result",
                "Final QC result must be no_visible_anomaly or confirmed_anomaly.",
            )
        if not isinstance(annotations, list) or len(annotations) > 1000:
            raise VisualQcServiceError(
                "invalid_final_annotations",
                "Final QC annotations must be an array containing at most 1000 items.",
            )
        confirmed_count = sum(
            isinstance(annotation, dict)
            and annotation.get("source") == "human_annotation"
            and annotation.get("review_status") == "confirmed"
            for annotation in annotations
        )
        if qc_result == "confirmed_anomaly" and confirmed_count == 0:
            raise VisualQcServiceError(
                "confirmed_anomaly_requires_annotation",
                "confirmed_anomaly requires at least one confirmed human annotation.",
            )
        if qc_result == "no_visible_anomaly" and confirmed_count:
            raise VisualQcServiceError(
                "no_visible_anomaly_conflicts_with_annotations",
                "no_visible_anomaly cannot contain confirmed annotations.",
            )

        reviewed_at = utc_now()
        qc_review_id = f"qcrev_{uuid.uuid4().hex}"
        capture_session = self._capture_session_payload(
            case["capture_session_id"],
            actor_id,
            case_id,
        )
        canonical_case = {
            "schema_version": "VISUAL-QC-CASE-V2",
            "case_id": case_id,
            "board_key": case["board_key"],
            "board_id": case["board_id"],
            "side_id": case["side_id"],
            "storage_scope": "server_authoritative_with_local_draft",
            "capture_stage": case["capture_stage"],
            "capture_session": {
                key: capture_session[key]
                for key in (
                    "schema_version",
                    "session_id",
                    "setup_id",
                    "expected_side_ids",
                    "captured_side_ids",
                    "pair_status",
                    "checklist",
                )
            },
            "image": {
                "file_name": image["original_filename"],
                "mime_type": image["mime_type"],
                "width": image["width"],
                "height": image["height"],
                "sha256": image["sha256"],
                "evidence_role": "physical_capture",
            },
            "quality": quality,
            "registration": self._training_registration_payload(
                registration_review,
                job,
            ),
            "annotations": annotations,
            "qc_result": {
                "status": qc_result,
                "reviewed_at": reviewed_at,
            },
            "server_qc_review": {
                "qc_review_id": qc_review_id,
                "case_id": case_id,
                "registration_review_id": registration_review["review_id"],
                "reviewer_id": actor_id,
                "version": 1,
                "qc_result": qc_result,
                "annotations": annotations,
                "notes": notes[:1000],
                "created_at": reviewed_at,
                "training_status": "eligible",
            },
        }
        validation_errors = validate_visual_qc_case(
            canonical_case,
            self.settings.project_root,
            training_ready=True,
        )
        if validation_errors:
            raise VisualQcServiceError(
                "training_review_invalid",
                "Final QC review is not training eligible: "
                + "; ".join(validation_errors),
            )
        return self.store.create_case_qc_review(
            {
                "qc_review_id": qc_review_id,
                "case_id": case_id,
                "registration_review_id": registration_review["review_id"],
                "reviewer_id": actor_id,
                "qc_result": qc_result,
                "annotations": annotations,
                "notes": notes[:1000],
                "created_at": reviewed_at,
            }
        )

    @staticmethod
    def _training_registration_payload(registration_review: dict, job: dict) -> dict:
        anchors = [
            {
                "board": {"x": pair["board"][0], "y": pair["board"][1]},
                "image": {"x": pair["image"][0], "y": pair["image"][1]},
            }
            for pair in registration_review.get("anchors", [])
        ]
        check_points = [
            {
                "board": {"x": pair["board"][0], "y": pair["board"][1]},
                "image": {"x": pair["image"][0], "y": pair["image"][1]},
            }
            for pair in registration_review.get("check_points", [])
        ]
        registration = (job.get("result") or {}).get("registration") or {}
        evidence = registration.get("evidence") or {}
        return {
            "method": registration_review["method"],
            "status": "reviewed",
            "matrix": registration_review["board_to_image_matrix"],
            "solve_anchors": anchors,
            "check_points": check_points,
            "error": registration_review.get("error") or {
                "count": 0,
                "rms": evidence.get("reprojection_rms"),
                "maximum": evidence.get("reprojection_maximum"),
            },
            "server_review_id": registration_review["review_id"],
        }

    def training_manifest(self) -> dict:
        cases = []
        annotation_count = 0
        category_counts = {category: 0 for category in sorted(HUMAN_DEFECT_CATEGORIES)}
        for review in self.store.list_latest_case_qc_reviews():
            if review["evidence_role"] != "physical_capture":
                continue
            if review.get("qualified_handoff_json") is None:
                continue
            self._stored_qualified_handoff(review["qualified_handoff_json"])
            confirmed = [
                annotation
                for annotation in review["annotations"]
                if annotation.get("review_status") == "confirmed"
            ]
            annotation_count += len(confirmed)
            for annotation in confirmed:
                category = annotation.get("category")
                if category in category_counts:
                    category_counts[category] += 1
            cases.append(
                {
                    "case_id": review["case_id"],
                    "board_key": review["board_key"],
                    "board_id": review["board_id"],
                    "side_id": review["side_id"],
                    "capture_stage": review["capture_stage"],
                    "capture_session_id": review["capture_session_id"],
                    "capture_setup_id": review["capture_setup_id"],
                    "image": {
                        "image_id": review["image_id"],
                        "file_name": review["original_filename"],
                        "mime_type": review["mime_type"],
                        "width": review["width"],
                        "height": review["height"],
                        "sha256": review["sha256"],
                    },
                    "qc_review": {
                        "qc_review_id": review["qc_review_id"],
                        "version": review["version"],
                        "reviewer_id": review["reviewer_id"],
                        "qc_result": review["qc_result"],
                        "annotations": review["annotations"],
                        "created_at": review["created_at"],
                    },
                }
            )
        return {
            "schema_version": "VISUAL-QC-TRAINING-MANIFEST-V1",
            "generated_at": utc_now(),
            "case_count": len(cases),
            "annotation_count": annotation_count,
            "category_counts": category_counts,
            "cases": cases,
        }

    def training_coco(self) -> dict:
        return build_coco_from_training_manifest(self.training_manifest())

    @staticmethod
    def _bundle_timestamp(manifest: dict) -> str:
        reviewed_at = [
            case["qc_review"]["created_at"]
            for case in manifest["cases"]
        ]
        return max(reviewed_at, default="1970-01-01T00:00:00+00:00")

    @staticmethod
    def _bundle_zip_info(archive_path: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        return info

    @staticmethod
    def _bundle_json_bytes(payload: dict) -> bytes:
        return (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def training_bundle(self) -> Path:
        manifest = self.training_manifest()
        generated_at = self._bundle_timestamp(manifest)
        manifest["generated_at"] = generated_at
        cases = sorted(manifest["cases"], key=lambda item: item["case_id"])
        manifest["cases"] = cases

        files = []
        source_images = []
        for case in cases:
            image = self.training_image(case["image"]["image_id"])
            extension = MIME_EXTENSIONS.get(image["mime_type"])
            if not extension:
                raise VisualQcServiceError(
                    "training_image_type_unsupported",
                    "Training image MIME type cannot be packaged.",
                    422,
                )
            source_path = Path(image["storage_path"])
            archive_path = f"images/{case['case_id']}{extension}"
            source_images.append((source_path, archive_path, image["sha256"]))
            files.append({
                "case_id": case["case_id"],
                "image_id": image["image_id"],
                "archive_path": archive_path,
                "mime_type": image["mime_type"],
                "sha256": image["sha256"],
                "byte_size": image["byte_size"],
            })

        required_bytes = sum(file["byte_size"] for file in files) + 1024 * 1024
        free_after_export = (
            shutil.disk_usage(self.settings.data_root).free - required_bytes
        )
        if free_after_export < self.settings.minimum_free_bytes:
            raise VisualQcServiceError(
                "insufficient_storage",
                "Server free-space reserve would be exceeded by the dataset bundle.",
                507,
            )

        coco = build_coco_from_training_manifest(manifest)
        archive_paths = {
            file["case_id"]: file["archive_path"]
            for file in files
        }
        for image in coco["images"]:
            image["file_name"] = archive_paths[image["case_id"]]
        index = {
            "schema_version": "VISUAL-QC-DATASET-BUNDLE-V1",
            "generated_at": generated_at,
            "case_count": len(cases),
            "annotation_count": manifest["annotation_count"],
            "manifest_path": "manifest.json",
            "coco_path": "annotations.coco.json",
            "files": files,
        }

        export_root = self.settings.data_root / "exports"
        export_root.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="visual-qc-training-",
            suffix=".zip",
            dir=export_root,
        )
        os.close(descriptor)
        try:
            with self.storage.reference_transaction():
                for source_path, _archive_path, expected_sha256 in source_images:
                    if not source_path.is_file():
                        raise VisualQcServiceError(
                            "training_image_missing",
                            "Training image storage object is missing.",
                            410,
                        )
                    if self._sha256_file(source_path) != expected_sha256:
                        raise VisualQcServiceError(
                            "training_image_integrity_mismatch",
                            "Training image does not match its governed SHA-256.",
                            409,
                        )
                with zipfile.ZipFile(temporary_name, mode="w") as bundle:
                    bundle.writestr(
                        self._bundle_zip_info("manifest.json"),
                        self._bundle_json_bytes(manifest),
                    )
                    bundle.writestr(
                        self._bundle_zip_info("annotations.coco.json"),
                        self._bundle_json_bytes(coco),
                    )
                    bundle.writestr(
                        self._bundle_zip_info("bundle-index.json"),
                        self._bundle_json_bytes(index),
                    )
                    for source_path, archive_path, _sha256 in source_images:
                        with bundle.open(self._bundle_zip_info(archive_path), "w") as target:
                            with source_path.open("rb") as source:
                                shutil.copyfileobj(source, target, length=1024 * 1024)
            return Path(temporary_name)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise

    def training_audit(self) -> dict:
        cases = []
        reason_counts = {}
        eligible_count = 0
        for record in self.store.list_dataset_audit_cases():
            quality = (record.get("job_result") or {}).get("quality") or {}
            registration_review = self.store.get_latest_registration_review(
                record["case_id"]
            )
            qc_review = self.store.get_latest_case_qc_review(record["case_id"])
            if record["evidence_role"] != "physical_capture":
                reason = "non_physical_evidence"
            else:
                qualified_handoff = self._stored_qualified_handoff(
                    record.get("qualified_handoff_json")
                )
                if qualified_handoff is None:
                    reason = "qualified_handoff_provenance_required"
                elif record["capture_checklist"].get("status") != "confirmed":
                    reason = "capture_checklist_required"
                elif record["job_status"] != "succeeded":
                    reason = "processing_incomplete"
                elif quality.get("status") == "retake":
                    reason = "image_retake_required"
                elif not registration_review:
                    reason = "registration_review_required"
                elif not qc_review:
                    reason = "final_qc_review_required"
                else:
                    reason = None

            status = "eligible" if reason is None else "excluded"
            if status == "eligible":
                eligible_count += 1
            else:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            cases.append({
                "case_id": record["case_id"],
                "board_key": record["board_key"],
                "board_id": record["board_id"],
                "side_id": record["side_id"],
                "capture_stage": record["capture_stage"],
                "evidence_role": record["evidence_role"],
                "image_id": record["image_id"],
                "job_status": record["job_status"],
                "quality_status": quality.get("status"),
                "registration_reviewed": registration_review is not None,
                "final_qc_reviewed": qc_review is not None,
                "status": status,
                "blocking_reason": reason,
                "created_at": record["created_at"],
            })
        return {
            "schema_version": "VISUAL-QC-DATASET-AUDIT-V1",
            "generated_at": utc_now(),
            "total_case_count": len(cases),
            "eligible_case_count": eligible_count,
            "excluded_case_count": len(cases) - eligible_count,
            "reason_counts": dict(sorted(reason_counts.items())),
            "cases": cases,
        }

    def training_image(self, image_id: str) -> dict:
        image = self.store.get_training_image(image_id)
        if not image:
            raise VisualQcServiceError(
                "training_image_not_found",
                "Training image was not found or is not attached to an eligible review.",
                404,
            )
        self._stored_qualified_handoff(image.get("qualified_handoff_json"))
        storage_path = Path(image["storage_path"])
        if not storage_path.is_file():
            raise VisualQcServiceError(
                "training_image_missing",
                "Training image storage object is missing.",
                410,
            )
        return image

    def _capture_session_payload(
        self,
        capture_session_id: str,
        actor_id: str,
        current_case_id: str | None = None,
    ) -> dict:
        records = self.store.list_capture_session(actor_id, capture_session_id)
        first = records[0]
        try:
            board = self.catalog.resolve_board(first["board_key"])
        except CatalogError as exc:
            raise VisualQcServiceError(exc.code, str(exc)) from exc
        expected_side_ids = board["side_ids"]
        captured_side_ids = sorted({record["side_id"] for record in records})
        pair_status = "single_side"
        if len(expected_side_ids) > 1:
            pair_status = (
                "pair_complete"
                if set(expected_side_ids).issubset(captured_side_ids)
                else "pair_in_progress"
            )
        checklist_record = next(
            (
                record
                for record in records
                if record["case_id"] == current_case_id
            ),
            records[-1],
        )
        latest_checklist = json.loads(
            checklist_record["capture_checklist_json"] or "{}"
        )
        return {
            "schema_version": "VISUAL-QC-CAPTURE-SESSION-V1",
            "session_id": capture_session_id,
            "board_key": first["board_key"],
            "board_id": first["board_id"],
            "capture_stage": first["capture_stage"],
            "evidence_role": first["evidence_role"],
            "setup_id": first["capture_setup_id"],
            "expected_side_ids": expected_side_ids,
            "captured_side_ids": captured_side_ids,
            "pair_status": pair_status,
            "checklist": latest_checklist,
            "cases": [
                {
                    "case_id": record["case_id"],
                    "side_id": record["side_id"],
                    "checklist_status": json.loads(
                        record["capture_checklist_json"] or "{}"
                    ).get("status", "pending"),
                    "created_at": record["created_at"],
                }
                for record in records
            ],
        }

    @staticmethod
    def _normalized_capture_session_id(
        value: str | None,
        actor_id: str,
        idempotency_key: str,
    ) -> str:
        normalized = (value or "").strip()
        if not normalized:
            digest = hashlib.sha256(
                f"{actor_id}:{idempotency_key}".encode("utf-8")
            ).hexdigest()[:24]
            normalized = f"legacy-{digest}"
        if len(normalized) > 128 or not all(
            character.isalnum() or character in "-_." for character in normalized
        ):
            raise VisualQcServiceError(
                "invalid_capture_session_id",
                "capture_session_id must use letters, numbers, dot, dash, or underscore and be at most 128 characters.",
            )
        return normalized

    @staticmethod
    def _normalized_capture_setup_id(value: str) -> str:
        normalized = (value or "").strip()
        if not normalized or len(normalized) > 128:
            raise VisualQcServiceError(
                "invalid_capture_setup_id",
                "capture_setup_id is required and must not exceed 128 characters.",
            )
        return normalized

    @staticmethod
    def _normalized_intake_provenance(
        batch_id: str | None,
        entry_id: str | None,
    ) -> tuple[str | None, str | None]:
        normalized_batch = (batch_id or "").strip() or None
        normalized_entry = (entry_id or "").strip() or None
        if (normalized_batch is None) != (normalized_entry is None):
            raise VisualQcServiceError(
                "incomplete_intake_provenance",
                "intake_batch_id and intake_entry_id must be provided together.",
            )
        for field, value in (
            ("intake_batch_id", normalized_batch),
            ("intake_entry_id", normalized_entry),
        ):
            if value is not None and (
                len(value) > 128
                or not value[0].isalnum()
                or not all(character.isalnum() or character in "-_." for character in value)
            ):
                raise VisualQcServiceError(
                    "invalid_intake_provenance",
                    f"{field} must use letters, numbers, dot, dash, or underscore and be at most 128 characters.",
                )
        return normalized_batch, normalized_entry

    @staticmethod
    def _normalized_qualified_handoff(
        *,
        evidence_role: str,
        raw: str | None,
        intake_batch_id: str | None,
        intake_entry_id: str | None,
    ) -> dict | None:
        if evidence_role == "physical_capture":
            if (
                intake_batch_id is None
                or intake_entry_id is None
                or raw is None
                or not raw.strip()
            ):
                raise VisualQcServiceError(
                    "physical_handoff_provenance_required",
                    "Physical capture requires controlled intake and qualified handoff provenance.",
                )
            try:
                return normalize_qualified_handoff(raw)
            except QualifiedHandoffError as exc:
                raise VisualQcServiceError(
                    "invalid_qualified_handoff",
                    str(exc),
                ) from exc
        if raw is not None and raw.strip():
            raise VisualQcServiceError(
                "qualified_handoff_not_allowed",
                "Qualified handoff provenance is allowed only for physical capture.",
            )
        return None

    @staticmethod
    def _stored_qualified_handoff(raw: str | None) -> dict | None:
        if raw is None:
            return None
        try:
            return normalize_qualified_handoff(raw)
        except QualifiedHandoffError as exc:
            raise VisualQcServiceError(
                "stored_qualified_handoff_invalid",
                "Stored qualified handoff provenance is invalid.",
                500,
            ) from exc

    @staticmethod
    def _normalized_capture_checklist(value: str, evidence_role: str) -> dict:
        try:
            parsed = json.loads(value or "{}")
        except json.JSONDecodeError as exc:
            raise VisualQcServiceError(
                "invalid_capture_checklist",
                "capture_checklist must be valid JSON.",
            ) from exc
        if not isinstance(parsed, dict):
            raise VisualQcServiceError(
                "invalid_capture_checklist",
                "capture_checklist must be a JSON object.",
            )
        if evidence_role != "physical_capture":
            return {"status": "not_applicable", "items": {}, "confirmed_at": None}
        items = parsed.get("items") if isinstance(parsed.get("items"), dict) else {}
        normalized_items = {
            key: items.get(key) is True
            for key in sorted(CAPTURE_CHECKLIST_ITEMS)
        }
        status = (
            "confirmed"
            if all(normalized_items.values())
            else "pending"
        )
        return {
            "status": status,
            "items": normalized_items,
            "confirmed_at": parsed.get("confirmed_at") if status == "confirmed" else None,
        }

    def get_job(self, job_id: str, actor_id: str) -> dict:
        record = self.store.get_job(job_id)
        if not record or record["actor_id"] != actor_id:
            raise VisualQcServiceError("job_not_found", "Visual-QC job was not found.", 404)
        result = self._public_job(record)
        if record["job_type"] == "difference_candidates":
            result["candidate_reviews"] = self.store.list_candidate_reviews(job_id)
        return result

    def retry_job(self, job_id: str, actor_id: str) -> dict:
        record = self.store.get_job(job_id)
        if not record or record["actor_id"] != actor_id:
            raise VisualQcServiceError("job_not_found", "Visual-QC job was not found.", 404)
        if record["status"] != "failed":
            raise VisualQcServiceError(
                "job_not_retryable",
                "Only failed jobs can be retried.",
                409,
            )
        retried = self.store.retry_failed_job(job_id)
        if not retried:
            raise VisualQcServiceError(
                "job_retry_conflict",
                "Job state changed before the retry was accepted.",
                409,
            )
        return self._public_job(retried)

    def review_registration(
        self,
        case_id: str,
        actor_id: str,
        decision: str,
        notes: str,
        board_to_image_matrix: list[float] | None = None,
        anchors: list[dict] | None = None,
        check_points: list[dict] | None = None,
        error: dict | None = None,
    ) -> dict:
        record = self.store.get_case(case_id)
        if not record or record["case"]["actor_id"] != actor_id:
            raise VisualQcServiceError("case_not_found", "Visual-QC case was not found.", 404)
        job = record["job"]
        registration = (job.get("result") or {}).get("registration") or {}
        if job["status"] != "succeeded":
            raise VisualQcServiceError(
                "completed_registration_job_required",
                "A completed registration job is required before review.",
                409,
            )
        if decision == "accept_automatic":
            if registration.get("status") != "candidate":
                raise VisualQcServiceError(
                    "automatic_candidate_required",
                    "A successful automatic registration candidate is required for this decision.",
                    409,
                )
            method = registration["method"]
            matrix = registration["board_to_image_matrix"]
            reviewed_anchors = []
            reviewed_check_points = []
            reviewed_error = {
                "count": 0,
                "rms": None,
                "maximum": None,
            }
        elif decision == "accept_manual":
            matrix = self._validate_manual_registration(
                board_to_image_matrix,
                anchors or [],
            )
            reviewed_check_points, reviewed_error = (
                self._validate_manual_check_points(
                    matrix,
                    check_points or [],
                    error or {},
                )
            )
            method = "reviewed_manual_four_point"
            reviewed_anchors = anchors or []
        else:
            raise VisualQcServiceError(
                "unsupported_review_decision",
                f"Unsupported registration review decision: {decision}",
            )
        existing = self.store.get_latest_registration_review(case_id)
        if existing:
            if existing["decision"] != decision:
                raise VisualQcServiceError(
                    "registration_already_reviewed",
                    "Registration review is immutable; create a new case to use a different method.",
                    409,
                )
            return existing
        review = {
            "review_id": f"regrev_{uuid.uuid4().hex}",
            "case_id": case_id,
            "job_id": job["job_id"],
            "reviewer_id": actor_id,
            "decision": decision,
            "method": method,
            "board_to_image_matrix": matrix,
            "anchors": reviewed_anchors,
            "check_points": reviewed_check_points,
            "error": reviewed_error,
            "notes": notes[:1000],
            "created_at": utc_now(),
        }
        return self.store.create_registration_review(review)

    @staticmethod
    def _validate_manual_registration(
        matrix_values: list[float] | None,
        anchors: list[dict],
    ) -> list[float]:
        if matrix_values is None or len(matrix_values) != 9:
            raise VisualQcServiceError(
                "invalid_homography",
                "Manual registration requires exactly nine matrix values.",
            )
        matrix = np.asarray(matrix_values, dtype=np.float64).reshape(3, 3)
        if not np.isfinite(matrix).all() or abs(float(np.linalg.det(matrix))) < 1e-8:
            raise VisualQcServiceError(
                "degenerate_homography",
                "Manual registration matrix is singular or non-finite.",
            )
        if abs(float(matrix[2, 2])) < 1e-10:
            raise VisualQcServiceError(
                "degenerate_homography",
                "Manual registration matrix cannot be normalized.",
            )
        matrix /= matrix[2, 2]

        if len(anchors) != 4:
            raise VisualQcServiceError(
                "invalid_manual_anchors",
                "Manual registration requires exactly four anchor pairs.",
            )
        for anchor in anchors:
            for key in ("board", "image"):
                point = anchor.get(key)
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or not all(
                        isinstance(value, (int, float))
                        and np.isfinite(value)
                        and 0 <= value <= 1
                        for value in point
                    )
                ):
                    raise VisualQcServiceError(
                        "invalid_manual_anchors",
                        "Manual anchor coordinates must be normalized pairs.",
                    )
        for key in ("board", "image"):
            unique = {
                (round(float(anchor[key][0]), 8), round(float(anchor[key][1]), 8))
                for anchor in anchors
            }
            if len(unique) != 4:
                raise VisualQcServiceError(
                    "duplicate_manual_anchors",
                    "Manual registration anchors must be unique.",
                )

        board_points = np.asarray(
            [[anchor["board"]] for anchor in anchors],
            dtype=np.float64,
        )
        image_points = np.asarray(
            [anchor["image"] for anchor in anchors],
            dtype=np.float64,
        )
        projected_anchors = cv2.perspectiveTransform(
            board_points,
            matrix,
        ).reshape(-1, 2)
        anchor_errors = np.linalg.norm(projected_anchors - image_points, axis=1)
        if float(np.max(anchor_errors)) > 0.015:
            raise VisualQcServiceError(
                "manual_anchor_matrix_mismatch",
                "Manual matrix does not reproduce the reviewed anchor pairs.",
            )

        corners = np.asarray(
            [[[0, 0]], [[1, 0]], [[1, 1]], [[0, 1]]],
            dtype=np.float64,
        )
        projected = cv2.perspectiveTransform(corners, matrix).reshape(-1, 2)
        if not np.isfinite(projected).all():
            raise VisualQcServiceError(
                "degenerate_homography",
                "Manual registration projects non-finite board coordinates.",
            )
        contour = projected.astype(np.float32).reshape(-1, 1, 2)
        area = abs(float(cv2.contourArea(contour)))
        if not cv2.isContourConvex(contour) or not 0.01 <= area <= 4:
            raise VisualQcServiceError(
                "degenerate_homography",
                "Manual registration projects an invalid board shape.",
            )
        return matrix.reshape(-1).tolist()

    @staticmethod
    def _validate_manual_check_points(
        matrix_values: list[float],
        check_points: list[dict],
        error: dict,
    ) -> tuple[list[dict], dict]:
        if not check_points:
            return [], {"count": 0, "rms": None, "maximum": None}
        for pair in check_points:
            for key in ("board", "image"):
                point = pair.get(key) if isinstance(pair, dict) else None
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or not all(
                        isinstance(value, (int, float))
                        and np.isfinite(value)
                        and 0 <= value <= 1
                        for value in point
                    )
                ):
                    raise VisualQcServiceError(
                        "invalid_manual_check_points",
                        "Manual check-point coordinates must be normalized pairs.",
                    )
        matrix = np.asarray(matrix_values, dtype=np.float64).reshape(3, 3)
        board_points = np.asarray(
            [[pair["board"]] for pair in check_points],
            dtype=np.float64,
        )
        image_points = np.asarray(
            [pair["image"] for pair in check_points],
            dtype=np.float64,
        )
        projected = cv2.perspectiveTransform(board_points, matrix).reshape(-1, 2)
        errors = np.linalg.norm(projected - image_points, axis=1)
        expected = {
            "count": len(check_points),
            "rms": float(np.sqrt(np.mean(np.square(errors)))),
            "maximum": float(np.max(errors)),
        }
        if error.get("count") != expected["count"] or any(
            not isinstance(error.get(key), (int, float))
            or abs(float(error[key]) - expected[key]) > 1e-5
            for key in ("rms", "maximum")
        ):
            raise VisualQcServiceError(
                "manual_check_error_mismatch",
                "Manual registration error must match its independent check points.",
            )
        return check_points, expected

    def create_golden_sample(
        self,
        *,
        case_id: str,
        capture_setup_id: str,
        confirmed_normal: bool,
        reviewer_id: str,
    ) -> dict:
        if not confirmed_normal:
            raise VisualQcServiceError(
                "normal_confirmation_required",
                "Golden Sample creation requires an explicit normal-board confirmation.",
                409,
            )
        if not capture_setup_id.strip() or len(capture_setup_id) > 128:
            raise VisualQcServiceError(
                "invalid_capture_setup",
                "capture_setup_id is required and must not exceed 128 characters.",
            )
        record = self.store.get_case(case_id)
        if not record:
            raise VisualQcServiceError("case_not_found", "Visual-QC case was not found.", 404)
        case = record["case"]
        image = record["image"]
        job = record["job"]
        if case["evidence_role"] != "physical_capture":
            raise VisualQcServiceError(
                "physical_capture_required",
                "Proxy and synthetic images cannot become Golden Samples.",
                409,
            )
        if case["capture_stage"] != "golden_reference":
            raise VisualQcServiceError(
                "golden_reference_stage_required",
                "Golden Sample creation requires a golden_reference capture.",
                409,
            )
        capture_checklist = json.loads(case["capture_checklist_json"] or "{}")
        if capture_checklist.get("status") != "confirmed":
            raise VisualQcServiceError(
                "capture_checklist_confirmation_required",
                "Golden Sample creation requires a confirmed physical capture checklist.",
                409,
            )
        if capture_setup_id.strip() != case["capture_setup_id"]:
            raise VisualQcServiceError(
                "capture_setup_mismatch",
                "Golden Sample setup must match the original capture session.",
                409,
            )
        review = self.store.get_latest_registration_review(case_id)
        if not review:
            raise VisualQcServiceError(
                "reviewed_registration_required",
                "Golden Sample creation requires reviewed registration.",
                409,
            )
        quality = (job.get("result") or {}).get("quality") or {}
        if quality.get("status") == "retake":
            raise VisualQcServiceError(
                "acceptable_image_quality_required",
                "Retake-quality images cannot become Golden Samples.",
                409,
            )
        golden = {
            "golden_sample_id": f"gold_{uuid.uuid4().hex}",
            "case_id": case_id,
            "registration_review_id": review["review_id"],
            "board_key": case["board_key"],
            "board_id": case["board_id"],
            "side_id": case["side_id"],
            "capture_setup_id": capture_setup_id.strip(),
            "source_sha256": image["sha256"],
            "reviewer_id": reviewer_id,
            "created_at": utc_now(),
        }
        return self.store.create_golden_sample(golden)

    def get_active_golden_sample(
        self,
        board_key: str,
        side_id: str,
        capture_setup_id: str,
    ) -> dict:
        try:
            self.catalog.resolve_side(board_key, side_id)
        except CatalogError as exc:
            raise VisualQcServiceError(exc.code, str(exc)) from exc
        record = self.store.get_active_golden_sample(
            board_key,
            side_id,
            capture_setup_id,
        )
        if not record:
            raise VisualQcServiceError(
                "golden_sample_not_found",
                "No active Golden Sample exists for this board-side capture setup.",
                404,
            )
        return record

    def create_difference_job(
        self,
        case_id: str,
        capture_setup_id: str,
        actor_id: str,
    ) -> dict:
        record = self.store.get_case(case_id)
        if not record or record["case"]["actor_id"] != actor_id:
            raise VisualQcServiceError("case_not_found", "Visual-QC case was not found.", 404)
        case = record["case"]
        review = self.store.get_latest_registration_review(case_id)
        if not review:
            raise VisualQcServiceError(
                "reviewed_registration_required",
                "Difference processing requires reviewed registration.",
                409,
            )
        golden = self.store.get_active_golden_sample(
            case["board_key"],
            case["side_id"],
            capture_setup_id,
        )
        if not golden:
            raise VisualQcServiceError(
                "golden_sample_not_found",
                "No active Golden Sample exists for this capture setup.",
                404,
            )
        timestamp = utc_now()
        job = self.store.create_job(
            {
                "job_id": f"job_{uuid.uuid4().hex}",
                "case_id": case_id,
                "image_id": record["image"]["image_id"],
                "job_type": "difference_candidates",
                "input": {
                    "golden_sample_id": golden["golden_sample_id"],
                    "registration_review_id": review["review_id"],
                },
                "dedupe_key": (
                    f"difference:{case_id}:{golden['golden_sample_id']}:"
                    f"{review['review_id']}"
                ),
                "created_at": timestamp,
            }
        )
        return self._public_job(job)

    def get_artifact(self, artifact_id: str, actor_id: str) -> dict:
        artifact = self.store.get_artifact(artifact_id)
        if not artifact or artifact["actor_id"] != actor_id:
            raise VisualQcServiceError("artifact_not_found", "Artifact was not found.", 404)
        return artifact

    def review_difference_candidate(
        self,
        *,
        job_id: str,
        candidate_id: str,
        decision: str,
        defect_category: str | None,
        notes: str,
        actor_id: str,
    ) -> dict:
        job = self.store.get_job(job_id)
        if not job or job["actor_id"] != actor_id:
            raise VisualQcServiceError("job_not_found", "Visual-QC job was not found.", 404)
        result = job.get("result") or {}
        if (
            job["job_type"] != "difference_candidates"
            or job["status"] != "succeeded"
            or result.get("schema_version") != "VISUAL-QC-DIFFERENCE-CANDIDATES-V1"
        ):
            raise VisualQcServiceError(
                "difference_candidate_job_required",
                "A completed difference-candidate job is required.",
                409,
            )
        if decision not in CANDIDATE_REVIEW_DECISIONS:
            raise VisualQcServiceError(
                "invalid_candidate_decision",
                f"Unsupported candidate decision: {decision}",
            )
        candidate = next(
            (
                item
                for item in result.get("candidates", [])
                if item["candidate_id"] == candidate_id
            ),
            None,
        )
        if not candidate:
            raise VisualQcServiceError(
                "candidate_not_found",
                "Difference candidate was not found in this job.",
                404,
            )
        if decision == "confirmed" and defect_category not in DEFECT_CATEGORIES:
            code = "defect_category_required" if not defect_category else "invalid_defect_category"
            raise VisualQcServiceError(
                code,
                "Confirmed candidates require a supported human defect category.",
            )
        if decision != "confirmed":
            defect_category = None
        review = {
            "candidate_review_id": f"candrev_{uuid.uuid4().hex}",
            "case_id": job["case_id"],
            "job_id": job_id,
            "candidate_id": candidate_id,
            "reviewer_id": actor_id,
            "decision": decision,
            "defect_category": defect_category,
            "label_source": (
                "human_annotation" if decision == "confirmed" else "human_review"
            ),
            "candidate": candidate,
            "notes": notes[:1000],
            "created_at": utc_now(),
        }
        return self.store.create_candidate_review(review)

    def process_next_job(self):
        job = self.store.claim_next_job()
        if not job:
            return None
        try:
            if not Path(job["storage_path"]).is_file():
                raise RuntimeError("uploaded image is missing")
            capture = cv2.imread(job["storage_path"], cv2.IMREAD_COLOR)
            if capture is None:
                raise RuntimeError("uploaded image could not be decoded")
            if job["job_type"] == "automatic_registration":
                result = self._process_registration_job(job, capture)
            elif job["job_type"] == "difference_candidates":
                result = self._process_difference_job(job, capture)
            else:
                raise RuntimeError(f"unsupported job type: {job['job_type']}")
            completed = self.store.complete_job(job["job_id"], result)
            return self._public_job(completed)
        except Exception as exc:
            failed = self.store.fail_job(
                job["job_id"],
                "processing_failed",
                str(exc),
            )
            return self._public_job(failed)

    def _process_registration_job(self, job: dict, capture: np.ndarray) -> dict:
        if not Path(job["reference_path"]).is_file():
            raise RuntimeError("selected board reference is missing")
        reference = cv2.imread(job["reference_path"], cv2.IMREAD_COLOR)
        if reference is None:
            raise RuntimeError("selected board reference could not be decoded")
        return {
            "schema_version": "VISUAL-QC-SERVER-JOB-RESULT-V1",
            "quality": analyze_image_quality(capture),
            "registration": register_board_image(
                reference,
                capture,
                RegistrationConfig(max_dimension=1600),
            ),
        }

    def _process_difference_job(self, job: dict, capture: np.ndarray) -> dict:
        golden = self.store.get_golden_sample_material(
            job["input"]["golden_sample_id"]
        )
        current_review = self.store.get_latest_registration_review(job["case_id"])
        if not golden or not current_review:
            raise RuntimeError("reviewed difference inputs are no longer available")
        if not Path(golden["storage_path"]).is_file():
            raise RuntimeError("Golden Sample image is missing")
        golden_image = cv2.imread(golden["storage_path"], cv2.IMREAD_COLOR)
        if golden_image is None:
            raise RuntimeError("Golden Sample image could not be decoded")
        result, heatmap_bytes = generate_difference_candidates(
            golden_image,
            golden["board_to_image_matrix"],
            capture,
            current_review["board_to_image_matrix"],
        )
        artifact_sha256 = hashlib.sha256(heatmap_bytes).hexdigest()
        with self.storage.reference_transaction():
            artifact_path = self.storage.put_artifact(
                heatmap_bytes,
                artifact_sha256,
                ".png",
            )
            artifact = self.store.create_artifact(
                {
                    "artifact_id": f"artifact_{uuid.uuid4().hex}",
                    "case_id": job["case_id"],
                    "job_id": job["job_id"],
                    "kind": "difference_heatmap",
                    "mime_type": "image/png",
                    "sha256": artifact_sha256,
                    "byte_size": len(heatmap_bytes),
                    "storage_path": str(artifact_path),
                    "created_at": utc_now(),
                }
            )
        result["golden_sample_id"] = golden["golden_sample_id"]
        result["heatmap"] = {
            "artifact_id": artifact["artifact_id"],
            "mime_type": artifact["mime_type"],
            "sha256": artifact["sha256"],
            "byte_size": artifact["byte_size"],
        }
        return result

    def start_workers(self):
        if self._workers or self.settings.worker_count <= 0:
            return
        self._stop_event.clear()
        for index in range(self.settings.worker_count):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"visual-qc-worker-{index + 1}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)

    def stop_workers(self):
        self._stop_event.set()
        for worker in self._workers:
            worker.join(timeout=5)
        self._workers.clear()

    def _worker_loop(self):
        while not self._stop_event.is_set():
            if self.process_next_job() is None:
                self._stop_event.wait(0.25)

    @staticmethod
    def _public_job(job: dict) -> dict:
        return {
            "job_id": job["job_id"],
            "case_id": job["case_id"],
            "job_type": job["job_type"],
            "status": job["status"],
            "attempt_count": job["attempt_count"],
            "result": job.get("result"),
            "error": (
                {
                    "code": job["error_code"],
                    "message": job["error_message"],
                }
                if job.get("error_code")
                else None
            ),
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
        }
