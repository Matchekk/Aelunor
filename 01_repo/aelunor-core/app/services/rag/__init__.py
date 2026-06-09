"""Deterministic RAG foundation (local core only).

Public surface for the campaign-memory RAG slice. No vector DB, no
embeddings, no LLM calls, no router wiring. See README.md / AGENTS.md.
"""

from __future__ import annotations

from .chunking import chunk_document
from .context_builder import build_rag_context
from .document_mapping import (
    build_rag_document_id,
    build_rag_documents_from_campaign_state,
)
from .memory_index import (
    CampaignMemoryIndex,
    build_campaign_memory_context,
    build_campaign_memory_index,
    retrieve_campaign_memory,
)
from .models import RAGChunk, RAGDocument, RetrievalQuery, RetrievalResult
from .retrieval import retrieve_chunks

__all__ = [
    "RAGDocument",
    "RAGChunk",
    "RetrievalQuery",
    "RetrievalResult",
    "chunk_document",
    "retrieve_chunks",
    "build_rag_context",
    "build_rag_documents_from_campaign_state",
    "build_rag_document_id",
    "CampaignMemoryIndex",
    "build_campaign_memory_index",
    "retrieve_campaign_memory",
    "build_campaign_memory_context",
]
