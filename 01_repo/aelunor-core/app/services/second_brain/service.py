"""Second Brain orchestrator — ties the four pillars together.

``SecondBrain`` is the public entry point. It owns a persistent store and an
optional embedder and exposes a small surface:

- ``ingest_state``   — structured campaign state -> nodes + edges (graph).
- ``remember_turn``  — append a per-turn memory node (persistence).
- ``recall``         — hybrid semantic + graph recall (recall.py).
- ``maintain``       — salience decay + turn consolidation (consolidation).
- ``context_block``  — render a bounded ``[CAMPAIGN MEMORY]`` prompt block.

Everything is offline by default: with no embedder it falls back to lexical
recall, so the whole pipeline runs deterministically in tests.
"""

from __future__ import annotations

from .consolidation import SummarizerPort, consolidate_turns, decay_salience
from .embeddings import EmbeddingPort
from .ingest import build_knowledge_from_state
from .models import KnowledgeNode, RecallQuery, RecallResult
from .recall import recall as _recall
from .store import SecondBrainStore


class SecondBrain:
    def __init__(
        self,
        *,
        store: SecondBrainStore | None = None,
        embedder: EmbeddingPort | None = None,
    ) -> None:
        self.store = store or SecondBrainStore()
        self.embedder = embedder

    # -- ingestion ---------------------------------------------------------
    def _embed_nodes(self, nodes: list[KnowledgeNode]) -> None:
        if not self.embedder or not nodes:
            return
        vectors = self.embedder.embed([f"{n.name}\n{n.text}" for n in nodes])
        for node, vec in zip(nodes, vectors):
            node.embedding = vec

    def ingest_state(self, campaign_id: str, state: dict) -> int:
        """Map campaign state to knowledge, embed, and persist. Returns the
        number of nodes written."""
        nodes, edges = build_knowledge_from_state(campaign_id, state)
        self._embed_nodes(nodes)
        written = self.store.upsert_nodes(nodes)
        self.store.upsert_edges(edges)
        return written

    def remember_turn(
        self,
        campaign_id: str,
        *,
        turn_index: int,
        text: str,
        name: str = "",
        salience: float = 0.5,
        metadata: dict | None = None,
    ) -> KnowledgeNode:
        node = KnowledgeNode(
            id=f"{campaign_id}:turn:{int(turn_index)}",
            campaign_id=campaign_id,
            kind="turn_summary",
            name=name or f"Turn {int(turn_index)}",
            text=text,
            metadata=metadata or {},
            salience=salience,
            canonical=False,
            updated_turn=int(turn_index),
        )
        self._embed_nodes([node])
        self.store.upsert_nodes([node])
        return node

    # -- recall ------------------------------------------------------------
    def recall(
        self,
        campaign_id: str,
        text: str,
        *,
        entities: tuple[str, ...] = (),
        kinds: tuple[str, ...] = (),
        max_results: int = 6,
        graph_hops: int = 1,
    ) -> list[RecallResult]:
        query = RecallQuery(
            text=text,
            campaign_id=campaign_id,
            entities=entities,
            kinds=kinds,
            max_results=max_results,
            graph_hops=graph_hops,
        )
        return _recall(self.store, query, embedder=self.embedder)

    def context_block(
        self,
        campaign_id: str,
        text: str,
        *,
        entities: tuple[str, ...] = (),
        max_results: int = 6,
        max_chars: int = 2400,
    ) -> str:
        """Bounded ``[CAMPAIGN MEMORY]`` block, never cut mid-item. Mirrors
        the RAG prompt contract: supporting memory, structured state wins."""
        results = self.recall(
            campaign_id, text, entities=entities, max_results=max_results
        )
        if not results:
            return ""
        header = (
            "[CAMPAIGN MEMORY] (supporting recall only; the current "
            "structured campaign state wins on any conflict)"
        )
        footer = "[/CAMPAIGN MEMORY]"
        lines = [header]
        budget = max_chars - len(header) - len(footer) - 2
        for r in results:
            snippet = r.node.text.strip().replace("\n", " ")
            if len(snippet) > 240:
                snippet = snippet[:239].rstrip() + "…"
            line = f"- ({r.node.kind}) {r.node.name}: {snippet}"
            if len(line) + 1 > budget:
                break
            lines.append(line)
            budget -= len(line) + 1
        if len(lines) == 1:
            return ""
        lines.append(footer)
        return "\n".join(lines)

    # -- maintenance -------------------------------------------------------
    def maintain(
        self,
        campaign_id: str,
        *,
        current_turn: int,
        keep_recent: int = 8,
        half_life_turns: int = 12,
        summarizer: SummarizerPort | None = None,
    ) -> dict:
        decayed = decay_salience(
            self.store,
            campaign_id,
            current_turn=current_turn,
            half_life_turns=half_life_turns,
        )
        chronicle = consolidate_turns(
            self.store,
            campaign_id,
            current_turn=current_turn,
            keep_recent=keep_recent,
            summarizer=summarizer,
        )
        return {
            "decayed": decayed,
            "consolidated": chronicle is not None,
            "chronicle_id": chronicle.id if chronicle else None,
        }
