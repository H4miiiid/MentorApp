from __future__ import annotations

from dataclasses import dataclass

from ..db.models import Submission, SubmissionStatus


@dataclass(frozen=True, slots=True)
class SubmissionSnapshot:
    """Immutable input for a grading pipeline (no live ORM session). Swap-friendly for LangGraph later."""

    id: str
    assignment_id: str
    student_id: str
    code: str

    @classmethod
    def from_submission(cls, row: Submission) -> SubmissionSnapshot:
        return cls(
            id=row.id,
            assignment_id=row.assignment_id,
            student_id=row.student_id,
            code=row.code,
        )


@dataclass(slots=True)
class GradingOutcome:
    """Result of a grading run; the worker persists this onto `Submission`."""

    grade: float
    status: SubmissionStatus
    corrected_code: str = ""
    diff: str = ""
    stdout: str = ""
    stderr: str = ""
    # Sandbox program output from the final successful run (corrected code if repaired).
    output: str = ""
    feedback: str = ""
