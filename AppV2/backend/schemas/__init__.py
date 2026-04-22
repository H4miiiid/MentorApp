"""Pydantic request/response models (API contracts)."""

from .auth import LoginRequest, RegisterRequest, TokenResponse
from .assignment import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentStudentAdd,
    AssignmentStudentRead,
    AssignmentUpdate,
)
from .document import (
    AssignmentDocumentsReplace,
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
)
from .health import HealthResponse
from .submission import SubmissionCreate, SubmissionRead, SubmissionUpdate
from .user import UserCreate, UserRead, UserUpdate
from .admin import AdminConfigResponse, AdminUserInsightsResponse, StudentEnrollmentItem
from .grading_model import (
    GradingModelCreate,
    GradingModelRead,
    GradingModelUpdate,
    GradingStatusResponse,
)

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "AssignmentCreate",
    "AssignmentRead",
    "AssignmentStudentAdd",
    "AssignmentStudentRead",
    "AssignmentUpdate",
    "AssignmentDocumentsReplace",
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
    "AdminConfigResponse",
    "AdminUserInsightsResponse",
    "StudentEnrollmentItem",
    "GradingModelCreate",
    "GradingModelRead",
    "GradingModelUpdate",
    "GradingStatusResponse",
]
