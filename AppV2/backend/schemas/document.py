from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
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
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    file_path: str | None = Field(None, min_length=1, max_length=1024)
    file_type: str | None = Field(None, max_length=120)
    file_size_bytes: int | None = Field(None, ge=0)
    assignment_id: Optional[str] = Field(None, min_length=1, max_length=36)
