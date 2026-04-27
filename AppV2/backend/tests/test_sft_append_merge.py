"""Tests for no-append completeness: provider default, grading with completeness
penalties on first-pass and repaired submissions, and workflow routing."""

from __future__ import annotations

from AppV2.backend.grading.langgraph_pipeline import _grade_from_result
from AppV2.backend.grading.workflow_settings_service import COMPLETENESS_PROVIDER_DEFAULT
from AppV2.backend.workflow_runtime.llm_clients import (
    extract_code_block,
    normalize_completeness_result,
    parse_completeness_payload,
)


def test_default_completeness_provider_is_local_sft() -> None:
    assert COMPLETENESS_PROVIDER_DEFAULT == "local_sft"


def test_extract_code_block_correct_code_tags() -> None:
    raw = "<correct_code>print(1)</correct_code>"
    assert extract_code_block(raw) == "print(1)"


def test_extract_code_block_fenced() -> None:
    raw = "```python\nprint(1)\n```"
    assert extract_code_block(raw).strip() == "print(1)"


def test_parse_completeness_payload_recovers_from_single_quotes() -> None:
    raw = (
        "Here is the result:\n"
        "{'complete': False, 'missing_requirements': ['explore_and_understand_data', 'make_predictions']}"
    )
    parsed = parse_completeness_payload(raw)
    assert isinstance(parsed, dict)
    assert parsed.get("complete") is False
    assert parsed.get("missing_requirements") == [
        "explore_and_understand_data",
        "make_predictions",
    ]


def test_parse_completeness_payload_recovers_list_from_plain_text() -> None:
    raw = (
        "missing_requirements: [\n"
        "  'explore_and_understand_data',\n"
        "  'evaluate_models',\n"
        "  'explain_feature_importance'\n"
        "]"
    )
    parsed = parse_completeness_payload(raw)
    assert isinstance(parsed, dict)
    assert parsed.get("complete") is False
    assert parsed.get("missing_requirements") == [
        "explore_and_understand_data",
        "evaluate_models",
        "explain_feature_importance",
    ]


def test_normalize_completeness_result_keeps_partial_and_missing_rows() -> None:
    normalized = normalize_completeness_result(
        {
            "complete": False,
            "partially_satisfied_requirements": ["evaluate_models"],
            "missing_requirements": ["make_predictions"],
        }
    )
    reqs = normalized.get("requirements") or []
    assert any(r.get("text") == "evaluate_models" and r.get("status") == "partial" for r in reqs)
    assert any(r.get("text") == "make_predictions" and r.get("status") == "missing" for r in reqs)
    assert normalized.get("complete") is False


def test_normalize_completeness_result_prefers_structured_rows_over_placeholder_missing() -> None:
    normalized = normalize_completeness_result(
        {
            "complete": False,
            "requirements": [
                {"text": "make_predictions", "status": "missing", "severity": "critical", "evidence": ""},
            ],
            "missing_requirements": ["Implementation appears partial or placeholder."],
        }
    )
    # The explicit requirement row should survive and drive the derived missing list.
    assert normalized.get("missing_requirements") == ["make_predictions"]


def test_first_pass_complete_gets_100() -> None:
    g = _grade_from_result(
        "a", "a",
        {"final_status": "success", "attempt_count": 0,
         "first_pass_completeness": {"complete": True}},
        grading_max_attempts=6,
    )
    assert g == 100.0


def test_first_pass_incomplete_reduces_grade() -> None:
    g = _grade_from_result(
        "a", "a",
        {"final_status": "success", "attempt_count": 0,
         "first_pass_completeness": {
             "complete": False,
             "missing_requirements": ["Train model with .fit()"],
         }},
        grading_max_attempts=6,
    )
    assert g < 100.0
    assert g >= 48.0


def test_repaired_complete_no_extra_penalty() -> None:
    """Repaired submission with all requirements met gets normal repair grade."""
    g = _grade_from_result(
        "a", "b",
        {"final_status": "success", "attempt_count": 2,
         "max_attempts": 6,
         "first_pass_completeness": {"complete": True},
         "error_events": [{"signature": "err", "category": "syntax_error"}]},
        grading_max_attempts=6,
    )
    assert g <= 98.0
    assert g >= 60.0


def test_repaired_incomplete_gets_extra_penalty() -> None:
    """Repaired submission with missing requirements gets lower grade than complete."""
    base_result = {
        "final_status": "success",
        "attempt_count": 2,
        "max_attempts": 6,
        "error_events": [{"signature": "err", "category": "syntax_error"}],
    }
    g_complete = _grade_from_result(
        "a", "b",
        {**base_result, "first_pass_completeness": {"complete": True}},
        grading_max_attempts=6,
    )
    g_incomplete = _grade_from_result(
        "a", "b",
        {**base_result, "first_pass_completeness": {
            "complete": False,
            "requirements": [
                {"text": "pipeline.fit()", "status": "missing", "severity": "critical", "evidence": ""},
            ],
        }},
        grading_max_attempts=6,
    )
    assert g_incomplete < g_complete
    assert g_incomplete >= 32.0


def test_repaired_incomplete_floor_at_minimum() -> None:
    """Grade never drops below the minimum floor even with heavy combined penalties."""
    g = _grade_from_result(
        "a",
        "b",
        {
            "final_status": "success",
            "attempt_count": 5,
            "max_attempts": 6,
            "first_pass_completeness": {
                "complete": False,
                "requirements": [
                    {"text": "fit()", "status": "missing", "severity": "critical", "evidence": ""},
                    {"text": "predict()", "status": "missing", "severity": "critical", "evidence": ""},
                    {"text": "evaluate()", "status": "missing", "severity": "critical", "evidence": ""},
                    {"text": "cross_val()", "status": "missing", "severity": "critical", "evidence": ""},
                ],
            },
            "error_events": [
                {"signature": "e1", "category": "api_library_error"},
                {"signature": "e2", "category": "timeout"},
            ],
        },
        grading_max_attempts=6,
    )
    assert g >= 32.0


def test_no_completeness_data_repaired_unaffected() -> None:
    """When completeness data is absent, repaired grade is unchanged."""
    g = _grade_from_result(
        "a", "b",
        {"final_status": "success", "attempt_count": 1,
         "max_attempts": 6,
         "error_events": [{"signature": "err", "category": "syntax_error"}]},
        grading_max_attempts=6,
    )
    assert g <= 98.0
    assert g >= 60.0
