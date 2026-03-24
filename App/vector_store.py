from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any

from .config import settings


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def ingest_library_document(
    *,
    library_name: str,
    library_version: str,
    source_title: str,
    content: str,
    professor_id: int,
) -> list[str]:
    try:
        import chromadb
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "chromadb is required for vector ingestion. Install it and retry."
        ) from exc

    chunks = _chunk_text(content)
    if not chunks:
        raise ValueError("Documentation content is empty.")

    ingested_at = _now_iso()
    total = len(chunks)

    client = chromadb.PersistentClient(path=settings.vector_db_path)
    collection = client.get_or_create_collection(name=settings.vector_collection_name)

    ids: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for index, chunk in enumerate(chunks):
        stable_key = (
            f"{library_name}|{library_version}|{source_title}|{index}|"
            f"{hashlib.sha1(chunk.encode('utf-8')).hexdigest()}"
        )
        vector_id = hashlib.sha1(stable_key.encode("utf-8")).hexdigest()
        ids.append(vector_id)

        metadatas.append(
            {
                "library_name": library_name,
                "library_version": library_version,
                "source_title": source_title,
                "chunk_index": index,
                "chunk_total": total,
                "professor_id": str(professor_id),
                "ingested_at": ingested_at,
            }
        )

    collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
    return ids
