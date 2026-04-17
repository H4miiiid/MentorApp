"""Regression tests: when the sandbox is unavailable, the grading graph must NOT
run the LLM repair loop on the student's code.

Prior bug (submission c9f9ddda-2bd9-4489-8198-f032bcb781a2):
  - Docker socket / image was unreachable at grade time.
  - ``execute_python_after_compile`` returned mode="unavailable" with an infra message.
  - ``run_checks`` blindly put that message into ``state["traceback"]``.
  - The graph then ran up to 2 LLM repair attempts trying to "fix" perfectly correct
    student code against a fake infra traceback, gave up with
    ``stop_reason=no_meaningful_change``, and assigned grade=0.

These tests lock in the fix: run_checks raises ``SandboxUnavailableError`` immediately,
and ``run_workflow`` surfaces ``final_status="sandbox_unavailable"`` without invoking
any LLM.
"""

from __future__ import annotations

from typing import Any

import pytest

from AppV2.backend.workflow_runtime import nodes, sandbox
from AppV2.backend.workflow_runtime.graph import run_workflow
from AppV2.backend.workflow_runtime.state import init_state


def _unavailable_result(stderr: str = "Sandbox unavailable: ...") -> dict[str, Any]:
    return {
        "ok": False,
        "stdout": "",
        "stderr": stderr,
        "returncode": -1,
        "mode": "unavailable",
    }


def test_run_checks_raises_sandbox_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nodes,
        "execute_python_after_compile",
        lambda code, timeout: _unavailable_result("docker socket missing"),
    )
    state = init_state(original_code="print('hi')")
    with pytest.raises(sandbox.SandboxUnavailableError) as exc:
        nodes.run_checks(state)
    assert "docker socket missing" in str(exc.value)
    assert state["check_result"]["sandbox_mode"] == "unavailable"


def test_run_checks_does_not_raise_on_real_student_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nodes,
        "execute_python_after_compile",
        lambda code, timeout: {
            "ok": False,
            "stdout": "",
            "stderr": "Traceback ...\nZeroDivisionError: division by zero",
            "returncode": 1,
            "mode": "docker",
        },
    )
    state = init_state(original_code="x = 1/0")
    state = nodes.run_checks(state)
    assert state["check_result"]["passed"] is False
    assert "ZeroDivisionError" in state["traceback"]


def test_run_workflow_short_circuits_on_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Graph should not call any LLM when sandbox is unavailable."""
    # Stub out HF endpoint + langsmith setup so the test does not hit network.
    import AppV2.backend.workflow_runtime.graph as graph_mod

    monkeypatch.setattr(graph_mod, "ensure_hf_endpoint_available", lambda: None)
    monkeypatch.setattr(graph_mod, "setup_langsmith", lambda: None)

    # Sandbox always unavailable.
    monkeypatch.setattr(
        nodes,
        "execute_python_after_compile",
        lambda code, timeout: _unavailable_result("image pull unauthorized"),
    )

    # If any repair node ran, it would call one of these; detonate if they do.
    def _explode(*a, **kw):  # noqa: ANN001, ARG001
        raise AssertionError("LLM repair must not run when sandbox is unavailable")

    monkeypatch.setattr("AppV2.backend.workflow_runtime.nodes.call_sft_model", _explode)
    monkeypatch.setattr("AppV2.backend.workflow_runtime.nodes.call_external_model", _explode)
    monkeypatch.setattr("AppV2.backend.workflow_runtime.nodes.call_reflection_model", _explode)

    student_code = "def fibo(n):\n    return n\n\nprint(fibo(10))\n"
    result = run_workflow(student_code, max_attempts=6)

    assert result["final_status"] == "sandbox_unavailable"
    assert result["attempt_count"] == 0
    assert result["final_code"] == student_code  # untouched
    assert result["error_category"] == "sandbox_unavailable"
    assert "image pull unauthorized" in result["sandbox_error"]


def test_pull_failure_marks_mode_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_ensure_image_pulled` failure must not masquerade as mode=docker."""
    monkeypatch.setattr(sandbox, "_image_exists_locally", lambda image: False)

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ARG001
        class _P:
            returncode = 1
            stderr = "Error: pull access denied"
            stdout = ""

        if cmd[:2] == ["docker", "pull"]:
            return _P()
        raise AssertionError(f"unexpected command {cmd}")

    monkeypatch.setattr(sandbox.subprocess, "run", fake_run)
    out = sandbox.run_python_in_docker("print(1)", timeout=5.0)
    assert out["mode"] == "unavailable"
    assert "pull access denied" in out["stderr"]


def test_langgraph_pipeline_uses_unavailable_outcome_not_student_blame() -> None:
    """Ensure _grade_from_result returns 0 for infra error without weird partial-credit math."""
    from AppV2.backend.grading.langgraph_pipeline import _grade_from_result

    g = _grade_from_result(
        "code",
        "code",
        {
            "final_status": "sandbox_unavailable",
            "attempt_count": 0,
            "max_attempts": 6,
            "error_category": "sandbox_unavailable",
            "stop_reason": "sandbox_unavailable",
            "no_meaningful_change_count": 0,
            "repeated_failure_count": 0,
        },
        grading_max_attempts=6,
    )
    assert g == 0.0
