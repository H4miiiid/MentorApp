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
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SANDBOX_LOG = logging.getLogger("AppV2.backend.workflow.sandbox")


class SandboxUnavailableError(RuntimeError):
    """Raised when the sandbox infrastructure (Docker) is unusable.

    Distinguishes *infra* problems (daemon down, image cannot be pulled, socket missing)
    from *student* problems (syntax error, runtime crash). The grading graph must not
    run LLM repair loops on infra errors — the student's code was never actually executed.
    """


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def docker_cli_available() -> bool:
    return shutil.which("docker") is not None


def sandbox_docker_enabled() -> bool:
    """Use Docker when CLI exists and ``SANDBOX_USE_DOCKER`` is not false."""
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


def sandbox_stdin_payload() -> str | None:
    """Bytes/text fed to the sandboxed process stdin.

    Student code that calls ``input()`` would otherwise hit EOF immediately and fail with
    ``EOFError``, making correct-looking submissions look broken. Default: many blank lines
    so typical ``input()`` loops get empty strings.

    Set ``SANDBOX_STDIN`` to a literal string (use ``\\n`` in .env for newlines), or
    ``SANDBOX_STDIN_BLANK_LINES`` to change how many ``\\n`` characters are sent when
    ``SANDBOX_STDIN`` is unset.
    """
    # Distinguish unset (use blank lines) from explicit empty string in env.
    if "SANDBOX_STDIN" in os.environ and os.environ["SANDBOX_STDIN"].strip():
        return os.environ["SANDBOX_STDIN"].strip().replace("\\n", "\n")
    try:
        n = int(os.getenv("SANDBOX_STDIN_BLANK_LINES", "512"))
    except ValueError:
        n = 512
    n = max(0, n)
    if n == 0:
        return None
    return "\n" * n


def _image_exists_locally(image: str) -> bool:
    """True if the image is already pulled; avoids pull progress leaking into stderr."""
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _ensure_image_pulled(image: str) -> tuple[bool, str]:
    """Pull the sandbox image once (quiet). Returns (ok, stderr_on_failure)."""
    if _image_exists_locally(image):
        return True, ""
    try:
        proc = subprocess.run(
            ["docker", "pull", "--quiet", image],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode == 0:
            return True, ""
        return False, (proc.stderr or proc.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return False, f"Timed out pulling sandbox image {image!r}."
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"Failed to pull sandbox image {image!r}: {exc}"


def _force_kill_container(name: str) -> None:
    """Best-effort kill + remove of a container whose CLI client got SIGKILLed.

    Without this, `subprocess.run(..., timeout=T)` leaves the Docker *daemon* running the
    container forever (the --rm flag does not help because the container never exits).
    """
    try:
        subprocess.run(
            ["docker", "kill", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        pass
    try:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        pass


def _scratch_volume_config() -> tuple[str, str] | None:
    """Return ``(volume_name, scratch_dir_in_backend)`` when a shared named volume is
    configured for sibling-sandbox file sharing, else ``None``.

    This is required when the backend itself runs inside a container (docker-compose):
    the host Docker daemon cannot see ``/tmp/...`` inside the backend container, so
    ``-v /tmp/xxx:/work`` silently mounts an empty directory. The fix is to pre-mount a
    named volume into the backend *and* reference it by name (with ``volume-subpath``)
    when spawning each sandbox container. Both sides then see identical files.

    When the env vars are unset (e.g. pytest on a developer laptop with Docker on the
    host), we fall back to a plain bind mount of a host tempdir, which is the right
    behavior for that environment.
    """
    vol = (os.getenv("SANDBOX_SCRATCH_VOLUME") or "").strip()
    root = (os.getenv("SANDBOX_SCRATCH_DIR") or "").strip()
    if vol and root and Path(root).is_dir():
        return vol, root
    return None


def run_python_in_docker(code: str, timeout: float) -> dict[str, Any]:
    """Run `code` in a throwaway container: network none, read-only workdir mount.

    Stdin for ``input()`` is supplied via a file mounted into the container and shell
    redirection (``python ... < /work/_stdin.txt``). Feeding ``subprocess.run(input=...)``
    to the ``docker`` CLI often does **not** forward to the Python process inside the
    container, which caused false EOFError failures for correct student code.

    The container is named so we can force-kill it when Python's subprocess timeout
    fires: otherwise the daemon keeps running student code (e.g. ``while True: pass``)
    indefinitely and ``--rm`` cannot remove a still-running container.
    """
    image = sandbox_image()
    ok, pull_err = _ensure_image_pulled(image)
    if not ok:
        # Infra failure: tag as "unavailable" so run_checks / graph can short-circuit
        # instead of feeding a fake "traceback" to the LLM repair loop.
        return {
            "ok": False,
            "stdout": "",
            "stderr": pull_err or f"Could not pull sandbox image {image!r}.",
            "returncode": -1,
            "mode": "unavailable",
        }

    scratch = _scratch_volume_config()
    if scratch is not None:
        volume_name, scratch_root = scratch
        work = tempfile.mkdtemp(prefix="sbx_", dir=scratch_root)
        subpath = Path(work).name
        mount_args = [
            "--mount",
            f"type=volume,source={volume_name},destination=/work,volume-subpath={subpath},readonly",
        ]
    else:
        work = tempfile.mkdtemp(prefix="mentorapp_sbx_")
        mount_args = ["-v", f"{work}:/work:ro"]
    container_name = f"mentorapp-sbx-{uuid.uuid4().hex[:12]}"
    try:
        host_file = Path(work) / "candidate.py"
        host_file.write_text(code, encoding="utf-8")
        stdin_payload = sandbox_stdin_payload()
        if stdin_payload is not None:
            (Path(work) / "_stdin.txt").write_text(stdin_payload, encoding="utf-8")

        # Shell runs inside the container so `<` attaches the file to Python's stdin reliably.
        if stdin_payload is None:
            inner_sh = "exec python /work/candidate.py"
        else:
            inner_sh = "exec python /work/candidate.py < /work/_stdin.txt"

        cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "-e",
            "MPLBACKEND=Agg",
            "--network",
            "none",
            "--memory",
            sandbox_memory(),
            "--cpus",
            str(sandbox_cpus()),
            "--stop-timeout",
            "1",
            *mount_args,
            image,
            "sh",
            "-c",
            inner_sh,
        ]
        run_kw: dict[str, Any] = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout + 5.0,
        }
        try:
            proc = subprocess.run(cmd, **run_kw)
        except subprocess.TimeoutExpired as exc:
            _force_kill_container(container_name)
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Sandbox timeout ({timeout}s): {exc}",
                "returncode": -1,
                "mode": "docker",
            }
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "returncode": proc.returncode,
            "mode": "docker",
        }
    except Exception as exc:
        # Any other failure (docker daemon dead, mount fails, etc.): try to clean up the
        # container if it was ever registered, then report.
        _force_kill_container(container_name)
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
        stdin_payload = sandbox_stdin_payload()
        run_kw: dict[str, Any] = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout,
        }
        if stdin_payload is not None:
            run_kw["input"] = stdin_payload
        proc = subprocess.run([sys.executable, temp_path], **run_kw)
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
