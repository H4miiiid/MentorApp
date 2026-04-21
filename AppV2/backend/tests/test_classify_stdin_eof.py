from __future__ import annotations

from AppV2.backend.workflow_runtime.state import classify_error


def test_eoferror_is_stdin_eof_not_api_library() -> None:
    tb = """Traceback (most recent call last):
  File \"candidate.py\", line 1, in <module>
    x = input()
EOFError: EOF when reading a line
"""
    out = classify_error(tb, {"compile_ok": True})
    assert out["category"] == "stdin_eof"
