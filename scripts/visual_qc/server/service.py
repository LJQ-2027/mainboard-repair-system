from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading
import uuid

import cv2
import numpy as np

from scripts.visual_qc.registration import RegistrationConfig, register_board_image
from scripts.export_visual_qc_coco import build_coco_from_training_manifest
from scripts.validate_visual_qc_dataset import validate_visual_qc_case
from scripts.visual_qc.server.catalog import BoardCatalog, CatalogError
from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.difference import generate_difference_candidates
from scripts.visual_qc.server.quality import analyze_image_quality
from scripts.visual_qc.server.storage import (
    LocalObjectStorage,
    StorageCleanupError,
    StorageError,
    detect_image_mime_type,
)
from scripts.visual_qc.server.store import (
    CaptureSessionIdentityConflict,
    VisualQcStore,
    utc_now,
)


CAPTURE_STAGES = {"golden_reference", "before_repair", "after_repair"}
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
        candidates = self.store.list_retention_candidates(
            cutoff_at,
            self.settings.retention_batch_limit,
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
                },
                "created_at": timestamp,
            }
        )
        deleted_ids = []
        object_result = {"deleted_objects": 0, "deleted_bytes": 0}
        try:
            with self.storage.reference_transaction():
                deleted_ids = self.store.delete_retention_candidates(
                    candidates,
                    cutoff_at,
                )
                deleted_paths = [
                    path
                    for candidate in candidates
                    if candidate["case_id"] in deleted_ids
                    for path in candidate["storage_paths"]
                ]
                object_result = self.storage.delete_unreferenced(
                    deleted_paths,
                    self.store.storage_path_is_referenced,
                )
            self.store.complete_retention_run(
                run_id,
                len(deleted_ids),
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
                len(deleted_ids),
                object_result["deleted_objects"],
                object_result["deleted_bytes"],
                str(exc),
                utc_now(),
            )
            raise
        result.update(
            {
                "run_id": run_id,
                "deleted_cases": len(deleted_ids),
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
            "schema_version": "VISUAL-QC-SERVER-CASE-V1",
            "case_id": case["case_id"],
            "board_key": case["board_key"],
            "board_id": case["board_id"],
            "side_id": case["side_id"],
            "capture_stage": case["capture_stage"],
            "evidence_role": case["evidence_role"],
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
