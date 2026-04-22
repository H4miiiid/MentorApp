from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ...api.cascade import delete_assignment_cascade
from ...api.deps import SessionDep, get_current_user
from ...db.models import (
    Assignment,
    AssignmentDocument,
    AssignmentStudent,
    Document,
    User,
    UserRole,
)
from ...schemas import (
    AssignmentCreate,
    AssignmentDocumentsReplace,
    AssignmentRead,
    AssignmentStudentAdd,
    AssignmentStudentRead,
    AssignmentUpdate,
    DocumentRead,
)

router = APIRouter(
    prefix="/assignments",
    tags=["assignments"],
    dependencies=[Depends(get_current_user)],
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _teacher_ok(u: User | None) -> bool:
    return u is not None and u.role in (UserRole.teacher, UserRole.admin)


def _to_read(a: Assignment) -> AssignmentRead:
    return AssignmentRead(
        id=a.id,
        title=a.title,
        description=a.description,
        teacher_id=a.teacher_id,
        due_date=a.due_date,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _can_view_assignment(session: Session, a: Assignment, u: User) -> bool:
    if u.role == UserRole.admin:
        return True
    if u.role == UserRole.teacher and a.teacher_id == u.id:
        return True
    if u.role == UserRole.student:
        return (
            session.exec(
                select(AssignmentStudent).where(
                    AssignmentStudent.assignment_id == a.id,
                    AssignmentStudent.student_id == u.id,
                )
            ).first()
            is not None
        )
    return False


def _can_manage_assignment(a: Assignment, u: User) -> bool:
    if u.role == UserRole.admin:
        return True
    return u.role == UserRole.teacher and a.teacher_id == u.id


def _get_assignment_or_404(session: Session, assignment_id: str) -> Assignment:
    a = session.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a


@router.get("", response_model=list[AssignmentRead])
def list_assignments(
    session: SessionDep, current: Annotated[User, Depends(get_current_user)]
) -> list[AssignmentRead]:
    if current.role == UserRole.admin:
        rows = session.exec(select(Assignment).order_by(Assignment.created_at.desc())).all()
    elif current.role == UserRole.teacher:
        rows = session.exec(
            select(Assignment)
            .where(Assignment.teacher_id == current.id)
            .order_by(Assignment.created_at.desc())
        ).all()
    else:
        rows = session.exec(
            select(Assignment)
            .where(
                Assignment.id.in_(
                    select(AssignmentStudent.assignment_id).where(
                        AssignmentStudent.student_id == current.id
                    )
                )
            )
            .order_by(Assignment.created_at.desc())
        ).all()
    return [_to_read(r) for r in rows]


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    body: AssignmentCreate,
) -> AssignmentRead:
    if current.role == UserRole.student:
        raise HTTPException(status_code=403, detail="Only teachers and admins can create assignments")
    if current.role == UserRole.teacher and body.teacher_id != current.id:
        raise HTTPException(status_code=403, detail="Cannot create assignment for another teacher")
    teacher = session.get(User, body.teacher_id)
    if not _teacher_ok(teacher):
        raise HTTPException(status_code=400, detail="teacher_id must be a teacher or admin user")
    a = Assignment(
        title=body.title.strip(),
        description=body.description or "",
        teacher_id=body.teacher_id,
        due_date=body.due_date,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(a)
    session.flush()
    seen: set[str] = set()
    for sid in body.student_ids:
        if sid in seen:
            continue
        seen.add(sid)
        st = session.get(User, sid)
        if st is None or st.role != UserRole.student:
            raise HTTPException(status_code=400, detail=f"Invalid student_id: {sid}")
        session.add(AssignmentStudent(assignment_id=a.id, student_id=sid, assigned_at=_now()))
    session.commit()
    session.refresh(a)
    return _to_read(a)


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    assignment_id: str,
) -> AssignmentRead:
    a = _get_assignment_or_404(session, assignment_id)
    if not _can_view_assignment(session, a, current):
        raise HTTPException(status_code=403, detail="Not allowed to view this assignment")
    return _to_read(a)


@router.patch("/{assignment_id}", response_model=AssignmentRead)
def update_assignment(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    assignment_id: str,
    body: AssignmentUpdate,
) -> AssignmentRead:
    a = _get_assignment_or_404(session, assignment_id)
    if not _can_manage_assignment(a, current):
        raise HTTPException(status_code=403, detail="Not allowed to update this assignment")
    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        a.title = data["title"].strip()
    if "description" in data and data["description"] is not None:
        a.description = data["description"]
    if "due_date" in data:
        a.due_date = data["due_date"]
    a.updated_at = _now()
    session.add(a)
    session.commit()
    session.refresh(a)
    return _to_read(a)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    assignment_id: str,
) -> None:
    a = _get_assignment_or_404(session, assignment_id)
    if not _can_manage_assignment(a, current):
        raise HTTPException(status_code=403, detail="Not allowed to delete this assignment")
    delete_assignment_cascade(session, assignment_id)
    session.commit()


