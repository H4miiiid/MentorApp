from __future__ import annotations

from ..core.config import Settings
from .langgraph_pipeline import LangGraphGradingPipeline
from .mock_pipeline import MockGradingPipeline
from .pipeline import GradingPipeline


def create_grading_pipeline(settings: Settings) -> GradingPipeline:
    """Build the active grading implementation (`mock` or `langgraph`)."""
    backend = settings.grading_backend.lower().strip()
    if backend == "mock":
        return MockGradingPipeline(settings)
    if backend in ("langgraph", "agent"):
        return LangGraphGradingPipeline(settings)
    raise ValueError(
        f"Unknown APPV2_GRADING_BACKEND={settings.grading_backend!r}. "
        "Supported: mock, langgraph."
    )
