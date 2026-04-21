"""Stdout logging for Docker / uvicorn so `AppV2.backend.*` (grading worker, LangGraph) is visible.

Uvicorn configures its own loggers; application loggers still need the root (or a dedicated
handler) to emit at INFO to the container stdout.
"""

from __future__ import annotations

import logging
import os
import sys


def _parse_level(name: str) -> int:
    return getattr(logging, name.upper(), logging.INFO)


def configure_logging() -> None:
    level = _parse_level(os.getenv("APPV2_LOG_LEVEL", "INFO"))
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        stream=sys.stdout,
        force=True,
    )

    # Explicit levels for backend trees (grading worker, future LangGraph pipelines)
    for prefix in (
        "AppV2.backend",
        "AppV2.backend.grading",
        "AppV2.backend.api",
    ):
        logging.getLogger(prefix).setLevel(level)

    # LangGraph (future grading pipeline) — same as app. LangChain core can be chatty at INFO;
    # raise APPV2_LOG_LEVEL=DEBUG when you need full LC traces.
    logging.getLogger("langgraph").setLevel(level)
    if level > logging.DEBUG:
        for chatty in ("langchain", "langchain_core", "langsmith"):
            logging.getLogger(chatty).setLevel(logging.WARNING)
        # Hub / HTTP clients are noisy at INFO during embedding model downloads.
        for noisy in (
            "httpx",
            "httpcore",
            "huggingface_hub",
            "sentence_transformers",
            "openai",
            "chromadb",
        ):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    # Uvicorn: keep access/error visible at same level
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(level)