@router.get("/{assignment_id}/students", response_model=list[AssignmentStudentRead])
def list_assignment_students(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    assignment_id: str,
) -> list[AssignmentStudentRead]:
    a = _get_assignment_or_404(session, assignment_id)
    if not _can_view_assignment(session, a, current):
        raise HTTPException(status_code=403, detail="Not allowed to view this assignment")
    rows = session.exec(
        select(AssignmentStudent).where(AssignmentStudent.assignment_id == assignment_id)
    ).all()
    return [
        AssignmentStudentRead(
            assignment_id=r.assignment_id, student_id=r.student_id, assigned_at=r.assigned_at
        )
        for r in rows
    ]


def _document_to_read(d: Document) -> DocumentRead:
    return DocumentRead(
        id=d.id,
        uploaded_by=d.uploaded_by,
        title=d.title,
        description=d.description,
        file_path=d.file_path,
        file_type=d.file_type,
        file_size_bytes=d.file_size_bytes,
        assignment_id=d.assignment_id,
        archived_at=d.archived_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


@router.get("/{assignment_id}/documents", response_model=list[DocumentRead])
def list_assignment_documents(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    assignment_id: str,
) -> list[DocumentRead]:
    """Documents currently attached to this assignment (visible to teacher + enrolled students)."""
    a = _get_assignment_or_404(session, assignment_id)
    if not _can_view_assignment(session, a, current):
        raise HTTPException(status_code=403, detail="Not allowed to view this assignment")
    rows = session.exec(
        select(AssignmentDocument).where(AssignmentDocument.assignment_id == assignment_id)
    ).all()
    docs: list[DocumentRead] = []
    for row in rows:
        d = session.get(Document, row.document_id)
        if d is None:
            continue
        docs.append(_document_to_read(d))
    return docs


@router.put(
    "/{assignment_id}/documents",
    response_model=list[DocumentRead],
    summary="Replace the full set of documents attached to an assignment (teacher/admin).",
)
def replace_assignment_documents(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    assignment_id: str,
    body: AssignmentDocumentsReplace,
) -> list[DocumentRead]:
    a = _get_assignment_or_404(session, assignment_id)
    if not _can_manage_assignment(a, current):
        raise HTTPException(status_code=403, detail="Not allowed to modify this assignment")

    # Validate every requested document (exists, owned by teacher unless admin, not archived).
    desired: list[Document] = []
    seen: set[str] = set()
    for doc_id in body.document_ids:
        if doc_id in seen:
            continue
        seen.add(doc_id)
        d = session.get(Document, doc_id)
        if d is None:
            raise HTTPException(status_code=400, detail=f"Document not found: {doc_id}")
        if d.archived_at is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Document is archived and cannot be attached: {doc_id}",
            )
        if current.role != UserRole.admin and d.uploaded_by != current.id:
            raise HTTPException(
                status_code=403,
                detail="Only the uploading teacher (or an admin) may attach a document.",
            )
        desired.append(d)

    current_rows = session.exec(
        select(AssignmentDocument).where(AssignmentDocument.assignment_id == assignment_id)
    ).all()
    current_ids = {row.document_id for row in current_rows}
    desired_ids = {d.id for d in desired}

    for row in current_rows:
        if row.document_id not in desired_ids:
            session.delete(row)

    for d in desired:
        if d.id not in current_ids:
            session.add(AssignmentDocument(assignment_id=assignment_id, document_id=d.id))

    a.updated_at = _now()
    session.add(a)
    session.commit()

    # Return the refreshed list in insertion order matching the caller's request.
    return [_document_to_read(d) for d in desired]


@router.post("/{assignment_id}/students", response_model=list[AssignmentStudentRead])
def add_assignment_students(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    assignment_id: str,
    body: AssignmentStudentAdd,
) -> list[AssignmentStudentRead]:
    a = _get_assignment_or_404(session, assignment_id)
    if not _can_manage_assignment(a, current):
        raise HTTPException(status_code=403, detail="Not allowed to modify this assignment")
    out: list[AssignmentStudentRead] = []
    seen: set[str] = set()
    for sid in body.student_ids:
        if sid in seen:
            continue
        seen.add(sid)
        st = session.get(User, sid)
        if st is None or st.role != UserRole.student:
            raise HTTPException(status_code=400, detail=f"Invalid student_id: {sid}")
        exists = session.exec(
            select(AssignmentStudent).where(
                AssignmentStudent.assignment_id == assignment_id,
                AssignmentStudent.student_id == sid,
            )
        ).first()
        if exists:
            out.append(
                AssignmentStudentRead(
                    assignment_id=exists.assignment_id,
                    student_id=exists.student_id,
                    assigned_at=exists.assigned_at,
                )
            )
            continue
        row = AssignmentStudent(assignment_id=assignment_id, student_id=sid, assigned_at=_now())
        session.add(row)
        session.flush()
        out.append(
            AssignmentStudentRead(
                assignment_id=row.assignment_id,
                student_id=row.student_id,
                assigned_at=row.assigned_at,
            )
        )
    session.commit()
    return out
