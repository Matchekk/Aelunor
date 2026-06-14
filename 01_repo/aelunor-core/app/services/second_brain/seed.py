"""First-run / campaign seed for the Second Brain (deterministic, no LLM).

Mirrors existing stable campaign data into the brain so a fresh campaign
starts with structured memory: campaign/world/NPC/location/quest summaries
(via the existing RAG mapper), plus items, open threads (plotpoints +
open_loops), and the active character. Tone/style and the active scene/actor
are stored as ``brain_meta`` (structured metadata), never as free prose nodes.

Rules: schema stays in code, the LLM never invents the brain format, there is
no new LLM call, and the pass is idempotent — re-running upserts by stable id
and never duplicates.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from app.config.feature_flags import second_brain_enabled

from .locator import open_campaign_brain
from .models import KnowledgeEdge, KnowledgeNode
from .service import SecondBrain

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_RESOLVED_STATUS = {"resolved", "closed", "done", "superseded", "abandoned"}
_MAX_SEED_THREADS = 8


def _slug(value: Any) -> str:
    return _SLUG_RE.sub("-", str(value).strip().lower()).strip("-") or "item"


def _records(container: Any) -> Iterable[tuple[str, Mapping[str, Any]]]:
    """Yield (stable_key, record) for dict- or list-shaped containers."""
    if isinstance(container, Mapping):
        for key, rec in container.items():
            if isinstance(rec, Mapping):
                yield str(key), rec
    elif isinstance(container, (list, tuple)):
        for idx, rec in enumerate(container):
            if isinstance(rec, Mapping):
                yield str(rec.get("id") or rec.get("slug") or idx), rec


def _text(record: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _campaign_id(campaign: Mapping[str, Any]) -> str:
    meta = campaign.get("campaign_meta")
    if isinstance(meta, Mapping):
        cid = meta.get("campaign_id")
        if isinstance(cid, str) and cid:
            return cid
    return ""


def _item_nodes(cid: str, state: Mapping[str, Any], turn: int) -> list[KnowledgeNode]:
    nodes: list[KnowledgeNode] = []
    for key, rec in _records(state.get("items")):
        name = _text(rec, ("name", "title")) or key
        desc = _text(rec, ("description", "desc", "summary"))
        rarity = _text(rec, ("rarity",))
        facts = " ".join(p for p in (rarity and f"({rarity})", desc) if p).strip()
        nodes.append(
            KnowledgeNode(
                id=f"{cid}:item:{_slug(key)}",
                campaign_id=cid,
                kind="item",
                name=name,
                text=f"{name}: {facts}".strip(": ").strip(),
                metadata={"rarity": rarity} if rarity else {},
                salience=0.4,
                updated_turn=turn,
            )
        )
    return nodes


def _open_thread_nodes(
    cid: str, state: Mapping[str, Any], boards: Mapping[str, Any], turn: int
) -> list[KnowledgeNode]:
    """Seed only genuinely-open threads, capped.

    Iteration 7: the seed used to mirror every plotpoint + open_loop (30 in the
    benchmark campaign) — most of which already live in the narrator context
    packet, flooding the retrieval pool with low-signal duplicates. We now skip
    resolved/closed threads and cap the seed to the most recent few; live play
    adds new threads via the write hook.
    """
    nodes: list[KnowledgeNode] = []
    for key, rec in _records(state.get("plotpoints")):
        status = (_text(rec, ("status", "state")) or "open").lower()
        if status in _RESOLVED_STATUS:
            continue
        title = _text(rec, ("title", "name", "objective")) or key
        notes = _text(rec, ("notes", "summary", "description"))
        nodes.append(
            KnowledgeNode(
                id=f"{cid}:thread:{_slug(title)}",
                campaign_id=cid,
                kind="open_thread",
                name=title,
                text=f"{title}: {notes}".strip(": ").strip(),
                metadata={"status": status},
                salience=0.6,
                updated_turn=turn,
            )
        )
    essentials = boards.get("plot_essentials") if isinstance(boards, Mapping) else None
    open_loops = essentials.get("open_loops") if isinstance(essentials, Mapping) else None
    if isinstance(open_loops, (list, tuple)):
        for loop in open_loops:
            text = str(loop).strip()
            if not text:
                continue
            nodes.append(
                KnowledgeNode(
                    id=f"{cid}:thread:loop-{_slug(text)[:40]}",
                    campaign_id=cid,
                    kind="open_thread",
                    name=text[:60],
                    text=text,
                    metadata={"status": "open", "source": "open_loops"},
                    salience=0.55,
                    updated_turn=turn,
                )
            )
    # Keep the seed lean: cap to the most salient handful (live play adds more).
    nodes.sort(key=lambda n: (-n.salience, n.id))
    return nodes[:_MAX_SEED_THREADS]


def _character_nodes(
    cid: str, state: Mapping[str, Any], turn: int
) -> tuple[list[KnowledgeNode], list[KnowledgeEdge], str, str]:
    """Active character entities. Returns (nodes, edges, active_actor, active_scene)."""
    nodes: list[KnowledgeNode] = []
    edges: list[KnowledgeEdge] = []
    active_actor = ""
    active_scene = ""
    for slot, rec in _records(state.get("characters")):
        bio = rec.get("bio") if isinstance(rec.get("bio"), Mapping) else {}
        name = _text(bio, ("name",)) or slot
        goal = _text(bio, ("goal",))
        scene_id = _text(rec, ("scene_id",))
        node_id = f"{cid}:character:{_slug(slot)}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                campaign_id=cid,
                kind="character",
                name=name,
                text=f"{name}" + (f" — goal: {goal}" if goal else ""),
                metadata={"slot": slot, "scene_id": scene_id},
                salience=0.7,
                updated_turn=turn,
            )
        )
        if not active_actor and _text(bio, ("name",)):
            active_actor = slot
            active_scene = scene_id
        if scene_id:
            edges.append(
                KnowledgeEdge(
                    campaign_id=cid,
                    src_id=node_id,
                    dst_id=f"{cid}:location:{_slug(scene_id)}",
                    relation="located_at",
                    weight=1.0,
                )
            )
    return nodes, edges, active_actor, active_scene


def seed_brain_from_state(brain: SecondBrain, campaign: Mapping[str, Any]) -> dict:
    """Deterministically seed a brain from a campaign dict. Idempotent.

    Returns a small summary. Flag-agnostic (callers gate on the flag); this is
    the directly-testable core.
    """
    cid = _campaign_id(campaign)
    if not cid:
        return {"seeded": False, "reason": "no campaign_id"}
    state = campaign.get("state") if isinstance(campaign.get("state"), Mapping) else {}
    boards = campaign.get("boards") if isinstance(campaign.get("boards"), Mapping) else {}
    try:
        turn = int(((state.get("meta") or {}).get("turn")) or 0)
    except (TypeError, ValueError):
        turn = 0

    # Base summaries + co-mention graph via the existing deterministic mapper.
    brain.ingest_state(cid, dict(state))

    extra_nodes: list[KnowledgeNode] = []
    extra_edges: list[KnowledgeEdge] = []
    extra_nodes += _item_nodes(cid, state, turn)
    extra_nodes += _open_thread_nodes(cid, state, boards, turn)
    char_nodes, char_edges, active_actor, active_scene = _character_nodes(cid, state, turn)
    extra_nodes += char_nodes
    extra_edges += char_edges
    brain._embed_nodes(extra_nodes)
    brain.store.upsert_nodes(extra_nodes)
    brain.store.upsert_edges(extra_edges)

    # Tone / style / orientation as structured metadata, never prose nodes.
    essentials = boards.get("plot_essentials") if isinstance(boards, Mapping) else {}
    essentials = essentials if isinstance(essentials, Mapping) else {}
    if not active_scene:
        active_scene = _text(essentials, ("active_scene",))
    for key in ("tone", "premise", "current_goal", "current_threat"):
        value = _text(essentials, (key,))
        if value:
            brain.store.set_meta(key, value[:300])
    if active_scene:
        brain.store.set_meta("active_scene", active_scene)
    if active_actor:
        brain.store.set_meta("active_actor", active_actor)
    brain.store.set_meta("seeded", "1")
    brain.store.set_meta("seeded_turn", str(turn))

    return {
        "seeded": True,
        "campaign_id": cid,
        "counts": brain.store.counts(cid),
        "active_scene": active_scene,
        "active_actor": active_actor,
    }


def seed_campaign_brain(
    campaign: Mapping[str, Any],
    *,
    campaigns_dir: str | None = None,
    embedder=None,
) -> SecondBrain | None:
    """Flag-gated first-run seed. Returns the open brain, or ``None`` when the
    flag is off or the brain cannot be opened. Never raises."""
    if not second_brain_enabled():
        return None
    cid = _campaign_id(campaign)
    if not cid:
        return None
    brain = open_campaign_brain(cid, campaigns_dir=campaigns_dir, embedder=embedder)
    if brain is None:
        return None
    try:
        seed_brain_from_state(brain, campaign)
    except Exception:  # noqa: BLE001 - seeding must never break a turn/start
        brain.store.note_failed_job("seed_failed")
    return brain
