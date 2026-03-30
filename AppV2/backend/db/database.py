from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from ..core.config import settings
from .models import (  # noqa: F401
    Assignment,
    AssignmentStudent,
    Document,
    GradingModel,
    Submission,
    User,
)

_engine = None


def get_engine():
    """Lazy singleton engine (allows tests to patch settings before first use)."""
    global _engine
    if _engine is None:
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return _engine


def init_db() -> None:
    """Create all tables and ensure local storage directory exists."""
    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Transactional session context manager."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
        session.commit()


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a session per request."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
