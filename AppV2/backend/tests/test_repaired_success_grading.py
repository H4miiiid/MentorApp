"""Regression tests for repaired-success grading fairness.

These tests ensure first-pass passes keep full marks, repaired outcomes are
penalized rationally, and latent multi-fix repairs do not score higher than
single-error repaired cases.
"""

from __future__ import annotations

import json

from AppV2.backend.grading.langgraph_pipeline import (
    _feedback_blob,
    _grade_from_result,
    _grade_repaired_success,
    _was_repaired,
)
from AppV2.backend.workflow_runtime.nodes import _capture_initial_failure
from AppV2.backend.workflow_runtime.state import init_state


def _base_success(**overrides):
    base = {
        "final_status": "success",
        "attempt_count": 0,
        "max_attempts": 6,
    }
    base.update(overrides)
    return base


def test_clean_first_try_pass_is_still_100() -> None:
    """Backwards compatibility: no repair attempts ⇒ full marks."""
    g = _grade_from_result("x", "x", _base_success(attempt_count=0), grading_max_attempts=6)
    assert g == 100.0


def test_repaired_success_is_strictly_below_100() -> None:
    """If the LLM had to intervene, the grade must not be 100."""
    g = _grade_from_result(
        "broken",
        "fixed",
        _base_success(attempt_count=1, initial_error_category="syntax_error"),
        grading_max_attempts=6,
    )
    assert 0.0 < g < 100.0


def test_repaired_success_grade_drops_as_attempts_increase() -> None:
    """A student whose code took more repair attempts should score lower than a
    student whose code was fixed on the first try."""
    one = _grade_repaired_success(attempts=1, max_attempts=6, weighted_units=1.0, mistake_count=1)
    two = _grade_repaired_success(attempts=2, max_attempts=6, weighted_units=1.0, mistake_count=1)
    three = _grade_repaired_success(attempts=3, max_attempts=6, weighted_units=1.0, mistake_count=1)
    assert one > two > three
    assert three >= 60.0


def test_repaired_success_grade_reflects_error_severity() -> None:
    """A syntax typo should be penalised less than a deep API misuse that
    required repair."""
    syntax = _grade_repaired_success(attempts=1, max_attempts=6, weighted_units=1.0, mistake_count=1)
    api = _grade_repaired_success(attempts=1, max_attempts=6, weighted_units=2.0, mistake_count=1)
    assert syntax > api


def test_repaired_success_has_floor() -> None:
    """Many repairs must still not zero out a student who eventually passed —
    they tried harder than the student who never passed."""
    g = _grade_repaired_success(attempts=12, max_attempts=6, weighted_units=3.0, mistake_count=4)
    assert g >= 60.0


def test_was_repaired_helper_discriminates_success_types() -> None:
    assert _was_repaired({"final_status": "success", "attempt_count": 0}) is False
    assert _was_repaired({"final_status": "success", "attempt_count": 3}) is True
    assert _was_repaired({"final_status": "failure", "attempt_count": 5}) is False


def test_feedback_blob_exposes_initial_error_for_frontend() -> None:
    """The JSON blob that lands in submission.feedback must carry the original
    error fields so FeedbackPanel.svelte can render the amber 'repaired' UI."""
    result = _base_success(
        attempt_count=1,
        initial_error_category="syntax_error",
        initial_error_type="SyntaxError",
        initial_error_explanation="expected ':'",
        initial_traceback=(
            "Traceback (most recent call last):\n"
            '  File "/work/candidate.py", line 2\n'
            "    if n == 1 or n == 0\n"
            "                       ^\n"
            "SyntaxError: expected ':'"
        ),
        attempt_history=[],
    )
    blob = json.loads(_feedback_blob(result, original_code="broken", final_code="fixed"))
    assert blob["repaired"] is True
    assert blob["initial_error_category"] == "syntax_error"
    assert blob["initial_error_type"] == "SyntaxError"
    assert "expected ':'" in blob["initial_error_explanation"]
    assert "SyntaxError" in blob["initial_traceback"]
    assert "inferred_fix_units" in blob
    assert "observed_mistake_count" in blob


