from __future__ import annotations

import asyncio
import difflib
import logging
import random

from ..core.config import Settings
from ..db.models import SubmissionStatus
from .pipeline import GradingPipeline
from .types import GradingOutcome, SubmissionSnapshot

logger = logging.getLogger(__name__)


def _mock_stderr() -> str:
    return (
        "Traceback (most recent call last):\n"
        '  File "<mock-sandbox>", line 2, in <module>\n'
        "    result = solve()\n"
        "NameError: name 'solve' is not defined\n"
        "\n"
        "[mock] Simulated runtime error for UI testing. Real pipeline will show actual tracebacks."
    )


def _mock_corrected_from_submitted(code: str) -> str:
    """Produce a plausible 'fixed' version so students see corrected_code + diff in the app."""
    base = code.rstrip() if code.strip() else "# (empty submission — mock filler)"
    return (
        f"{base}\n\n"
        "# --- [mock] autograder suggestion ---\n"
        "# Example fix: define missing names and handle edge cases.\n"
        "def solve():\n"
        "    return 42\n"
    )


def _unified_diff(before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="submitted.py",
            tofile="corrected.py",
        )
    )


class MockGradingPipeline(GradingPipeline):
    """End-to-end stand-in: delay + random grade. Replace with LangGraph via `GradingPipeline`."""

    def __init__(self, settings: Settings) -> None:
        self._sleep_seconds = settings.grading_mock_sleep_seconds

    async def run(self, submission: SubmissionSnapshot) -> GradingOutcome:
        logger.info(
            "[grading-mock] simulating work | submission=%s | sleep=%ss",
            submission.id,
            self._sleep_seconds,
        )
        await asyncio.sleep(self._sleep_seconds)
        grade = round(random.uniform(0.0, 100.0), 1)
        src = submission.code or ""
        corrected = _mock_corrected_from_submitted(src)
        diff_text = _unified_diff(src, corrected)
        stderr = _mock_stderr()
        stdout = (
            "[mock] tests collected 1 item\n"
            "[mock] running test_student_submission ... FAILED\n"
            f"[mock] autograder score (random): {grade}\n"
        )
        logger.info(
            "[grading-mock] done | submission=%s | grade=%s",
            submission.id,
            grade,
        )
        return GradingOutcome(
            grade=grade,
            status=SubmissionStatus.completed,
            corrected_code=corrected,
            diff=diff_text if diff_text.strip() else "(no diff — identical)\n",
            stdout=stdout,
            stderr=stderr,
            feedback=(
                f"Mock autograder: review stderr for simulated errors, corrected code, and diff. "
                f"Submission {submission.id[:8]}… scored {grade}."
            ),
        )
