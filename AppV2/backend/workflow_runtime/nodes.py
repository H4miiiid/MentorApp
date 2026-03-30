from __future__ import annotations

import traceback as tb
from typing import Any

from AppV2.backend.workflow_runtime.config import CFG
from AppV2.backend.workflow_runtime.sandbox import execute_python_after_compile
from AppV2.backend.workflow_runtime.llm_clients import (
    call_external_model,
    call_reflection_model,
    call_sft_model,
    summarize_docs_to_hints,
)
from AppV2.backend.workflow_runtime.rag import rerank_docs, retrieve_from_vector_db, web_search
from AppV2.backend.workflow_runtime.observability import traceable
from AppV2.backend.workflow_runtime.state import (
    RepairState,
    build_error_brief,
    classify_error,
    clean_traceback_text,
    code_changed_meaningfully,
    extract_failure_signature,
    now_iso,
    push_route,
)


def record_attempt(state: RepairState, route: str, before_code: str, after_code: str, prompt: str) -> None:
    changed = code_changed_meaningfully(before_code, after_code)
    state["attempt_count"] += 1
    state["attempt_history"].append(
        {
            "attempt": state["attempt_count"],
            "route": route,
            "changed_meaningfully": changed,
            "timestamp": now_iso(),
            "prompt_preview": prompt[:220],
        }
    )
    state["no_meaningful_change_count"] = 0 if changed else state["no_meaningful_change_count"] + 1


@traceable(name="run_checks", run_type="chain")
def run_checks(state: RepairState) -> RepairState:
    push_route(state, "run_checks")
    code = state["current_code"]

    result: dict[str, Any] = {
        "passed": False,
        "compile_ok": False,
        "runtime_ok": False,
        "stdout": "",
        "stderr": "",
        "traceback": "",
    }

    try:
        compile(code, "<candidate_code>", "exec")
        result["compile_ok"] = True
    except Exception as exc:
        trace = "".join(tb.format_exception(exc))
        result["traceback"] = trace
        state["traceback"] = trace
        state["check_result"] = result
        state["failure_signature"] = extract_failure_signature(trace)
        return state

    try:
        run_out = execute_python_after_compile(code, float(CFG.execution_timeout_seconds))
        result["stdout"] = run_out.get("stdout") or ""
        result["stderr"] = run_out.get("stderr") or ""
        result["sandbox_mode"] = run_out.get("mode", "")

        if run_out.get("ok"):
            result["runtime_ok"] = True
            result["passed"] = True
            state["traceback"] = ""
            state["failure_signature"] = ""
        else:
            trace = result["stderr"] or "Runtime failed without stderr output."
            result["traceback"] = trace
            state["traceback"] = trace
            state["failure_signature"] = extract_failure_signature(trace)
    except Exception as exc:
        err = f"Sandbox execution error: {exc}"
        result["traceback"] = err
        state["traceback"] = err
        state["failure_signature"] = extract_failure_signature(err)
        result["stderr"] = (result.get("stderr") or "") + "\n" + err

    state["check_result"] = result
    return state


@traceable(name="attempt_sft_with_traceback", run_type="chain")
def attempt_sft_with_traceback(state: RepairState) -> RepairState:
    push_route(state, "attempt_sft_with_traceback")
    if not state.get("initial_traceback"):
        state["initial_traceback"] = state.get("traceback", "")

    before = state["current_code"]
    cleaned_tb = clean_traceback_text(state.get("traceback", ""))
    prompt = (
        "Repair code using this cleaned traceback. Apply minimal edits only.\n"
        "Solve the error in the code based on the traceback details.\n"
        "Do not do a full rewrite.\n"
        f"TRACEBACK:\n{cleaned_tb}\n\n"
        f"CURRENT_CODE:\n{before}\n"
    )
    candidate = call_sft_model(prompt)
    state["used_traceback"] = True
    state["current_code"] = candidate
    record_attempt(state, "attempt_sft_with_traceback", before, candidate, prompt)
    return state


