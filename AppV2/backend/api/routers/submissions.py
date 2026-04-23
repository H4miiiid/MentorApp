from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ...api.deps import SessionDep, get_current_user
from ...db.models import Assignment, AssignmentStudent, Submission, User, UserRole
from ...schemas import SubmissionCreate, SubmissionRead, SubmissionUpdate

router = APIRouter(
    prefix="/submissions",
    tags=["submissions"],
    dependencies=[Depends(get_current_user)],
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_read(s: Submission) -> SubmissionRead:
    return SubmissionRead(
        id=s.id,
        assignment_id=s.assignment_id,
        student_id=s.student_id,
        code=s.code,
        corrected_code=s.corrected_code,
        diff=s.diff,
        grade=s.grade,
        status=s.status,
        stdout=s.stdout,
        stderr=s.stderr,
        output=s.output,
        feedback=s.feedback,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _assignment(session: Session, assignment_id: str) -> Assignment | None:
    return session.get(Assignment, assignment_id)


def _teacher_owns_assignment(session: Session, assignment_id: str, teacher_id: str) -> bool:
    a = _assignment(session, assignment_id)
    return a is not None and a.teacher_id == teacher_id


def _can_view_submission(session: Session, s: Submission, u: User) -> bool:
    if u.role == UserRole.admin:
        return True
    if u.role == UserRole.student and s.student_id == u.id:
        return True
    if u.role == UserRole.teacher:
        return _teacher_owns_assignment(session, s.assignment_id, u.id)
    return False


def _can_edit_submission(session: Session, s: Submission, u: User) -> bool:
    if u.role == UserRole.admin:
        return True
    if u.role == UserRole.student and s.student_id == u.id:
        return True
    if u.role == UserRole.teacher:
        return _teacher_owns_assignment(session, s.assignment_id, u.id)
    return False


@router.get("", response_model=list[SubmissionRead])
def list_submissions(
    session: SessionDep, current: Annotated[User, Depends(get_current_user)]
) -> list[SubmissionRead]:
    stmt = select(Submission).order_by(Submission.created_at.desc())
    if current.role == UserRole.admin:
        rows = session.exec(stmt).all()
    elif current.role == UserRole.teacher:
        rows = session.exec(
            select(Submission).where(
                Submission.assignment_id.in_(
                    select(Assignment.id).where(Assignment.teacher_id == current.id)
                )
            ).order_by(Submission.created_at.desc())
        ).all()
    else:
        rows = session.exec(
            select(Submission)
            .where(Submission.student_id == current.id)
            .order_by(Submission.created_at.desc())
        ).all()
    return [_to_read(r) for r in rows]


@router.post("", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def create_submission(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    body: SubmissionCreate,
) -> SubmissionRead:
    if current.role == UserRole.teacher:
        raise HTTPException(status_code=403, detail="Only students submit work")
    if current.role == UserRole.student and body.student_id != current.id:
        raise HTTPException(status_code=403, detail="Cannot submit for another student")
    if session.get(Assignment, body.assignment_id) is None:
        raise HTTPException(status_code=400, detail="Assignment not found")
    st = session.get(User, body.student_id)
    if st is None or st.role != UserRole.student:
        raise HTTPException(status_code=400, detail="student_id must be a student")
    enr = session.exec(
        select(AssignmentStudent).where(
            AssignmentStudent.assignment_id == body.assignment_id,
            AssignmentStudent.student_id == body.student_id,
        )
    ).first()
    if enr is None:
        raise HTTPException(status_code=400, detail="Student is not enrolled in this assignment")
    sub = Submission(
        assignment_id=body.assignment_id,
        student_id=body.student_id,
        code=body.code,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return _to_read(sub)


@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    submission_id: str,
) -> SubmissionRead:
    s = session.get(Submission, submission_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not _can_view_submission(session, s, current):
        raise HTTPException(status_code=403, detail="Not allowed to view this submission")
    return _to_read(s)


@router.patch("/{submission_id}", response_model=SubmissionRead)
def update_submission(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    submission_id: str,
    body: SubmissionUpdate,
) -> SubmissionRead:
    s = session.get(Submission, submission_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not _can_edit_submission(session, s, current):
        raise HTTPException(status_code=403, detail="Not allowed to update this submission")
    data = body.model_dump(exclude_unset=True)
    for key in (
        "code",
        "corrected_code",
        "diff",
        "grade",
        "status",
        "stdout",
        "stderr",
        "output",
        "feedback",
    ):
        if key in data and data[key] is not None:
            setattr(s, key, data[key])
    s.updated_at = _now()
    session.add(s)
    session.commit()
    session.refresh(s)
    return _to_read(s)


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    submission_id: str,
) -> None:
    s = session.get(Submission, submission_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not _can_edit_submission(session, s, current):
        raise HTTPException(status_code=403, detail="Not allowed to delete this submission")
    session.delete(s)
    session.commit()
