"""Ingestion + graph construction for the Second Brain (graph pillar).

Reuses the existing deterministic RAG mapper
(``build_rag_documents_from_campaign_state``) so structured campaign state
becomes ``KnowledgeNode`` objects, then derives ``KnowledgeEdge`` relations
from entity co-mentions. Fully offline and deterministic: no LLM, no I/O,
no randomness, no timestamps.
"""

from __future__ import annotations

import re

from app.services.rag import build_rag_documents_from_campaign_state
from app.services.rag.models import RAGDocument

from .models import KnowledgeEdge, KnowledgeNode


def _node_name(doc: RAGDocument) -> str:
    meta = doc.metadata or {}
    for key in ("name", "title", "location"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return doc.source_type


def _entities(doc: RAGDocument) -> list[str]:
    raw = (doc.metadata or {}).get("entities")
    if isinstance(raw, (list, tuple)):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def documents_to_nodes(documents: list[RAGDocument]) -> list[KnowledgeNode]:
    """Map RAG documents to knowledge nodes (one node per document)."""
    nodes: list[KnowledgeNode] = []
    for doc in documents:
        nodes.append(
            KnowledgeNode(
                id=doc.id,
                campaign_id=doc.campaign_id,
                kind=doc.source_type,
                name=_node_name(doc),
                text=doc.text,
                metadata=dict(doc.metadata or {}),
                salience=doc.salience,
                canonical=doc.canonical,
            )
        )
    return nodes


def derive_edges(nodes: list[KnowledgeNode]) -> list[KnowledgeEdge]:
    """Co-mention edges: connect a node to any other node whose name is
    referenced in its declared entities or appears as a word in its text."""
    edges: list[KnowledgeEdge] = []
    # Index named nodes (skip generic single-token source-type names).
    named = [n for n in nodes if n.name and n.name != n.kind]
    by_lower = {n.name.lower(): n for n in named}
    for node in nodes:
        haystack_entities = {
            e.lower() for e in _entities_from_node(node)
        }
        text_words = set(re.findall(r"[a-z0-9]+", node.text.lower()))
        for other in named:
            if other.id == node.id:
                continue
            name_lower = other.name.lower()
            if name_lower in haystack_entities:
                edges.append(_edge(node, other, "mentions", 1.0))
            elif name_lower in text_words and " " not in name_lower:
                edges.append(_edge(node, other, "references", 0.5))
    return _dedupe_edges(edges, by_lower)


def _entities_from_node(node: KnowledgeNode) -> list[str]:
    raw = (node.metadata or {}).get("entities")
    if isinstance(raw, (list, tuple)):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _edge(src: KnowledgeNode, dst: KnowledgeNode, relation: str, weight: float) -> KnowledgeEdge:
    return KnowledgeEdge(
        campaign_id=src.campaign_id,
        src_id=src.id,
        dst_id=dst.id,
        relation=relation,
        weight=weight,
    )


def _dedupe_edges(edges: list[KnowledgeEdge], _named: dict) -> list[KnowledgeEdge]:
    seen: dict[tuple[str, str, str], KnowledgeEdge] = {}
    for e in edges:
        key = (e.src_id, e.dst_id, e.relation)
        prior = seen.get(key)
        if prior is None or e.weight > prior.weight:
            seen[key] = e
    return list(seen.values())


def build_knowledge_from_state(
    campaign_id: str, state: dict, *, max_text_chars: int = 4000
) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
    """End-to-end: campaign state -> (nodes, edges), deterministic."""
    documents = build_rag_documents_from_campaign_state(
        campaign_id, state, max_text_chars=max_text_chars
    )
    nodes = documents_to_nodes(documents)
    edges = derive_edges(nodes)
    return nodes, edges
