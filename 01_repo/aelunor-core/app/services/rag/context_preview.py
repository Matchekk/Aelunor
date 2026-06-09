"""Read-only RAG context preview service (local core only).

Given a campaign and a hypothetical player action, build a small, bounded
preview of what RAG would currently surface: the in-memory index shape, the
retrieved results and the bounded ``<RAG_MEMORY>`` block. This is a preview
only: it never mutates campaign/state, never persists anything, performs no
LLM/HTTP/runtime-file access and is not wired into the turn pipeline.

The service composes the existing deterministic building blocks
(``build_campaign_memory_index`` -> ``retrieve_campaign_memory`` ->
``build_rag_context``) and shapes their output into a stable, UI/debug-friendly
response. Input limits are clamped (never raising) so a malformed request
yields a valid, empty-ish preview instead of a 500.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .context_builder import build_rag_context
from .memory_index import build_campaign_memory_index, retrieve_campaign_memory
from .models import RetrievalResult

# Clamp ranges. Documented behaviour: out-of-range request values are clamped
# into these inclusive bounds instead of raising, so a preview is always safe.
_MAX_RESULTS_MIN, _MAX_RESULTS_MAX = 0, 20
_MAX_ITEMS_MIN, _MAX_ITEMS_MAX = 0, 10
_MAX_CHARS_MIN, _MAX_CHARS_MAX = 0, 8000

# A single result excerpt stays short so large bodies are not duplicated in
# both ``results`` and the bounded ``context`` block.
_EXCERPT_MAX_CHARS = 280


@dataclass(frozen=True)
class RagContextPreviewDependencies:
    """Injected, side-effect-free dependencies for the preview service.

    ``load_campaign`` returns the structured campaign mapping for an id.
    ``authenticate_player`` is called with ``required=True`` and must raise on
    a missing/invalid player; it is never expected to mutate state.
    """

    load_campaign: Callable[[str], Mapping[str, Any]]
    authenticate_player: Callable[..., None]


def _clamp(value: Any, low: int, high: int, default: int) -> int:
    """Clamp ``value`` into [low, high]; fall back to ``default`` on garbage."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def _normalize_terms(values: Sequence[str]) -> tuple[str, ...]:
    """Normalize a sequence into deduped, non-empty, stripped string terms."""
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = str(value).strip()
        if term and term not in seen:
            seen.add(term)
            normalized.append(term)
    return tuple(normalized)


def _excerpt(text: str) -> str:
    """Return a single-line, length-bounded excerpt of chunk text."""
    flattened = " ".join(str(text).split())
    if len(flattened) <= _EXCERPT_MAX_CHARS:
        return flattened
    return flattened[: _EXCERPT_MAX_CHARS - 1].rstrip() + "…"


def _result_entry(rank: int, result: RetrievalResult) -> dict[str, Any]:
    chunk = result.chunk
    metadata = chunk.metadata if isinstance(chunk.metadata, Mapping) else {}
    return {
        "rank": rank,
        "score": round(float(result.score), 2),
        "chunk_id": chunk.id,
        "document_id": chunk.document_id,
        "source_type": chunk.source_type,
        "metadata": dict(metadata),
        "reasons": list(result.reasons),
        "text_excerpt": _excerpt(chunk.text),
    }


def _index_summary(documents: Sequence[Any]) -> dict[str, Any]:
    source_types = sorted({doc.source_type for doc in documents})
    return {
        "document_count": len(documents),
        "chunk_count": 0,  # filled in by caller (chunks live on the index)
        "source_types": source_types,
    }


def _collect_warnings(
    *, document_count: int, chunk_count: int, results: Sequence[Any], context: str
) -> list[str]:
    warnings: list[str] = []
    if document_count == 0 or chunk_count == 0:
        warnings.append("no memory documents/chunks were produced from state")
    if not context:
        if results:
            warnings.append("context is empty: max_chars too small for any item")
        else:
            warnings.append("context is empty: no retrieval matches")
    return warnings


def preview_campaign_rag_context(
    *,
    campaign_id: str,
    text: str,
    player_id: str | None,
    player_token: str | None,
    deps: RagContextPreviewDependencies,
    entities: Sequence[str] = (),
    source_types: Sequence[str] = (),
    max_results: int = 5,
    max_items: int = 5,
    max_chars: int = 2500,
) -> dict[str, Any]:
    """Build a read-only RAG context preview for a hypothetical action.

    Loads the campaign, authenticates the player (``required=True``) and then
    composes the deterministic RAG building blocks over ``campaign["state"]``.
    Nothing is mutated or persisted. Limits are clamped (never raising):
    ``max_results`` to [0, 20], ``max_items`` to [0, 10], ``max_chars`` to
    [0, 8000]. Empty/malformed state yields a valid, empty preview with
    explanatory ``warnings``.
    """
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)

    query_text = str(text or "")
    norm_entities = _normalize_terms(entities)
    norm_source_types = _normalize_terms(source_types)
    eff_max_results = _clamp(max_results, _MAX_RESULTS_MIN, _MAX_RESULTS_MAX, 5)
    eff_max_items = _clamp(max_items, _MAX_ITEMS_MIN, _MAX_ITEMS_MAX, 5)
    eff_max_chars = _clamp(max_chars, _MAX_CHARS_MIN, _MAX_CHARS_MAX, 2500)

    state = campaign.get("state") if isinstance(campaign, Mapping) else None

    index = build_campaign_memory_index(campaign_id, state if state is not None else {})
    results = retrieve_campaign_memory(
        index,
        text=query_text,
        entities=norm_entities,
        source_types=norm_source_types,
        max_results=eff_max_results,
    )
    context = build_rag_context(results, max_items=eff_max_items, max_chars=eff_max_chars)

    index_summary = _index_summary(index.documents)
    index_summary["chunk_count"] = len(index.chunks)

    return {
        "campaign_id": index.campaign_id,
        "query": {
            "text": query_text,
            "entities": list(norm_entities),
            "source_types": list(norm_source_types),
            "max_results": eff_max_results,
            "max_items": eff_max_items,
            "max_chars": eff_max_chars,
        },
        "index": index_summary,
        "results": [
            _result_entry(rank, result) for rank, result in enumerate(results, start=1)
        ],
        "context": context,
        "warnings": _collect_warnings(
            document_count=index_summary["document_count"],
            chunk_count=index_summary["chunk_count"],
            results=results,
            context=context,
        ),
    }


__all__ = [
    "RagContextPreviewDependencies",
    "preview_campaign_rag_context",
]
