from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class WorkflowConfig:
    llama_server_url: str = os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8081/v1").strip()
    llama_model: str = os.getenv("LLAMA_OPENAI_MODEL", "local-gguf").strip()

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

    chroma_dir: str = str(Path(os.getenv("MENTOR_APP_VECTOR_DB_PATH", "VectorDB/chroma_library_docs")).resolve())
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
