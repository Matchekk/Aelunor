"""Data models for the deterministic RAG foundation.

Plain stdlib dataclasses, no Pydantic. All models stay simple and
serializable so they can be reused offline in tests and future slices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clamp_unit(value: float) -> float:
    """Clamp a float into the inclusive [0.0, 1.0] range."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


@dataclass
class RAGDocument:
    """A source document that may later feed campaign-memory retrieval."""

    id: str
    campaign_id: str
    source_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    salience: float = 0.5
    canonical: bool = True

    def __post_init__(self) -> None:
        self.salience = _clamp_unit(self.salience)


@dataclass
class RAGChunk:
    """A retrievable slice of a document with a contextual header."""

    id: str
    document_id: str
    campaign_id: str
    source_type: str
    text: str
    contextual_header: str
    metadata: dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0
    salience: float = 0.5
    canonical: bool = True

    def __post_init__(self) -> None:
        self.salience = _clamp_unit(self.salience)
        self.token_estimate = max(0, int(self.token_estimate))


@dataclass
class RetrievalQuery:
    """A lexical retrieval request scoped to a single campaign."""

    text: str
    campaign_id: str
    entities: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    max_results: int = 5


@dataclass
class RetrievalResult:
    """A scored chunk plus the human-readable reasons it matched."""

    chunk: RAGChunk
    score: float
    reasons: tuple[str, ...] = ()
