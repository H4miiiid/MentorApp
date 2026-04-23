from __future__ import annotations

from AppV2.backend.workflow_runtime.llm_clients import heuristic_first_pass_completeness
from AppV2.backend.workflow_runtime.nodes import summarize_context
from AppV2.backend.workflow_runtime.rag import _sanitize_doc_text


def test_sanitize_doc_text_removes_null_and_controls() -> None:
    raw = "alpha\x00beta\x07\nnext"
    cleaned = _sanitize_doc_text(raw)
    assert "\x00" not in cleaned
    assert "\x07" not in cleaned
    assert "alpha" in cleaned
    assert "next" in cleaned


def test_heuristic_first_pass_completeness_flags_stub() -> None:
    result = heuristic_first_pass_completeness(
        "Write a function that returns factorial.",
        "def fact(n):\n    pass\n",
    )
    assert result["complete"] is False


def test_summarize_context_handles_mixed_doc_shapes() -> None:
    state = {
        "route_history": [],
        "local_docs": [(0.9, "Numpy reshape requires matching total element count.", {"library": "numpy"})],
        "traceback": "ValueError: cannot reshape array of size 10 into shape (3,3)",
        "web_docs": ["Check final exception line and adjust requested shape to preserve element count."],
        "summarized_hints": "",
    }
    out = summarize_context(state)
    hints = out.get("summarized_hints", "")
    assert isinstance(hints, str)
    assert hints.strip() != ""
