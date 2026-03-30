from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class UserRole(str, Enum):
    """Maps V1 student/professor; professor is renamed to teacher; admin is new."""

    student = "student"
    teacher = "teacher"
    admin = "admin"


class SubmissionStatus(str, Enum):
    """Lifecycle for async sandbox + LLM pipeline."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=_new_uuid, primary_key=True, max_length=36)
    email: str = Field(index=True, unique=True, max_length=320)
    full_name: str = Field(max_length=200)
    role: UserRole = Field(index=True)
    student_id_number: str = Field(default="", max_length=64, index=True)
    password_hash: str = Field(max_length=512)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class Assignment(SQLModel, table=True):
    __tablename__ = "assignments"

    id: str = Field(default_factory=_new_uuid, primary_key=True, max_length=36)
    title: str = Field(max_length=300)
    description: str = Field(default="")
    teacher_id: str = Field(foreign_key="users.id", index=True, max_length=36)
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class AssignmentStudent(SQLModel, table=True):
    """Many-to-many: which students are enrolled on an assignment."""

    __tablename__ = "assignment_students"

    assignment_id: str = Field(foreign_key="assignments.id", primary_key=True, max_length=36)
    student_id: str = Field(foreign_key="users.id", primary_key=True, max_length=36)
    assigned_at: datetime = Field(default_factory=_utc_now)


class Submission(SQLModel, table=True):
    __tablename__ = "submissions"

    id: str = Field(default_factory=_new_uuid, primary_key=True, max_length=36)
    assignment_id: str = Field(foreign_key="assignments.id", index=True, max_length=36)
    student_id: str = Field(foreign_key="users.id", index=True, max_length=36)
    code: str = Field(default="")
    corrected_code: str = Field(default="")
    diff: str = Field(default="")
    grade: float = Field(default=0.0)
    status: SubmissionStatus = Field(default=SubmissionStatus.pending, index=True)
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    feedback: str = Field(default="")
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class GradingModel(SQLModel, table=True):
    """Catalog of local llama.cpp SFT endpoints (one row active for grading)."""

    __tablename__ = "grading_models"

    id: str = Field(default_factory=_new_uuid, primary_key=True, max_length=36)
    display_name: str = Field(max_length=200)
    # Filename under host models/gguf (must match llama sidecar -m /models/<file>).
    gguf_filename: str = Field(max_length=512)
    # OpenAI-compatible model id sent to llama-server (often matches GGUF or alias).
    openai_model_name: str = Field(max_length=200)
    n_ctx: int = Field(default=8192, ge=256)
    is_active: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=_new_uuid, primary_key=True, max_length=36)
    uploaded_by: str = Field(foreign_key="users.id", index=True, max_length=36)
    title: str = Field(max_length=300)
    description: str = Field(default="")
    file_path: str = Field(max_length=1024)
    file_type: str = Field(default="", max_length=120)
    file_size_bytes: int = Field(default=0, ge=0)
    assignment_id: Optional[str] = Field(default=None, foreign_key="assignments.id", index=True, max_length=36)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
