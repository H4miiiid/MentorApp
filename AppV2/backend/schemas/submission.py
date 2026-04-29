from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..db.models import SubmissionStatus


class SubmissionCreate(BaseModel):
    assignment_id: str = Field(..., min_length=1, max_length=36)
    student_id: str = Field(..., min_length=1, max_length=36)
    code: str = Field(..., min_length=1)


class SubmissionRead(BaseModel):
    id: str
    assignment_id: str
    student_id: str
    code: str
    corrected_code: str
    diff: str
    grade: float
    status: SubmissionStatus
    stdout: str
    stderr: str
    output: str
    feedback: str
    created_at: datetime
    updated_at: datetime
    hidden_from_student: bool = False


class SubmissionUpdate(BaseModel):
    code: str | None = None
    corrected_code: str | None = None
    diff: str | None = None
    grade: float | None = None
    status: SubmissionStatus | None = None
    stdout: str | None = None
    stderr: str | None = None
    output: str | None = None
    feedback: str | None = None
    hidden_from_student: bool | None = None
