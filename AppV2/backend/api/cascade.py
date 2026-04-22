from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sqlmodel import Session, select

from ..core.config import settings
from ..db.models import (
    Assignment,
    AssignmentDocument,
    AssignmentStudent,
    Document,
    Submission,
    User,
)

logger = logging.getLogger(__name__)


def _document_storage_path(file_path: str) -> Path | None:
    """Return the absolute stored path for a Document.file_path, or None if invalid."""
    if not file_path:
        return None
    root = Path(settings.storage_dir).resolve()
    p = Path(file_path)
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return None
    return p


def _hard_delete_document(session: Session, doc: Document) -> None:
    """Delete a document row, its attachment links, and the bytes on disk."""
    for row in session.exec(
        select(AssignmentDocument).where(AssignmentDocument.document_id == doc.id)
    ).all():
        session.delete(row)
    path = _document_storage_path(doc.file_path)
    if path is not None and path.exists():
        try:
            parent = path.parent
            path.unlink(missing_ok=True)
            # Remove the per-document subdirectory when we own it.
            if parent.is_dir() and parent.name == doc.id:
                shutil.rmtree(parent, ignore_errors=True)
        except Exception:
            logger.warning(
                "cascade: failed to remove storage for document %s at %s", doc.id, path
            )
    session.delete(doc)


def delete_assignment_cascade(session: Session, assignment_id: str) -> None:
    """Delete an assignment: submissions + enrollments go away, document attachments
    are removed, but the Documents themselves stay in the teacher's library."""
    for sub in session.exec(select(Submission).where(Submission.assignment_id == assignment_id)).all():
        session.delete(sub)
    for row in session.exec(
        select(AssignmentStudent).where(AssignmentStudent.assignment_id == assignment_id)
    ).all():
        session.delete(row)
    for attach in session.exec(
        select(AssignmentDocument).where(AssignmentDocument.assignment_id == assignment_id)
    ).all():
        session.delete(attach)
    # Legacy FK: any Document still pinned to this assignment via the old column stays
    # in the library; just null out the dangling FK so we never reference a dead row.
    for doc in session.exec(select(Document).where(Document.assignment_id == assignment_id)).all():
        doc.assignment_id = None
        session.add(doc)
    a = session.get(Assignment, assignment_id)
    if a is not None:
        session.delete(a)


def delete_user_cascade(session: Session, user_id: str) -> None:
    """Hard-delete a user and everything they own (docs, files, submissions, assignments)."""
    for doc in session.exec(select(Document).where(Document.uploaded_by == user_id)).all():
        _hard_delete_document(session, doc)
    for sub in session.exec(select(Submission).where(Submission.student_id == user_id)).all():
        session.delete(sub)
    for row in session.exec(select(AssignmentStudent).where(AssignmentStudent.student_id == user_id)).all():
        session.delete(row)
    for a in session.exec(select(Assignment).where(Assignment.teacher_id == user_id)).all():
        delete_assignment_cascade(session, a.id)
    u = session.get(User, user_id)
    if u is not None:
        session.delete(u)
