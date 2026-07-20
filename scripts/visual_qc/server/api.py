from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.service import VisualQcService, VisualQcServiceError


class RegistrationReviewRequest(BaseModel):
    decision: str
    notes: str = Field(default="", max_length=1000)
    board_to_image_matrix: list[float] | None = None
    anchors: list[dict] = Field(default_factory=list)


class GoldenSampleRequest(BaseModel):
    case_id: str
    capture_setup_id: str = Field(min_length=1, max_length=128)
    confirmed_normal: bool


class DifferenceJobRequest(BaseModel):
    capture_setup_id: str = Field(min_length=1, max_length=128)


class CandidateReviewRequest(BaseModel):
    candidate_id: str
    decision: str
    defect_category: str | None = None
    notes: str = Field(default="", max_length=1000)


def create_app(settings: VisualQcServerSettings | None = None) -> FastAPI:
    settings = settings or VisualQcServerSettings.from_environment()
    service = VisualQcService(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        service.start_workers()
        try:
            yield
        finally:
            service.stop_workers()

    app = FastAPI(
        title="Mainboard Repair Visual QC API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.visual_qc_service = service
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Idempotency-Key",
                "X-Actor-Id",
                "X-Actor-Role",
            ],
        )

    def actor_id(value: str | None):
        if not value or not value.strip():
            raise HTTPException(
                status_code=401,
                detail={"code": "actor_required", "message": "Verified actor identity is required."},
            )
        return value.strip()

    def service_error(exc: VisualQcServiceError):
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    @app.get("/api/v1/visual-qc/health")
    def health():
        return {
            "status": "ok",
            "service": "visual-qc",
            "schema_version": "VISUAL-QC-SERVER-CASE-V1",
            "workers": settings.worker_count,
        }

    @app.post("/api/v1/visual-qc/cases", status_code=202)
    async def create_case(
        board_key: str = Form(...),
        side_id: str = Form(...),
        capture_stage: str = Form(...),
        evidence_role: str = Form(...),
        sha256: str = Form(..., min_length=64, max_length=64),
        file: UploadFile = File(...),
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    ):
        verified_actor = actor_id(x_actor_id)
        content = await file.read(settings.maximum_upload_bytes + 1)
        try:
            return service.create_case(
                actor_id=verified_actor,
                idempotency_key=idempotency_key or "",
                board_key=board_key,
                side_id=side_id,
                capture_stage=capture_stage,
                evidence_role=evidence_role,
                claimed_sha256=sha256,
                original_filename=file.filename or "upload",
                mime_type=(file.content_type or "").lower(),
                content=content,
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.get("/api/v1/visual-qc/cases/{case_id}")
    def get_case(
        case_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            return service.get_case(case_id, actor_id(x_actor_id))
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.get("/api/v1/visual-qc/jobs/{job_id}")
    def get_job(
        job_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            return service.get_job(job_id, actor_id(x_actor_id))
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.post("/api/v1/visual-qc/jobs/{job_id}/retry", status_code=202)
    def retry_job(
        job_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            return service.retry_job(job_id, actor_id(x_actor_id))
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.post(
        "/api/v1/visual-qc/cases/{case_id}/registration-reviews",
        status_code=201,
    )
    def review_registration(
        case_id: str,
        request: RegistrationReviewRequest,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            return service.review_registration(
                case_id,
                actor_id(x_actor_id),
                request.decision,
                request.notes,
                request.board_to_image_matrix,
                request.anchors,
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.post("/api/v1/visual-qc/golden-samples", status_code=201)
    def create_golden_sample(
        request: GoldenSampleRequest,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        verified_actor = actor_id(x_actor_id)
        if x_actor_role != "reviewer":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "reviewer_role_required",
                    "message": "Golden Sample approval requires the reviewer role.",
                },
            )
        try:
            return service.create_golden_sample(
                case_id=request.case_id,
                capture_setup_id=request.capture_setup_id,
                confirmed_normal=request.confirmed_normal,
                reviewer_id=verified_actor,
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.get("/api/v1/visual-qc/golden-samples/active")
    def get_active_golden_sample(
        board_key: str,
        side_id: str,
        capture_setup_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        actor_id(x_actor_id)
        try:
            return service.get_active_golden_sample(
                board_key,
                side_id,
                capture_setup_id,
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.post(
        "/api/v1/visual-qc/cases/{case_id}/difference-jobs",
        status_code=202,
    )
    def create_difference_job(
        case_id: str,
        request: DifferenceJobRequest,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            return service.create_difference_job(
                case_id,
                request.capture_setup_id,
                actor_id(x_actor_id),
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.get("/api/v1/visual-qc/artifacts/{artifact_id}")
    def get_artifact(
        artifact_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            artifact = service.get_artifact(artifact_id, actor_id(x_actor_id))
            return FileResponse(
                artifact["storage_path"],
                media_type=artifact["mime_type"],
                filename=f"{artifact_id}.png",
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.post(
        "/api/v1/visual-qc/jobs/{job_id}/candidate-reviews",
        status_code=201,
    )
    def review_difference_candidate(
        job_id: str,
        request: CandidateReviewRequest,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            return service.review_difference_candidate(
                job_id=job_id,
                candidate_id=request.candidate_id,
                decision=request.decision,
                defect_category=request.defect_category,
                notes=request.notes,
                actor_id=actor_id(x_actor_id),
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    return app


app = create_app()
