"""The sandbox must expose assignment-attached documents via ``ASSIGNMENT_DATA_DIR``
so student code can ``os.environ["ASSIGNMENT_DATA_DIR"]`` without hard-coding paths.

This covers the in-process (fallback) executor, which is what CI runs because the
Docker daemon is not available there. The Docker branch uses the same materializer
(``_materialize_data_files``) and mounts the same scratch dir, so this gives us
regression coverage of the contract even when Docker is off.
"""

from __future__ import annotations

from pathlib import Path

from AppV2.backend.workflow_runtime.sandbox import (
    ASSIGNMENT_DATA_ENV_VAR,
    run_python_in_process,
)


def test_in_process_sandbox_exposes_attached_data_files(tmp_path: Path) -> None:
    source = tmp_path / "file1.txt"
    source.write_text("hello-from-teacher\n", encoding="utf-8")

    code = (
        "import os\n"
        f"data_dir = os.environ['{ASSIGNMENT_DATA_ENV_VAR}']\n"
        "with open(os.path.join(data_dir, 'file1.txt')) as f:\n"
        "    print(f.read().strip())\n"
    )

    result = run_python_in_process(code, timeout=10.0, data_files=[(str(source), "file1.txt")])

    assert result["ok"] is True, result
    assert "hello-from-teacher" in (result.get("stdout") or ""), result


def test_in_process_sandbox_without_data_files_has_no_env_var() -> None:
    """Baseline: when no docs are attached, the env var must be absent so student
    code that depends on it gets a clean ``KeyError`` (not a stale path from CI)."""
    code = (
        "import os\n"
        f"print('missing' if '{ASSIGNMENT_DATA_ENV_VAR}' not in os.environ else 'present')\n"
    )

    result = run_python_in_process(code, timeout=10.0, data_files=None)

    assert result["ok"] is True, result
    assert "missing" in (result.get("stdout") or ""), result
