from __future__ import annotations

import logging
import re
import traceback as tb
from typing import Any

from AppV2.backend.workflow_runtime.config import CFG
from AppV2.backend.workflow_runtime.sandbox import (
    SandboxUnavailableError,
    execute_python_after_compile,
)
from AppV2.backend.workflow_runtime.llm_clients import (
    call_external_model,
    call_reflection_model,
    call_requirement_completion_model,
    call_sft_model,
    dispatch_completeness_check,
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

logger = logging.getLogger(__name__)

_MISSING_MODULE_RE = re.compile(r"ModuleNotFoundError:\\s+No module named ['\"]([^'\"]+)['\"]")
_SANDBOX_EXPECTED_MODULES = {
    "sklearn",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "seaborn",
}


def _extract_missing_module(trace_text: str) -> str:
    match = _MISSING_MODULE_RE.search(trace_text or "")
    if not match:
        return ""
    return match.group(1).strip()


def _capture_initial_failure(state: RepairState, result: dict[str, Any], trace: str) -> None:
    """Snapshot the *first* failed run so grading and the UI can show the student's
    original error even after the LLM has repaired it.

    Called from ``run_checks`` the very first time a check fails (either at compile
    time or during sandbox execution). Subsequent failures during the repair loop
    must NOT overwrite this snapshot — the point is to remember what the student
    actually submitted.
    """
    if state.get("initial_traceback"):
        return
    cleaned = trace or ""
    state["initial_traceback"] = cleaned
    classification = classify_error(cleaned, result)
    state["initial_error_category"] = classification.get("category", "")
    state["initial_error_type"] = classification.get("error_type", "")
    state["initial_error_explanation"] = classification.get("error_explanation", "")
    state["initial_stdout"] = result.get("stdout", "") or ""
    state["initial_stderr"] = result.get("stderr", "") or cleaned


def _record_error_event(state: RepairState, result: dict[str, Any], trace: str) -> None:
    """Track observed failures so grading can use mistake-count weighting."""
    cleaned = trace or ""
    if not cleaned.strip():
        return
    classification = classify_error(cleaned, result)
    signature = extract_failure_signature(cleaned)
    state["error_events"].append(
        {
            "attempt": state.get("attempt_count", 0),
            "signature": signature,
            "category": classification.get("category", "api_library_error"),
            "error_type": classification.get("error_type", "UnknownError"),
            "error_line": classification.get("error_line", ""),
            "timestamp": now_iso(),
        }
    )
    distinct_signatures = {
        (evt.get("signature") or "").strip()
        for evt in state.get("error_events", [])
        if (evt.get("signature") or "").strip()
    }
    state["mistake_count"] = len(distinct_signatures)


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
        _capture_initial_failure(state, result, trace)
        _record_error_event(state, result, trace)
        logger.debug("run_checks compile failed (no sandbox)")
        return state

    try:
        run_out = execute_python_after_compile(
            code,
            float(CFG.execution_timeout_seconds),
            data_files=state.get("data_files") or None,
        )
    except Exception as exc:
        err = f"Sandbox execution error: {exc}"
        result["traceback"] = err
        state["traceback"] = err
        state["failure_signature"] = extract_failure_signature(err)
        result["stderr"] = (result.get("stderr") or "") + "\n" + err
        state["check_result"] = result
        return state

    result["stdout"] = run_out.get("stdout") or ""
    result["stderr"] = run_out.get("stderr") or ""
    result["sandbox_mode"] = run_out.get("mode", "")
    result["returncode"] = run_out.get("returncode")

    # Infra failure: bail out of the graph entirely. The student's code never ran,
    # so feeding the infra message to the LLM repair loop is worse than useless —
    # it produces a confident grade of 0 for perfectly correct code.
    if result["sandbox_mode"] == "unavailable":
        state["check_result"] = result
        raise SandboxUnavailableError(result["stderr"] or "Sandbox unavailable.")

    if run_out.get("ok"):
        result["runtime_ok"] = True
        result["passed"] = True
        state["traceback"] = ""
        state["failure_signature"] = ""
        state["no_meaningful_change_count"] = 0
        state["repeated_failure_count"] = 0
    else:
        trace = result["stderr"] or "Runtime failed without stderr output."
        result["traceback"] = trace
        state["traceback"] = trace
        state["failure_signature"] = extract_failure_signature(trace)

        missing_module = _extract_missing_module(trace)
        if (
            state.get("attempt_count", 0) == 0
            and missing_module
            and missing_module.split(".", 1)[0] in _SANDBOX_EXPECTED_MODULES
        ):
            # If a known course/runtime library is missing from the sandbox image,
            # this is environment drift, not a student code mistake.
            state["check_result"] = result
            raise SandboxUnavailableError(
                f"Sandbox dependency missing: {missing_module}. "
                "Execution could not be validated in the sandbox image."
            )

        _capture_initial_failure(state, result, trace)
        _record_error_event(state, result, trace)

    state["check_result"] = result
    logger.debug(
        "run_checks sandbox_mode=%s passed=%s",
        result.get("sandbox_mode"),
        result.get("passed"),
    )
    if not result.get("passed"):
        err_preview = (result.get("stderr") or "")[:800].replace("\n", " ")
        logger.info(
            "run_checks failed | compile_ok=%s runtime_ok=%s sandbox_mode=%s returncode=%s stderr_preview=%s",
            result.get("compile_ok"),
            result.get("runtime_ok"),
            result.get("sandbox_mode"),
            result.get("returncode"),
            err_preview or "(empty)",
        )
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
        last_route = (state.get("attempt_history") or [{}])[-1].get("route", "")
        if last_route == "attempt_sft_with_traceback":
            state["used_traceback"] = False
    if signature:
        state["previous_failure_signature"] = signature

    if state["attempt_count"] >= state["max_attempts"]:
        state["should_stop"] = True
        state["stop_reason"] = "max_attempts_reached"
    elif state["no_meaningful_change_count"] >= 3:
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
    history = state.get("attempt_history", [])
    rag_attempts = sum(1 for attempt in history if attempt.get("route") == "attempt_sft_with_rag")
    traceback_attempts = sum(1 for attempt in history if attempt.get("route") == "attempt_sft_with_traceback")
    reflection_attempts = sum(1 for attempt in history if attempt.get("route") == "attempt_sft_with_reflection")
    last_route = history[-1].get("route", "") if history else ""
    same_error_repeated = int(state.get("repeated_failure_count", 0) or 0) > 0
    remaining_attempts = max(0, int(state.get("max_attempts", 0) or 0) - int(state.get("attempt_count", 0) or 0))

    # Keep OpenRouter/external as the true last resort. The local SFT gets at least
    # repeated direct attempts (RAG for API/library errors, traceback otherwise).
    # If the same error persists after a direct local SFT attempt, ask reflection to
    # guide the next local SFT repair; if the error changes, try local SFT directly again.
    if remaining_attempts <= 1 and not state["used_external"]:
        state["next_strategy"] = "external_expert"
        return state

    if category == "api_library_error":
        if last_route == "attempt_sft_with_rag" and same_error_repeated and reflection_attempts < 2:
            state["next_strategy"] = "reflection_critic"
        elif rag_attempts < 2 or (not same_error_repeated and reflection_attempts < 2):
            state["next_strategy"] = "local_rag"
        elif reflection_attempts < 2:
            state["next_strategy"] = "reflection_critic"
        elif not state["used_external"]:
            state["next_strategy"] = "external_expert"
        else:
            state["next_strategy"] = "finalize_failure"
            state["should_stop"] = True
            state["stop_reason"] = "all_strategies_exhausted"
        return state

    if category != "api_library_error":
        if last_route == "attempt_sft_with_traceback" and same_error_repeated and reflection_attempts < 2:
            state["next_strategy"] = "reflection_critic"
        elif traceback_attempts < 2 or (not same_error_repeated and reflection_attempts < 2):
            state["next_strategy"] = "traceback_sft"
        elif reflection_attempts < 2:
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

    if reranked:
        scores = [float(score) for score, _, _ in reranked]
        best_score = max(scores)
        avg_score = sum(scores) / len(scores)
        state["local_context_quality"] = "good" if (best_score > 0.35 or avg_score > 0.3) else "weak"
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
        for item in local_docs:
            if isinstance(item, tuple):
                doc = item[0] if len(item) > 0 else ""
                if isinstance(doc, str) and doc.strip():
                    chunks.append(doc)
            elif isinstance(item, str) and item.strip():
                chunks.append(item)
        chunks.extend(state.get("web_docs", []))
        bullets = []
        for chunk in chunks[:6]:
            if not isinstance(chunk, str):
                continue
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


@traceable(name="verify_completeness", run_type="chain")
def verify_completeness(state: RepairState) -> RepairState:
    """Check whether the current (runnable) code satisfies all assignment requirements."""
    push_route(state, "verify_completeness")
    description = state.get("assignment_description", "")
    code = state["current_code"]
    result = dispatch_completeness_check(description, code)
    if not state.get("original_code_completeness"):
        state["original_code_completeness"] = result
    state["first_pass_completeness"] = result
    logger.info(
        "[verify_completeness] complete=%s provider=%s confidence=%.2f missing=%d",
        result.get("complete"),
        result.get("provider", "?"),
        result.get("confidence", 0),
        len(result.get("missing_requirements", [])),
    )
    return state


@traceable(name="verify_original_completeness", run_type="chain")
def verify_original_completeness(state: RepairState) -> RepairState:
    """Check the student's submitted code once inside the LangGraph run."""
    push_route(state, "verify_original_completeness")
    description = state.get("assignment_description", "")
    result = dispatch_completeness_check(description, state.get("original_code", ""))
    state["original_code_completeness"] = result
    if state.get("check_result", {}).get("passed", False):
        state["first_pass_completeness"] = result
    logger.info(
        "[verify_original_completeness] complete=%s provider=%s confidence=%.2f missing=%d",
        result.get("complete"),
        result.get("provider", "?"),
        result.get("confidence", 0),
        len(result.get("missing_requirements", [])),
    )
    return state


@traceable(name="attempt_requirement_completion", run_type="chain")
def attempt_requirement_completion(state: RepairState) -> RepairState:
    """Add only evaluator-listed missing requirements to code that already runs."""
    push_route(state, "attempt_requirement_completion")
    before = state["current_code"]
    completeness = state.get("first_pass_completeness") or {}
    if completeness.get("complete", False) or completeness.get("model_complete", False):
        logger.info("[requirement-completion] skipped because completeness gate marked code complete")
        return state
    missing_reqs = [
        str(r.get("text", ""))
        for r in (completeness.get("requirements") or [])
        if isinstance(r, dict) and str(r.get("status", "")).strip().lower() == "missing"
    ] or completeness.get("missing_requirements", [])

    if not missing_reqs:
        logger.info("[requirement-completion] no truly missing requirements; skipping")
        return state

    prompt_preview = (
        "Add missing assignment requirements only.\n"
        f"MISSING_REQUIREMENTS:\n{missing_reqs}\n\n"
        f"CURRENT_CODE:\n{before}\n"
    )
    candidate = call_requirement_completion_model(
        assignment_description=state.get("assignment_description", ""),
        current_code=before,
        completeness=completeness,
    )
    state["current_code"] = candidate
    state["used_requirement_repair"] = True
    state["requirement_repair_count"] = int(state.get("requirement_repair_count", 0)) + 1
    record_attempt(state, "attempt_requirement_completion", before, candidate, prompt_preview)
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
