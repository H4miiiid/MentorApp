from __future__ import annotations

import json
import re
import time
from typing import Any

import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from AppV2.backend.workflow_runtime.config import CFG, openrouter_headers
from AppV2.backend.workflow_runtime.observability import setup_langsmith, traceable
from AppV2.backend.workflow_runtime.server_manager import ensure_llama_server_running
from AppV2.backend.workflow_runtime.state import extract_failure_signature


def llama_health_url_from_openai_base(openai_base_url: str) -> str:
    """Derive llama.cpp ``/health`` URL from an OpenAI-compatible base URL."""
    base = openai_base_url.rstrip("/")
    return base.replace("/v1", "") + "/health"


def models_url_from_openai_base(openai_base_url: str) -> str:
    """Derive an OpenAI-compatible ``/models`` URL from a base URL."""
    base = openai_base_url.rstrip("/")
    return base + "/models" if base.endswith("/v1") else base + "/v1/models"


def sft_auth_headers() -> dict[str, str]:
    """Return bearer auth headers for protected endpoints when configured."""
    token = (CFG.sft_api_key or "").strip()
    if not token or token == "llama.cpp":
        return {}
    return {"Authorization": f"Bearer {token}"}


def ensure_llama_server_available() -> None:
    """Verify the SFT endpoint is reachable.

    Probe order:
    1) ``/health`` for llama.cpp-style servers
    2) ``/v1/models`` for OpenAI-compatible endpoints (HF, etc.)
    """
    setup_langsmith()
    health_url = llama_health_url_from_openai_base(CFG.llama_server_url)
    models_url = models_url_from_openai_base(CFG.llama_server_url)
    headers = sft_auth_headers()

    if CFG.llama_server_auto_start:
        ensure_llama_server_running()

    max_attempts = 6
    sleep_seconds = 5
    transient_statuses = {429, 500, 502, 503, 504}
    health_status = ""
    models_status = ""

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(health_url, timeout=3, headers=headers)
            health_status = f"HTTP {response.status_code}"
            if response.status_code == 200:
                return
            if response.status_code in {401, 403}:
                break
        except Exception as exc:
            health_status = f"ERROR {exc}"

        try:
            response = requests.get(models_url, timeout=5, headers=headers)
            models_status = f"HTTP {response.status_code}"
            if response.status_code == 200:
                return
            if response.status_code in {401, 403}:
                break
        except Exception as exc:
            models_status = f"ERROR {exc}"

        health_retryable = any(f"HTTP {code}" == health_status for code in transient_statuses) or health_status.startswith(
            "ERROR "
        )
        models_retryable = any(f"HTTP {code}" == models_status for code in transient_statuses) or models_status.startswith(
            "ERROR "
        )
        should_retry = health_retryable or models_retryable

        if attempt < max_attempts and should_retry:
            time.sleep(sleep_seconds)
            continue
        break

    token_hint = (
        " Set HF_TOKEN in AppV2/.env if your Hugging Face endpoint is protected."
        if not headers
        else " Verify HF_TOKEN/endpoint token is valid for this endpoint."
    )

    raise RuntimeError(
        f"SFT endpoint preflight failed for base URL {CFG.llama_server_url!r}. "
        f"Probe {health_url} -> {health_status}; probe {models_url} -> {models_status}. "
        "Verify HF_INFERENCE_BASE_URL or LLAMA_SERVER_URL points to your OpenAI-compatible /v1 endpoint."
        + token_hint
    )


def ensure_hf_endpoint_available() -> None:
    """Compatibility wrapper for HF-named call sites."""
    ensure_llama_server_available()


def get_sft_llm() -> ChatOpenAI:
    from AppV2.backend.grading.grading_model_service import get_active_openai_model_name

    model_name = get_active_openai_model_name()
    return ChatOpenAI(
        base_url=CFG.llama_server_url,
        api_key=CFG.sft_api_key,
        model=model_name,
        temperature=0.1,
        max_tokens=CFG.max_generation_tokens,
        timeout=CFG.http_timeout_seconds,
    )


def get_reflection_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=CFG.openrouter_base_url,
        api_key=CFG.openrouter_api_key,
        default_headers=openrouter_headers(),
        model=CFG.reflection_model,
        temperature=0.1,
        max_tokens=700,
        timeout=CFG.http_timeout_seconds,
    )


