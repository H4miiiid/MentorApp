from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..db.models import UserRole


class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=320)
    full_name: str = Field(..., min_length=2, max_length=200)
    role: UserRole
    student_id_number: str = Field("", max_length=64)
    password: str = Field(..., min_length=6, max_length=256)


class UserRead(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    student_id_number: str = ""
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    student_id_number: str | None = None
    password: str | None = Field(None, min_length=6, max_length=256)
    is_active: bool | None = None
