"""LangGraph repair workflow from `workflow_runtime` (ported legacy agentic grading)."""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from ..core.config import Settings
from ..db.database import get_engine
from ..db.models import Assignment, AssignmentDocument, Document, SubmissionStatus
from ..workflow_runtime.graph import run_workflow
from ..workflow_runtime.llm_clients import infer_requirement_severity
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


MISTAKE_WEIGHT_BY_CATEGORY: dict[str, float] = {
    "syntax_error": 1.0,
    "name_error": 1.0,
    "stdin_eof": 1.0,
    "local_reasoning_error": 1.25,
    "api_library_error": 1.35,
    "timeout": 1.5,
    "sandbox_unavailable": 0.0,
}

INFERRED_FIX_UNIT_WEIGHT = 0.4
MAX_INFERRED_FIX_UNITS = 4

# Requirement penalties are intentionally moderate: the UI explains missing work,
# while the score should still reward runnable partial solutions.
_COMPLETENESS_SEVERITY_WEIGHT: dict[str, float] = {"critical": 10.0, "medium": 5.0, "minor": 2.0}
_COMPLETENESS_PARTIAL_FACTOR = 1.0
_MAX_COMPLETENESS_PENALTY = 40.0
_MIN_GRADE_INCOMPLETE_FIRST_PASS = 55.0
_PASS_GRADE_THRESHOLD = 70.0


