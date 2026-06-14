"""Campaign Second Brain (exploratory prototype).

Evolves the deterministic RAG foundation (``app/services/rag``) into a
persistent campaign knowledge system across four pillars:

1. Persistence       — SQLite-backed store (``SecondBrainStore``).
2. Semantic recall   — swappable ``EmbeddingPort`` + cosine similarity.
3. Entity graph      — ``KnowledgeNode`` / ``KnowledgeEdge`` co-mention graph.
4. Auto consolidation— salience decay + rolling turn chronicle.

Offline by default: with no embedder wired, recall falls back to lexical
matching, so the whole pipeline stays deterministic and testable. See
README.md. This is a prototype slice; the public surface may still move.
"""

from __future__ import annotations

from .consolidation import consolidate_turns, decay_salience
from .embeddings import (
    DeterministicHashEmbedding,
    EmbeddingPort,
    OllamaEmbedding,
    cosine_similarity,
)
from .ingest import build_knowledge_from_state
from .models import KnowledgeEdge, KnowledgeNode, RecallQuery, RecallResult
from .recall import recall
from .service import SecondBrain
from .store import SecondBrainStore

__all__ = [
    "SecondBrain",
    "SecondBrainStore",
    "KnowledgeNode",
    "KnowledgeEdge",
    "RecallQuery",
    "RecallResult",
    "EmbeddingPort",
    "DeterministicHashEmbedding",
    "OllamaEmbedding",
    "cosine_similarity",
    "build_knowledge_from_state",
    "recall",
    "decay_salience",
    "consolidate_turns",
]
