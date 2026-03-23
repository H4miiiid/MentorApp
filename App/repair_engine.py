from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from importlib import import_module
from typing import Any

from .config import settings
from .schemas import RepairResult


class RepairEngineError(RuntimeError):
    """Raised when the selected repair engine cannot process a request."""


class BaseRepairEngine(ABC):
    """Common interface for all repair backends."""

    @abstractmethod
    def repair(self, broken_code: str, max_attempts: int) -> RepairResult:
        raise NotImplementedError


class MockRepairEngine(BaseRepairEngine):
    """Safe default backend that does not require GPU resources."""

    def repair(self, broken_code: str, max_attempts: int) -> RepairResult:
        preview_lines = broken_code.splitlines()[:40]
        preview = "\n".join(preview_lines)

        final_code = (
            "# Mock output: workflow execution is disabled in this environment.\n"
            "# Configure REPAIR_BACKEND_MODE=workflow on a GPU machine to run the real graph.\n\n"
            f"{preview}"
        )

        return RepairResult(
            final_code=final_code,
            final_status="mocked",
            attempt_count=0,
            route_history=["mock_backend"],
            attempt_history=[],
            error_category="",
            stop_reason="GPU workflow not executed in local mode",
            backend_mode="mock",
        )


class WorkflowRepairEngine(BaseRepairEngine):
    """Adapter around an external workflow module exposing run_workflow(...)."""

    def __init__(self, module_name: str, function_name: str) -> None:
        self._module_name = module_name
        self._function_name = function_name
        self._workflow_fn = self._load_workflow_function(module_name, function_name)

    @staticmethod
    def _load_workflow_function(module_name: str, function_name: str):
        try:
            module = import_module(module_name)
        except Exception as exc:
            raise RepairEngineError(
                f"Failed to import workflow module '{module_name}': {exc}"
            ) from exc

        workflow_fn = getattr(module, function_name, None)
        if workflow_fn is None or not callable(workflow_fn):
            raise RepairEngineError(
                f"Module '{module_name}' does not expose callable '{function_name}'."
            )

        return workflow_fn

    def repair(self, broken_code: str, max_attempts: int) -> RepairResult:
        try:
            payload = self._workflow_fn(broken_code, max_attempts=max_attempts)
        except Exception as exc:
            raise RepairEngineError(f"Workflow execution failed: {exc}") from exc

        if not isinstance(payload, dict):
            raise RepairEngineError("Workflow function must return a dictionary.")

        normalized: dict[str, Any] = {
            "final_code": str(payload.get("final_code", "")),
            "final_status": str(payload.get("final_status", "unknown")),
            "attempt_count": int(payload.get("attempt_count", 0)),
            "route_history": list(payload.get("route_history", [])),
            "attempt_history": list(payload.get("attempt_history", [])),
            "error_category": str(payload.get("error_category", "")),
            "stop_reason": str(payload.get("stop_reason", "")),
            "backend_mode": "workflow",
        }

        return RepairResult(**normalized)


@lru_cache(maxsize=1)
def get_repair_engine() -> BaseRepairEngine:
    """Resolve the configured repair backend implementation."""

    if settings.backend_mode == "workflow":
        return WorkflowRepairEngine(
            module_name=settings.workflow_module,
            function_name=settings.workflow_function,
        )

    return MockRepairEngine()