@traceable(name="diagnose_failure", run_type="chain")
def diagnose_failure(state: RepairState) -> RepairState:
    push_route(state, "diagnose_failure")

    classification = classify_error(state.get("traceback", ""), state.get("check_result", {}))
    state["error_category"] = classification.get("category", "api_library_error")
    state["error_type"] = classification.get("error_type", "UnknownError")
    state["error_explanation"] = classification.get("error_explanation", "")

    signature = state.get("failure_signature", "")
    previous_signature = state.get("previous_failure_signature", "")
    if signature and previous_signature and signature == previous_signature:
        state["repeated_failure_count"] += 1
    else:
        state["repeated_failure_count"] = 0
    if signature:
        state["previous_failure_signature"] = signature

    if state["attempt_count"] >= state["max_attempts"]:
        state["should_stop"] = True
        state["stop_reason"] = "max_attempts_reached"
    elif state["no_meaningful_change_count"] >= 2:
        if state["used_reflection"] and not state["used_external"]:
            state["should_stop"] = False
            state["stop_reason"] = ""
        else:
            state["should_stop"] = True
            state["stop_reason"] = "no_meaningful_change"

    return state


@traceable(name="choose_next_strategy", run_type="chain")
def choose_next_strategy(state: RepairState) -> RepairState:
    push_route(state, "choose_next_strategy")

    if state["should_stop"]:
        state["next_strategy"] = "finalize_failure"
        return state

    category = state.get("error_category", "api_library_error")

    if category == "api_library_error":
        if not state["used_rag"]:
            state["next_strategy"] = "local_rag"
        elif not state["used_traceback"]:
            state["next_strategy"] = "traceback_sft"
        elif not state["used_reflection"]:
            state["next_strategy"] = "reflection_critic"
        elif not state["used_external"]:
            state["next_strategy"] = "external_expert"
        else:
            state["next_strategy"] = "finalize_failure"
            state["should_stop"] = True
            state["stop_reason"] = "all_strategies_exhausted"
        return state

    if category in ("syntax_error", "name_error", "timeout"):
        if not state["used_traceback"]:
            state["next_strategy"] = "traceback_sft"
        elif not state["used_reflection"]:
            state["next_strategy"] = "reflection_critic"
        elif not state["used_external"]:
            state["next_strategy"] = "external_expert"
        else:
            state["next_strategy"] = "finalize_failure"
            state["should_stop"] = True
            state["stop_reason"] = "all_strategies_exhausted"
        return state

    if not state["used_reflection"]:
        state["next_strategy"] = "reflection_critic"
    elif not state["used_traceback"]:
        state["next_strategy"] = "traceback_sft"
    elif not state["used_external"]:
        state["next_strategy"] = "external_expert"
    else:
        state["next_strategy"] = "finalize_failure"
        state["should_stop"] = True
        state["stop_reason"] = "all_strategies_exhausted"

    return state


@traceable(name="retrieve_local_docs", run_type="chain")
def retrieve_local_docs(state: RepairState) -> RepairState:
    push_route(state, "retrieve_local_docs")
    query = state.get("traceback") or state.get("failure_signature") or "python error fix"
    state["local_docs"] = retrieve_from_vector_db(query)
    state["used_rag"] = True
    return state


@traceable(name="assess_local_context", run_type="chain")
def assess_local_context(state: RepairState) -> RepairState:
    push_route(state, "assess_local_context")
    candidates = state.get("local_docs", [])
    if not candidates:
        state["local_context_quality"] = "weak"
        return state

    query = state.get("traceback") or state.get("failure_signature") or ""
    reranked = rerank_docs(query, candidates)
    state["local_docs"] = reranked

    if reranked and len(reranked) >= 2:
        avg_score = sum(score for score, _, _ in reranked) / len(reranked)
        state["local_context_quality"] = "good" if avg_score > 0.3 else "weak"
    else:
        state["local_context_quality"] = "weak"

    return state


@traceable(name="web_search_docs", run_type="chain")
def web_search_docs(state: RepairState) -> RepairState:
    push_route(state, "web_search_docs")
    query = state.get("failure_signature") or "python runtime error fix"
    state["web_docs"] = web_search(query)
    state["used_web"] = True
    return state


