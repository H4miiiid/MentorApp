from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from AppV2.backend.workflow_runtime.llm_clients import ensure_hf_endpoint_available
from AppV2.backend.workflow_runtime.observability import setup_langsmith
from AppV2.backend.workflow_runtime.sandbox import SandboxUnavailableError
from AppV2.backend.workflow_runtime.nodes import (
    assess_local_context,
    attempt_requirement_completion,
    attempt_sft_with_rag,
    attempt_sft_with_reflection,
    attempt_sft_with_traceback,
    choose_next_strategy,
    diagnose_failure,
    external_expert_repair,
    finalize_failure,
    finalize_success,
    reflection_critic,
    retrieve_local_docs,
    run_checks,
    summarize_context,
    verify_completeness,
    verify_original_completeness,
    web_search_docs,
)
from AppV2.backend.workflow_runtime.state import RepairState, init_state


logger = logging.getLogger(__name__)


def route_after_checks(state: RepairState) -> str:
    if state["check_result"].get("passed", False):
        return "success"
    if state.get("used_external", False):
        return "external_failed"
    return "diagnose"


def route_after_diagnose(state: RepairState) -> str:
    return "finalize_failure" if state.get("should_stop", False) else "choose"


def route_strategy(state: RepairState) -> str:
    return state.get("next_strategy", "finalize_failure")


def route_local_context(state: RepairState) -> str:
    return "web" if state.get("local_context_quality") == "weak" else "summarize"


def _has_truly_missing_requirements(completeness: dict) -> bool:
    """Return True only if at least one requirement has status 'missing' (not partial)."""
    requirements = completeness.get("requirements") or []
    if isinstance(requirements, list):
        for item in requirements:
            if isinstance(item, dict) and str(item.get("status", "")).strip().lower() == "missing":
                return True
    missing_list = completeness.get("missing_requirements") or []
    return bool(missing_list)


def route_after_completeness(state: RepairState) -> str:
    completeness = state.get("first_pass_completeness") or {}
    if completeness.get("complete", True) or completeness.get("model_complete", False):
        return "finalize_success"

    if not _has_truly_missing_requirements(completeness):
        return "finalize_success"

    used = int(state.get("requirement_repair_count", 0))
    budget = int(state.get("max_requirement_repairs", 1))
    if used < budget:
        return "attempt_requirement_completion"

    state["requirement_repair_exhausted"] = True
    return "finalize_success"


def bootstrap(state: RepairState) -> RepairState:
    return state


def route_bootstrap(state: RepairState) -> str:
    check = state.get("check_result") or {}
    if not check:
        return "check"
    if not check.get("passed", False):
        return "diagnose"
    if not state.get("original_code_completeness"):
        return "verify_original_completeness"
    completeness = state.get("first_pass_completeness") or {}
    if (
        completeness
        and not completeness.get("complete", True)
        and not completeness.get("model_complete", False)
        and _has_truly_missing_requirements(completeness)
    ):
        return "requirement_completion"
    return "success"


def route_after_original_completeness(state: RepairState) -> str:
    check = state.get("check_result") or {}
    if not check.get("passed", False):
        return "diagnose"
    completeness = state.get("original_code_completeness") or {}
    if completeness.get("complete", True) or completeness.get("model_complete", False):
        return "finalize_success"
    if not _has_truly_missing_requirements(completeness):
        return "finalize_success"
    return "attempt_requirement_completion"


def build_graph():
    builder = StateGraph(RepairState)

    builder.add_node("bootstrap", bootstrap)
    builder.add_node("attempt_sft_with_traceback", attempt_sft_with_traceback)
    builder.add_node("run_checks", run_checks)
    builder.add_node("diagnose_failure", diagnose_failure)
    builder.add_node("choose_next_strategy", choose_next_strategy)
    builder.add_node("retrieve_local_docs", retrieve_local_docs)
    builder.add_node("assess_local_context", assess_local_context)
    builder.add_node("web_search_docs", web_search_docs)
    builder.add_node("summarize_context", summarize_context)
    builder.add_node("attempt_sft_with_rag", attempt_sft_with_rag)
    builder.add_node("reflection_critic", reflection_critic)
    builder.add_node("attempt_sft_with_reflection", attempt_sft_with_reflection)
    builder.add_node("external_expert_repair", external_expert_repair)
    builder.add_node("verify_original_completeness", verify_original_completeness)
    builder.add_node("verify_completeness", verify_completeness)
    builder.add_node("attempt_requirement_completion", attempt_requirement_completion)
    builder.add_node("finalize_success", finalize_success)
    builder.add_node("finalize_failure", finalize_failure)

    builder.set_entry_point("bootstrap")

    builder.add_conditional_edges(
        "bootstrap",
        route_bootstrap,
        {
            "check": "run_checks",
            "diagnose": "diagnose_failure",
            "success": "verify_completeness",
            "requirement_completion": "attempt_requirement_completion",
            "verify_original_completeness": "verify_original_completeness",
        },
    )

    builder.add_conditional_edges(
        "verify_original_completeness",
        route_after_original_completeness,
        {
            "diagnose": "diagnose_failure",
            "attempt_requirement_completion": "attempt_requirement_completion",
            "finalize_success": "finalize_success",
        },
    )

    for node in [
        "attempt_sft_with_traceback",
        "attempt_sft_with_rag",
        "attempt_sft_with_reflection",
        "external_expert_repair",
    ]:
        builder.add_edge(node, "run_checks")

    builder.add_conditional_edges(
        "run_checks",
        route_after_checks,
        {
            "success": "verify_completeness",
            "diagnose": "diagnose_failure",
            "external_failed": "finalize_failure",
        },
    )

    builder.add_conditional_edges(
        "verify_completeness",
        route_after_completeness,
        {
            "attempt_requirement_completion": "attempt_requirement_completion",
            "finalize_success": "finalize_success",
        },
    )
    builder.add_edge("attempt_requirement_completion", "run_checks")

    builder.add_conditional_edges(
        "diagnose_failure",
        route_after_diagnose,
        {
            "choose": "choose_next_strategy",
            "finalize_failure": "finalize_failure",
        },
    )

    builder.add_conditional_edges(
        "choose_next_strategy",
        route_strategy,
        {
            "traceback_sft": "attempt_sft_with_traceback",
            "local_rag": "retrieve_local_docs",
            "reflection_critic": "reflection_critic",
            "external_expert": "external_expert_repair",
            "finalize_failure": "finalize_failure",
        },
    )

    builder.add_edge("retrieve_local_docs", "assess_local_context")
    builder.add_conditional_edges(
        "assess_local_context",
        route_local_context,
        {
            "web": "web_search_docs",
            "summarize": "summarize_context",
        },
    )
    builder.add_edge("web_search_docs", "summarize_context")
    builder.add_edge("summarize_context", "attempt_sft_with_rag")

    builder.add_edge("reflection_critic", "attempt_sft_with_reflection")

    builder.add_edge("finalize_success", END)
    builder.add_edge("finalize_failure", END)

    return builder.compile()


