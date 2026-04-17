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


# Highest possible grade when the student's ORIGINAL submission did not pass and the
# LLM repair loop had to intervene. Anchoring strictly below 100 means the grade itself
# communicates "you got help" without needing to read the feedback panel.
REPAIRED_SUCCESS_CAP = 85.0
REPAIRED_SUCCESS_FLOOR = 40.0


def _grade_repaired_success(*, attempts: int, max_attempts: int, initial_category: str) -> float:
    """Grade a submission that only passed after N >= 1 LLM repair attempts.

    Design goals:
      * First-try passes stay at 100.0 (handled by the caller).
      * One small fix for a clearly "typo-ish" error (syntax/name/stdin_eof) → high
        80s, still noticeably less than 100.
      * A single repair for a deeper logic / API error → low 70s.
      * Many repair attempts drop the score proportionally, never below
        ``REPAIRED_SUCCESS_FLOOR``, so a student who eventually passed is still
        rewarded above a student who never did.
    """
    if attempts <= 0:
        return 100.0

    # Anchor score by the *initial* error category (what the student actually wrote),
    # not the per-attempt category drift during repair.
    anchor_by_category: dict[str, float] = {
        "syntax_error": 82.0,
        "name_error": 78.0,
        "stdin_eof": 80.0,
        "local_reasoning_error": 72.0,
        "api_library_error": 70.0,
        "timeout": 68.0,
    }
    anchor = anchor_by_category.get(initial_category, 72.0)

    # Each extra repair attempt beyond the first compounds the deduction. We use a
    # smooth curve so we never cliff-drop, and we scale by the workflow's configured
    # ``max_attempts`` so admins tuning the budget don't silently change the grading
    # curve.
    budget = max(max_attempts, 2)
    extra = max(0, attempts - 1)
    dock = 6.0 * extra + 18.0 * (extra / budget)

    score = min(REPAIRED_SUCCESS_CAP, anchor) - dock
    score = max(REPAIRED_SUCCESS_FLOOR, score)
    return round(score, 1)


def _grade_from_result(
    original_code: str,
    final_code: str,
    result: dict[str, Any],
    *,
    grading_max_attempts: int,
) -> float:
    """Partial credit on failure: uses error category, attempt budget used, stagnation, and edit distance.

    The old formula ``55 - min(attempts * 8, 55)`` always yielded the same score for a fixed attempt
    count (e.g. 23 when attempt_count == 4), regardless of error severity or progress.

    **Repaired-success grading.** The prior policy returned a flat ``100.0`` whenever
    ``final_status == "success"``, which meant a student whose original submission had a
    syntax error and was rewritten by the LLM got the same grade as a student whose code
    passed on the first try. We now distinguish:

    * ``attempt_count == 0`` (no repairs needed) → full 100.
    * repairs were needed but the workflow eventually succeeded → partial credit
      anchored by the *initial* error category, then docked per repair attempt. Capped
      at 85 so it's always clear from the number alone that help was required.
    """
    status = (result.get("final_status") or "").lower()
    attempts = int(result.get("attempt_count") or 0)
    max_a = int(result.get("max_attempts") or grading_max_attempts or 6)

    if status == "success":
        if attempts <= 0:
            return 100.0
        return _grade_repaired_success(
            attempts=attempts,
            max_attempts=max_a,
            initial_category=(result.get("initial_error_category") or "").strip(),
        )
    if status == "sandbox_unavailable":
        # Infra failure — do not punish the student. Grade stays at 0 only because
        # we never ran the code; status/feedback make clear it was not their fault
        # and the submission should be re-graded.
        return 0.0

    category = (result.get("error_category") or "").strip()
    stop = (result.get("stop_reason") or "").strip()
    nmc = int(result.get("no_meaningful_change_count") or 0)
    rep = int(result.get("repeated_failure_count") or 0)

    # Midpoint partial credit by error class (syntax/name tend to be "smaller" than deep logic issues).
    cat_mid: dict[str, float] = {
        "syntax_error": 74.0,
        "name_error": 70.0,
        "stdin_eof": 72.0,
        "timeout": 52.0,
        "local_reasoning_error": 56.0,
        "api_library_error": 52.0,
    }
    base = cat_mid.get(category, 48.0)

    # Penalize using more of the repair attempt budget (smooth, not a single step per attempt).
    frac_used = attempts / max(max_a, 1)
    score = base * (1.0 - 0.62 * frac_used)

    # Stagnation: repair steps that did not change code meaningfully.
    score -= min(18.0, nmc * 5.5)
    # Same traceback signature repeating.
    score -= min(14.0, rep * 4.0)

    if stop == "no_meaningful_change":
        score -= 10.0
    elif stop == "max_attempts_reached":
        score -= 4.0

    orig = original_code or ""
    final = final_code or ""
    sim = difflib.SequenceMatcher(a=orig, b=final).ratio()
    if sim >= 0.998:
        score -= 22.0
    else:
        score += min(12.0, (1.0 - sim) * 28.0)

    return max(0.0, min(99.9, round(score, 1)))


