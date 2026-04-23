from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, TypedDict

_workflow_trace = logging.getLogger("AppV2.backend.workflow.trace")


class WorkflowContext(TypedDict, total=False):
    """Optional correlation IDs for grading runs (admin monitoring)."""

    submission_id: str
    assignment_id: str
    run_id: str


class RepairState(TypedDict):
    original_code: str
    current_code: str
    traceback: str
    check_result: dict[str, Any]

    attempt_count: int
    max_attempts: int
    attempt_history: list[dict[str, Any]]
    route_history: list[str]

    error_category: str
    error_type: str
    error_explanation: str

    used_traceback: bool
    used_rag: bool
    used_web: bool
    used_reflection: bool
    used_external: bool

    local_docs: list[Any]
    web_docs: list[str]
    local_context_quality: str
    summarized_hints: str
    reflection_feedback: dict[str, Any]
    initial_traceback: str
    # Snapshot of the student's *original* first-attempt run (before any LLM repair).
    # Used to (a) surface the real error in the UI even when the workflow later succeeds,
    # and (b) drive the "repaired vs. clean pass" grading policy.
    initial_error_category: str
    initial_error_type: str
    initial_error_explanation: str
    initial_stdout: str
    initial_stderr: str

    next_strategy: str
    failure_signature: str
    previous_failure_signature: str
    repeated_failure_count: int
    no_meaningful_change_count: int
    error_events: list[dict[str, Any]]
    mistake_count: int
    should_stop: bool
    stop_reason: str

    final_status: str
    final_code: str

    workflow_context: WorkflowContext
    assignment_description: str
    first_pass_completeness: dict[str, Any]

    # Assignment-attached data files to expose inside the sandbox via
    # ``ASSIGNMENT_DATA_DIR``. Each entry is ``(host_path, target_filename)``.
    data_files: list[tuple[str, str]]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def push_route(state: RepairState, node_name: str) -> None:
    state["route_history"].append(node_name)
    ctx = state.get("workflow_context") or {}
    sid = ctx.get("submission_id") or ""
    aid = ctx.get("assignment_id") or ""
    extra: dict[str, Any] = {
        "wf_kind": "agent",
        "wf_agent": node_name,
        "wf_phase": "workflow_node",
        "wf_level": "INFO",
    }
    if sid:
        extra["wf_submission_id"] = sid
    if aid:
        extra["wf_assignment_id"] = aid
    _workflow_trace.info(
        "[workflow] node=%s attempt=%s sub=%s asg=%s",
        node_name,
        state.get("attempt_count", 0),
        sid or "-",
        aid or "-",
        extra=extra,
    )


def normalize_code(code: str) -> str:
    return "\n".join(line.rstrip() for line in code.strip().splitlines())


def code_changed_meaningfully(before: str, after: str, ratio_threshold: float = 0.99999) -> bool:
    _ = ratio_threshold  # kept for compatibility with existing call sites
    if normalize_code(before) == normalize_code(after):
        return False
    # Any non-trivial normalized change should count as meaningful.
    return True


def extract_failure_signature(traceback_text: str) -> str:
    lines = [line.strip() for line in traceback_text.splitlines() if line.strip()]
    return lines[-1] if lines else "unknown_failure"


def clean_traceback_text(traceback_text: str) -> str:
    text = traceback_text or ""
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    text = ansi_escape.sub("", text)
    lines = [ln.rstrip() for ln in text.splitlines()]
    cleaned = "\n".join([ln for ln in lines if ln.strip()])
    return cleaned or "No traceback available."


def build_error_brief(traceback_text: str, error_explanation: str = "", max_chars: int = 320) -> str:
    line = extract_failure_signature(traceback_text)
    hint = (error_explanation or "").strip()
    if len(hint) > max_chars:
        hint = hint[:max_chars].rstrip() + "..."
    if hint and hint != line:
        return f"{line}\nHint: {hint}"
    return line


def extract_error_details(traceback_text: str) -> tuple[str, str, str]:
    lines = [line.strip() for line in traceback_text.splitlines() if line.strip()]
    if not lines:
        return "UnknownError", "", ""

    for line in reversed(lines):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):\s*(.*)$", line)
        if match:
            return match.group(1), match.group(2).strip(), line

    tail = lines[-1]
    return "UnknownError", tail, tail


