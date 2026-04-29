from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import select

from ... import __version__
from ...api.deps import SessionDep, require_admin
from ...core.config import settings
from ...core.log_buffer import get_app_log_buffer, json_sse_event
from ...db.models import Assignment, AssignmentStudent, GradingModel, Submission, User, UserRole
from ...grading.grading_model_service import get_active_grading_model, list_grading_models
from ...schemas import AssignmentRead, SubmissionRead, UserRead
from ...schemas.admin import (
    AdminConfigResponse,
    AdminUserInsightsResponse,
    CompletenessProviderResponse,
    CompletenessProviderUpdate,
    StudentEnrollmentItem,
)
from ...schemas.grading_model import (
    GradingModelCreate,
    GradingModelRead,
    GradingModelUpdate,
    GradingStatusResponse,
)
from ...grading.workflow_settings_service import get_completeness_provider, set_completeness_provider
from ...workflow_runtime.config import CFG
from ...workflow_runtime.llm_clients import endpoint_health_url_from_openai_base


router = APIRouter(prefix="/admin", tags=["admin"])


def _user_read(u: User) -> UserRead:
    return UserRead(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        student_id_number=u.student_id_number,
        is_active=u.is_active,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


def _assignment_read(a: Assignment) -> AssignmentRead:
    return AssignmentRead(
        id=a.id,
        title=a.title,
        description=a.description,
        teacher_id=a.teacher_id,
        due_date=a.due_date,
        created_at=a.created_at,
        updated_at=a.updated_at,
        removed_from_lists_at=getattr(a, "removed_from_lists_at", None),
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _grading_model_read(m: GradingModel) -> GradingModelRead:
    return GradingModelRead(
        id=m.id,
        display_name=m.display_name,
        notes=m.gguf_filename,
        openai_model_name=m.openai_model_name,
        n_ctx=m.n_ctx,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _submission_read(s: Submission) -> SubmissionRead:
    return SubmissionRead(
        id=s.id,
        assignment_id=s.assignment_id,
        student_id=s.student_id,
        code=s.code,
        corrected_code=s.corrected_code,
        diff=s.diff,
        grade=s.grade,
        status=s.status,
        stdout=s.stdout,
        stderr=s.stderr,
        output=s.output,
        feedback=s.feedback,
        created_at=s.created_at,
        updated_at=s.updated_at,
        hidden_from_student=bool(getattr(s, "hidden_from_student", False)),
    )


@router.get("/grading/status", response_model=GradingStatusResponse)
def get_grading_status(_: Annotated[User, Depends(require_admin)]) -> GradingStatusResponse:
    health_url = endpoint_health_url_from_openai_base(CFG.hf_inference_base_url)
    ok = False
    health_err: str | None = None
    try:
        r = requests.get(health_url, timeout=3)
        ok = r.status_code == 200
        if not ok:
            health_err = f"HTTP {r.status_code}"
    except Exception as exc:
        ok = False
        health_err = str(exc)
    active = get_active_grading_model()
    note = (
        "SFT grading uses ChatOpenAI against HF_INFERENCE_BASE_URL (OpenAI-compatible /v1). "
        "The active catalog row sets the model id string sent to the Hugging Face endpoint."
    )
    return GradingStatusResponse(
        endpoint_health_ok=ok,
        endpoint_health_url=health_url,
        hf_inference_base_url=CFG.hf_inference_base_url,
        active_model=_grading_model_read(active) if active else None,
        endpoint_health_error=health_err,
        note=note,
    )


@router.get("/grading-models", response_model=list[GradingModelRead])
def list_grading_models_endpoint(
    session: SessionDep,
    _: Annotated[User, Depends(require_admin)],
) -> list[GradingModelRead]:
    return [_grading_model_read(m) for m in list_grading_models(session)]


@router.post("/grading-models", response_model=GradingModelRead)
def create_grading_model(
    body: GradingModelCreate,
    session: SessionDep,
    _: Annotated[User, Depends(require_admin)],
) -> GradingModelRead:
    existing = list(session.exec(select(GradingModel)).all())
    is_first = len(existing) == 0
    m = GradingModel(
        display_name=body.display_name.strip(),
        gguf_filename=body.notes.strip(),
        openai_model_name=body.openai_model_name.strip(),
        n_ctx=body.n_ctx,
        is_active=is_first,
        updated_at=_utc_now(),
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return _grading_model_read(m)


@router.patch("/grading-models/{model_id}", response_model=GradingModelRead)
def update_grading_model(
    model_id: str,
    body: GradingModelUpdate,
    session: SessionDep,
    _: Annotated[User, Depends(require_admin)],
) -> GradingModelRead:
    m = session.get(GradingModel, model_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Grading model not found")
    if body.display_name is not None:
        m.display_name = body.display_name.strip()
    if body.notes is not None:
        m.gguf_filename = body.notes.strip()
    if body.openai_model_name is not None:
        m.openai_model_name = body.openai_model_name.strip()
    if body.n_ctx is not None:
        m.n_ctx = body.n_ctx
    m.updated_at = _utc_now()
    session.add(m)
    session.commit()
    session.refresh(m)
    return _grading_model_read(m)


@router.post("/grading-models/{model_id}/activate", response_model=GradingModelRead)
def activate_grading_model(
    model_id: str,
    session: SessionDep,
    _: Annotated[User, Depends(require_admin)],
) -> GradingModelRead:
    target = session.get(GradingModel, model_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Grading model not found")
    for row in session.exec(select(GradingModel)).all():
        row.is_active = row.id == model_id
        row.updated_at = _utc_now()
        session.add(row)
    session.commit()
    session.refresh(target)
    return _grading_model_read(target)


@router.delete("/grading-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grading_model(
    model_id: str,
    session: SessionDep,
    _: Annotated[User, Depends(require_admin)],
) -> None:
    m = session.get(GradingModel, model_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Grading model not found")
    if m.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the active grading model; activate another first.",
        )
    session.delete(m)
    session.commit()


@router.get("/completeness-provider", response_model=CompletenessProviderResponse)
def get_completeness_provider_endpoint(
    _: Annotated[User, Depends(require_admin)],
) -> CompletenessProviderResponse:
    return CompletenessProviderResponse(provider=get_completeness_provider())


@router.put("/completeness-provider", response_model=CompletenessProviderResponse)
def update_completeness_provider_endpoint(
    body: CompletenessProviderUpdate,
    _: Annotated[User, Depends(require_admin)],
) -> CompletenessProviderResponse:
    try:
        value = set_completeness_provider(body.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CompletenessProviderResponse(provider=value)


@router.get("/config", response_model=AdminConfigResponse)
def get_admin_config(_: Annotated[User, Depends(require_admin)]) -> AdminConfigResponse:
    return AdminConfigResponse(
        backend_version=__version__,
        database_path=settings.database_path,
        storage_dir=settings.storage_dir,
        grading_worker_enabled=settings.grading_worker_enabled,
        grading_backend=settings.grading_backend,
        grading_poll_interval_seconds=settings.grading_poll_interval_seconds,
        grading_mock_sleep_seconds=settings.grading_mock_sleep_seconds,
        grading_max_attempts=settings.grading_max_attempts,
        jwt_expire_minutes=settings.jwt_expire_minutes,
    )


@router.get("/users", response_model=list[UserRead])
def list_users_for_admin(
    session: SessionDep,
    _: Annotated[User, Depends(require_admin)],
    role: UserRole | None = Query(None, description="Filter by role"),
) -> list[UserRead]:
    stmt = select(User).order_by(User.email)
    if role is not None:
        stmt = stmt.where(User.role == role)
    rows = session.exec(stmt).all()
    return [_user_read(r) for r in rows]


@router.get("/users/{user_id}/insights", response_model=AdminUserInsightsResponse)
def get_user_insights(
    session: SessionDep,
    user_id: str,
    _: Annotated[User, Depends(require_admin)],
) -> AdminUserInsightsResponse:
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")

    teacher_assignments: list[AssignmentRead] | None = None
    student_enrollments: list[StudentEnrollmentItem] | None = None
    student_submissions: list[SubmissionRead] | None = None

    if u.role == UserRole.teacher:
        rows = session.exec(
            select(Assignment)
            .where(Assignment.teacher_id == u.id)
            .order_by(Assignment.created_at.desc())
        ).all()
        teacher_assignments = [_assignment_read(a) for a in rows]

    if u.role == UserRole.student:
        enr = session.exec(
            select(AssignmentStudent)
            .where(AssignmentStudent.student_id == u.id)
            .order_by(AssignmentStudent.assigned_at.desc())
        ).all()
        items: list[StudentEnrollmentItem] = []
        for row in enr:
            a = session.get(Assignment, row.assignment_id)
            if a is None:
                continue
            items.append(
                StudentEnrollmentItem(
                    assignment=_assignment_read(a),
                    assigned_at=row.assigned_at,
                )
            )
        student_enrollments = items

        subs = session.exec(
            select(Submission)
            .where(Submission.student_id == u.id)
            .order_by(Submission.updated_at.desc())
        ).all()
        student_submissions = [_submission_read(s) for s in subs]

    return AdminUserInsightsResponse(
        user=_user_read(u),
        teacher_assignments=teacher_assignments,
        student_enrollments=student_enrollments,
        student_submissions=student_submissions,
    )


@router.get("/logs/stream")
async def stream_logs(_: Annotated[User, Depends(require_admin)]) -> StreamingResponse:
    """Server-Sent Events: recent logs + live tail (in-memory backend process only)."""

    buf = get_app_log_buffer()

    def _payload(seq: int, line: str, meta: dict | None) -> dict:
        payload: dict = {"seq": seq, "line": line}
        if meta:
            payload["kind"] = meta.get("kind", "backend")
            if meta.get("agent"):
                payload["agent"] = meta["agent"]
            if meta.get("phase"):
                payload["phase"] = meta["phase"]
            if meta.get("level"):
                payload["level"] = meta["level"]
            if meta.get("submission_id"):
                payload["submission_id"] = meta["submission_id"]
            if meta.get("assignment_id"):
                payload["assignment_id"] = meta["assignment_id"]
        else:
            payload["kind"] = "backend"
        return payload

    async def event_generator():
        last_seq = 0
        for seq, line, meta in buf.snapshot()[-500:]:
            yield json_sse_event(_payload(seq, line, meta))
            last_seq = seq
        while True:
            await asyncio.sleep(0.25)
            batch = buf.since(last_seq)
            if not batch:
                yield ":\n\n"
                continue
            for seq, line, meta in batch:
                yield json_sse_event(_payload(seq, line, meta))
                last_seq = seq

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
