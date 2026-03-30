from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_fallback() -> None:
    # AppV2/backend/workflow_runtime/config.py -> repo root is four levels up
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        os.environ.setdefault(key, value)


if load_dotenv is not None:
    load_dotenv()
else:
    _load_env_fallback()

# Repo root (…/MentorApp): same layout as App v1 + Graph Workflow notebook (models/gguf, VectorDB/…).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _resolve_chroma_dir() -> str:
    raw = os.getenv("MENTOR_APP_VECTOR_DB_PATH", "").strip()
    if raw:
        return str(Path(raw).expanduser().resolve())
    return str(_REPO_ROOT / "VectorDB" / "chroma_library_docs")


@dataclass(frozen=True)
class WorkflowConfig:
    llama_server_url: str = os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8081/v1").strip()
    llama_model: str = os.getenv("LLAMA_OPENAI_MODEL", "local-gguf").strip()
    llama_server_host: str = os.getenv("LLAMA_SERVER_HOST", "127.0.0.1").strip()
    llama_server_port: int = int(os.getenv("LLAMA_SERVER_PORT", "8081"))
    llama_server_ctx: int = int(os.getenv("LLAMA_SERVER_CTX", "8192"))
    llama_server_n_gpu_layers: int = int(os.getenv("LLAMA_SERVER_N_GPU_LAYERS", "999"))
    llama_server_threads: int = int(os.getenv("LLAMA_SERVER_THREADS", str(max(1, (os.cpu_count() or 4) - 1))))
    # Default false: Docker / CI have no llama-server binary; run llama-server on the host and connect.
    # Local one-click auto-spawn: set LLAMA_SERVER_AUTO_START=true (and LOCAL_GGUF_PATH, etc.).
    llama_server_auto_start: bool = _bool_env("LLAMA_SERVER_AUTO_START", False)
    llama_server_path: str = os.getenv("LLAMA_SERVER_PATH", "").strip()
    local_gguf_path: str = os.getenv("LOCAL_GGUF_PATH", "").strip()

    openrouter_api_key: str = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    reflection_model: str = os.getenv("OPENROUTER_REFLECTION_MODEL", "anthropic/claude-sonnet-4.6").strip()
    external_model: str = os.getenv("OPENROUTER_EXTERNAL_MODEL", "anthropic/claude-opus-4.6").strip()
    summarizer_model: str = os.getenv("OPENROUTER_SUMMARIZER_MODEL", "openai/gpt-oss-120b").strip()

    openrouter_http_referer: str = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
    openrouter_x_title: str = os.getenv("OPENROUTER_X_TITLE", "MentorApp").strip()

    execution_timeout_seconds: int = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "45"))
    http_timeout_seconds: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "120"))
    max_generation_tokens: int = int(os.getenv("MAX_GENERATION_TOKENS", "3000"))

    chroma_dir: str = _resolve_chroma_dir()
    collection_name: str = os.getenv("MENTOR_APP_VECTOR_COLLECTION", "library_docs").strip()
    embedding_model: str = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5").strip()
    reranker_model: str = os.getenv("RAG_RERANKER_MODEL", "BAAI/bge-reranker-base").strip()

    n_retrieve: int = int(os.getenv("RAG_N_RETRIEVE", "10"))
    n_rerank: int = int(os.getenv("RAG_N_RERANK", "3"))
    max_query_len: int = int(os.getenv("RAG_MAX_QUERY_LEN", "500"))

    langsmith_api_key: str = (os.getenv("LANGCHAIN_API_KEY") or "").strip()
    langsmith_project: str = os.getenv("LANGCHAIN_PROJECT", "MentorApp-LangGraph-SFT-Repair").strip()
    langsmith_endpoint: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com").strip()
    langsmith_enabled: bool = _bool_env("LANGSMITH_ENABLED", True)


CFG = WorkflowConfig()


def openrouter_headers() -> dict[str, str]:
    headers = {
        "HTTP-Referer": CFG.openrouter_http_referer,
        "X-Title": CFG.openrouter_x_title,
    }
    return {k: v for k, v in headers.items() if v}
