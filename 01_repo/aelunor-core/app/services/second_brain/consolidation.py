"""Auto-consolidation for the Second Brain (consolidation pillar).

Two deterministic maintenance passes that keep the knowledge store from
growing without bound and let salience reflect recency:

- ``decay_salience`` — ages non-canonical nodes by turn distance so stale,
  one-off details fade while canonical anchors stay put.
- ``consolidate_turns`` — folds old per-turn memories beyond a recency
  window into a single rolling ``chronicle`` node. A summarizer port may
  compress the text via a local LLM; without one it falls back to a bounded
  deterministic digest, so the pass is always offline-safe.
"""

from __future__ import annotations

from typing import Callable

from .models import KnowledgeNode
from .store import SecondBrainStore

# Optional LLM summarizer: takes joined text, returns a shorter summary.
SummarizerPort = Callable[[str], str]

_TURN_KIND = "turn_summary"
_CHRONICLE_KIND = "chronicle"


def decay_salience(
    store: SecondBrainStore,
    campaign_id: str,
    *,
    current_turn: int,
    half_life_turns: int = 12,
    floor: float = 0.05,
) -> int:
    """Halve salience every ``half_life_turns`` of age; canonical nodes are
    exempt. Returns the number of nodes touched."""
    half_life = max(1, int(half_life_turns))
    touched = 0
    for node in store.get_nodes(campaign_id):
        if node.canonical:
            continue
        age = max(0, current_turn - node.updated_turn)
        if age <= 0:
            continue
        factor = 0.5 ** (age / half_life)
        new_salience = max(floor, node.salience * factor)
        if abs(new_salience - node.salience) > 1e-9:
            store.set_salience(campaign_id, node.id, new_salience)
            touched += 1
    return touched


def consolidate_turns(
    store: SecondBrainStore,
    campaign_id: str,
    *,
    current_turn: int,
    keep_recent: int = 8,
    max_digest_chars: int = 1200,
    summarizer: SummarizerPort | None = None,
) -> KnowledgeNode | None:
    """Fold turn memories older than ``keep_recent`` turns into one rolling
    chronicle node. Returns the chronicle node, or ``None`` if nothing aged
    out. The folded turn nodes are demoted (non-canonical, low salience) so
    recall favors the consolidated digest."""
    turns = [
        n
        for n in store.get_nodes(campaign_id, kinds=(_TURN_KIND,))
        if (current_turn - n.updated_turn) > keep_recent
    ]
    if not turns:
        return None

    turns.sort(key=lambda n: n.updated_turn)
    joined = "\n".join(f"[T{n.updated_turn}] {n.text}".strip() for n in turns)

    if summarizer is not None:
        try:
            digest = summarizer(joined).strip() or joined
        except Exception:
            digest = joined
    else:
        digest = joined
    if len(digest) > max_digest_chars:
        digest = digest[: max_digest_chars - 1].rstrip() + "…"

    chronicle = KnowledgeNode(
        id=f"{campaign_id}:chronicle",
        campaign_id=campaign_id,
        kind=_CHRONICLE_KIND,
        name="Chronicle",
        text=digest,
        metadata={"folded_turns": [n.updated_turn for n in turns]},
        salience=0.7,
        canonical=True,
        updated_turn=current_turn,
    )
    store.upsert_nodes([chronicle])

    # Demote the folded turn nodes so they no longer dominate recall.
    demoted = [
        KnowledgeNode(
            id=n.id,
            campaign_id=n.campaign_id,
            kind=n.kind,
            name=n.name,
            text=n.text,
            metadata={**(n.metadata or {}), "folded": True},
            salience=0.1,
            canonical=False,
            embedding=n.embedding,
            updated_turn=n.updated_turn,
        )
        for n in turns
    ]
    store.upsert_nodes(demoted)
    return chronicle
