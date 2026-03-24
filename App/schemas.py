from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RepairRequest(BaseModel):
    """Request body for code repair."""

    broken_code: str = Field(..., min_length=1, description="Python code that needs repair")
    max_attempts: int = Field(6, ge=1, le=20)


class RepairResult(BaseModel):
    """Normalized workflow response returned by the API and UI."""

    final_code: str
    final_status: str
    attempt_count: int
    route_history: list[str] = Field(default_factory=list)
    attempt_history: list[dict[str, Any]] = Field(default_factory=list)
    error_category: str = ""
    stop_reason: str = ""
    backend_mode: str


class HealthResponse(BaseModel):
    status: str = "ok"
    backend_mode: str


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    full_name: str = Field(..., min_length=2, max_length=120)
    student_id_number: str = Field("", max_length=64)
    password: str = Field(..., min_length=6, max_length=256)
    role: str = Field(..., pattern="^(student|professor)$")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=256)
    role: str = Field(..., pattern="^(student|professor)$")


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    student_id_number: str = ""


class ProjectCreateRequest(BaseModel):
    professor_id: int
    student_id_number: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5)


class ProjectAssignFailure(BaseModel):
    student_id_number: str
    error: str


class ProjectBulkCreateRequest(BaseModel):
    professor_id: int
    student_id_numbers: list[str] = Field(..., min_length=1)
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5)


class ProjectBulkCreateResponse(BaseModel):
    created_projects: list[ProjectOut] = Field(default_factory=list)
    failed_assignments: list[ProjectAssignFailure] = Field(default_factory=list)


class ProjectOut(BaseModel):
    id: int
    professor_id: int
    student_id: int
    title: str
    description: str
    created_at: str


class SubmissionCreateRequest(BaseModel):
    project_id: int
    student_id: int
    student_code: str = Field(..., min_length=1)
    max_attempts: int = Field(6, ge=1, le=20)


class SubmissionOut(BaseModel):
    id: int
    project_id: int
    student_id: int
    student_code: str
    corrected_code: str
    mistakes_diff: str
    grade_percent: float
    status: str
    created_at: str


class SubmissionSummary(BaseModel):
    id: int
    project_id: int
    project_title: str
    student_id: int
    student_name: str
    student_id_number: str = ""
    grade_percent: float
    status: str
    created_at: str


class StudentSubmissionSummary(BaseModel):
    id: int
    project_id: int
    project_title: str
    grade_percent: float
    status: str
    created_at: str


class LibraryDocumentCreateRequest(BaseModel):
    professor_id: int
    library_name: str = Field(..., min_length=1, max_length=120)
    library_version: str = Field(..., min_length=1, max_length=60)
    source_title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=20)


class LibraryDocumentOut(BaseModel):
    id: int
    professor_id: int
    library_name: str
    library_version: str
    source_title: str
    content: str
    chunk_count: int
    vector_ids_json: str
    created_at: str
