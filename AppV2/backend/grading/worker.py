from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..core.config import Settings
from ..db.database import get_engine
from ..db.models import Submission, SubmissionStatus
from .pipeline import GradingPipeline
from .types import GradingOutcome, SubmissionSnapshot

logger = logging.getLogger(__name__)

# Log at INFO when idle so operators see the worker is alive (avoid spamming every poll tick).
_IDLE_HEARTBEAT_SEC = 30.0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _claim_next_pending(session: Session) -> Submission | None:
    row = session.exec(
        select(Submission)
        .where(Submission.status == SubmissionStatus.pending)
        .order_by(Submission.created_at)
        .limit(1)
    ).first()
    if row is None:
        return None
    row.status = SubmissionStatus.running
    row.updated_at = _utc_now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _apply_outcome(row: Submission, outcome: GradingOutcome) -> None:
    row.grade = outcome.grade
    row.status = outcome.status
    row.corrected_code = outcome.corrected_code
    row.diff = outcome.diff
    row.stdout = outcome.stdout
    row.stderr = outcome.stderr
    row.output = outcome.output
    row.feedback = outcome.feedback
    row.updated_at = _utc_now()


class GradingWorker:
    """Polls for `pending` submissions, claims one as `running`, runs `GradingPipeline`, saves outcome."""

    def __init__(self, pipeline: GradingPipeline, settings: Settings) -> None:
        self._pipeline = pipeline
        self._settings = settings
        self._last_idle_heartbeat = 0.0

    async def run_until_stopped(self, stop: asyncio.Event) -> None:
        logger.info(
            "[grading-worker] started | backend=%s poll_interval=%ss idle_heartbeat=%ss",
            self._settings.grading_backend,
            self._settings.grading_poll_interval_seconds,
            _IDLE_HEARTBEAT_SEC,
        )
        while not stop.is_set():
            try:
                processed = await self._process_one()
            except Exception:
                logger.exception("[grading-worker] iteration failed (will retry)")
                processed = False

            if not processed:
                now = time.monotonic()
                if now - self._last_idle_heartbeat >= _IDLE_HEARTBEAT_SEC:
                    logger.info(
                        "[grading-worker] idle | no pending submissions (poll every %ss)",
                        self._settings.grading_poll_interval_seconds,
                    )
                    self._last_idle_heartbeat = now
                try:
                    await asyncio.wait_for(
                        stop.wait(),
                        timeout=self._settings.grading_poll_interval_seconds,
                    )
                except asyncio.TimeoutError:
                    pass
        logger.info("[grading-worker] stopped")

    async def _process_one(self) -> bool:
        engine = get_engine()
        with Session(engine) as session:
            row = _claim_next_pending(session)
            if row is None:
                return False
            snap = SubmissionSnapshot.from_submission(row)

        logger.info(
            "[grading-worker] claimed submission %s | assignment=%s student=%s | status pending→running",
            snap.id,
            snap.assignment_id,
            snap.student_id,
        )

        outcome: GradingOutcome
        t0 = time.perf_counter()
        try:
            logger.info("[grading-worker] pipeline running | submission=%s", snap.id)
            outcome = await self._pipeline.run(snap)
        except Exception as e:
            logger.exception("[grading-worker] pipeline failed | submission=%s", snap.id)
            outcome = GradingOutcome(
                grade=0.0,
                status=SubmissionStatus.failed,
                stderr=str(e),
                feedback="Grading pipeline raised an exception.",
            )

        elapsed = time.perf_counter() - t0
        with Session(engine) as session:
            row = session.get(Submission, snap.id)
            if row is None:
                logger.warning(
                    "[grading-worker] submission %s missing after pipeline; skip persist",
                    snap.id,
                )
                return True
            if row.status != SubmissionStatus.running:
                logger.warning(
                    "[grading-worker] submission %s expected status=running, got %s; skip persist",
                    snap.id,
                    row.status,
                )
                return True
            _apply_outcome(row, outcome)
            session.add(row)
            session.commit()

        logger.info(
            "[grading-worker] finished submission %s | status=%s grade=%s | pipeline %.2fs | persisted",
            snap.id,
            outcome.status.value,
            outcome.grade,
            elapsed,
        )
        self._last_idle_heartbeat = time.monotonic()
        return True
