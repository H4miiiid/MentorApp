from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Legacy JSON-create body. Prefer ``POST /documents/upload`` (multipart)."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="")
    uploaded_by: str = Field(..., min_length=1, max_length=36)
    file_path: str = Field(..., min_length=1, max_length=1024)
    file_type: str = Field("", max_length=120)
    file_size_bytes: int = Field(0, ge=0)
    assignment_id: Optional[str] = Field(None, min_length=1, max_length=36)


class DocumentRead(BaseModel):
    id: str
    uploaded_by: str
    title: str
    description: str
    file_path: str
    file_type: str
    file_size_bytes: int
    assignment_id: Optional[str] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    """Partial update for document *metadata* only.

    ``file_path`` / ``file_size_bytes`` / ``file_type`` are no longer client-settable;
    they are owned by the upload endpoint. ``assignment_id`` attachments are managed
    via ``PUT /assignments/{id}/documents``. These fields are still accepted for
    backward compatibility with older clients but have no effect.
    """

    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    file_path: str | None = Field(None, min_length=1, max_length=1024)
    file_type: str | None = Field(None, max_length=120)
    file_size_bytes: int | None = Field(None, ge=0)
    assignment_id: Optional[str] = Field(None, min_length=1, max_length=36)


class AssignmentDocumentsReplace(BaseModel):
    """Full replacement of the attached document set for an assignment."""

    document_ids: list[str] = Field(default_factory=list)
