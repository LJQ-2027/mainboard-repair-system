from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from scripts.visual_qc.server.config import VisualQcServerSettings
from scripts.visual_qc.server.service import VisualQcService, VisualQcServiceError


class RegistrationReviewRequest(BaseModel):
    decision: str
    notes: str = Field(default="", max_length=1000)
    board_to_image_matrix: list[float] | None = None
    anchors: list[dict] = Field(default_factory=list)
    check_points: list[dict] = Field(default_factory=list)
    error: dict = Field(
        default_factory=lambda: {
            "count": 0,
            "rms": None,
            "maximum": None,
        }
    )


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


class FinalQcReviewRequest(BaseModel):
    qc_result: str
    annotations: list[dict] = Field(default_factory=list, max_length=1000)
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

    @app.middleware("http")
    async def protect_visual_intake(request: Request, call_next):
        if (
            request.method == "POST"
            and request.url.path.rstrip("/") == "/api/v1/visual-qc/cases"
            and request.headers.get("X-Actor-Role") != "reviewer"
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": {
                        "code": "data_admin_role_required",
                        "message": "Visual data intake requires the data administrator role.",
                    }
                },
            )
        return await call_next(request)

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

    def require_data_admin(role: str | None):
        if role != "reviewer":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "data_admin_role_required",
                    "message": "Visual data management requires the data administrator role.",
                },
            )

    @app.get("/api/v1/visual-qc/health")
    def health():
        return service.health()

    @app.get("/api/v1/visual-qc/identity")
    def identity(
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        return {
            "schema_version": "VISUAL-QC-IDENTITY-V1",
            "actor_id": actor_id(x_actor_id),
            "role": "reviewer" if x_actor_role == "reviewer" else "technician",
        }

    @app.post("/api/v1/visual-qc/cases", status_code=202)
    async def create_case(
        board_key: str = Form(...),
        side_id: str = Form(...),
        capture_stage: str = Form(...),
        evidence_role: str = Form(...),
        capture_session_id: str | None = Form(None),
        capture_setup_id: str = Form("standard-bench"),
        capture_checklist: str = Form("{}"),
        intake_batch_id: str | None = Form(None, max_length=128),
        intake_entry_id: str | None = Form(None, max_length=128),
        sha256: str = Form(..., min_length=64, max_length=64),
        file: UploadFile = File(...),
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    ):
        if x_actor_role != "reviewer":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "data_admin_role_required",
                    "message": "Visual data intake requires the data administrator role.",
                },
            )
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
                capture_session_id=capture_session_id,
                capture_setup_id=capture_setup_id,
                capture_checklist=capture_checklist,
                intake_batch_id=intake_batch_id,
                intake_entry_id=intake_entry_id,
                claimed_sha256=sha256,
                original_filename=file.filename or "upload",
                mime_type=(file.content_type or "").lower(),
                content=content,
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.get("/api/v1/visual-qc/capture-sessions/{capture_session_id}")
    def get_capture_session(
        capture_session_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            return service.get_capture_session(
                capture_session_id,
                actor_id(x_actor_id),
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

    @app.get("/api/v1/visual-qc/admin/cases")
    def list_admin_cases(
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=100),
        board_key: str | None = None,
        side_id: str | None = None,
        capture_stage: str | None = None,
        state: str | None = None,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        require_data_admin(x_actor_role)
        try:
            return service.list_admin_cases(
                actor_id(x_actor_id),
                board_key=board_key,
                side_id=side_id,
                capture_stage=capture_stage,
                state=state,
                page=page,
                page_size=page_size,
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.get("/api/v1/visual-qc/admin/cases/{case_id}")
    def get_admin_case(
        case_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        require_data_admin(x_actor_role)
        try:
            return service.get_admin_case(case_id, actor_id(x_actor_id))
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.get("/api/v1/visual-qc/admin/cases/{case_id}/image")
    def get_admin_case_original(
        case_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        require_data_admin(x_actor_role)
        try:
            original = service.get_admin_case_original(case_id, actor_id(x_actor_id))
            return FileResponse(
                original["storage_path"],
                media_type=original["mime_type"],
                filename=original["original_filename"],
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.post(
        "/api/v1/visual-qc/cases/{case_id}/qc-reviews",
        status_code=201,
    )
    def review_case_qc(
        case_id: str,
        request: FinalQcReviewRequest,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
    ):
        try:
            return service.review_case_qc(
                case_id=case_id,
                actor_id=actor_id(x_actor_id),
                qc_result=request.qc_result,
                annotations=request.annotations,
                notes=request.notes,
            )
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
                request.check_points,
                request.error,
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
        allow_missing: bool = False,
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
            if allow_missing and exc.code == "golden_sample_not_found":
                return {
                    "schema_version": "VISUAL-QC-GOLDEN-LOOKUP-V1",
                    "status": "missing",
                    "board_key": board_key,
                    "side_id": side_id,
                    "capture_setup_id": capture_setup_id,
                }
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

    @app.get("/api/v1/visual-qc/datasets/training-manifest")
    def training_manifest(
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        actor_id(x_actor_id)
        if x_actor_role != "reviewer":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "reviewer_role_required",
                    "message": "Training dataset export requires the reviewer role.",
                },
            )
        return service.training_manifest()

    @app.get("/api/v1/visual-qc/datasets/images/{image_id}")
    def training_image(
        image_id: str,
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        actor_id(x_actor_id)
        if x_actor_role != "reviewer":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "reviewer_role_required",
                    "message": "Training image export requires the reviewer role.",
                },
            )
        try:
            image = service.training_image(image_id)
            return FileResponse(
                image["storage_path"],
                media_type=image["mime_type"],
                filename=image["original_filename"],
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    @app.get("/api/v1/visual-qc/datasets/coco")
    def training_coco(
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        actor_id(x_actor_id)
        if x_actor_role != "reviewer":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "reviewer_role_required",
                    "message": "COCO dataset export requires the reviewer role.",
                },
            )
        return service.training_coco()

    @app.get("/api/v1/visual-qc/datasets/audit")
    def training_audit(
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        actor_id(x_actor_id)
        if x_actor_role != "reviewer":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "reviewer_role_required",
                    "message": "Dataset readiness audit requires the reviewer role.",
                },
            )
        return service.training_audit()

    @app.get("/api/v1/visual-qc/datasets/bundle")
    def training_bundle(
        x_actor_id: str | None = Header(None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    ):
        actor_id(x_actor_id)
        if x_actor_role != "reviewer":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "reviewer_role_required",
                    "message": "Training dataset bundle export requires the reviewer role.",
                },
            )
        try:
            bundle_path = service.training_bundle()
            return FileResponse(
                bundle_path,
                media_type="application/zip",
                filename="visual-qc-training-dataset.zip",
                background=BackgroundTask(bundle_path.unlink, missing_ok=True),
            )
        except VisualQcServiceError as exc:
            service_error(exc)

    return app


app = create_app()
