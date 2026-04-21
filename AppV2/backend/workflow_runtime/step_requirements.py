"""Workflow node requirements (audit reference for LangGraph grading).

Each node in `graph.py` may depend on sandbox execution, HF endpoint SFT (OpenAI-compatible),
OpenRouter API keys, Chroma RAG, or outbound web search. Use this map for
operations docs and optional preflight checks.
"""

from __future__ import annotations

from typing import Any, TypedDict


class NodeRequirement(TypedDict):
    """Human-readable requirements for one graph node."""

    node: str
    needs_sandbox: bool
    needs_endpoint_sft: bool
    needs_openrouter: bool
    needs_chroma_rag: bool
    needs_web_search: bool
    notes: str


# run_checks: compile + execute student code — must be isolated (Docker sandbox).
# SFT nodes: HF OpenAI-compatible inference endpoint.
# reflection_critic, external_expert_repair, summarize (when OpenRouter key set): OpenRouter.
# retrieve_local_docs, assess_local_context: Chroma + optional sentence-transformers on host.
# web_search_docs: duckduckgo-search (network).
NODE_REQUIREMENTS: list[NodeRequirement] = [
    {
        "node": "run_checks",
        "needs_sandbox": True,
        "needs_endpoint_sft": False,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Compiles and runs candidate Python; must not execute on the API host.",
    },
    {
        "node": "diagnose_failure",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Heuristic classification only.",
    },
    {
        "node": "choose_next_strategy",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Routing logic only.",
    },
    {
        "node": "attempt_sft_with_traceback",
        "needs_sandbox": False,
        "needs_endpoint_sft": True,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Fine-tuned repair via Hugging Face OpenAI-compatible endpoint (/v1).",
    },
    {
        "node": "retrieve_local_docs",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": False,
        "needs_chroma_rag": True,
        "needs_web_search": False,
        "notes": "Chroma persistent store; may return empty if DB missing or deps not installed.",
    },
    {
        "node": "assess_local_context",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": False,
        "needs_chroma_rag": True,
        "needs_web_search": False,
        "notes": "Reranker model (sentence-transformers) if available.",
    },
    {
        "node": "web_search_docs",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": True,
        "notes": "DuckDuckGo search; requires network egress.",
    },
    {
        "node": "summarize_context",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": True,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Uses OpenRouter summarizer when key set; otherwise heuristic bullets.",
    },
    {
        "node": "attempt_sft_with_rag",
        "needs_sandbox": False,
        "needs_endpoint_sft": True,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Endpoint SFT with RAG hints in prompt.",
    },
    {
        "node": "reflection_critic",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": True,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "OpenRouter reflection model; falls back to heuristics if no API key.",
    },
    {
        "node": "attempt_sft_with_reflection",
        "needs_sandbox": False,
        "needs_endpoint_sft": True,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Endpoint SFT with reflection JSON hints.",
    },
    {
        "node": "external_expert_repair",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": True,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "OpenRouter external model; falls back to heuristics if no API key.",
    },
    {
        "node": "finalize_success",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Terminal state.",
    },
    {
        "node": "finalize_failure",
        "needs_sandbox": False,
        "needs_endpoint_sft": False,
        "needs_openrouter": False,
        "needs_chroma_rag": False,
        "needs_web_search": False,
        "notes": "Terminal state.",
    },
]


def requirements_by_node() -> dict[str, NodeRequirement]:
    return {row["node"]: row for row in NODE_REQUIREMENTS}