def _completeness_penalty_from_dict(completeness: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """Weighted penalty points for missing/partial requirements; capped."""
    requirements = completeness.get("requirements") or []
    breakdown_items: list[dict[str, Any]] = []
    penalty = 0.0
    for r in requirements:
        if not isinstance(r, dict):
            continue
        status = (r.get("status") or "").lower()
        if status not in ("missing", "partial"):
            continue
        sev = (r.get("severity") or "medium").lower()
        if sev not in _COMPLETENESS_SEVERITY_WEIGHT:
            sev = "medium"
        unit = _COMPLETENESS_SEVERITY_WEIGHT[sev]
        if status == "partial":
            unit *= _COMPLETENESS_PARTIAL_FACTOR
        penalty += unit
        breakdown_items.append(
            {
                "text": str(r.get("text", "")).strip(),
                "status": status,
                "severity": sev,
                "penalty_points": round(unit, 2),
            }
        )

    if penalty == 0.0 and not completeness.get("complete", True):
        for m in completeness.get("missing_requirements") or []:
            if not isinstance(m, str):
                continue
            mt = m.strip()
            if not mt:
                continue
            sev = infer_requirement_severity(mt)
            unit = float(_COMPLETENESS_SEVERITY_WEIGHT.get(sev, 10.0))
            penalty += unit
            breakdown_items.append(
                {
                    "text": mt,
                    "status": "missing",
                    "severity": sev,
                    "penalty_points": round(unit, 2),
                }
            )

    penalty = min(_MAX_COMPLETENESS_PENALTY, penalty)
    details = {
        "items": breakdown_items,
        "total_penalty": round(penalty, 2),
        "penalty_cap": _MAX_COMPLETENESS_PENALTY,
    }
    return penalty, details


def _grade_first_pass_incomplete(completeness: dict[str, Any]) -> float:
    penalty, _ = _completeness_penalty_from_dict(completeness)
    return max(_MIN_GRADE_INCOMPLETE_FIRST_PASS, round(100.0 - penalty, 1))


def _is_meaningful_code_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return False
    return True


def _infer_repair_fix_units(original_code: str, final_code: str) -> int:
    before = (original_code or "").splitlines()
    after = (final_code or "").splitlines()
    if before == after:
        return 0

    matcher = difflib.SequenceMatcher(a=before, b=after)
    units = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        before_changed = [line for line in before[i1:i2] if _is_meaningful_code_line(line)]
        after_changed = [line for line in after[j1:j2] if _is_meaningful_code_line(line)]
        if before_changed or after_changed:
            units += max(len(before_changed), len(after_changed), 1)

    return min(MAX_INFERRED_FIX_UNITS, units)


def _extract_mistake_profile(
    result: dict[str, Any],
    *,
    original_code: str = "",
    final_code: str = "",
) -> dict[str, Any]:
    events = result.get("error_events") or []
    by_signature: dict[str, dict[str, Any]] = {}
    for event in events:
        signature = (event.get("signature") or "").strip()
        if not signature:
            continue
        if signature not in by_signature:
            by_signature[signature] = {
                "category": (event.get("category") or "api_library_error").strip(),
                "line": (event.get("error_line") or "").strip(),
            }

    if not by_signature:
        fallback_category = (
            (result.get("initial_error_category") or "").strip()
            or (result.get("error_category") or "").strip()
        )
        if fallback_category:
            by_signature[fallback_category] = {
                "category": fallback_category,
                "line": (result.get("initial_error_type") or "").strip(),
            }

    categories = sorted({item["category"] for item in by_signature.values() if item.get("category")})
    mistake_lines = [item.get("line", "") for item in by_signature.values() if item.get("line")][:8]
    # Per distinct error signature (not per unique category): two API errors both count.
    observed_weighted_units = sum(
        MISTAKE_WEIGHT_BY_CATEGORY.get(
            (item.get("category") or "").strip() or "api_library_error",
            1.6,
        )
        for item in by_signature.values()
    )
    # Use computed signatures first; fallback to workflow-provided aggregate when available.
    observed_mistake_count = len(by_signature) or int(result.get("mistake_count") or 0)

    inferred_fix_units = 0
    status = (result.get("final_status") or "").lower()
    attempts = int(result.get("attempt_count") or 0)
    if status == "success" and attempts > 0:
        inferred_fix_units = _infer_repair_fix_units(original_code, final_code)

    effective_mistake_count = max(observed_mistake_count, inferred_fix_units)
    inferred_extra_units = max(0, effective_mistake_count - observed_mistake_count)
    weighted_units = observed_weighted_units + INFERRED_FIX_UNIT_WEIGHT * inferred_extra_units
    if effective_mistake_count > 0 and weighted_units <= 0:
        weighted_units = 1.0

    return {
        "mistake_count": effective_mistake_count,
        "observed_mistake_count": observed_mistake_count,
        "inferred_fix_units": inferred_fix_units,
        "mistake_categories": categories,
        "mistake_lines": mistake_lines,
        "weighted_units": weighted_units,
    }


def _grade_repaired_success(*, attempts: int, max_attempts: int, weighted_units: float, mistake_count: int) -> float:
    """Grade repaired-success outcomes using weighted mistake severity + attempts."""
    if attempts <= 0:
        return 100.0

    budget = max(max_attempts, 2)
    extra_attempts = max(0, attempts - 1)
    attempt_penalty = 0.9 * extra_attempts + 2.0 * (extra_attempts / budget)
    mistake_penalty = 2.5 * max(1.0, weighted_units)
    multiplicity_penalty = max(0, mistake_count - 1) * 0.6

    score = 100.0 - mistake_penalty - attempt_penalty - multiplicity_penalty
    score = max(75.0, min(99.0, score))
    return round(score, 1)


def _grade_from_result(
    original_code: str,
    final_code: str,
    result: dict[str, Any],
    *,
    grading_max_attempts: int,
) -> float:
    """Mistake-weighted scoring with guaranteed 100 for clean first-pass success."""
    status = (result.get("final_status") or "").lower()
    attempts = int(result.get("attempt_count") or 0)
    max_a = int(result.get("max_attempts") or grading_max_attempts or 6)
    profile = _extract_mistake_profile(result, original_code=original_code, final_code=final_code)
    weighted_units = float(profile["weighted_units"])
    mistake_count = int(profile["mistake_count"])

    if status == "success":
        completeness = result.get("original_code_completeness") or result.get("first_pass_completeness") or {}
        if attempts <= 0:
            if not completeness.get("complete", True):
                return _grade_first_pass_incomplete(completeness)
            return 100.0
        repair_grade = _grade_repaired_success(
            attempts=attempts,
            max_attempts=max_a,
            weighted_units=weighted_units,
            mistake_count=mistake_count,
        )
        if not completeness.get("complete", True):
            comp_penalty, _ = _completeness_penalty_from_dict(completeness)
            repair_grade = max(_MIN_GRADE_INCOMPLETE_FIRST_PASS, round(repair_grade - comp_penalty, 1))
        return repair_grade
    if status == "sandbox_unavailable":
        # Infra failure — do not punish the student. Grade stays at 0 only because
        # we never ran the code; status/feedback make clear it was not their fault
        # and the submission should be re-graded.
        return 0.0

    stop = (result.get("stop_reason") or "").strip()
    nmc = int(result.get("no_meaningful_change_count") or 0)
    rep = int(result.get("repeated_failure_count") or 0)

    # Failure outcomes still get partial credit based on weighted mistakes and progress.
    budget_ratio = attempts / max(max_a, 1)
    score = 92.0
    score -= 3.5 * max(1.0, weighted_units)
    score -= 2.5 * budget_ratio
    score -= min(3.5, nmc * 1.0)
    score -= min(3.5, rep * 1.0)

    if stop == "no_meaningful_change":
        score -= 1.5
    elif stop == "max_attempts_reached":
        score -= 1.0
    elif stop == "all_strategies_exhausted":
        score -= 1.25

    # Small boost when there is evidence of real edits toward a fix.
    orig = original_code or ""
    final = final_code or ""
    sim = difflib.SequenceMatcher(a=orig, b=final).ratio()
    if sim < 0.995:
        score += min(6.0, (1.0 - sim) * 30.0)

    if mistake_count >= 3:
        score -= 0.75 * (mistake_count - 2)

    return max(45.0, min(97.0, round(score, 1)))


def _was_repaired(result: dict[str, Any]) -> bool:
    """True when the student's original submission failed but the workflow later
    succeeded via LLM repair. Used to gate the "repaired" UI banner + grade cap."""
    return (result.get("final_status") or "").lower() == "success" and int(
        result.get("attempt_count") or 0
    ) > 0


def _used_requirement_repair(result: dict[str, Any]) -> bool:
    return bool(result.get("used_requirement_repair")) or int(result.get("requirement_repair_count") or 0) > 0


def _submission_status_from_grade(final_status: str, grade: float) -> SubmissionStatus:
    """Map workflow success + numeric grade to pass/fail submission status.

    Policy: grade >= 75 is pass (completed); otherwise fail.
    """
    if (final_status or "").lower() != "success":
        return SubmissionStatus.failed
    return SubmissionStatus.completed if float(grade) >= _PASS_GRADE_THRESHOLD else SubmissionStatus.failed


def _initial_error_snippet(result: dict[str, Any], max_chars: int = 1200) -> str:
    """Short, student-readable summary of the original failure."""
    tb = (result.get("initial_traceback") or "").strip()
    if not tb:
        return ""
    if len(tb) > max_chars:
        tb = tb[:max_chars].rstrip() + "\n... (truncated)"
    return tb


def _feedback_blob(result: dict[str, Any], *, original_code: str = "", final_code: str = "") -> str:
    profile = _extract_mistake_profile(result, original_code=original_code, final_code=final_code)
    payload: dict[str, Any] = {
        "final_status": result.get("final_status"),
        "attempt_count": result.get("attempt_count"),
        "max_attempts": result.get("max_attempts"),
        "error_category": result.get("error_category"),
        "mistake_count": profile["mistake_count"],
        "observed_mistake_count": profile["observed_mistake_count"],
        "inferred_fix_units": profile["inferred_fix_units"],
        "mistake_categories": profile["mistake_categories"],
        "mistake_lines": profile["mistake_lines"],
        "stop_reason": result.get("stop_reason"),
        "route_history": result.get("route_history"),
        "attempt_history_tail": (result.get("attempt_history") or [])[-8:],
        "no_meaningful_change_count": result.get("no_meaningful_change_count"),
        "repeated_failure_count": result.get("repeated_failure_count"),
        # Exposed so the frontend FeedbackPanel can show a "Repaired by assistant"
        # banner + original error preview whenever attempt_count > 0.
        "repaired": _was_repaired(result),
        "requirement_repaired": _used_requirement_repair(result),
        "requirement_repair_count": result.get("requirement_repair_count", 0),
        "max_requirement_repairs": result.get("max_requirement_repairs", 1),
        "requirement_repair_exhausted": result.get("requirement_repair_exhausted", False),
        "initial_error_category": result.get("initial_error_category") or "",
        "initial_error_type": result.get("initial_error_type") or "",
        "initial_error_explanation": result.get("initial_error_explanation") or "",
        "initial_traceback": _initial_error_snippet(result),
    }
    if result.get("sandbox_error"):
        payload["sandbox_error"] = result["sandbox_error"]

    completeness = result.get("original_code_completeness") or result.get("first_pass_completeness") or {}
    if completeness:
        _, grading_breakdown = _completeness_penalty_from_dict(completeness)
        payload["completeness"] = {
            "complete": completeness.get("complete"),
            "provider": completeness.get("provider", ""),
            "confidence": completeness.get("confidence", 0),
            "rationale": completeness.get("rationale", ""),
            "missing_requirements": completeness.get("missing_requirements", []),
            "requirements": completeness.get("requirements", []),
            "grading_breakdown": grading_breakdown,
        }

    final_completeness = result.get("first_pass_completeness") or {}
    if final_completeness and final_completeness != completeness:
        payload["final_completeness"] = {
            "complete": final_completeness.get("complete"),
            "provider": final_completeness.get("provider", ""),
            "confidence": final_completeness.get("confidence", 0),
            "rationale": final_completeness.get("rationale", ""),
            "missing_requirements": final_completeness.get("missing_requirements", []),
            "requirements": final_completeness.get("requirements", []),
        }

    return json.dumps(payload, indent=2, ensure_ascii=False)


def _collect_assignment_data_files(settings: Settings, assignment_id: str) -> list[tuple[str, str]]:
    """Resolve the absolute paths of every document currently attached to an assignment.

    Archived documents that remain attached are still included so past submissions keep
    running against the same files the student saw when they submitted. Entries whose
    files are missing on disk are skipped (logged as a warning by the sandbox layer).
    """
    if not assignment_id:
        return []
    engine = get_engine()
    root = Path(settings.storage_dir).resolve()
    files: list[tuple[str, str]] = []
    with Session(engine) as session:
        rows = session.exec(
            select(AssignmentDocument).where(AssignmentDocument.assignment_id == assignment_id)
        ).all()
        for row in rows:
            d = session.get(Document, row.document_id)
            if d is None or not d.file_path:
                continue
            p = Path(d.file_path)
            if not p.is_absolute():
                p = (root / p).resolve()
            else:
                p = p.resolve()
            # Refuse anything that escapes the storage root — defense in depth.
            try:
                p.relative_to(root)
            except ValueError:
                continue
            target_name = Path(d.file_path).name or f"doc_{d.id}"
            files.append((str(p), target_name))
    return files


def _load_assignment_description(assignment_id: str) -> str:
    if not assignment_id:
        return ""
    engine = get_engine()
    with Session(engine) as session:
        row = session.get(Assignment, assignment_id)
        if row is None:
            return ""
        return (row.description or "").strip()


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

        data_files = _collect_assignment_data_files(self._settings, submission.assignment_id)
        assignment_description = _load_assignment_description(submission.assignment_id)
        if data_files:
            logger.info(
                "[grading-langgraph] attached_documents=%s | submission=%s",
                len(data_files),
                submission.id,
            )

        def _sync_run() -> dict[str, Any]:
            return run_workflow(
                submission.code,
                max_attempts=self._settings.grading_max_attempts,
                submission_id=submission.id,
                assignment_id=submission.assignment_id,
                assignment_description=assignment_description,
                run_id=submission.id,
                data_files=data_files or None,
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
                output="",
                feedback="LangGraph workflow raised an exception.",
            )

        final_code = (result.get("final_code") or submission.code).strip()
        original = submission.code
        diff = _unified_diff(original, final_code) if final_code != original else ""
        final_status = (result.get("final_status") or "failure").lower()
        final_output = (
            (result.get("final_success_stdout") or "").strip() if final_status == "success" else ""
        )
        grade = _grade_from_result(
            submission.code,
            final_code,
            result,
            grading_max_attempts=self._settings.grading_max_attempts,
        )
        status = _submission_status_from_grade(final_status, grade)

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
                output="",
                feedback=_feedback_blob(result, original_code=original, final_code=original),
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
            if first_tb or result.get("initial_error_category"):
                header = (
                    "Your original submission did not run. The grading assistant repaired it for you; "
                    "the corrected version is in the diff panel below. The full grade is capped when "
                    "auto-repair is needed — please study the original error so the same issue does not "
                    "repeat on your next submission."
                )
            elif _used_requirement_repair(result):
                header = (
                    "Your original submission ran, but it did not satisfy every assignment requirement. "
                    "The grading assistant added the missing requirement work; the completed version is "
                    "shown in the corrected-code and diff panels below."
                )
            else:
                header = (
                    "The grading assistant changed the code before final validation; review the corrected "
                    "version and diff below."
                )
            stderr_parts.append(header)
            if first_tb:
                label = f"Original error ({cat}{f', {err_type}' if err_type else ''}):"
                stderr_parts.append(label)
                stderr_parts.append(first_tb)

        return GradingOutcome(
            grade=grade,
            status=status,
            corrected_code=final_code,
            diff=diff,
            stdout="",
            stderr="\n\n".join(stderr_parts) if stderr_parts else "",
            output=final_output,
            feedback=_feedback_blob(result, original_code=submission.code, final_code=final_code),
        )
