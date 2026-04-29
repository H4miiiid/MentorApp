from __future__ import annotations

import logging
from typing import Any

from AppV2.backend.workflow_runtime.config import CFG

try:
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except Exception:  # pragma: no cover
    chromadb = None
    SentenceTransformerEmbeddingFunction = None

try:
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover
    CrossEncoder = None

try:
    from ddgs import DDGS

    DDGS_AVAILABLE = True
except Exception:  # pragma: no cover
    DDGS_AVAILABLE = False


_chroma_collection = None
_reranker = None
logger = logging.getLogger(__name__)


def _sanitize_doc_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = text.replace("\x00", " ")
    cleaned = "".join(ch if (ord(ch) >= 32 or ch in "\n\t") else " " for ch in cleaned)
    return cleaned.strip()


def get_chroma_collection():
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection

    if chromadb is None or SentenceTransformerEmbeddingFunction is None:
        return None

    try:
        embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=CFG.embedding_model,
            device="cpu",
            normalize_embeddings=True,
        )
        client = chromadb.PersistentClient(path=CFG.chroma_dir)
        _chroma_collection = client.get_collection(
            name=CFG.collection_name,
            embedding_function=embedding_fn,
        )
        return _chroma_collection
    except Exception:
        return None


def get_reranker():
    global _reranker
    if _reranker is not None:
        return _reranker

    if CrossEncoder is None:
        return None

    try:
        _reranker = CrossEncoder(CFG.reranker_model, max_length=512)
        return _reranker
    except Exception:
        return None


def retrieve_from_vector_db(query: str) -> list[tuple[str, dict[str, Any]]]:
    collection = get_chroma_collection()
    if collection is None:
        return []

    query_text = query[: CFG.max_query_len]
    try:
        result = collection.query(
            query_texts=[query_text],
            n_results=CFG.n_retrieve,
            include=["documents", "metadatas"],
        )
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        if len(docs) != len(metas):
            logger.warning("[rag-retrieve] docs/metadatas length mismatch docs=%s metas=%s", len(docs), len(metas))
        size = min(len(docs), len(metas))
        pairs: list[tuple[str, dict[str, Any]]] = []
        for idx in range(size):
            safe_doc = _sanitize_doc_text(docs[idx])
            if not safe_doc:
                continue
            meta = metas[idx] if isinstance(metas[idx], dict) else {}
            pairs.append((safe_doc, meta))
        return pairs
    except Exception:
        return []


def rerank_docs(query: str, candidates: list[tuple[str, dict[str, Any]]]) -> list[tuple[float, str, dict[str, Any]]]:
    if not candidates:
        return []

    reranker = get_reranker()
    if reranker is None:
        return [(0.5, _sanitize_doc_text(doc), meta if isinstance(meta, dict) else {}) for doc, meta in candidates[: CFG.n_rerank]]

    query_text = query[: CFG.max_query_len]
    pairs = [(query_text, _sanitize_doc_text(doc)) for doc, _ in candidates]
    try:
        scores = reranker.predict(pairs)
        scored = sorted(zip(scores, candidates), key=lambda item: item[0], reverse=True)
        out: list[tuple[float, str, dict[str, Any]]] = []
        for score, (doc, meta) in scored[: CFG.n_rerank]:
            text = _sanitize_doc_text(doc)
            if not text:
                continue
            out.append((float(score), text, meta if isinstance(meta, dict) else {}))
        return out
    except Exception:
        return [(0.5, _sanitize_doc_text(doc), meta if isinstance(meta, dict) else {}) for doc, meta in candidates[: CFG.n_rerank]]


def web_search(query: str, max_results: int = 5) -> list[str]:
    if not DDGS_AVAILABLE:
        return [
            "Official Python traceback guide: focus on final exception line and originating frame.",
            "Best practice: apply smallest diff that resolves failing tests/runtime.",
        ]

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"python {query} fix solution", max_results=max_results))
        snippets: list[str] = []
        for item in results:
            title = _sanitize_doc_text(item.get("title", ""))
            body = _sanitize_doc_text(item.get("body", ""))
            snippet = f"{title}: {body}" if title else body
            if snippet:
                if len(snippet) > 300:
                    clipped = snippet[:300]
                    ws = clipped.rfind(" ")
                    snippet = clipped[:ws] if ws > 120 else clipped
                snippets.append(snippet)
        return snippets
    except Exception:
        return [
            "Official Python traceback guide: focus on final exception line and originating frame.",
            "Best practice: apply smallest diff that resolves failing tests/runtime.",
        ]