def test_capture_initial_failure_populates_state_once_only() -> None:
    """_capture_initial_failure must latch on the FIRST failed check and never
    be overwritten by a later failure during the repair loop — otherwise the
    'original error' shown to the student would drift as the LLM tries things."""
    state = init_state(original_code="broken", max_attempts=6)
    first_trace = (
        "Traceback (most recent call last):\n"
        '  File "/work/candidate.py", line 2\n'
        "SyntaxError: expected ':'"
    )
    check_result_first = {"stdout": "", "stderr": first_trace, "compile_ok": False}
    _capture_initial_failure(state, check_result_first, first_trace)

    assert state["initial_traceback"] == first_trace
    assert state["initial_error_category"] == "syntax_error"
    assert state["initial_error_type"] == "SyntaxError"

    # A later, different failure must NOT overwrite the snapshot.
    later_trace = "Traceback...\nValueError: bad input"
    check_result_later = {"stdout": "x", "stderr": later_trace, "compile_ok": True}
    _capture_initial_failure(state, check_result_later, later_trace)

    assert state["initial_traceback"] == first_trace, "later failures must not clobber the first"
    assert state["initial_error_category"] == "syntax_error"


def test_sandbox_unavailable_grade_unchanged_by_repair_policy() -> None:
    """Infrastructure failures must still bypass the student-blame grading
    entirely — the code was never executed."""
    g = _grade_from_result(
        "ok",
        "ok",
        {"final_status": "sandbox_unavailable", "attempt_count": 0},
        grading_max_attempts=6,
    )
    assert g == 0.0


def test_latent_second_fix_counts_against_grade() -> None:
    """When one surfaced syntax error hides another bug fixed in the same repair,
    effective mistake count should be >= 2 and grade should not exceed a single
    API-misuse repaired baseline."""
    original = "\n".join(
        [
            "digits = load_digits",
            "model = SVC(gamma=0.001",
        ]
    )
    fixed = "\n".join(
        [
            "digits = load_digits()",
            "model = SVC(gamma=0.001)",
        ]
    )
    latent = {
        "final_status": "success",
        "attempt_count": 1,
        "max_attempts": 6,
        "error_events": [
            {
                "signature": "SyntaxError: '(' was never closed",
                "category": "syntax_error",
                "error_line": "SyntaxError: '(' was never closed",
            }
        ],
        "initial_error_category": "syntax_error",
    }
    api_single = {
        "final_status": "success",
        "attempt_count": 1,
        "max_attempts": 6,
        "error_events": [
            {
                "signature": "ModuleNotFoundError: No module named 'x'",
                "category": "api_library_error",
                "error_line": "ModuleNotFoundError: No module named 'x'",
            }
        ],
        "initial_error_category": "api_library_error",
    }

    g_latent = _grade_from_result(original, fixed, latent, grading_max_attempts=6)
    g_api = _grade_from_result("x", "y", api_single, grading_max_attempts=6)
    blob = json.loads(_feedback_blob(latent, original_code=original, final_code=fixed))

    assert blob["mistake_count"] >= 2
    assert blob["inferred_fix_units"] >= 2
    assert g_latent < g_api


def test_comment_and_whitespace_only_edits_do_not_add_inferred_fix_units() -> None:
    result = {
        "final_status": "success",
        "attempt_count": 1,
        "max_attempts": 6,
        "error_events": [
            {
                "signature": "SyntaxError: invalid syntax",
                "category": "syntax_error",
                "error_line": "SyntaxError: invalid syntax",
            }
        ],
        "initial_error_category": "syntax_error",
    }
    original = "value = 1\n# comment\n"
    final = "value = 1\n\n# updated comment\n"

    blob = json.loads(_feedback_blob(result, original_code=original, final_code=final))

    assert blob["inferred_fix_units"] == 0
    assert blob["mistake_count"] == blob["observed_mistake_count"]