def run_workflow(
    original_code: str,
    max_attempts: int = 6,
    *,
    submission_id: str = "",
    assignment_id: str = "",
    assignment_description: str = "",
    run_id: str = "",
    data_files: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    setup_langsmith()
    try:
        ensure_hf_endpoint_available()
    except RuntimeError as exc:
        msg = str(exc)
        transient_http_markers = ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504")
        if any(marker in msg for marker in transient_http_markers):
            logger.warning(
                "[sft-endpoint] preflight failed with transient status; continuing workflow with best-effort fallback: %s",
                msg,
            )
        else:
            raise

    ctx = {}
    if submission_id:
        ctx["submission_id"] = submission_id
    if assignment_id:
        ctx["assignment_id"] = assignment_id
    if run_id:
        ctx["run_id"] = run_id
    state = init_state(
        original_code=original_code,
        max_attempts=max_attempts,
        workflow_context=ctx or None,
        assignment_description=assignment_description,
        data_files=data_files,
    )

    try:
        state = run_checks(state)
    except SandboxUnavailableError as exc:
        # Infra failure — do NOT pretend the student's code was wrong.
        return {
            "final_code": original_code,
            "final_status": "sandbox_unavailable",
            "attempt_count": 0,
            "max_attempts": max_attempts,
            "route_history": ["run_checks"],
            "attempt_history": [],
            "error_category": "sandbox_unavailable",
            "stop_reason": "sandbox_unavailable",
            "no_meaningful_change_count": 0,
            "repeated_failure_count": 0,
            "error_events": [],
            "mistake_count": 0,
            "sandbox_error": str(exc),
        }

    app = build_graph()
    try:
        final_state = app.invoke(state)
    except SandboxUnavailableError as exc:
        # Infra failure — do NOT pretend the student's code was wrong.
        return {
            "final_code": original_code,
            "final_status": "sandbox_unavailable",
            "attempt_count": 0,
            "max_attempts": max_attempts,
            "route_history": ["run_checks"],
            "attempt_history": [],
            "error_category": "sandbox_unavailable",
            "stop_reason": "sandbox_unavailable",
            "no_meaningful_change_count": 0,
            "repeated_failure_count": 0,
            "error_events": [],
            "mistake_count": 0,
            "sandbox_error": str(exc),
        }

    last_check = final_state.get("check_result") or {}
    final_success_stdout = (
        (last_check.get("stdout") or "")
        if (final_state.get("final_status") or "").lower() == "success" and last_check.get("passed")
        else ""
    )

    return {
        "final_code": final_state["final_code"],
        "final_status": final_state["final_status"],
        "attempt_count": final_state["attempt_count"],
        "max_attempts": final_state["max_attempts"],
        "route_history": final_state["route_history"],
        "attempt_history": final_state["attempt_history"],
        "error_category": final_state.get("error_category", ""),
        "stop_reason": final_state.get("stop_reason", ""),
        "no_meaningful_change_count": final_state.get("no_meaningful_change_count", 0),
        "repeated_failure_count": final_state.get("repeated_failure_count", 0),
        "error_events": final_state.get("error_events", []),
        "mistake_count": final_state.get("mistake_count", 0),
        "requirement_repair_count": final_state.get("requirement_repair_count", 0),
        "max_requirement_repairs": final_state.get("max_requirement_repairs", 1),
        "used_requirement_repair": final_state.get("used_requirement_repair", False),
        "requirement_repair_exhausted": final_state.get("requirement_repair_exhausted", False),
        # Snapshot of the student's ORIGINAL failing run. These survive LLM repairs and let
        # the grader + UI distinguish a clean first-try pass from a "we had to fix it for you"
        # pass, and let the student see the actual mistake in their own code.
        "initial_traceback": final_state.get("initial_traceback", ""),
        "initial_error_category": final_state.get("initial_error_category", ""),
        "initial_error_type": final_state.get("initial_error_type", ""),
        "initial_error_explanation": final_state.get("initial_error_explanation", ""),
        "initial_stdout": final_state.get("initial_stdout", ""),
        "initial_stderr": final_state.get("initial_stderr", ""),
        "original_code_completeness": final_state.get("original_code_completeness", state.get("original_code_completeness", {})),
        "first_pass_completeness": final_state.get("first_pass_completeness", state.get("first_pass_completeness", {})),
        "final_success_stdout": final_success_stdout,
    }
