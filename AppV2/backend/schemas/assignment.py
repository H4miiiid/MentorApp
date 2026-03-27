from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="")
    teacher_id: str = Field(..., min_length=1, max_length=36)
    due_date: Optional[datetime] = None
    student_ids: list[str] = Field(default_factory=list, description="Students to enroll at creation")


class AssignmentRead(BaseModel):
    id: str
    title: str
    description: str
    teacher_id: str
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AssignmentStudentAdd(BaseModel):
    """Add one or more students to an assignment after creation (teacher or admin)."""

    student_ids: list[str] = Field(..., min_length=1)


class AssignmentStudentRead(BaseModel):
    assignment_id: str
    student_id: str
    assigned_at: datetime


class AssignmentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    due_date: Optional[datetime] = None
