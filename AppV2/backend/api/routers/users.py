from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from ...api.deps import SessionDep, get_current_user, require_admin
from ...api.cascade import delete_user_cascade
from ...core.security import hash_password
from ...db.models import User, UserRole
from ...schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)


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


@router.get("", response_model=list[UserRead])
def list_users(session: SessionDep) -> list[UserRead]:
    rows = session.exec(select(User).order_by(User.email)).all()
    return [_to_read(r) for r in rows]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_user(session: SessionDep, body: UserCreate) -> UserRead:
    email = body.email.strip().lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if body.role == UserRole.student and not body.student_id_number.strip():
        raise HTTPException(status_code=400, detail="student_id_number required for students")
    user = User(
        email=email,
        full_name=body.full_name.strip(),
        role=body.role,
        student_id_number=body.student_id_number.strip(),
        password_hash=hash_password(body.password),
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_read(user)


@router.get("/{user_id}", response_model=UserRead)
def get_user(session: SessionDep, user_id: str) -> UserRead:
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_read(u)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_admin)],
)
def update_user(session: SessionDep, user_id: str, body: UserUpdate) -> UserRead:
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        ne = data["email"].strip().lower()
        existing = session.exec(select(User).where(User.email == ne, User.id != user_id)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        u.email = ne
    if "full_name" in data and data["full_name"] is not None:
        u.full_name = data["full_name"].strip()
    if "role" in data and data["role"] is not None:
        u.role = data["role"]
    if "student_id_number" in data and data["student_id_number"] is not None:
        u.student_id_number = data["student_id_number"].strip()
    if "is_active" in data and data["is_active"] is not None:
        u.is_active = data["is_active"]
    if "password" in data and data["password"] is not None:
        u.password_hash = hash_password(data["password"])
    u.updated_at = _now()
    session.add(u)
    session.commit()
    session.refresh(u)
    return _to_read(u)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_user(session: SessionDep, user_id: str) -> None:
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    delete_user_cascade(session, user_id)
    session.commit()
