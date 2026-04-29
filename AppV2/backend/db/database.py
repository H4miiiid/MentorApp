from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

from ..core.config import settings
from .models import (  # noqa: F401
    Assignment,
    AssignmentDocument,
    AssignmentStudent,
    Document,
    GradingModel,
    Submission,
    User,
    WorkflowSetting,
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
    """Create all tables, apply light schema migrations, and ensure storage dir exists."""
    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _apply_light_migrations(engine)


def _apply_light_migrations(engine) -> None:
    """Idempotent, code-based schema upkeep (no Alembic in this project).

    1. Add ``documents.archived_at`` column when missing (pre-existing SQLite DBs).
    2. Backfill legacy ``documents.assignment_id`` values into the new
       ``assignment_documents`` join table so attachments survive the N-to-N move.
    3. Add ``submissions.output`` for final sandbox program output.
    4. Add ``submissions.hidden_from_student`` for soft-remove from student UI only.
    5. Add ``assignments.removed_from_lists_at`` when missing (soft-hide for teacher/student lists).
    """
    inspector = inspect(engine)
    try:
        doc_columns = {col["name"] for col in inspector.get_columns("documents")}
    except Exception:
        return

    if "archived_at" not in doc_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE documents ADD COLUMN archived_at TIMESTAMP"))

    try:
        sub_columns = {col["name"] for col in inspector.get_columns("submissions")}
    except Exception:
        sub_columns = set()
    if sub_columns and "output" not in sub_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE submissions ADD COLUMN output VARCHAR DEFAULT ''"))

    try:
        sub_cols2 = {col["name"] for col in inspector.get_columns("submissions")}
    except Exception:
        sub_cols2 = set()
    if sub_cols2 and "hidden_from_student" not in sub_cols2:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE submissions ADD COLUMN hidden_from_student BOOLEAN DEFAULT 0")
            )

    try:
        asg_columns = {col["name"] for col in inspector.get_columns("assignments")}
    except Exception:
        asg_columns = set()
    if asg_columns and "removed_from_lists_at" not in asg_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE assignments ADD COLUMN removed_from_lists_at TIMESTAMP"))

    try:
        with Session(engine) as session:
            legacy = session.exec(
                select(Document).where(Document.assignment_id.is_not(None))
            ).all()
            for doc in legacy:
                existing = session.exec(
                    select(AssignmentDocument).where(
                        AssignmentDocument.assignment_id == doc.assignment_id,
                        AssignmentDocument.document_id == doc.id,
                    )
                ).first()
                if existing is None:
                    session.add(
                        AssignmentDocument(
                            assignment_id=doc.assignment_id,
                            document_id=doc.id,
                        )
                    )
            session.commit()
    except Exception:
        # Backfill is best-effort; never block startup on legacy quirks.
        pass


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
