from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlmodel import select

from ...api.deps import SessionDep, get_current_user
from ...core.config import settings
from ...db.models import Assignment, Document, User, UserRole
from ...schemas import DocumentCreate, DocumentRead, DocumentUpdate

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(get_current_user)],
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_read(d: Document) -> DocumentRead:
    return DocumentRead(
        id=d.id,
        uploaded_by=d.uploaded_by,
        title=d.title,
        description=d.description,
        file_path=d.file_path,
        file_type=d.file_type,
        file_size_bytes=d.file_size_bytes,
        assignment_id=d.assignment_id,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _resolve_storage_file(stored: str) -> Path:
    root = Path(settings.storage_dir).resolve()
    p = Path(stored)
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()
    try:
        p.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return p


def _can_access_document(d: Document, u: User) -> bool:
    if u.role == UserRole.admin:
        return True
    return d.uploaded_by == u.id


@router.get("", response_model=list[DocumentRead])
def list_documents(
    session: SessionDep, current: Annotated[User, Depends(get_current_user)]
) -> list[DocumentRead]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if current.role != UserRole.admin:
        stmt = stmt.where(Document.uploaded_by == current.id)
    rows = session.exec(stmt).all()
    return [_to_read(r) for r in rows]


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(session: SessionDep, body: DocumentCreate) -> DocumentRead:
    if session.get(User, body.uploaded_by) is None:
        raise HTTPException(status_code=400, detail="uploaded_by user not found")
    if body.assignment_id is not None and session.get(Assignment, body.assignment_id) is None:
        raise HTTPException(status_code=400, detail="assignment not found")
    doc = Document(
        uploaded_by=body.uploaded_by,
        title=body.title.strip(),
        description=body.description or "",
        file_path=body.file_path.strip(),
        file_type=body.file_type or "",
        file_size_bytes=body.file_size_bytes,
        assignment_id=body.assignment_id,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return _to_read(doc)


@router.get("/{document_id}/file")
def download_document_file(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    document_id: str,
) -> FileResponse:
    d = session.get(Document, document_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_document(d, current):
        raise HTTPException(status_code=403, detail="Not allowed to access this document")
    path = _resolve_storage_file(d.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/octet-stream",
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    document_id: str,
) -> DocumentRead:
    d = session.get(Document, document_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_document(d, current):
        raise HTTPException(status_code=403, detail="Not allowed to view this document")
    return _to_read(d)


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    document_id: str,
    body: DocumentUpdate,
) -> DocumentRead:
    d = session.get(Document, document_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_document(d, current):
        raise HTTPException(status_code=403, detail="Not allowed to update this document")
    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        d.title = data["title"].strip()
    if "description" in data and data["description"] is not None:
        d.description = data["description"]
    if "file_path" in data and data["file_path"] is not None:
        d.file_path = data["file_path"].strip()
    if "file_type" in data and data["file_type"] is not None:
        d.file_type = data["file_type"]
    if "file_size_bytes" in data and data["file_size_bytes"] is not None:
        d.file_size_bytes = data["file_size_bytes"]
    if "assignment_id" in data:
        aid = data["assignment_id"]
        if aid is not None and session.get(Assignment, aid) is None:
            raise HTTPException(status_code=400, detail="assignment not found")
        d.assignment_id = aid
    d.updated_at = _now()
    session.add(d)
    session.commit()
    session.refresh(d)
    return _to_read(d)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    document_id: str,
) -> None:
    d = session.get(Document, document_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_document(d, current):
        raise HTTPException(status_code=403, detail="Not allowed to delete this document")
    session.delete(d)
    session.commit()
