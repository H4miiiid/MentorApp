"""Pydantic request/response models (API contracts)."""

from .auth import LoginRequest, RegisterRequest, TokenResponse
from .assignment import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentStudentAdd,
    AssignmentStudentRead,
    AssignmentUpdate,
)
from .document import DocumentCreate, DocumentRead, DocumentUpdate
from .health import HealthResponse
from .submission import SubmissionCreate, SubmissionRead, SubmissionUpdate
from .user import UserCreate, UserRead, UserUpdate

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "AssignmentCreate",
    "AssignmentRead",
    "AssignmentStudentAdd",
    "AssignmentStudentRead",
    "AssignmentUpdate",
    "DocumentCreate",
    "DocumentRead",
    "DocumentUpdate",
    "HealthResponse",
    "SubmissionCreate",
    "SubmissionRead",
    "SubmissionUpdate",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]
