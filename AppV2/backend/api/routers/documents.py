from __future__ import annotations

import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ...api.deps import SessionDep, get_current_user
from ...core.config import settings
from ...db.models import Assignment, AssignmentDocument, AssignmentStudent, Document, User, UserRole
from ...schemas import DocumentCreate, DocumentRead, DocumentUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(get_current_user)],
)


_DOCUMENTS_SUBDIR = "documents"
_UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


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
        archived_at=d.archived_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _storage_root() -> Path:
    root = Path(settings.storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_storage_file(stored: str) -> Path:
    """Resolve a DB-stored path and refuse anything that escapes the storage root."""
    root = _storage_root()
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


def _safe_filename(raw: str) -> str:
    """Strip path components and unsafe characters; never return empty."""
    base = Path(raw or "").name or "upload"
    cleaned = _UNSAFE_NAME_RE.sub("_", base).strip("._") or "upload"
    return cleaned[:200]


def _document_dir(doc_id: str) -> Path:
    return _storage_root() / _DOCUMENTS_SUBDIR / doc_id


def _extension_allowed(filename: str) -> bool:
    allowed = tuple(ext.lower() for ext in settings.document_allowed_extensions)
    if not allowed:
        return True
    return Path(filename).suffix.lower() in allowed


def _doc_is_attached_to_assignment(session: Session, document_id: str, assignment_id: str) -> bool:
    row = session.exec(
        select(AssignmentDocument).where(
            AssignmentDocument.assignment_id == assignment_id,
            AssignmentDocument.document_id == document_id,
        )
    ).first()
    return row is not None


def _user_can_view_document(session: Session, d: Document, u: User) -> bool:
    """Owner/admin always; any student/teacher with access to an assignment the doc is attached to."""
    if u.role == UserRole.admin or d.uploaded_by == u.id:
        return True
    # Teachers see docs attached to assignments they own.
    # Students see docs attached to assignments they are enrolled in.
    attachments = session.exec(
        select(AssignmentDocument.assignment_id).where(AssignmentDocument.document_id == d.id)
    ).all()
    if not attachments:
        return False
    if u.role == UserRole.teacher:
        for aid in attachments:
            assignment = session.get(Assignment, aid)
            if assignment is not None and assignment.teacher_id == u.id:
                return True
        return False
    if u.role == UserRole.student:
        for aid in attachments:
            enrolled = session.exec(
                select(AssignmentStudent).where(
                    AssignmentStudent.assignment_id == aid,
                    AssignmentStudent.student_id == u.id,
                )
            ).first()
            if enrolled is not None:
                return True
    return False


def _user_can_manage_document(d: Document, u: User) -> bool:
    return u.role == UserRole.admin or d.uploaded_by == u.id


@router.get("", response_model=list[DocumentRead])
def list_documents(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    include_archived: bool = Query(
        False,
        description="Teachers can opt in to show archived (soft-deleted) documents.",
    ),
) -> list[DocumentRead]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if current.role != UserRole.admin:
        stmt = stmt.where(Document.uploaded_by == current.id)
    if not include_archived:
        stmt = stmt.where(Document.archived_at.is_(None))
    rows = session.exec(stmt).all()
    return [_to_read(r) for r in rows]


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document file (multipart) into the current user's library.",
)
async def upload_document(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
) -> DocumentRead:
    if current.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(
            status_code=403,
            detail="Only teachers or admins can upload documents.",
        )

    raw_name = file.filename or ""
    if not raw_name:
        raise HTTPException(status_code=400, detail="Missing filename.")
    if not _extension_allowed(raw_name):
        allowed = ", ".join(settings.document_allowed_extensions) or "(none)"
        raise HTTPException(
            status_code=415,
            detail=f"File type not allowed. Permitted extensions: {allowed}",
        )

    max_bytes = settings.document_max_upload_bytes
    new_doc = Document(
        uploaded_by=current.id,
        title=(title or raw_name).strip()[:300] or raw_name,
        description=(description or "").strip(),
        file_path="",
        file_type=(file.content_type or "").strip()[:120],
        file_size_bytes=0,
        assignment_id=None,
        archived_at=None,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(new_doc)
    session.flush()

    doc_dir = _document_dir(new_doc.id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    stored_name = _safe_filename(raw_name)
    target = doc_dir / stored_name

    # Stream to disk with a running size check. We cannot trust Content-Length
    # because clients (and multipart frameworks) may lie; read in 1 MiB chunks
    # and abort as soon as the limit is exceeded so malicious uploads cannot
    # fill the storage volume.
    total = 0
    chunk_size = 1024 * 1024
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File exceeds configured upload limit of "
                            f"{settings.document_max_upload_mb} MB."
                        ),
                    )
                out.write(chunk)
    except HTTPException:
        shutil.rmtree(doc_dir, ignore_errors=True)
        session.rollback()
        raise
    except Exception as exc:
        shutil.rmtree(doc_dir, ignore_errors=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to persist upload: {exc}") from exc
    finally:
        try:
            await file.close()
        except Exception:  # pragma: no cover - defensive
            pass

    rel_path = str(Path(_DOCUMENTS_SUBDIR) / new_doc.id / stored_name)
    new_doc.file_path = rel_path
    new_doc.file_size_bytes = total
    new_doc.updated_at = _now()
    session.add(new_doc)
    session.commit()
    session.refresh(new_doc)
    logger.info(
        "documents.upload | user=%s doc=%s size=%s name=%s",
        current.id,
        new_doc.id,
        total,
        stored_name,
    )
    return _to_read(new_doc)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
    summary="Legacy JSON-only create. New clients should use /documents/upload.",
)
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
        archived_at=None,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(doc)
    session.flush()
    if body.assignment_id:
        session.add(AssignmentDocument(assignment_id=body.assignment_id, document_id=doc.id))
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
    if not _user_can_view_document(session, d, current):
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
    if not _user_can_view_document(session, d, current):
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
    if not _user_can_manage_document(d, current):
        raise HTTPException(status_code=403, detail="Not allowed to update this document")
    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        d.title = data["title"].strip()
    if "description" in data and data["description"] is not None:
        d.description = data["description"]
    d.updated_at = _now()
    session.add(d)
    session.commit()
    session.refresh(d)
    return _to_read(d)


@router.post(
    "/{document_id}/unarchive",
    response_model=DocumentRead,
    summary="Restore a soft-deleted document back to the teacher's library.",
)
def unarchive_document(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    document_id: str,
) -> DocumentRead:
    d = session.get(Document, document_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _user_can_manage_document(d, current):
        raise HTTPException(status_code=403, detail="Not allowed to update this document")
    if d.archived_at is not None:
        d.archived_at = None
        d.updated_at = _now()
        session.add(d)
        session.commit()
        session.refresh(d)
    return _to_read(d)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete: hides from pickers + library but keeps file for existing attachments.",
)
def delete_document(
    session: SessionDep,
    current: Annotated[User, Depends(get_current_user)],
    document_id: str,
) -> None:
    d = session.get(Document, document_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _user_can_manage_document(d, current):
        raise HTTPException(status_code=403, detail="Not allowed to delete this document")
    if d.archived_at is None:
        d.archived_at = _now()
        d.updated_at = _now()
        session.add(d)
        session.commit()
