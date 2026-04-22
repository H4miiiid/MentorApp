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
from typing import Any, Sequence

logger = logging.getLogger(__name__)

_SANDBOX_LOG = logging.getLogger("AppV2.backend.workflow.sandbox")


# ``SandboxDataFile`` is how callers pass assignment resources (datasets, reference
# documents) into the sandbox. The tuple is (host_path, name_inside_data_dir).
# We keep it as a plain tuple to avoid a circular dep on db models and so tests
# can construct them with bare file paths.
SandboxDataFile = tuple[str, str]
"""(absolute source path on host, target filename inside /work/data/)."""

ASSIGNMENT_DATA_ENV_VAR = "ASSIGNMENT_DATA_DIR"
_CONTAINER_DATA_DIR = "/work/data"


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
    """Image used by `docker run` for each student submission.

    Default is the dedicated ``mentorapp-sandbox:latest`` image built from
    ``AppV2/sandbox/Dockerfile`` (via the ``sandbox-image`` service in
    ``docker-compose.yml``). It ships a curated data-science stack — numpy,
    pandas, scipy, scikit-learn, matplotlib, seaborn, pyarrow, lxml, Pillow,
    statsmodels, sympy, networkx, requests, openpyxl, tqdm — so common course
    assignments don't crash with ``ModuleNotFoundError``.

    Override with ``SANDBOX_PYTHON_IMAGE`` (e.g. ``python:3.13-slim-bookworm``
    for a minimal stdlib-only runtime or a fully custom image you maintain).
    """
    return os.getenv("SANDBOX_PYTHON_IMAGE", "mentorapp-sandbox:latest").strip()


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


def _safe_data_filename(name: str) -> str:
    """Strip path components from caller-supplied names before mounting into the sandbox."""
    base = Path(name or "").name or "data"
    return base[:200]


def _materialize_data_files(
    work: Path, data_files: Sequence[SandboxDataFile] | None
) -> bool:
    """Copy caller-supplied data files into ``{work}/data``.

    Returns True when at least one file was copied (so the caller knows to set
    ``ASSIGNMENT_DATA_DIR``). Silently skips entries whose source doesn't exist
    — the sandbox should still run the student's code even if a teacher deletes
    a file between upload and grading.
    """
    if not data_files:
        return False
    data_dir = work / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for raw_src, raw_name in data_files:
        src = Path(raw_src)
        if not src.is_file():
            logger.warning("sandbox: skipping missing data file %s", src)
            continue
        dst_name = _safe_data_filename(raw_name) or src.name
        dst = data_dir / dst_name
        try:
            shutil.copyfile(src, dst)
            copied += 1
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("sandbox: failed to copy data file %s -> %s (%s)", src, dst, exc)
    return copied > 0


def run_python_in_docker(
    code: str,
    timeout: float,
    *,
    data_files: Sequence[SandboxDataFile] | None = None,
) -> dict[str, Any]:
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

        has_data = _materialize_data_files(Path(work), data_files)

        # Shell runs inside the container so `<` attaches the file to Python's stdin reliably.
        if stdin_payload is None:
            inner_sh = "exec python /work/candidate.py"
        else:
            inner_sh = "exec python /work/candidate.py < /work/_stdin.txt"

        env_args: list[str] = ["-e", "MPLBACKEND=Agg"]
        if has_data:
            # Students read attached resources via this env var (see Note banner on the
            # submission page). The directory is read-only because the scratch mount is.
            env_args.extend(["-e", f"{ASSIGNMENT_DATA_ENV_VAR}={_CONTAINER_DATA_DIR}"])

        cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            *env_args,
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


def run_python_in_process(
    code: str,
    timeout: float,
    *,
    data_files: Sequence[SandboxDataFile] | None = None,
) -> dict[str, Any]:
    """UNSAFE: run temp file with same interpreter as API (legacy behavior).

    Supports the same ``ASSIGNMENT_DATA_DIR`` contract as the Docker sandbox so student
    code that reads from ``os.environ["ASSIGNMENT_DATA_DIR"]`` works identically in the
    dev fallback. The data directory is created as a sibling of the candidate script.
    """
    temp_path: str | None = None
    data_workdir: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as handle:
            handle.write(code)
            temp_path = handle.name

        env = os.environ.copy()
        if data_files:
            data_workdir = tempfile.mkdtemp(prefix="mentorapp_data_")
            copied = _materialize_data_files(Path(data_workdir), data_files)
            if copied:
                env[ASSIGNMENT_DATA_ENV_VAR] = str(Path(data_workdir) / "data")

        stdin_payload = sandbox_stdin_payload()
        run_kw: dict[str, Any] = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout,
            "env": env,
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
        if data_workdir:
            shutil.rmtree(data_workdir, ignore_errors=True)


def execute_python_after_compile(
    code: str,
    timeout: float,
    *,
    data_files: Sequence[SandboxDataFile] | None = None,
) -> dict[str, Any]:
    """After successful `compile()`, run code and return runtime result dict.

    ``data_files`` is an optional list of ``(host_path, target_name)`` tuples to
    expose to the student code via ``ASSIGNMENT_DATA_DIR``. Used for assignment-
    attached documents/datasets the teacher uploaded in the Documents tab.
    """
    if sandbox_docker_enabled() and _docker_socket_exists():
        result = run_python_in_docker(code, timeout, data_files=data_files)
        _SANDBOX_LOG.info(
            "sandbox exec mode=%s ok=%s data_files=%s",
            result.get("mode"),
            result.get("ok"),
            len(data_files) if data_files else 0,
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
        result = run_python_in_process(code, timeout, data_files=data_files)
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
