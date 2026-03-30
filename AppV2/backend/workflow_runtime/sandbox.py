"""Sandboxed execution of candidate Python for grading (`run_checks`).

Prefers Docker (`docker run`) with no network and resource limits when available.
Falls back to in-process timeout-only execution only when explicitly allowed
(`SANDBOX_ALLOW_UNSAFE_FALLBACK=true`), for local dev without Docker socket.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import traceback as tb
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SANDBOX_LOG = logging.getLogger("AppV2.backend.workflow.sandbox")


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def docker_cli_available() -> bool:
    return shutil.which("docker") is not None


def sandbox_docker_enabled() -> bool:
    """Use Docker when CLI exists and SANBOX_USE_DOCKER is not false."""
    if not _bool("SANDBOX_USE_DOCKER", True):
        return False
    return docker_cli_available()


def sandbox_allow_unsafe_fallback() -> bool:
    return _bool("SANDBOX_ALLOW_UNSAFE_FALLBACK", False)


def _docker_socket_exists() -> bool:
    return Path("/var/run/docker.sock").exists()


def sandbox_image() -> str:
    return os.getenv("SANDBOX_PYTHON_IMAGE", "python:3.13-slim-bookworm").strip()


def sandbox_memory() -> str:
    return os.getenv("SANDBOX_MEMORY", "256m").strip()


def sandbox_cpus() -> float:
    try:
        return float(os.getenv("SANDBOX_CPUS", "0.5"))
    except ValueError:
        return 0.5


def run_python_in_docker(code: str, timeout: float) -> dict[str, Any]:
    """Run `code` in a throwaway container: network none, read-only workdir mount."""
    work = tempfile.mkdtemp(prefix="mentorapp_sbx_")
    host_file = Path(work) / "candidate.py"
    host_file.write_text(code, encoding="utf-8")
    inner = "/work/candidate.py"
    try:
        cmd = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "--memory",
            sandbox_memory(),
            "--cpus",
            str(sandbox_cpus()),
            "-v",
            f"{work}:/work:ro",
            sandbox_image(),
            "python",
            inner,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 5.0,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "returncode": proc.returncode,
            "mode": "docker",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Sandbox timeout ({timeout}s): {exc}",
            "returncode": -1,
            "mode": "docker",
        }
    except Exception as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Sandbox error: {exc}",
            "returncode": -1,
            "mode": "docker",
        }
    finally:
        try:
            shutil.rmtree(work, ignore_errors=True)
        except Exception:
            pass


def run_python_in_process(code: str, timeout: float) -> dict[str, Any]:
    """UNSAFE: run temp file with same interpreter as API (legacy behavior)."""
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as handle:
            handle.write(code)
            temp_path = handle.name
        proc = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "returncode": proc.returncode,
            "mode": "unsafe_host",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Execution timeout ({timeout}s): {exc}",
            "returncode": -1,
            "mode": "unsafe_host",
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def execute_python_after_compile(code: str, timeout: float) -> dict[str, Any]:
    """After successful `compile()`, run code and return runtime result dict."""
    if sandbox_docker_enabled() and _docker_socket_exists():
        result = run_python_in_docker(code, timeout)
        _SANDBOX_LOG.info(
            "sandbox exec mode=%s ok=%s",
            result.get("mode"),
            result.get("ok"),
            extra={
                "wf_kind": "sandbox",
                "wf_phase": "execute",
                "wf_agent": "docker",
                "wf_level": "INFO",
            },
        )
        return result

    if sandbox_allow_unsafe_fallback():
        logger.warning(
            "SANDBOX_ALLOW_UNSAFE_FALLBACK=true: executing candidate code on API host (not isolated)."
        )
        result = run_python_in_process(code, timeout)
        _SANDBOX_LOG.warning(
            "sandbox unsafe fallback mode=%s",
            result.get("mode"),
            extra={
                "wf_kind": "sandbox",
                "wf_phase": "execute",
                "wf_agent": "unsafe_host",
                "wf_level": "WARNING",
            },
        )
        return result

    # Docker expected but not available
    return {
        "ok": False,
        "stdout": "",
        "stderr": (
            "Sandbox unavailable: install Docker CLI, mount /var/run/docker.sock for the backend, "
            "or set SANDBOX_ALLOW_UNSAFE_FALLBACK=true for local dev only."
        ),
        "returncode": -1,
        "mode": "unavailable",
    }
