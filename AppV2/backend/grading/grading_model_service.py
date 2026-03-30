"""Persistent global grading model selection (SQLite).

Exactly one `GradingModel.is_active` row is preferred; bootstrap creates a default
from `LLAMA_GGUF_FILE` / `LLAMA_OPENAI_MODEL` when the table is empty.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..db.database import get_engine
from ..db.models import GradingModel

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_grading_models_bootstrapped() -> None:
    """Create default catalog row if missing; ensure one active row."""
    engine = get_engine()
    with Session(engine) as session:
        rows = list(session.exec(select(GradingModel)).all())
        if not rows:
            gguf = os.getenv("LLAMA_GGUF_FILE", "model.gguf").strip() or "model.gguf"
            openai = os.getenv("LLAMA_OPENAI_MODEL", "local-gguf").strip() or "local-gguf"
            m = GradingModel(
                display_name="Default",
                gguf_filename=gguf,
                openai_model_name=openai,
                is_active=True,
            )
            session.add(m)
            session.commit()
            logger.info("grading_models: created default catalog row | gguf=%s openai=%s", gguf, openai)
            return
        if not any(r.is_active for r in rows):
            first = rows[0]
            first.is_active = True
            first.updated_at = _utc_now()
            session.add(first)
            session.commit()
            logger.info("grading_models: activated first catalog row | id=%s", first.id)


def get_active_openai_model_name() -> str:
    """OpenAI-compatible model name for ChatOpenAI -> llama-server."""
    try:
        engine = get_engine()
        with Session(engine) as session:
            row = session.exec(select(GradingModel).where(GradingModel.is_active)).first()
            if row:
                return row.openai_model_name.strip()
    except Exception:
        logger.debug("grading_models: read active model failed, using env", exc_info=True)
    return os.getenv("LLAMA_OPENAI_MODEL", "local-gguf").strip()


def get_active_grading_model() -> GradingModel | None:
    try:
        engine = get_engine()
        with Session(engine) as session:
            return session.exec(select(GradingModel).where(GradingModel.is_active)).first()
    except Exception:
        return None


def list_grading_models(session: Session) -> list[GradingModel]:
    return list(session.exec(select(GradingModel).order_by(GradingModel.created_at)).all())
