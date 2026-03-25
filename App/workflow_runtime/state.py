from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone
from typing import Any, TypedDict


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

    next_strategy: str
    failure_signature: str
    previous_failure_signature: str
    repeated_failure_count: int
    no_meaningful_change_count: int
    should_stop: bool
    stop_reason: str

    final_status: str
    final_code: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def push_route(state: RepairState, node_name: str) -> None:
    state["route_history"].append(node_name)


def normalize_code(code: str) -> str:
    return "\n".join(line.rstrip() for line in code.strip().splitlines())


def code_changed_meaningfully(before: str, after: str, ratio_threshold: float = 0.995) -> bool:
    if normalize_code(before) == normalize_code(after):
        return False
    ratio = difflib.SequenceMatcher(a=before, b=after).ratio()
    return ratio < ratio_threshold


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


def init_state(original_code: str, max_attempts: int = 6) -> RepairState:
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
        next_strategy="",
        failure_signature="",
        previous_failure_signature="",
        repeated_failure_count=0,
        no_meaningful_change_count=0,
        should_stop=False,
        stop_reason="",
        final_status="",
        final_code="",
    )
