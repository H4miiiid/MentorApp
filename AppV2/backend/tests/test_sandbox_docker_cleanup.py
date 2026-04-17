"""Regression tests for the Docker sandbox.

Covers two previously undetected bugs:

1. On ``subprocess.TimeoutExpired``, the CLI client was SIGKILL'd but the container kept
   running on the Docker daemon (infinite loops leaked forever). The fix names the
   container with ``--name`` and force-kills it on timeout.
2. On first use, ``docker run`` printed pull progress to stderr, which then ended up in
   the student traceback. The fix pre-pulls the image via ``docker pull --quiet`` so the
   run's stderr stays clean.

These tests do not require Docker: they monkeypatch ``subprocess.run`` and record the
commands that the sandbox would have issued.
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

from AppV2.backend.workflow_runtime import sandbox


class _FakeProc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture(autouse=True)
def _stable_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic stdin payload so docker cmdline is predictable."""
    monkeypatch.setenv("SANDBOX_STDIN_BLANK_LINES", "0")
    monkeypatch.delenv("SANDBOX_STDIN", raising=False)


def _install_fake_run(monkeypatch: pytest.MonkeyPatch, responses):
    """Install a ``subprocess.run`` replacement.

    ``responses`` is a callable (cmd, kwargs) -> _FakeProc | raises.
    Records every call in ``calls`` (returned list) in order.
    """
    calls: list[list[str]] = []

    def _run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        return responses(cmd, kwargs)

    monkeypatch.setattr(sandbox.subprocess, "run", _run)
    return calls


def test_image_inspect_skips_pull_when_image_present(monkeypatch: pytest.MonkeyPatch) -> None:
    def responder(cmd: list[str], kwargs: dict[str, Any]) -> _FakeProc:
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _FakeProc(returncode=0)
        if cmd[:2] == ["docker", "pull"]:
            raise AssertionError("pull should be skipped when image is already local")
        if cmd[:2] == ["docker", "run"]:
            return _FakeProc(returncode=0, stdout="hi\n", stderr="")
        raise AssertionError(f"unexpected command {cmd}")

    calls = _install_fake_run(monkeypatch, responder)
    result = sandbox.run_python_in_docker("print('hi')", timeout=5.0)

    assert result["ok"] is True
    assert result["stdout"] == "hi\n"
    assert result["stderr"] == ""
    assert any(c[:3] == ["docker", "image", "inspect"] for c in calls)
    assert not any(c[:2] == ["docker", "pull"] for c in calls)


def test_image_pulled_quietly_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def responder(cmd: list[str], kwargs: dict[str, Any]) -> _FakeProc:
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _FakeProc(returncode=1, stderr="no such image")
        if cmd[:2] == ["docker", "pull"]:
            assert "--quiet" in cmd, "pull must be quiet to avoid polluting stderr"
            return _FakeProc(returncode=0)
        if cmd[:2] == ["docker", "run"]:
            return _FakeProc(returncode=0, stdout="42\n", stderr="")
        raise AssertionError(f"unexpected command {cmd}")

    calls = _install_fake_run(monkeypatch, responder)
    result = sandbox.run_python_in_docker("print(42)", timeout=5.0)

    assert result["ok"] is True
    assert "Pulling" not in result["stderr"]
    assert any(c[:2] == ["docker", "pull"] and "--quiet" in c for c in calls)


def test_pull_failure_is_reported_without_running(monkeypatch: pytest.MonkeyPatch) -> None:
    def responder(cmd: list[str], kwargs: dict[str, Any]) -> _FakeProc:
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _FakeProc(returncode=1)
        if cmd[:2] == ["docker", "pull"]:
            return _FakeProc(returncode=1, stderr="unauthorized")
        if cmd[:2] == ["docker", "run"]:
            raise AssertionError("run must be skipped when image pull fails")
        raise AssertionError(f"unexpected command {cmd}")

    _install_fake_run(monkeypatch, responder)
    result = sandbox.run_python_in_docker("print(1)", timeout=5.0)

    assert result["ok"] is False
    assert "unauthorized" in result["stderr"]
    # Pull failure is an infra error, not a student error: mode must be "unavailable"
    # so run_checks short-circuits instead of invoking the LLM repair loop.
    assert result["mode"] == "unavailable"


