"""Default admin account: CLI bootstrap or automatic ensure on API startup.

Automatic (default): enabled via ``APPV2_BOOTSTRAP_ADMIN`` (default ``true``).
Disable in production if you manage admins only via migrations or manual DB:

    APPV2_BOOTSTRAP_ADMIN=false

Optional overrides: ``APPV2_ADMIN_EMAIL``, ``APPV2_ADMIN_PASSWORD``.

CLI (same DB as the running process — use for repair or when startup bootstrap is off):

    PYTHONPATH=. python -m AppV2.backend.bootstrap_admin

    docker compose exec backend python -m AppV2.backend.bootstrap_admin
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from sqlmodel import Session, select

from .core.config import settings
from .core.security import hash_password
from .db.database import get_engine, init_db
from .db.models import User, UserRole

logger = logging.getLogger(__name__)

BootstrapAdminResult = Literal["disabled", "skipped_empty_email", "exists", "created"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_default_admin() -> BootstrapAdminResult:
    """Create the configured default admin if missing. Idempotent."""
    if not settings.bootstrap_admin_enabled:
        logger.debug("Default admin bootstrap skipped (APPV2_BOOTSTRAP_ADMIN is false).")
        return "disabled"

    email = settings.bootstrap_admin_email.strip().lower()
    if not email:
        logger.warning("Default admin bootstrap skipped: APPV2_ADMIN_EMAIL is empty.")
        return "skipped_empty_email"

    password = settings.bootstrap_admin_password
    full_name = "Administrator"

    engine = get_engine()
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing is not None:
            logger.debug("Default admin already present: %s (id=%s)", email, existing.id)
            return "exists"

        user = User(
            email=email,
            full_name=full_name,
            role=UserRole.admin,
            student_id_number="",
            password_hash=hash_password(password),
            is_active=True,
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(
            "Provisioned default admin %s (id=%s). Change password after first login.",
            email,
            user.id,
        )
        return "created"


def main() -> None:
    init_db()
    print(f"[bootstrap_admin] Using database: {settings.database_path}")
    outcome = ensure_default_admin()
    if outcome == "disabled":
        print("[bootstrap_admin] Skipped: APPV2_BOOTSTRAP_ADMIN is false.")
    elif outcome == "skipped_empty_email":
        print("[bootstrap_admin] Skipped: APPV2_ADMIN_EMAIL is empty.")
    elif outcome == "exists":
        email = settings.bootstrap_admin_email.strip().lower()
        engine = get_engine()
        with Session(engine) as session:
            u = session.exec(select(User).where(User.email == email)).first()
            if u is not None:
                print(f"[bootstrap_admin] User already exists: {email} (id={u.id})")
    else:
        email = settings.bootstrap_admin_email.strip().lower()
        engine = get_engine()
        with Session(engine) as session:
            u = session.exec(select(User).where(User.email == email)).first()
            if u is not None:
                print(f"[bootstrap_admin] Created admin user {email} (id={u.id})")


if __name__ == "__main__":
    main()
