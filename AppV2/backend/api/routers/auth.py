from __future__ import annotations

from datetime import datetime, timezone

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from ...api.deps import SessionDep, get_current_user
from ...core.jwt_tokens import create_access_token
from ...core.security import hash_password, verify_password
from ...db.models import User, UserRole
from ...schemas import UserRead
from ...schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_read(u: User) -> UserRead:
    return UserRead(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        student_id_number=u.student_id_number,
        is_active=u.is_active,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(session: SessionDep, body: RegisterRequest) -> UserRead:
    """Create a student or teacher account (not admin)."""
    email = body.email.strip().lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    role = UserRole.student if body.role == "student" else UserRole.teacher
    sid = body.student_id_number.strip()
    if role == UserRole.student and not sid:
        raise HTTPException(status_code=400, detail="student_id_number is required for students")
    user = User(
        email=email,
        full_name=body.full_name.strip(),
        role=role,
        student_id_number=sid,
        password_hash=hash_password(body.password),
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_read(user)


@router.post("/login", response_model=TokenResponse)
def login(session: SessionDep, body: LoginRequest) -> TokenResponse:
    email = body.email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    try:
        token = create_access_token(user)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def me(current: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Current user from JWT (private)."""
    return _to_read(current)
