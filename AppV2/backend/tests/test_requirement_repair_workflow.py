from __future__ import annotations

import json
from typing import Any

from AppV2.backend.grading.langgraph_pipeline import _feedback_blob, _grade_from_result
from AppV2.backend.workflow_runtime import graph as graph_module
from AppV2.backend.workflow_runtime import nodes as nodes_module
from AppV2.backend.workflow_runtime.nodes import record_attempt
from AppV2.backend.workflow_runtime.state import RepairState, init_state, push_route


def _incomplete() -> dict[str, Any]:
    return {
        "complete": False,
        "rationale": "Missing required output.",
        "requirements": [
            {
                "text": "Print the required summary",
                "status": "missing",
                "severity": "minor",
                "evidence": "",
            }
        ],
        "missing_requirements": ["Print the required summary"],
        "confidence": 0.9,
        "provider": "local_sft",
    }


def _complete() -> dict[str, Any]:
    return {
        "complete": True,
        "rationale": "All requirements are present.",
        "requirements": [
            {
                "text": "Print the required summary",
                "status": "present",
                "severity": "minor",
                "evidence": "summary print is present",
            }
        ],
        "missing_requirements": [],
        "confidence": 0.95,
        "provider": "local_sft",
    }


def _complete_with_partial() -> dict[str, Any]:
    return {
        "complete": False,
        "model_complete": True,
        "rationale": "Model marked complete but noticed a partial optional explanation.",
        "requirements": [
            {
                "text": "Explain the output",
                "status": "partial",
                "severity": "minor",
                "evidence": "brief explanation exists",
            }
        ],
        "missing_requirements": ["Explain the output"],
        "confidence": 0.85,
        "provider": "local_sft",
    }


def _passing_check(state: RepairState) -> RepairState:
    push_route(state, "run_checks")
    state["check_result"] = {
        "passed": True,
        "compile_ok": True,
        "runtime_ok": True,
        "stdout": "ok\n",
        "stderr": "",
        "traceback": "",
    }
    state["traceback"] = ""
    state["failure_signature"] = ""
    return state


def test_first_pass_incomplete_enters_requirement_completion(monkeypatch) -> None:
    monkeypatch.setattr(graph_module, "ensure_hf_endpoint_available", lambda: None)
    monkeypatch.setattr(graph_module, "run_checks", _passing_check)

    def fake_completeness(_assignment: str, code: str) -> dict[str, Any]:
        return _complete() if "added_requirement" in code else _incomplete()

    monkeypatch.setattr(nodes_module, "dispatch_completeness_check", fake_completeness)
    monkeypatch.setattr(
        nodes_module,
        "call_requirement_completion_model",
        lambda assignment_description, current_code, completeness: current_code + "\nadded_requirement = True\n",
    )

    result = graph_module.run_workflow(
        "print('hello')\n",
        max_attempts=3,
        assignment_description="Print the required summary.",
    )

    assert result["final_status"] == "success"
    assert result["attempt_count"] == 1
    assert result["requirement_repair_count"] == 1
    assert result["original_code_completeness"]["complete"] is False
    assert result["first_pass_completeness"]["complete"] is True
    assert "verify_original_completeness" in result["route_history"]
    assert "attempt_requirement_completion" in result["route_history"]
    assert "added_requirement = True" in result["final_code"]


def test_first_pass_complete_checks_requirements_once_inside_graph(monkeypatch) -> None:
    calls = {"n": 0}
    monkeypatch.setattr(graph_module, "ensure_hf_endpoint_available", lambda: None)
    monkeypatch.setattr(graph_module, "run_checks", _passing_check)

    def fake_completeness(_assignment: str, _code: str) -> dict[str, Any]:
        calls["n"] += 1
        return _complete()

    monkeypatch.setattr(nodes_module, "dispatch_completeness_check", fake_completeness)

    result = graph_module.run_workflow(
        "print('done')\n",
        max_attempts=3,
        assignment_description="Print the required summary.",
    )

    assert result["final_status"] == "success"
    assert result["attempt_count"] == 0
    assert calls["n"] == 1
    assert result["route_history"] == [
        "run_checks",
        "verify_original_completeness",
        "finalize_success",
    ]


def test_model_complete_true_skips_requirement_completion(monkeypatch) -> None:
    monkeypatch.setattr(graph_module, "ensure_hf_endpoint_available", lambda: None)
    monkeypatch.setattr(graph_module, "run_checks", _passing_check)
    monkeypatch.setattr(nodes_module, "dispatch_completeness_check", lambda _assignment, _code: _complete_with_partial())

    result = graph_module.run_workflow(
        "print('done')\n",
        max_attempts=3,
        assignment_description="Print and explain.",
    )

    assert result["final_status"] == "success"
    assert result["attempt_count"] == 0
    assert result["requirement_repair_count"] == 0
    assert "attempt_requirement_completion" not in result["route_history"]


