"""In-memory campaign memory index service (local core only).

Connects the existing RAG building blocks into one small, deterministic
service: structured campaign state -> RAGDocument -> RAGChunk ->
RetrievalResult -> bounded <RAG_MEMORY> context block.

Pure stdlib, offline. No persistence, no caches, no global mutable
registry, no file/runtime/LLM/HTTP access, and the input state is never
mutated. Not wired into routers, API or the turn pipeline yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .chunking import chunk_document
from .context_builder import build_rag_context
from .document_mapping import build_rag_documents_from_campaign_state
from .models import RAGChunk, RAGDocument, RetrievalQuery, RetrievalResult
from .retrieval import retrieve_chunks


@dataclass(frozen=True)
class CampaignMemoryIndex:
    """An immutable, in-memory bundle of documents and chunks for one campaign.

    Built once from structured campaign state and then queried read-only.
    Holds no caches and performs no I/O; ``campaign_id`` is the hard scope
    used for every retrieval against this index.
    """

    campaign_id: str
    documents: tuple[RAGDocument, ...]
    chunks: tuple[RAGChunk, ...]


def _validate_campaign_id(campaign_id: str) -> str:
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        raise ValueError("campaign_id must be a non-empty string")
    return campaign_id


def build_campaign_memory_index(
    campaign_id: str,
    state: Mapping[str, Any],
    *,
    document_max_text_chars: int = 4000,
    chunk_max_chars: int = 900,
    chunk_overlap_chars: int = 120,
) -> CampaignMemoryIndex:
    """Build a deterministic in-memory index from structured campaign state.

    Maps ``state`` to RAGDocuments via the existing mapper, then chunks each
    document. Empty / malformed state yields an empty index (never raises on
    content). ``campaign_id`` is validated up front. The input state is never
    mutated; document and chunk ordering are deterministic.
    """
    _validate_campaign_id(campaign_id)

    documents = build_rag_documents_from_campaign_state(
        campaign_id,
        state,
        max_text_chars=document_max_text_chars,
    )

    chunks: list[RAGChunk] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                max_chars=chunk_max_chars,
                overlap_chars=chunk_overlap_chars,
            )
        )

    return CampaignMemoryIndex(
        campaign_id=campaign_id,
        documents=tuple(documents),
        chunks=tuple(chunks),
    )


def retrieve_campaign_memory(
    index: CampaignMemoryIndex,
    *,
    text: str,
    entities: Sequence[str] = (),
    source_types: Sequence[str] = (),
    max_results: int = 5,
) -> list[RetrievalResult]:
    """Retrieve the most relevant chunks from a campaign memory index.

    The retrieval query is always scoped to ``index.campaign_id`` so a caller
    cannot reach across campaigns. ``entities``, ``source_types`` and
    ``max_results`` are passed through to the existing lexical retriever.
    Returns an empty list for an empty index or a query with no matches.
    """
    query = RetrievalQuery(
        text=text or "",
        campaign_id=index.campaign_id,
        entities=tuple(entities),
        source_types=tuple(source_types),
        max_results=max_results,
    )
    return retrieve_chunks(query, index.chunks)


def build_campaign_memory_context(
    index: CampaignMemoryIndex,
    *,
    text: str,
    entities: Sequence[str] = (),
    source_types: Sequence[str] = (),
    max_results: int = 5,
    max_items: int = 5,
    max_chars: int = 2500,
) -> str:
    """Build a bounded <RAG_MEMORY> context block for a campaign query.

    Retrieves campaign-scoped chunks and renders them with the existing
    bounded context builder. Returns ``""`` when the index is empty or there
    are no matches. ``max_results``, ``max_items`` and ``max_chars`` are
    forwarded unchanged; no debug or index data leaks into the block.
    """
    results = retrieve_campaign_memory(
        index,
        text=text,
        entities=entities,
        source_types=source_types,
        max_results=max_results,
    )
    return build_rag_context(results, max_items=max_items, max_chars=max_chars)


__all__ = [
    "CampaignMemoryIndex",
    "build_campaign_memory_index",
    "retrieve_campaign_memory",
    "build_campaign_memory_context",
]
