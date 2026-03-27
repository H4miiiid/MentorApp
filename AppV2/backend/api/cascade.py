from __future__ import annotations

from sqlmodel import Session, select

from ..db.models import Assignment, AssignmentStudent, Document, Submission, User


def delete_assignment_cascade(session: Session, assignment_id: str) -> None:
    for sub in session.exec(select(Submission).where(Submission.assignment_id == assignment_id)).all():
        session.delete(sub)
    for row in session.exec(
        select(AssignmentStudent).where(AssignmentStudent.assignment_id == assignment_id)
    ).all():
        session.delete(row)
    for doc in session.exec(select(Document).where(Document.assignment_id == assignment_id)).all():
        session.delete(doc)
    a = session.get(Assignment, assignment_id)
    if a is not None:
        session.delete(a)


def delete_user_cascade(session: Session, user_id: str) -> None:
    for doc in session.exec(select(Document).where(Document.uploaded_by == user_id)).all():
        session.delete(doc)
    for sub in session.exec(select(Submission).where(Submission.student_id == user_id)).all():
        session.delete(sub)
    for row in session.exec(select(AssignmentStudent).where(AssignmentStudent.student_id == user_id)).all():
        session.delete(row)
    for a in session.exec(select(Assignment).where(Assignment.teacher_id == user_id)).all():
        delete_assignment_cascade(session, a.id)
    u = session.get(User, user_id)
    if u is not None:
        session.delete(u)
