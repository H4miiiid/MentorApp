from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    """Self-service signup: only student or teacher (admins are created separately)."""

    email: str = Field(..., min_length=5, max_length=320)
    full_name: str = Field(..., min_length=2, max_length=200)
    password: str = Field(..., min_length=6, max_length=256)
    role: Literal["student", "teacher"]
    student_id_number: str = Field("", max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
