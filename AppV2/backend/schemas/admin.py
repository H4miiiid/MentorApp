from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .assignment import AssignmentRead
from .submission import SubmissionRead
from .user import UserRead


class AdminConfigResponse(BaseModel):
    """Read-only snapshot for admin configuration page."""

    backend_version: str
    database_path: str
    storage_dir: str
    grading_worker_enabled: bool
    grading_backend: str
    grading_poll_interval_seconds: float
    grading_mock_sleep_seconds: float
    grading_max_attempts: int
    jwt_expire_minutes: int


class StudentEnrollmentItem(BaseModel):
    assignment: AssignmentRead
    assigned_at: datetime


class AdminUserInsightsResponse(BaseModel):
    user: UserRead
    teacher_assignments: list[AssignmentRead] | None = None
    student_enrollments: list[StudentEnrollmentItem] | None = None
    student_submissions: list[SubmissionRead] | None = None


class CompletenessProviderResponse(BaseModel):
    provider: str


class CompletenessProviderUpdate(BaseModel):
    provider: str
