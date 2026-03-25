from __future__ import annotations

from typing import Any

from App.workflow_runtime.config import CFG

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
        return list(zip(docs, metas))
    except Exception:
        return []


def rerank_docs(query: str, candidates: list[tuple[str, dict[str, Any]]]) -> list[tuple[float, str, dict[str, Any]]]:
    if not candidates:
        return []

    reranker = get_reranker()
    if reranker is None:
        return [(0.5, doc, meta) for doc, meta in candidates[: CFG.n_rerank]]

    query_text = query[: CFG.max_query_len]
    pairs = [(query_text, doc) for doc, _ in candidates]
    try:
        scores = reranker.predict(pairs)
        scored = sorted(zip(scores, candidates), key=lambda item: item[0], reverse=True)
        return [
            (float(score), doc, meta)
            for score, (doc, meta) in scored[: CFG.n_rerank]
            if float(score) > 0.0
        ]
    except Exception:
        return [(0.5, doc, meta) for doc, meta in candidates[: CFG.n_rerank]]


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
            title = item.get("title", "")
            body = item.get("body", "")
            snippet = f"{title}: {body}" if title else body
            if snippet:
                snippets.append(snippet[:300])
        return snippets
    except Exception:
        return [
            "Official Python traceback guide: focus on final exception line and originating frame.",
            "Best practice: apply smallest diff that resolves failing tests/runtime.",
        ]
