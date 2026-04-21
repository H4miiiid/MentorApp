from __future__ import annotations

import os

import pytest

from AppV2.backend.workflow_runtime import sandbox


def test_sandbox_stdin_default_is_many_newlines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SANDBOX_STDIN", raising=False)
    monkeypatch.setenv("SANDBOX_STDIN_BLANK_LINES", "3")
    s = sandbox.sandbox_stdin_payload()
    assert s == "\n\n\n"


def test_sandbox_stdin_custom_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SANDBOX_STDIN", "a\\nb")
    assert sandbox.sandbox_stdin_payload() == "a\nb"
