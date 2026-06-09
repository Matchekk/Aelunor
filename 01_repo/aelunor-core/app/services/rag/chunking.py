"""Deterministic chunking for RAG documents.

Splits a document into bounded, slightly overlapping chunks and attaches a
contextual header so each chunk carries its campaign / source identity.
No external dependencies, no LLM calls.
"""

from __future__ import annotations

from typing import Any

from .models import RAGChunk, RAGDocument

_HEADER_METADATA_KEYS = ("title", "name", "location", "entities")


def _stringify(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value if str(item).strip())
    return str(value)


def build_contextual_header(document: RAGDocument) -> str:
    """Build a compact, deterministic header for a document's chunks."""
    parts = [
        f"campaign_id={document.campaign_id}",
        f"source_type={document.source_type}",
    ]
    metadata = document.metadata or {}
    for key in _HEADER_METADATA_KEYS:
        value = metadata.get(key)
        if value in (None, "", [], ()):  # skip empty values
            continue
        rendered = _stringify(value).strip()
        if rendered:
            parts.append(f"{key}={rendered}")
    return " | ".join(parts)


def _split_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split text into bounded pieces, preferring whitespace boundaries."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    step_overlap = max(0, min(overlap_chars, max_chars - 1))
    pieces: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            boundary = cleaned.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        piece = cleaned[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= length:
            break
        start = max(end - step_overlap, start + 1)
    return pieces


def chunk_document(
    document: RAGDocument,
    *,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[RAGChunk]:
    """Chunk a document deterministically.

    Small documents yield exactly one chunk. Empty / whitespace-only text
    yields no chunks (safe, never raises). Chunk ids are stable:
    ``f"{document.id}#chunk-{i}"``.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    header = build_contextual_header(document)
    pieces = _split_text(document.text, max_chars, overlap_chars)
    metadata = dict(document.metadata or {})

    chunks: list[RAGChunk] = []
    for index, piece in enumerate(pieces):
        chunks.append(
            RAGChunk(
                id=f"{document.id}#chunk-{index}",
                document_id=document.id,
                campaign_id=document.campaign_id,
                source_type=document.source_type,
                text=piece,
                contextual_header=header,
                metadata=dict(metadata),
                token_estimate=max(1, len(piece) // 4),
                salience=document.salience,
                canonical=document.canonical,
            )
        )
    return chunks
