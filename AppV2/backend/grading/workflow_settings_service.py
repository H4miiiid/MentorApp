"""Read/write global workflow settings from the DB (admin-managed, no restart needed)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import Session

from ..db.database import get_engine
from ..db.models import WorkflowSetting

logger = logging.getLogger(__name__)

COMPLETENESS_PROVIDER_KEY = "completeness_provider"
COMPLETENESS_PROVIDER_DEFAULT = "local_sft"
VALID_COMPLETENESS_PROVIDERS = {"local_sft", "openrouter"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_completeness_provider() -> str:
    """Return the active completeness provider (``local_sft`` or ``openrouter``)."""
    try:
        engine = get_engine()
        with Session(engine) as session:
            row = session.get(WorkflowSetting, COMPLETENESS_PROVIDER_KEY)
            if row and row.value in VALID_COMPLETENESS_PROVIDERS:
                return row.value
    except Exception:
        logger.debug("[workflow-settings] could not read completeness_provider; using default")
    return COMPLETENESS_PROVIDER_DEFAULT


def set_completeness_provider(provider: str) -> str:
    """Set the active completeness provider; returns the persisted value."""
    if provider not in VALID_COMPLETENESS_PROVIDERS:
        raise ValueError(f"Invalid provider {provider!r}; choose from {VALID_COMPLETENESS_PROVIDERS}")
    engine = get_engine()
    with Session(engine) as session:
        row = session.get(WorkflowSetting, COMPLETENESS_PROVIDER_KEY)
        if row is None:
            row = WorkflowSetting(key=COMPLETENESS_PROVIDER_KEY, value=provider, updated_at=_utc_now())
        else:
            row.value = provider
            row.updated_at = _utc_now()
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.value