def test_docker_run_uses_named_container(monkeypatch: pytest.MonkeyPatch) -> None:
    """`docker run` must include --name so we can force-kill on timeout."""
    captured: dict[str, str] = {}

    def responder(cmd: list[str], kwargs: dict[str, Any]) -> _FakeProc:
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _FakeProc(returncode=0)
        if cmd[:2] == ["docker", "run"]:
            assert "--name" in cmd, "docker run must pass --name"
            idx = cmd.index("--name")
            captured["name"] = cmd[idx + 1]
            assert captured["name"].startswith("mentorapp-sbx-")
            assert "--network" in cmd and "none" in cmd
            assert "--rm" in cmd
            return _FakeProc(returncode=0)
        raise AssertionError(f"unexpected command {cmd}")

    _install_fake_run(monkeypatch, responder)
    result = sandbox.run_python_in_docker("print('x')", timeout=5.0)
    assert result["ok"] is True
    assert captured.get("name", "").startswith("mentorapp-sbx-")


def test_timeout_force_kills_container(monkeypatch: pytest.MonkeyPatch) -> None:
    """Previously, a timeout left the container running on the Docker daemon."""
    captured_name: dict[str, str] = {}
    kill_calls: list[str] = []

    def responder(cmd: list[str], kwargs: dict[str, Any]) -> _FakeProc:
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _FakeProc(returncode=0)
        if cmd[:2] == ["docker", "run"]:
            idx = cmd.index("--name")
            captured_name["name"] = cmd[idx + 1]
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 0))
        if cmd[:2] == ["docker", "kill"]:
            kill_calls.append(cmd[2])
            return _FakeProc(returncode=0)
        if cmd[:3] == ["docker", "rm", "-f"]:
            kill_calls.append(f"rm:{cmd[3]}")
            return _FakeProc(returncode=0)
        raise AssertionError(f"unexpected command {cmd}")

    _install_fake_run(monkeypatch, responder)
    result = sandbox.run_python_in_docker("while True: pass", timeout=1.0)

    assert result["ok"] is False
    assert result["returncode"] == -1
    assert "timeout" in result["stderr"].lower()
    assert captured_name["name"] in kill_calls, (
        "expected docker kill <name> after TimeoutExpired to avoid zombie container"
    )


def test_temp_dir_cleaned_even_when_run_raises(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """If docker run raises a non-timeout error, the work dir must still be removed."""

    created_dirs: list[str] = []
    real_mkdtemp = sandbox.tempfile.mkdtemp

    def _mkdtemp(*args: Any, **kwargs: Any) -> str:
        path = real_mkdtemp(*args, **kwargs)
        created_dirs.append(path)
        return path

    monkeypatch.setattr(sandbox.tempfile, "mkdtemp", _mkdtemp)

    def responder(cmd: list[str], kwargs: dict[str, Any]) -> _FakeProc:
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _FakeProc(returncode=0)
        if cmd[:2] == ["docker", "run"]:
            raise RuntimeError("boom")
        if cmd[:2] == ["docker", "kill"] or cmd[:3] == ["docker", "rm", "-f"]:
            return _FakeProc(returncode=0)
        raise AssertionError(f"unexpected command {cmd}")

    _install_fake_run(monkeypatch, responder)
    result = sandbox.run_python_in_docker("print(1)", timeout=1.0)
    assert result["ok"] is False
    assert "boom" in result["stderr"]

    import os

    for d in created_dirs:
        assert not os.path.exists(d), f"leaked sandbox temp dir: {d}"
