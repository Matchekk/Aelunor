"""Data models for the Campaign Second Brain prototype.

Plain stdlib dataclasses, no Pydantic. The Second Brain extends the existing
deterministic RAG foundation (``app/services/rag``) with four pillars:
persistence, semantic recall, an entity/knowledge graph, and auto
consolidation. These models stay simple and serializable so they can be
persisted to SQLite and reused offline in tests.
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
    return min(1.0, max(0.0, number))


@dataclass
class KnowledgeNode:
    """A persistent piece of campaign knowledge (graph vertex).

    ``kind`` mirrors the RAG ``source_type`` vocabulary (npc, location,
    quest, world_summary, lore, turn_summary, ...). ``embedding`` is an
    optional dense vector used for semantic recall; it stays ``None`` until
    an embedder has been run so the store is usable without one.
    """

    id: str
    campaign_id: str
    kind: str
    name: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    salience: float = 0.5
    canonical: bool = True
    embedding: tuple[float, ...] | None = None
    updated_turn: int = 0

    def __post_init__(self) -> None:
        self.salience = _clamp_unit(self.salience)
        self.updated_turn = max(0, int(self.updated_turn))


@dataclass
class KnowledgeEdge:
    """A typed relation between two knowledge nodes (graph edge)."""

    campaign_id: str
    src_id: str
    dst_id: str
    relation: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        try:
            self.weight = float(self.weight)
        except (TypeError, ValueError):
            self.weight = 1.0


@dataclass
class RecallQuery:
    """A hybrid recall request scoped to a single campaign."""

    text: str
    campaign_id: str
    entities: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    max_results: int = 6
    graph_hops: int = 1


@dataclass
class RecallResult:
    """A recalled node with its blended score and human-readable reasons."""

    node: KnowledgeNode
    score: float
    reasons: tuple[str, ...] = ()
