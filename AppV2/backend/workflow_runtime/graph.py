from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from AppV2.backend.workflow_runtime.llm_clients import ensure_llama_server_available
from AppV2.backend.workflow_runtime.observability import setup_langsmith
from AppV2.backend.workflow_runtime.nodes import (
    assess_local_context,
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
    web_search_docs,
)
from AppV2.backend.workflow_runtime.state import RepairState, init_state


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


def build_graph():
    builder = StateGraph(RepairState)

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
    builder.add_node("finalize_success", finalize_success)
    builder.add_node("finalize_failure", finalize_failure)

    builder.set_entry_point("run_checks")

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
            "success": "finalize_success",
            "diagnose": "diagnose_failure",
            "external_failed": "finalize_failure",
        },
    )

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
    run_id: str = "",
) -> dict[str, Any]:
    setup_langsmith()
    ensure_llama_server_available()

    app = build_graph()
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
    )
    final_state = app.invoke(state)

    return {
        "final_code": final_state["final_code"],
        "final_status": final_state["final_status"],
        "attempt_count": final_state["attempt_count"],
        "route_history": final_state["route_history"],
        "attempt_history": final_state["attempt_history"],
        "error_category": final_state.get("error_category", ""),
        "stop_reason": final_state.get("stop_reason", ""),
    }
