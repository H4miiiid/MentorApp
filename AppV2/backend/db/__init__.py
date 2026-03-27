"""Database engine, sessions, and SQLModel tables."""

from .database import get_engine, get_session, init_db, session_scope
from .models import (
    Assignment,
    AssignmentStudent,
    Document,
    Submission,
    SubmissionStatus,
    User,
    UserRole,
)

__all__ = [
    "Assignment",
    "AssignmentStudent",
    "Document",
    "Submission",
    "SubmissionStatus",
    "User",
    "UserRole",
    "get_engine",
    "get_session",
    "init_db",
    "session_scope",
]
