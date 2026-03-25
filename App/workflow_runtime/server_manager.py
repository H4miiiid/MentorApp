from __future__ import annotations

import atexit
import shutil
import subprocess
import time
from pathlib import Path

import requests

from App.workflow_runtime.config import CFG

_llama_server_proc: subprocess.Popen | None = None


def _health_url() -> str:
    base = CFG.llama_server_url.rstrip("/")
    return base.replace("/v1", "") + "/health"


def _health_ok(timeout: int = 2) -> bool:
    try:
        response = requests.get(_health_url(), timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def _resolve_server_executable() -> Path | None:
    if CFG.llama_server_path:
        p = Path(CFG.llama_server_path).expanduser().resolve()
        return p if p.exists() else None

    # 1) Look on PATH first.
    path_hit = shutil.which("llama-server") or shutil.which("llama-server.exe")
    if path_hit:
        return Path(path_hit).resolve()

    # 2) Check common local build output locations.
    candidates = [
        Path("llama.cpp/build/bin/Release/llama-server.exe").resolve(),
        Path("llama.cpp/build/bin/llama-server.exe").resolve(),
        Path("llama.cpp/build/bin/llama-server").resolve(),
        Path("llama.cpp/build/bin/Release/llama-server").resolve(),
        Path("App/llama.cpp/build/bin/Release/llama-server.exe").resolve(),
        Path("App/llama.cpp/build/bin/llama-server.exe").resolve(),
        Path("App/llama.cpp/build/bin/llama-server").resolve(),
        Path("App/llama.cpp/build/bin/Release/llama-server").resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    # 3) Fall back to recursive search under known build roots.
    for build_root in (Path("llama.cpp/build").resolve(), Path("App/llama.cpp/build").resolve()):
        if not build_root.exists():
            continue
        hits = [
            f
            for f in build_root.rglob("llama-server*")
            if f.is_file() and f.name.lower().startswith("llama-server")
        ]
        if hits:
            hits.sort(key=lambda p: len(str(p)))
            return hits[0]

    return None


def ensure_llama_server_running() -> None:
    global _llama_server_proc

    if _health_ok():
        return

    if not CFG.llama_server_auto_start:
        raise RuntimeError(
            f"Cannot connect to llama-server at {_health_url()} and LLAMA_SERVER_AUTO_START is disabled."
        )

    exe = _resolve_server_executable()
    if exe is None:
        raise RuntimeError(
            "Cannot auto-start llama-server: executable not found. "
            "Set LLAMA_SERVER_PATH, add llama-server to PATH, or build llama.cpp first."
        )

    if not CFG.local_gguf_path:
        raise RuntimeError(
            "Cannot auto-start llama-server: LOCAL_GGUF_PATH is empty. "
            "Set LOCAL_GGUF_PATH in .env to your .gguf file."
        )

    model_path = Path(CFG.local_gguf_path).expanduser().resolve()
    if not model_path.exists():
        raise RuntimeError(f"Cannot auto-start llama-server: LOCAL_GGUF_PATH not found: {model_path}")

    cmd = [
        str(exe),
        "--model",
        str(model_path),
        "--host",
        CFG.llama_server_host,
        "--port",
        str(CFG.llama_server_port),
        "--ctx-size",
        str(CFG.llama_server_ctx),
        "--n-gpu-layers",
        str(CFG.llama_server_n_gpu_layers),
        "--threads",
        str(CFG.llama_server_threads),
    ]

    _llama_server_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    for _ in range(90):
        time.sleep(1)
        if _health_ok():
            return

    raise RuntimeError(
        f"llama-server auto-start failed to become healthy at {_health_url()} within timeout."
    )


def stop_llama_server_if_managed() -> None:
    global _llama_server_proc
    if _llama_server_proc is None:
        return
    if _llama_server_proc.poll() is not None:
        _llama_server_proc = None
        return

    _llama_server_proc.terminate()
    try:
        _llama_server_proc.wait(timeout=5)
    except Exception:
        _llama_server_proc.kill()
    _llama_server_proc = None


atexit.register(stop_llama_server_if_managed)
