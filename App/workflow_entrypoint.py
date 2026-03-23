from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any
from typing import Callable

from .config import settings


WorkflowCallable = Callable[[str, int], dict[str, Any]]
_WORKFLOW_FN: WorkflowCallable | None = None


def _load_from_module() -> WorkflowCallable:
    module = importlib.import_module(settings.workflow_module)
    workflow_fn = getattr(module, settings.workflow_function, None)
    if workflow_fn is None or not callable(workflow_fn):
        raise RuntimeError(
            f"Callable '{settings.workflow_function}' not found in module '{settings.workflow_module}'."
        )

    # Avoid resolving this wrapper function itself, which would recurse forever.
    if module.__name__ == __name__ and workflow_fn is run_workflow:
        raise RuntimeError(
            "REPAIR_WORKFLOW_MODULE points to App.workflow_entrypoint.run_workflow, "
            "which is only a loader wrapper. Point to the real workflow module/function."
        )

    return workflow_fn


def _load_from_py_file() -> WorkflowCallable:
    if not settings.workflow_py_path:
        raise RuntimeError("REPAIR_WORKFLOW_PY_PATH is empty.")

    file_path = Path(settings.workflow_py_path)
    if not file_path.exists():
        raise RuntimeError(f"Workflow python file not found: {file_path}")

    spec = importlib.util.spec_from_file_location("workflow_runtime", file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load workflow python file: {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    workflow_fn = getattr(module, settings.workflow_function, None)
    if workflow_fn is None or not callable(workflow_fn):
        raise RuntimeError(
            f"Callable '{settings.workflow_function}' not found in file '{file_path}'."
        )
    return workflow_fn


def _load_from_notebook() -> WorkflowCallable:
    notebook_path = Path(settings.workflow_notebook_path)
    if not notebook_path.exists():
        raise RuntimeError(f"Workflow notebook not found: {notebook_path}")

    data = json.loads(notebook_path.read_text(encoding="utf-8"))
    namespace: dict[str, Any] = {"__name__": "workflow_notebook_runtime"}

    for cell in data.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        # Skip shell/magic commands and verification snippets that rely on local test files.
        if source.lstrip().startswith(("%", "!")):
            continue
        if "Path(\"test.py\")" in source or "Compact route verification" in source:
            continue

        exec(compile(source, str(notebook_path), "exec"), namespace)

    workflow_fn = namespace.get(settings.workflow_function)
    if workflow_fn is None or not callable(workflow_fn):
        raise RuntimeError(
            f"Callable '{settings.workflow_function}' not found after executing notebook '{notebook_path}'."
        )
    return workflow_fn


def _resolve_workflow_function() -> WorkflowCallable:
    source = settings.workflow_source

    if source == "module":
        return _load_from_module()
    if source == "pyfile":
        return _load_from_py_file()
    if source == "notebook":
        return _load_from_notebook()

    loaders = [_load_from_module]
    if settings.workflow_py_path:
        loaders.append(_load_from_py_file)
    loaders.append(_load_from_notebook)

    last_error: Exception | None = None
    for loader in loaders:
        try:
            return loader()
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Failed to resolve workflow function: {last_error}")


def _get_workflow_function() -> WorkflowCallable:
    global _WORKFLOW_FN
    if _WORKFLOW_FN is None:
        _WORKFLOW_FN = _resolve_workflow_function()
    return _WORKFLOW_FN


def run_workflow(original_code: str, max_attempts: int = 6) -> dict[str, Any]:
    """Call the configured LangGraph workflow and normalize result shape."""

    workflow_fn = _get_workflow_function()
    payload = workflow_fn(original_code, max_attempts=max_attempts)

    if not isinstance(payload, dict):
        raise RuntimeError("Workflow function must return a dict payload.")

    return {
        "final_code": str(payload.get("final_code", "")),
        "final_status": str(payload.get("final_status", "unknown")),
        "attempt_count": int(payload.get("attempt_count", 0)),
        "route_history": list(payload.get("route_history", [])),
        "attempt_history": list(payload.get("attempt_history", [])),
        "error_category": str(payload.get("error_category", "")),
        "stop_reason": str(payload.get("stop_reason", "")),
    }
