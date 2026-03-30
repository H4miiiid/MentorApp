from __future__ import annotations

from abc import ABC, abstractmethod

from .types import GradingOutcome, SubmissionSnapshot


class GradingPipeline(ABC):
    """Pluggable grading execution (mock, LangGraph agent, remote worker, …).

    Implementations must be async-friendly and should not perform DB I/O; the
    `GradingWorker` loads/saves `Submission` rows and applies `GradingOutcome`.
    """

    @abstractmethod
    async def run(self, submission: SubmissionSnapshot) -> GradingOutcome:
        """Execute grading for one submission."""