def get_external_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=CFG.openrouter_base_url,
        api_key=CFG.openrouter_api_key,
        default_headers=openrouter_headers(),
        model=CFG.external_model,
        temperature=0.1,
        max_tokens=CFG.max_generation_tokens,
        timeout=CFG.http_timeout_seconds,
    )


def get_summarizer_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=CFG.openrouter_base_url,
        api_key=CFG.openrouter_api_key,
        default_headers=openrouter_headers(),
        model=CFG.summarizer_model,
        temperature=0.0,
        max_tokens=400,
        timeout=CFG.http_timeout_seconds,
    )


SFT_REPAIR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a code repair model. Apply minimal edits only. "
            "Fix code so it compiles and runs. Do not rewrite unrelated parts. "
            "Return ONLY corrected code wrapped in <correct_code> tags.",
        ),
        (
            "human",
            "{context}\n\nCURRENT_CODE:\n{code}\n\n<correct_code>",
        ),
    ]
)

REFLECTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a strict Python code critic. Return ONLY valid JSON "
            "with keys: diagnosis, hints, do_not_do, confidence. "
            "Output raw JSON only and do not return repaired code.",
        ),
        (
            "human",
            "Traceback:\n{traceback}\n\nCurrent code:\n{code}\n\nRecent attempts:\n{attempts}",
        ),
    ]
)

EXTERNAL_EXPERT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a careful Python repair assistant. Return only corrected code "
            "wrapped in <correct_code> tags. Keep edits as small as possible.",
        ),
        (
            "human",
            "TRACEBACK:\n{traceback}\n\nCURRENT_CODE:\n{code}\n\n<correct_code>",
        ),
    ]
)

RAG_SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a concise technical summarizer. Return only bullet lines that start with '- '. "
            "Maximum 3 bullets, each one sentence, focused on the exact error.",
        ),
        (
            "human",
            "Error: {error}\n\nDocumentation snippets:\n{docs}",
        ),
    ]
)


def extract_current_code_from_prompt(prompt: str) -> str:
    marker = "CURRENT_CODE:\n"
    idx = prompt.find(marker)
    return prompt[idx + len(marker) :].strip() if idx != -1 else prompt


def extract_code_block(text: str) -> str:
    if not text:
        return text

    tag_match = re.search(r"<correct_code>(.*?)(?:</correct_code>|$)", text, re.DOTALL)
    if tag_match:
        return tag_match.group(1).strip()

    fenced = re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced[0].strip()

    return text.strip()


def heuristic_minimal_fix(code: str, context: str) -> str:
    fixed = code.replace("pritn(", "print(")
    fixed_lines: list[str] = []
    block_keywords = (
        "def ",
        "if ",
        "for ",
        "while ",
        "class ",
        "elif ",
        "else",
        "try",
        "except",
        "finally",
    )
    for line in fixed.splitlines():
        stripped = line.strip()
        needs_colon = (
            any(stripped.startswith(keyword) for keyword in block_keywords)
            and not stripped.endswith(":")
            and not stripped.startswith("#")
        )
        fixed_lines.append(line + ":" if needs_colon else line)

    fixed = "\n".join(fixed_lines)
    if "NameError: name 'np' is not defined" in context and "import numpy as np" not in fixed:
        fixed = "import numpy as np\n" + fixed
    return fixed


@traceable(name="call_sft_model", run_type="llm")
def call_sft_model(prompt: str) -> str:
    setup_langsmith()
    original_code = extract_current_code_from_prompt(prompt)
    context = ""
    code = original_code

    if "CURRENT_CODE:" in prompt:
        parts = prompt.split("CURRENT_CODE:", 1)
        context = parts[0]
        code = parts[1].strip()

    try:
        chain = SFT_REPAIR_PROMPT | get_sft_llm().bind(stop=["</correct_code>"]) | StrOutputParser()
        result = chain.invoke(
            {"context": context, "code": code},
            config={"run_name": "sft_repair", "tags": ["mentorapp", "sft", "workflow"]},
        )
        candidate = extract_code_block(result)
        if candidate:
            return candidate
    except Exception:
        pass

    return heuristic_minimal_fix(original_code, prompt)