def test_failed_code_is_repaired_then_completed_for_requirements(monkeypatch) -> None:
    monkeypatch.setattr(graph_module, "ensure_hf_endpoint_available", lambda: None)

    def fake_run_checks(state: RepairState) -> RepairState:
        push_route(state, "run_checks")
        if state["current_code"] == "broken":
            state["check_result"] = {
                "passed": False,
                "compile_ok": False,
                "runtime_ok": False,
                "stdout": "",
                "stderr": "SyntaxError: invalid syntax",
                "traceback": "SyntaxError: invalid syntax",
            }
            state["traceback"] = "SyntaxError: invalid syntax"
            state["failure_signature"] = "SyntaxError: invalid syntax"
            return state
        state["check_result"] = {
            "passed": True,
            "compile_ok": True,
            "runtime_ok": True,
            "stdout": "ok\n",
            "stderr": "",
            "traceback": "",
        }
        state["traceback"] = ""
        state["failure_signature"] = ""
        return state

    def fake_traceback_repair(state: RepairState) -> RepairState:
        push_route(state, "attempt_sft_with_traceback")
        before = state["current_code"]
        candidate = "print('fixed')\n"
        state["used_traceback"] = True
        state["current_code"] = candidate
        record_attempt(state, "attempt_sft_with_traceback", before, candidate, "TRACEBACK:\nSyntaxError")
        return state

    def fake_completeness(_assignment: str, code: str) -> dict[str, Any]:
        return _complete() if "added_requirement" in code else _incomplete()

    monkeypatch.setattr(graph_module, "run_checks", fake_run_checks)
    monkeypatch.setattr(graph_module, "attempt_sft_with_traceback", fake_traceback_repair)
    monkeypatch.setattr(nodes_module, "dispatch_completeness_check", fake_completeness)
    monkeypatch.setattr(
        nodes_module,
        "call_requirement_completion_model",
        lambda assignment_description, current_code, completeness: current_code + "added_requirement = True\n",
    )

    result = graph_module.run_workflow(
        "broken",
        max_attempts=4,
        assignment_description="Fix runtime and print the required summary.",
    )

    assert result["final_status"] == "success"
    assert result["attempt_count"] == 2
    assert result["requirement_repair_count"] == 1
    assert result["original_code_completeness"]["complete"] is False
    assert result["route_history"].index("attempt_sft_with_traceback") < result["route_history"].index(
        "attempt_requirement_completion"
    )
    assert result["first_pass_completeness"]["complete"] is True
    assert "added_requirement = True" in result["final_code"]


def test_complete_first_pass_still_receives_full_marks() -> None:
    grade = _grade_from_result(
        "print('done')\n",
        "print('done')\n",
        {
            "final_status": "success",
            "attempt_count": 0,
            "original_code_completeness": _complete(),
        },
        grading_max_attempts=6,
    )

    assert grade == 100.0


def test_requirement_completion_feedback_marks_assistant_completion() -> None:
    result = {
        "final_status": "success",
        "attempt_count": 1,
        "max_attempts": 6,
        "used_requirement_repair": True,
        "requirement_repair_count": 1,
        "original_code_completeness": _incomplete(),
        "first_pass_completeness": _complete(),
        "attempt_history": [{"attempt": 1, "route": "attempt_requirement_completion"}],
    }

    payload = json.loads(_feedback_blob(result, original_code="print('x')", final_code="print('x')\nprint('summary')"))

    assert payload["repaired"] is True
    assert payload["requirement_repaired"] is True
    assert payload["requirement_repair_count"] == 1
    assert payload["completeness"]["complete"] is False
    assert payload["final_completeness"]["complete"] is True


def test_non_api_errors_start_with_traceback_sft() -> None:
    state = init_state("broken")
    state["error_category"] = "local_reasoning_error"

    nodes_module.choose_next_strategy(state)

    assert state["next_strategy"] == "traceback_sft"


def test_api_errors_start_with_rag() -> None:
    state = init_state("broken")
    state["error_category"] = "api_library_error"

    nodes_module.choose_next_strategy(state)

    assert state["next_strategy"] == "local_rag"


def test_api_errors_try_local_sft_after_rag_before_reflection() -> None:
    state = init_state("broken")
    state["error_category"] = "api_library_error"
    state["used_rag"] = True
    state["attempt_history"] = [{"route": "attempt_sft_with_rag"}]

    nodes_module.choose_next_strategy(state)

    assert state["next_strategy"] == "local_rag"


def test_same_traceback_error_routes_to_reflection() -> None:
    state = init_state("broken")
    state["error_category"] = "syntax_error"
    state["attempt_history"] = [{"route": "attempt_sft_with_traceback"}]
    state["repeated_failure_count"] = 1

    nodes_module.choose_next_strategy(state)

    assert state["next_strategy"] == "reflection_critic"


def test_changed_traceback_error_routes_back_to_traceback_sft() -> None:
    state = init_state("broken")
    state["error_category"] = "syntax_error"
    state["attempt_history"] = [{"route": "attempt_sft_with_traceback"}]
    state["repeated_failure_count"] = 0

    nodes_module.choose_next_strategy(state)

    assert state["next_strategy"] == "traceback_sft"


def test_same_api_error_after_rag_routes_to_reflection() -> None:
    state = init_state("broken")
    state["error_category"] = "api_library_error"
    state["attempt_history"] = [{"route": "attempt_sft_with_rag"}]
    state["repeated_failure_count"] = 1

    nodes_module.choose_next_strategy(state)

    assert state["next_strategy"] == "reflection_critic"


def test_local_sft_gets_two_reflection_attempts_before_external() -> None:
    state = init_state("broken")
    state["error_category"] = "syntax_error"
    state["attempt_history"] = [
        {"route": "attempt_sft_with_traceback"},
        {"route": "attempt_sft_with_traceback"},
        {"route": "attempt_sft_with_reflection"},
    ]
    state["repeated_failure_count"] = 1

    nodes_module.choose_next_strategy(state)

    assert state["next_strategy"] == "reflection_critic"


def test_external_is_after_local_sft_attempt_budget() -> None:
    state = init_state("broken")
    state["error_category"] = "syntax_error"
    state["attempt_history"] = [
        {"route": "attempt_sft_with_traceback"},
        {"route": "attempt_sft_with_traceback"},
        {"route": "attempt_sft_with_reflection"},
        {"route": "attempt_sft_with_reflection"},
    ]

    nodes_module.choose_next_strategy(state)

    assert state["next_strategy"] == "external_expert"