def classify_error(traceback_text: str, check_result: dict[str, Any]) -> dict[str, str]:
    error_type, error_msg, error_line = extract_error_details(traceback_text)
    msg_lower = (error_msg or error_line or "").lower()
    line_lower = (error_line or "").lower()
    err_lower = (error_type or "").lower()

    if (
        not check_result.get("compile_ok", True)
        or "syntaxerror" in line_lower
        or "indentationerror" in line_lower
        or "syntaxerror" in msg_lower
        or "indentationerror" in msg_lower
        or err_lower in {"syntaxerror", "indentationerror"}
    ):
        return {
            "category": "syntax_error",
            "error_type": error_type,
            "error_explanation": error_msg,
            "error_line": error_line,
        }

    if "timeout" in msg_lower or "timeoutexpired" in msg_lower:
        return {
            "category": "timeout",
            "error_type": error_type,
            "error_explanation": error_msg,
            "error_line": error_line,
        }

    if err_lower == "nameerror":
        return {
            "category": "name_error",
            "error_type": error_type,
            "error_explanation": error_msg,
            "error_line": error_line,
        }

    # input() hitting EOF (no stdin) — sandbox now feeds blank lines by default
    if err_lower == "eoferror":
        return {
            "category": "stdin_eof",
            "error_type": error_type,
            "error_explanation": error_msg,
            "error_line": error_line,
        }

    api_indicators = [
        "importerror",
        "modulenotfounderror",
        "attributeerror",
        "deprecat",
        "no module named",
        "cannot import",
        "unexpected keyword argument",
        "positional argument",
        "got an unexpected",
        "missing required",
    ]
    if error_type in {"ImportError", "ModuleNotFoundError", "AttributeError"} or any(
        indicator in msg_lower for indicator in api_indicators
    ):
        return {
            "category": "api_library_error",
            "error_type": error_type,
            "error_explanation": error_msg,
            "error_line": error_line,
        }

    reasoning_indicators = [
        "valueerror",
        "typeerror",
        "indexerror",
        "keyerror",
        "shape",
        "dimension",
        "broadcast",
        "mismatch",
        "cannot convert",
        "invalid",
    ]
    if error_type in {"ValueError", "TypeError", "IndexError", "KeyError", "AssertionError"} or any(
        indicator in msg_lower for indicator in reasoning_indicators
    ):
        return {
            "category": "local_reasoning_error",
            "error_type": error_type,
            "error_explanation": error_msg,
            "error_line": error_line,
        }

    return {
        "category": "api_library_error",
        "error_type": error_type,
        "error_explanation": error_msg,
        "error_line": error_line,
    }


def init_state(
    original_code: str,
    max_attempts: int = 6,
    workflow_context: WorkflowContext | None = None,
    data_files: list[tuple[str, str]] | None = None,
    assignment_description: str = "",
) -> RepairState:
    wc: WorkflowContext = dict(workflow_context) if workflow_context else {}
    return RepairState(
        original_code=original_code,
        current_code=original_code,
        traceback="",
        check_result={},
        attempt_count=0,
        max_attempts=max_attempts,
        attempt_history=[],
        route_history=[],
        error_category="",
        error_type="",
        error_explanation="",
        used_traceback=False,
        used_rag=False,
        used_web=False,
        used_reflection=False,
        used_external=False,
        local_docs=[],
        web_docs=[],
        local_context_quality="",
        summarized_hints="",
        reflection_feedback={},
        initial_traceback="",
        initial_error_category="",
        initial_error_type="",
        initial_error_explanation="",
        initial_stdout="",
        initial_stderr="",
        next_strategy="",
        failure_signature="",
        previous_failure_signature="",
        repeated_failure_count=0,
        no_meaningful_change_count=0,
        error_events=[],
        mistake_count=0,
        should_stop=False,
        stop_reason="",
        final_status="",
        final_code="",
        workflow_context=wc,
        assignment_description=assignment_description or "",
        first_pass_completeness={},
        data_files=list(data_files or []),
    )