@traceable(name="call_reflection_model", run_type="llm")
def call_reflection_model(current_code: str, traceback_text: str, attempt_history: list[dict[str, Any]]) -> dict[str, Any]:
    setup_langsmith()
    fallback = {
        "diagnosis": extract_failure_signature(traceback_text),
        "hints": ["Focus on the top traceback line.", "Apply the smallest change that fixes the failure."],
        "do_not_do": ["No full rewrites"],
        "confidence": 0.35,
    }

    if not CFG.openrouter_api_key:
        return fallback

    try:
        chain = REFLECTION_PROMPT | get_reflection_llm() | StrOutputParser()
        result = chain.invoke(
            {
                "traceback": traceback_text,
                "code": current_code,
                "attempts": str(attempt_history[-3:]),
            },
            config={"run_name": "reflection_critic", "tags": ["mentorapp", "reflection", "workflow"]},
        )
        raw = (result or "").strip()
        if not raw:
            return fallback

        raw = re.sub(r"^```(?:json)?\n|\n```$", "", raw.strip(), flags=re.IGNORECASE)
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        parsed = json.loads(match.group(0) if match else raw)
        if not isinstance(parsed, dict):
            return fallback

        parsed.setdefault("diagnosis", fallback["diagnosis"])
        parsed.setdefault("hints", fallback["hints"])
        parsed.setdefault("do_not_do", fallback["do_not_do"])
        parsed.setdefault("confidence", fallback["confidence"])
        if not isinstance(parsed.get("hints"), list):
            parsed["hints"] = fallback["hints"]
        if not isinstance(parsed.get("do_not_do"), list):
            parsed["do_not_do"] = fallback["do_not_do"]
        return parsed
    except Exception:
        return fallback


@traceable(name="call_external_model", run_type="llm")
def call_external_model(prompt: str) -> str:
    setup_langsmith()
    original_code = extract_current_code_from_prompt(prompt)

    if not CFG.openrouter_api_key:
        return heuristic_minimal_fix(original_code, prompt)

    traceback_text = ""
    if "TRACEBACK:" in prompt and "CURRENT_CODE:" in prompt:
        start = prompt.find("TRACEBACK:") + len("TRACEBACK:")
        end = prompt.find("CURRENT_CODE:")
        traceback_text = prompt[start:end].strip() if end > start else ""

    try:
        chain = EXTERNAL_EXPERT_PROMPT | get_external_llm().bind(stop=["</correct_code>"]) | StrOutputParser()
        result = chain.invoke(
            {"traceback": traceback_text, "code": original_code},
            config={"run_name": "external_expert", "tags": ["mentorapp", "external", "workflow"]},
        )
        candidate = extract_code_block(result)
        if candidate:
            return candidate
    except Exception:
        pass

    return heuristic_minimal_fix(original_code, prompt)


@traceable(name="summarize_docs_to_hints", run_type="chain")
def summarize_docs_to_hints(reranked_docs: list[tuple[float, str, dict[str, Any]]], error_text: str) -> str:
    setup_langsmith()
    if not reranked_docs:
        return ""

    if not CFG.openrouter_api_key:
        bullets = []
        for _, doc, _ in reranked_docs[:3]:
            first_line = doc.strip().splitlines()[0] if doc.strip() else ""
            if first_line:
                bullets.append(f"- {first_line[:150]}")
        return "\n".join(bullets[:3])

    docs_text = "\n---\n".join(
        [
            f"[{meta.get('library', 'unknown')} v{meta.get('version', '?')} score={score:.2f}]\n{doc}"
            for score, doc, meta in reranked_docs
        ]
    )

    error_lines = [line.strip() for line in error_text.splitlines() if line.strip()]
    error_line = error_lines[-1] if error_lines else error_text[:200]

    try:
        chain = RAG_SUMMARIZE_PROMPT | get_summarizer_llm() | StrOutputParser()
        content = chain.invoke(
            {"error": error_line, "docs": docs_text},
            config={"run_name": "rag_summarize", "tags": ["mentorapp", "rag", "workflow"]},
        )
        bullets = [line.strip() for line in content.split("\n") if line.strip().startswith("- ")][:3]
        return "\n".join(bullets) if bullets else content.strip()
    except Exception:
        return ""