def _was_repaired(result: dict[str, Any]) -> bool:
    """True when the student's original submission failed but the workflow later
    succeeded via LLM repair. Used to gate the "repaired" UI banner + grade cap."""
    return (result.get("final_status") or "").lower() == "success" and int(
        result.get("attempt_count") or 0
    ) > 0


def _initial_error_snippet(result: dict[str, Any], max_chars: int = 1200) -> str:
    """Short, student-readable summary of the original failure."""
    tb = (result.get("initial_traceback") or "").strip()
    if not tb:
        return ""
    if len(tb) > max_chars:
        tb = tb[:max_chars].rstrip() + "\n... (truncated)"
    return tb


def _feedback_blob(result: dict[str, Any]) -> str:
    payload: dict[str, Any] = {
        "final_status": result.get("final_status"),
        "attempt_count": result.get("attempt_count"),
        "max_attempts": result.get("max_attempts"),
        "error_category": result.get("error_category"),
        "stop_reason": result.get("stop_reason"),
        "route_history": result.get("route_history"),
        "attempt_history_tail": (result.get("attempt_history") or [])[-8:],
        "no_meaningful_change_count": result.get("no_meaningful_change_count"),
        "repeated_failure_count": result.get("repeated_failure_count"),
        # Exposed so the frontend FeedbackPanel can show a "Repaired by assistant"
        # banner + original error preview whenever attempt_count > 0.
        "repaired": _was_repaired(result),
        "initial_error_category": result.get("initial_error_category") or "",
        "initial_error_type": result.get("initial_error_type") or "",
        "initial_error_explanation": result.get("initial_error_explanation") or "",
        "initial_traceback": _initial_error_snippet(result),
    }
    if result.get("sandbox_error"):
        payload["sandbox_error"] = result["sandbox_error"]
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
        grade = _grade_from_result(
            submission.code,
            final_code,
            result,
            grading_max_attempts=self._settings.grading_max_attempts,
        )

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

        if final_status == "sandbox_unavailable":
            sandbox_msg = (result.get("sandbox_error") or "").strip() or (
                "The grading sandbox (Docker) was unavailable at grading time."
            )
            stderr_text = (
                "Grading infrastructure error: the code was not executed because the "
                "sandbox was unavailable.\n" + sandbox_msg
            )
            return GradingOutcome(
                grade=grade,
                status=status,
                corrected_code=original,
                diff="",
                stdout="",
                stderr=stderr_text,
                feedback=_feedback_blob(result),
            )

        stderr_parts: list[str] = []
        if final_status != "success":
            if result.get("stop_reason"):
                stderr_parts.append(f"stop_reason: {result.get('stop_reason')}")
            if result.get("error_category"):
                stderr_parts.append(f"error_category: {result.get('error_category')}")
        elif _was_repaired(result):
            # The student's ORIGINAL code failed and the LLM fixed it. Without this
            # block the submission page would show empty stdout/stderr and the grade
            # would look unjustified next to the (now correct) code. Surface the real
            # first-attempt traceback so the student can learn from it.
            cat = (result.get("initial_error_category") or "").strip() or "error"
            err_type = (result.get("initial_error_type") or "").strip()
            first_tb = _initial_error_snippet(result)
            header = (
                "Your original submission did not run. The grading assistant repaired it for you; "
                "the corrected version is in the diff panel below. The full grade is capped when "
                "auto-repair is needed — please study the original error so the same issue does not "
                "repeat on the next assignment."
            )
            label = f"Original error ({cat}{f', {err_type}' if err_type else ''}):"
            stderr_parts.append(header)
            if first_tb:
                stderr_parts.append(label)
                stderr_parts.append(first_tb)

        return GradingOutcome(
            grade=grade,
            status=status,
            corrected_code=final_code,
            diff=diff,
            stdout="",
            stderr="\n\n".join(stderr_parts) if stderr_parts else "",
            feedback=_feedback_blob(result),
        )
