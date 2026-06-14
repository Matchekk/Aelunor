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
from .locator import (
    brain_dir_for_campaign,
    brain_path_for_campaign,
    is_safe_campaign_id,
    open_campaign_brain,
)
from .models import KnowledgeEdge, KnowledgeNode, RecallQuery, RecallResult
from .recall import recall
from .seed import seed_brain_from_state, seed_campaign_brain
from .service import SecondBrain
from .write_hook import maybe_record_turn, record_turn
from .store import SCHEMA_VERSION, SecondBrainStore

__all__ = [
    "SecondBrain",
    "SecondBrainStore",
    "SCHEMA_VERSION",
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
    "open_campaign_brain",
    "brain_path_for_campaign",
    "brain_dir_for_campaign",
    "is_safe_campaign_id",
    "seed_brain_from_state",
    "seed_campaign_brain",
    "record_turn",
    "maybe_record_turn",
]
