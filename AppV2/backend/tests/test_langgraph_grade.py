"""Grading outcome: partial scores must vary with category and context, not only attempt_count."""

from __future__ import annotations

from AppV2.backend.db.models import SubmissionStatus
from AppV2.backend.grading.langgraph_pipeline import _grade_from_result, _submission_status_from_grade


def test_success_is_full_marks() -> None:
    g = _grade_from_result("a", "a", {"final_status": "success"}, grading_max_attempts=6)
    assert g == 100.0


def test_success_incomplete_first_pass_reduces_grade() -> None:
    g = _grade_from_result(
        "a",
        "a",
        {
            "final_status": "success",
            "attempt_count": 0,
            "first_pass_completeness": {
                "complete": False,
                "rationale": "Stub-like implementation detected.",
                "missing_requirements": ["Missing feature A"],
            },
        },
        grading_max_attempts=6,
    )
    assert g < 100.0
    assert g >= 70.0


def test_success_incomplete_multiple_missing_reqs_lowers_further() -> None:
    g = _grade_from_result(
        "a",
        "a",
        {
            "final_status": "success",
            "attempt_count": 0,
            "first_pass_completeness": {
                "complete": False,
                "rationale": "Many missing requirements.",
                "missing_requirements": ["A", "B", "C"],
            },
        },
        grading_max_attempts=6,
    )
    assert g < 92.0
    assert g >= 70.0


def test_incomplete_critical_penalizes_more_than_minor() -> None:
    g_crit = _grade_from_result(
        "a",
        "a",
        {
            "final_status": "success",
            "attempt_count": 0,
            "first_pass_completeness": {
                "complete": False,
                "requirements": [
                    {
                        "text": "Train model with pipeline.fit(X_train, y_train)",
                        "status": "missing",
                        "severity": "critical",
                        "evidence": "",
                    },
                ],
            },
        },
        grading_max_attempts=6,
    )
    g_min = _grade_from_result(
        "a",
        "a",
        {
            "final_status": "success",
            "attempt_count": 0,
            "first_pass_completeness": {
                "complete": False,
                "requirements": [
                    {
                        "text": "Print evaluation metrics to stdout",
                        "status": "missing",
                        "severity": "minor",
                        "evidence": "",
                    },
                ],
            },
        },
        grading_max_attempts=6,
    )
    assert g_crit < g_min
    assert g_crit >= 32.0
    assert g_min <= 100.0


def test_incomplete_partial_counts_less_than_full_missing() -> None:
    g_full = _grade_from_result(
        "a",
        "a",
        {
            "final_status": "success",
            "attempt_count": 0,
            "first_pass_completeness": {
                "complete": False,
                "requirements": [
                    {
                        "text": "Cross-validation step",
                        "status": "missing",
                        "severity": "medium",
                        "evidence": "",
                    },
                ],
            },
        },
        grading_max_attempts=6,
    )
    g_partial = _grade_from_result(
        "a",
        "a",
        {
            "final_status": "success",
            "attempt_count": 0,
            "first_pass_completeness": {
                "complete": False,
                "requirements": [
                    {
                        "text": "Cross-validation step",
                        "status": "partial",
                        "severity": "medium",
                        "evidence": "",
                    },
                ],
            },
        },
        grading_max_attempts=6,
    )
    assert g_partial > g_full


def test_success_complete_first_pass_remains_100() -> None:
    g = _grade_from_result(
        "a",
        "a",
        {
            "final_status": "success",
            "attempt_count": 0,
            "first_pass_completeness": {
                "complete": True,
                "rationale": "Looks complete.",
            },
        },
        grading_max_attempts=6,
    )
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


def test_submission_status_threshold_pass_at_75() -> None:
    assert _submission_status_from_grade("success", 70.0) == SubmissionStatus.completed
    assert _submission_status_from_grade("success", 75.0) == SubmissionStatus.completed
    assert _submission_status_from_grade("success", 92.5) == SubmissionStatus.completed


def test_submission_status_threshold_fail_below_70() -> None:
    assert _submission_status_from_grade("success", 69.9) == SubmissionStatus.failed
    assert _submission_status_from_grade("failure", 98.0) == SubmissionStatus.failed