@traceable(name="summarize_context", run_type="chain")
def summarize_context(state: RepairState) -> RepairState:
    push_route(state, "summarize_context")

    local_docs = state.get("local_docs", [])
    traceback_text = state.get("traceback", "")
    hints = ""

    if local_docs and isinstance(local_docs[0], tuple) and len(local_docs[0]) == 3:
        hints = summarize_docs_to_hints(local_docs, traceback_text)
    else:
        chunks: list[str] = []
        if local_docs:
            if isinstance(local_docs[0], tuple):
                chunks.extend([doc for doc, _ in local_docs])
            else:
                chunks.extend(local_docs)
        chunks.extend(state.get("web_docs", []))
        bullets = []
        for chunk in chunks[:6]:
            first_line = chunk.strip().splitlines()[0] if chunk.strip() else ""
            if first_line:
                bullets.append(f"- {first_line[:180]}")
        hints = "\n".join(bullets) if bullets else "- No helpful context found."

    state["summarized_hints"] = hints
    return state


@traceable(name="attempt_sft_with_rag", run_type="chain")
def attempt_sft_with_rag(state: RepairState) -> RepairState:
    push_route(state, "attempt_sft_with_rag")
    before = state["current_code"]
    tb_brief = build_error_brief(state.get("traceback", ""), state.get("error_explanation", ""))
    prompt = (
        "Repair code using documentation hints as hard constraints.\n"
        "Apply minimal edits only and do not rewrite unrelated code.\n"
        f"HINTS FROM DOCUMENTATION:\n{state.get('summarized_hints', '')}\n\n"
        f"TRACEBACK:\n{tb_brief}\n\n"
        f"CURRENT_CODE:\n{before}\n"
    )
    candidate = call_sft_model(prompt)
    state["current_code"] = candidate
    record_attempt(state, "attempt_sft_with_rag", before, candidate, prompt)
    return state


@traceable(name="reflection_critic", run_type="chain")
def reflection_critic(state: RepairState) -> RepairState:
    push_route(state, "reflection_critic")
    feedback = call_reflection_model(
        current_code=state["current_code"],
        traceback_text=state.get("traceback", ""),
        attempt_history=state.get("attempt_history", []),
    )
    state["reflection_feedback"] = feedback
    state["used_reflection"] = True
    return state


@traceable(name="attempt_sft_with_reflection", run_type="chain")
def attempt_sft_with_reflection(state: RepairState) -> RepairState:
    push_route(state, "attempt_sft_with_reflection")
    before = state["current_code"]
    tb_brief = build_error_brief(state.get("traceback", ""), state.get("error_explanation", ""))
    prompt = (
        "Repair code using reflection hints. Minimal edits only.\n"
        f"REFLECTION_FEEDBACK:\n{state.get('reflection_feedback', {})}\n\n"
        f"TRACEBACK:\n{tb_brief}\n\n"
        f"CURRENT_CODE:\n{before}\n"
    )
    candidate = call_sft_model(prompt)
    state["current_code"] = candidate
    record_attempt(state, "attempt_sft_with_reflection", before, candidate, prompt)
    return state


@traceable(name="external_expert_repair", run_type="chain")
def external_expert_repair(state: RepairState) -> RepairState:
    push_route(state, "external_expert_repair")
    before = state["current_code"]
    tb_brief = build_error_brief(state.get("traceback", ""), state.get("error_explanation", ""))
    prompt = (
        "Final fallback repair. Keep edits as small as possible while fixing failure.\n"
        f"TRACEBACK:\n{tb_brief}\n\n"
        f"REFLECTION_HINTS:\n{state.get('reflection_feedback', {})}\n\n"
        f"RAG_HINTS:\n{state.get('summarized_hints', '')}\n\n"
        f"CURRENT_CODE:\n{before}\n"
    )
    candidate = call_external_model(prompt)
    state["used_external"] = True
    state["current_code"] = candidate
    record_attempt(state, "external_expert_repair", before, candidate, prompt)
    return state


@traceable(name="finalize_success", run_type="chain")
def finalize_success(state: RepairState) -> RepairState:
    push_route(state, "finalize_success")
    state["final_status"] = "success"
    state["final_code"] = state["current_code"]
    return state


@traceable(name="finalize_failure", run_type="chain")
def finalize_failure(state: RepairState) -> RepairState:
    push_route(state, "finalize_failure")
    state["final_status"] = "failure"
    state["final_code"] = state["current_code"]
    return state
