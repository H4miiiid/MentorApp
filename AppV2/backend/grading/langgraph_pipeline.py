"""LangGraph repair workflow from `workflow_runtime` (ported legacy agentic grading)."""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
from typing import Any

from ..core.config import Settings
from ..db.models import SubmissionStatus
from ..workflow_runtime.graph import run_workflow
from .pipeline import GradingPipeline
from .types import GradingOutcome, SubmissionSnapshot

logger = logging.getLogger(__name__)


def _unified_diff(original: str, final: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            original.splitlines(),
            final.splitlines(),
            fromfile="student",
            tofile="corrected",
            lineterm="",
        )
    )


def _grade_from_result(result: dict[str, Any]) -> float:
    status = result.get("final_status") or ""
    if status == "success":
        return 100.0
    attempts = int(result.get("attempt_count") or 0)
    return max(0.0, 55.0 - min(attempts * 8.0, 55.0))


def _feedback_blob(result: dict[str, Any]) -> str:
    payload = {
        "final_status": result.get("final_status"),
        "attempt_count": result.get("attempt_count"),
        "error_category": result.get("error_category"),
        "stop_reason": result.get("stop_reason"),
        "route_history": result.get("route_history"),
        "attempt_history_tail": (result.get("attempt_history") or [])[-8:],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


class LangGraphGradingPipeline(GradingPipeline):
    """Runs the LangGraph repair workflow in a thread pool (blocking `invoke`)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def run(self, submission: SubmissionSnapshot) -> GradingOutcome:
        logger.info(
            "[grading-langgraph] start | submission=%s assignment=%s",
            submission.id,
            submission.assignment_id,
            extra={
                "wf_kind": "backend",
                "wf_phase": "grading",
                "wf_submission_id": submission.id,
                "wf_assignment_id": submission.assignment_id,
            },
        )

        def _sync_run() -> dict[str, Any]:
            return run_workflow(
                submission.code,
                max_attempts=self._settings.grading_max_attempts,
                submission_id=submission.id,
                assignment_id=submission.assignment_id,
                run_id=submission.id,
            )

        try:
            result = await asyncio.to_thread(_sync_run)
        except Exception as e:
            logger.exception(
                "[grading-langgraph] workflow failed | submission=%s",
                submission.id,
                extra={
                    "wf_kind": "backend",
                    "wf_phase": "grading",
                    "wf_submission_id": submission.id,
                    "wf_assignment_id": submission.assignment_id,
                },
            )
            return GradingOutcome(
                grade=0.0,
                status=SubmissionStatus.failed,
                corrected_code=submission.code,
                stderr=str(e),
                feedback="LangGraph workflow raised an exception.",
            )

        final_code = (result.get("final_code") or submission.code).strip()
        original = submission.code
        diff = _unified_diff(original, final_code) if final_code != original else ""
        final_status = (result.get("final_status") or "failure").lower()
        status = SubmissionStatus.completed if final_status == "success" else SubmissionStatus.failed
        grade = _grade_from_result(result)

        logger.info(
            "[grading-langgraph] done | submission=%s final_status=%s grade=%s",
            submission.id,
            final_status,
            grade,
            extra={
                "wf_kind": "backend",
                "wf_phase": "grading",
                "wf_submission_id": submission.id,
                "wf_assignment_id": submission.assignment_id,
            },
        )

        stderr_parts = []
        if final_status != "success":
            if result.get("stop_reason"):
                stderr_parts.append(f"stop_reason: {result.get('stop_reason')}")
            if result.get("error_category"):
                stderr_parts.append(f"error_category: {result.get('error_category')}")

        return GradingOutcome(
            grade=grade,
            status=status,
            corrected_code=final_code,
            diff=diff,
            stdout="",
            stderr="\n".join(stderr_parts) if stderr_parts else "",
            feedback=_feedback_blob(result),
        )
