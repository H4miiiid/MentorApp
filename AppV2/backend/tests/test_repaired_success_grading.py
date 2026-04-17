"""Regression tests for the repaired-success grading policy.

Previously ``_grade_from_result`` returned a flat 100.0 whenever
``final_status == "success"``, which meant a student whose original code crashed
at parse time and was rewritten by the LLM got the same grade as a student whose
code passed on the first try. The fix introduces partial credit for repaired
successes and exposes the student's original error (``initial_traceback`` et al.)
to the frontend so the UI can show the actual mistake.

These tests pin down the contract so the old behaviour cannot silently return.
"""

from __future__ import annotations

import json

from AppV2.backend.grading.langgraph_pipeline import (
    REPAIRED_SUCCESS_CAP,
    REPAIRED_SUCCESS_FLOOR,
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
    assert g <= REPAIRED_SUCCESS_CAP


def test_repaired_success_grade_drops_as_attempts_increase() -> None:
    """A student whose code took more repair attempts should score lower than a
    student whose code was fixed on the first try."""
    one = _grade_repaired_success(attempts=1, max_attempts=6, initial_category="syntax_error")
    two = _grade_repaired_success(attempts=2, max_attempts=6, initial_category="syntax_error")
    three = _grade_repaired_success(attempts=3, max_attempts=6, initial_category="syntax_error")
    assert one > two > three
    assert three >= REPAIRED_SUCCESS_FLOOR


def test_repaired_success_grade_reflects_error_severity() -> None:
    """A syntax typo should be penalised less than a deep API misuse that
    required repair."""
    syntax = _grade_repaired_success(attempts=1, max_attempts=6, initial_category="syntax_error")
    api = _grade_repaired_success(attempts=1, max_attempts=6, initial_category="api_library_error")
    assert syntax > api


def test_repaired_success_has_floor() -> None:
    """Many repairs must still not zero out a student who eventually passed —
    they tried harder than the student who never passed."""
    g = _grade_repaired_success(attempts=12, max_attempts=6, initial_category="api_library_error")
    assert g >= REPAIRED_SUCCESS_FLOOR


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
    blob = json.loads(_feedback_blob(result))
    assert blob["repaired"] is True
    assert blob["initial_error_category"] == "syntax_error"
    assert blob["initial_error_type"] == "SyntaxError"
    assert "expected ':'" in blob["initial_error_explanation"]
    assert "SyntaxError" in blob["initial_traceback"]


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
