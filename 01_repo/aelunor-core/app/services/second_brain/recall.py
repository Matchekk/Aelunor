"""Hybrid recall for the Second Brain (semantic + graph pillars).

Blends three deterministic signals over campaign-scoped knowledge nodes:

1. Semantic — cosine similarity between the query embedding and node
   embeddings (skipped cleanly when no embedder/vector is present).
2. Lexical — shared-token overlap, so recall still works before embeddings
   exist and as a stable tie-breaker.
3. Graph — one-hop (or N-hop) neighbors of the strongest hits get a boost,
   surfacing related NPCs/locations/quests even if their text didn't match.

Salience and canonical act only as light, stable tie-breakers. The result is
ordered, bounded, and reproducible.
"""

from __future__ import annotations

import re

from .embeddings import EmbeddingPort, cosine_similarity
from .models import KnowledgeNode, RecallQuery, RecallResult
from .store import SecondBrainStore

_GRAPH_BOOST = 0.25


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _lexical_score(query_tokens: set[str], node: KnowledgeNode) -> float:
    if not query_tokens:
        return 0.0
    node_tokens = _tokens(f"{node.name} {node.text}")
    if not node_tokens:
        return 0.0
    overlap = len(query_tokens & node_tokens)
    return overlap / len(query_tokens)


def recall(
    store: SecondBrainStore,
    query: RecallQuery,
    *,
    embedder: EmbeddingPort | None = None,
) -> list[RecallResult]:
    nodes = store.get_nodes(query.campaign_id, kinds=query.kinds)
    if not nodes:
        return []

    query_tokens = _tokens(query.text) | {e.lower() for e in query.entities}
    query_vec = embedder.embed([query.text])[0] if embedder else None

    scored: dict[str, tuple[float, list[str]]] = {}
    for node in nodes:
        reasons: list[str] = []
        semantic = 0.0
        if query_vec is not None and node.embedding is not None:
            semantic = max(0.0, cosine_similarity(query_vec, node.embedding))
            if semantic > 0.0:
                reasons.append(f"semantic {semantic:.2f}")
        lexical = _lexical_score(query_tokens, node)
        if lexical > 0.0:
            reasons.append(f"lexical {lexical:.2f}")
        # Entity hit is a strong, explicit signal.
        if any(e.lower() in _tokens(node.name) for e in query.entities):
            lexical += 0.5
            reasons.append("entity match")
        base = 0.65 * semantic + 0.35 * lexical
        if base > 0.0:
            scored[node.id] = (base, reasons)

    # Graph expansion: boost neighbors of the current strongest hits.
    if query.graph_hops > 0 and scored:
        frontier = set(scored)
        for _ in range(query.graph_hops):
            neighbor_ids = store.neighbors(query.campaign_id, frontier)
            new_frontier: set[str] = set()
            for nid in neighbor_ids:
                if nid not in scored:
                    scored[nid] = (_GRAPH_BOOST, ["graph neighbor"])
                    new_frontier.add(nid)
            if not new_frontier:
                break
            frontier = new_frontier

    by_id = {n.id: n for n in nodes}
    # Pull in any neighbor nodes that were not in the kind-filtered set.
    missing = [nid for nid in scored if nid not in by_id]
    if missing:
        for nid in missing:
            node = store.get_node(query.campaign_id, nid)
            if node is not None:
                by_id[nid] = node

    results = [
        RecallResult(node=by_id[nid], score=score, reasons=tuple(reasons))
        for nid, (score, reasons) in scored.items()
        if nid in by_id
    ]
    # Order: score desc, then salience desc, canonical first, then id (stable).
    results.sort(
        key=lambda r: (-r.score, -r.node.salience, not r.node.canonical, r.node.id)
    )
    return results[: max(0, query.max_results)]
