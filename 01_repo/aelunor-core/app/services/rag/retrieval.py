"""Deterministic lexical retrieval over RAG chunks.

Pure in-memory scoring: no network, no embeddings, no vector database.
campaign_id is a hard filter; results are sorted deterministically.
"""

from __future__ import annotations

import re
from typing import Any, Optional, Sequence

from .models import RAGChunk, RetrievalQuery, RetrievalResult

# Unicode-aware token rule: match runs of Unicode word characters (letters
# and digits, incl. umlauts/accents like ä, ö, ü, é, û) but treat underscore
# as a separator rather than a normal word character. Pure stdlib, fully
# deterministic, no external dependency. Matching stays case-insensitive
# because `normalize_text` lowercases the input first.
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

# Scoring weights. Entity > keyword > metadata; salience / canonical are
# only light, stable tie-breakers and never produce a match on their own.
_ENTITY_WEIGHT = 3.0
_KEYWORD_WEIGHT = 1.0
_METADATA_WEIGHT = 0.5
_SALIENCE_WEIGHT = 0.5
_CANONICAL_WEIGHT = 0.25


def normalize_text(text: Any) -> str:
    """Lowercase a value for case-insensitive matching."""
    return str(text).lower()


def tokenize(text: Any) -> list[str]:
    """Split text into lowercase Unicode-alphanumeric tokens."""
    return _TOKEN_RE.findall(normalize_text(text))


def _metadata_tokens(chunk: RAGChunk) -> set[str]:
    tokens: set[str] = set()
    for value in (chunk.metadata or {}).values():
        if isinstance(value, (list, tuple)):
            for item in value:
                tokens.update(tokenize(item))
        else:
            tokens.update(tokenize(value))
    return tokens


def _score_chunk(
    query: RetrievalQuery, chunk: RAGChunk
) -> Optional[tuple[float, tuple[str, ...]]]:
    haystack = normalize_text(chunk.text + " " + chunk.contextual_header)
    text_tokens = set(tokenize(chunk.text))
    header_tokens = (
        set(tokenize(chunk.contextual_header))
        | _metadata_tokens(chunk)
        | set(tokenize(chunk.source_type))
    )
    query_tokens = set(tokenize(query.text))

    reasons: list[str] = []
    score = 0.0

    matched_entities = [
        entity
        for entity in query.entities
        if normalize_text(entity).strip()
        and normalize_text(entity).strip() in haystack
    ]
    if matched_entities:
        score += _ENTITY_WEIGHT * len(matched_entities)
        reasons.append("entities:" + ",".join(matched_entities))

    keyword_overlap = query_tokens & text_tokens
    if keyword_overlap:
        score += _KEYWORD_WEIGHT * len(keyword_overlap)
        reasons.append(f"keywords:{len(keyword_overlap)}")

    metadata_overlap = (query_tokens & header_tokens) - text_tokens
    if metadata_overlap:
        score += _METADATA_WEIGHT * len(metadata_overlap)
        reasons.append(f"metadata:{len(metadata_overlap)}")

    if score <= 0:
        return None

    if chunk.salience:
        boost = _SALIENCE_WEIGHT * chunk.salience
        if boost:
            score += boost
            reasons.append("salience")
    if chunk.canonical:
        score += _CANONICAL_WEIGHT
        reasons.append("canonical")

    return score, tuple(reasons)


def retrieve_chunks(
    query: RetrievalQuery, chunks: Sequence[RAGChunk]
) -> list[RetrievalResult]:
    """Return the best matching chunks for a query, most relevant first.

    campaign_id and (when set) source_types are hard filters. Chunks with a
    non-positive score are dropped. Ties break on chunk.id for stability.
    max_results is strictly enforced.
    """
    results: list[RetrievalResult] = []
    for chunk in chunks:
        if chunk.campaign_id != query.campaign_id:
            continue
        if query.source_types and chunk.source_type not in query.source_types:
            continue
        scored = _score_chunk(query, chunk)
        if scored is None:
            continue
        score, reasons = scored
        results.append(RetrievalResult(chunk=chunk, score=score, reasons=reasons))

    results.sort(key=lambda result: (-result.score, result.chunk.id))
    limit = max(0, int(query.max_results))
    return results[:limit]
