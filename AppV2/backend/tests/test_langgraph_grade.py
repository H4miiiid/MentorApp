"""Grading outcome: partial scores must vary with category and context, not only attempt_count."""

from __future__ import annotations

from AppV2.backend.grading.langgraph_pipeline import _grade_from_result


def test_success_is_full_marks() -> None:
    g = _grade_from_result("a", "a", {"final_status": "success"}, grading_max_attempts=6)
    assert g == 100.0


def test_failure_varies_by_category_not_only_attempts() -> None:
    base = {
        "final_status": "failure",
        "attempt_count": 4,
        "max_attempts": 6,
        "no_meaningful_change_count": 0,
        "repeated_failure_count": 0,
        "stop_reason": "",
    }
    g_syntax = _grade_from_result("x", "y", {**base, "error_category": "syntax_error"}, grading_max_attempts=6)
    g_api = _grade_from_result("x", "y", {**base, "error_category": "api_library_error"}, grading_max_attempts=6)
    assert g_syntax != g_api
    assert g_syntax > g_api


def test_no_edit_penalizes() -> None:
    code = "def f():\n    pass\n"
    g = _grade_from_result(
        code,
        code,
        {
            "final_status": "failure",
            "attempt_count": 2,
            "max_attempts": 6,
            "error_category": "syntax_error",
            "no_meaningful_change_count": 0,
            "repeated_failure_count": 0,
            "stop_reason": "",
        },
        grading_max_attempts=6,
    )
    g2 = _grade_from_result(
        code,
        "def f():\n    return 1\n",
        {
            "final_status": "failure",
            "attempt_count": 2,
            "max_attempts": 6,
            "error_category": "syntax_error",
            "no_meaningful_change_count": 0,
            "repeated_failure_count": 0,
            "stop_reason": "",
        },
        grading_max_attempts=6,
    )
    assert g2 > g
