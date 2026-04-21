"""Sandbox env parsing: SANDBOX_USE_DOCKER must disable Docker path when set false."""

from __future__ import annotations

import os

import pytest

from AppV2.backend.workflow_runtime import sandbox


@pytest.fixture(autouse=True)
def restore_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Save/restore env keys touched by tests."""
    keys = ("SANDBOX_USE_DOCKER", "SANBOX_USE_DOCKER")
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for k in keys:
        if saved[k] is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, saved[k])


def test_sandbox_docker_respects_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SANDBOX_USE_DOCKER", "false")
    assert sandbox.sandbox_docker_enabled() is False


def test_sandbox_docker_default_true_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SANDBOX_USE_DOCKER", raising=False)
    # Still depends on docker CLI on PATH; only assert env gate is open.
    assert sandbox._bool("SANDBOX_USE_DOCKER", True) is True
