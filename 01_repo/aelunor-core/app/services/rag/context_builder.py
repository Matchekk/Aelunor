"""Render retrieval results into a bounded narrator-context block.

Output is a clearly delimited <RAG_MEMORY> block. Item and character
budgets are strictly enforced; the block is never truncated mid-tag.
"""

from __future__ import annotations

from typing import Sequence

from .models import RetrievalResult

_OPEN = "<RAG_MEMORY>"
_CLOSE = "</RAG_MEMORY>"
_NOTE = (
    "note: RAG is supporting memory only; the current structured campaign "
    "state takes precedence on conflict."
)


def _render_entry(index: int, result: RetrievalResult) -> str:
    chunk = result.chunk
    lines = [
        f"[{index}] {chunk.source_type} / {chunk.document_id} / "
        f"score={result.score:.2f}:"
    ]
    if chunk.contextual_header:
        lines.append(chunk.contextual_header)
    lines.append(chunk.text.strip())
    return "\n".join(lines)


def build_rag_context(
    results: Sequence[RetrievalResult],
    *,
    max_items: int = 5,
    max_chars: int = 2500,
) -> str:
    """Build a bounded <RAG_MEMORY> block from retrieval results.

    Returns "" when there are no results (or when nothing fits the budget).
    Result order is preserved. Both max_items and max_chars are strict; an
    item is only included if the whole closed block still fits max_chars.
    """
    if not results:
        return ""

    limit = min(len(results), max(0, int(max_items)))
    body: list[str] = []
    for offset in range(limit):
        entry = _render_entry(offset + 1, results[offset])
        candidate = "\n".join([_OPEN, _NOTE, *body, entry, _CLOSE])
        if len(candidate) > max_chars:
            break
        body.append(entry)

    if not body:
        return ""
    return "\n".join([_OPEN, _NOTE, *body, _CLOSE])
