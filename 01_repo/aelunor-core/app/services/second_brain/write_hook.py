"""Deterministic post-turn write hook for the Second Brain (no LLM).

After a turn succeeds, mirror its outcome into the campaign brain: one event
memory card, deterministic facts/entities from the merged patch, NPC/item
entity updates, open-thread updates, and co-mention edges. Everything is
derived from data already on the turn record — no new LLM call, no full
prompts, no long evidence blobs, no secrets.

Safety contract: a brain write must NEVER break a turn. ``maybe_record_turn``
(the integration entry point) is flag-gated, opens the per-campaign brain,
seeds it on first turn, records the turn, and swallows every error
(``store.note_failed_job``) — it never raises.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Mapping

from app.config.feature_flags import second_brain_enabled

from .locator import open_campaign_brain
from .models import KnowledgeEdge, KnowledgeNode
from .seed import seed_brain_from_state
from .service import SecondBrain

_log = logging.getLogger("aelunor.second_brain")
_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Keep memory cards short — cards are pointers, not transcripts.
_MAX_PLAYER_CHARS = 160
_MAX_GM_CHARS = 220


def _slug(value: Any) -> str:
    return _SLUG_RE.sub("-", str(value).strip().lower()).strip("-") or "x"


def _short(text: Any, limit: int) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def _scene_for_actor(state: Mapping[str, Any], actor: str) -> str:
    chars = state.get("characters") if isinstance(state, Mapping) else None
    if isinstance(chars, Mapping) and isinstance(chars.get(actor), Mapping):
        sid = chars[actor].get("scene_id")
        if isinstance(sid, str):
            return sid.strip()
    return ""


def record_turn(brain: SecondBrain, campaign_id: str, turn_record: Mapping[str, Any]) -> dict:
    """Deterministically write one turn into an open brain. Returns a summary.

    May raise on a broken store; callers (``maybe_record_turn``) wrap it.
    """
    cid = campaign_id
    turn_id = str(turn_record.get("turn_id") or "")
    try:
        turn_no = int(turn_record.get("turn_number") or 0)
    except (TypeError, ValueError):
        turn_no = 0
    actor = str(turn_record.get("actor") or "")
    player_action = _short(turn_record.get("input_text_raw"), _MAX_PLAYER_CHARS)
    gm_text = _short(turn_record.get("gm_text_display"), _MAX_GM_CHARS)
    patch = turn_record.get("patch") if isinstance(turn_record.get("patch"), Mapping) else {}
    state_after = (
        turn_record.get("state_after") if isinstance(turn_record.get("state_after"), Mapping) else {}
    )
    scene_id = _scene_for_actor(state_after, actor)

    nodes: list[KnowledgeNode] = []
    edges: list[KnowledgeEdge] = []

    # 1) Event memory card.
    event_id = f"{cid}:event:{turn_id or turn_no}"
    importance = 0.6 if (patch.get("plotpoints_add") or patch.get("plotpoints_update")) else 0.5
    card_text = " → ".join(p for p in (player_action, gm_text) if p) or f"Turn {turn_no}"
    nodes.append(
        KnowledgeNode(
            id=event_id,
            campaign_id=cid,
            kind="event",
            name=f"Turn {turn_no}",
            text=card_text,
            metadata={"turn_id": turn_id, "actor": actor, "scene_id": scene_id},
            salience=importance,
            canonical=True,
            updated_turn=turn_no,
        )
    )
    if actor:
        edges.append(KnowledgeEdge(cid, event_id, f"{cid}:character:{_slug(actor)}", "involves", 1.0))
    if scene_id:
        edges.append(KnowledgeEdge(cid, event_id, f"{cid}:location:{_slug(scene_id)}", "at", 0.8))

    # 2) New items -> item entities (+ mention edge).
    for key, rec in (patch.get("items_new") or {}).items() if isinstance(patch.get("items_new"), Mapping) else []:
        if not isinstance(rec, Mapping):
            continue
        name = str(rec.get("name") or key).strip()
        desc = _short(rec.get("description") or rec.get("desc"), 160)
        item_id = f"{cid}:item:{_slug(key)}"
        nodes.append(
            KnowledgeNode(
                id=item_id, campaign_id=cid, kind="item", name=name,
                text=f"{name}: {desc}".strip(": ").strip(),
                metadata={"first_turn": turn_no}, salience=0.4, updated_turn=turn_no,
            )
        )
        edges.append(KnowledgeEdge(cid, event_id, item_id, "mentions", 0.5))

    # 3) NPC updates -> npc entities (+ mention edge).
    npc_updates = turn_record.get("npc_updates")
    if isinstance(npc_updates, (list, tuple)):
        for rec in npc_updates:
            if not isinstance(rec, Mapping):
                continue
            ident = str(rec.get("id") or rec.get("npc_id") or rec.get("name") or "").strip()
            name = str(rec.get("name") or ident).strip()
            if not ident or not name:
                continue
            npc_id = f"{cid}:npc:{_slug(ident)}"
            nodes.append(
                KnowledgeNode(
                    id=npc_id, campaign_id=cid, kind="npc", name=name,
                    text=_short(rec.get("description") or rec.get("summary") or name, 200),
                    metadata={"last_seen_turn": turn_no}, salience=0.5, updated_turn=turn_no,
                )
            )
            edges.append(KnowledgeEdge(cid, event_id, npc_id, "mentions", 0.6))

    # 4) Plotpoints -> open threads; updates may resolve/supersede them.
    for rec in patch.get("plotpoints_add") or []:
        if not isinstance(rec, Mapping):
            continue
        title = str(rec.get("title") or rec.get("name") or "").strip()
        if not title:
            continue
        tid = f"{cid}:thread:{_slug(title)}"
        nodes.append(
            KnowledgeNode(
                id=tid, campaign_id=cid, kind="open_thread", name=title,
                text=_short(rec.get("notes") or rec.get("summary") or title, 200),
                metadata={"status": str(rec.get("status") or "open")}, salience=0.6,
                updated_turn=turn_no,
            )
        )
        edges.append(KnowledgeEdge(cid, event_id, tid, "advances", 0.6))
    for rec in patch.get("plotpoints_update") or []:
        if not isinstance(rec, Mapping):
            continue
        title = str(rec.get("title") or rec.get("name") or "").strip()
        status = str(rec.get("status") or "").strip().lower()
        if not title or not status:
            continue
        tid = f"{cid}:thread:{_slug(title)}"
        existing = brain.store.get_node(cid, tid)
        if existing is not None:
            meta = dict(existing.metadata or {})
            meta["status"] = status
            resolved = status in ("resolved", "closed", "done", "superseded")
            nodes.append(
                KnowledgeNode(
                    id=tid, campaign_id=cid, kind="open_thread", name=existing.name,
                    text=existing.text, metadata=meta,
                    salience=0.1 if resolved else existing.salience,
                    canonical=existing.canonical, embedding=existing.embedding,
                    updated_turn=turn_no,
                )
            )

    # 5) Deterministic fact: actor scene change vs. prior turn.
    state_before = (
        turn_record.get("state_before") if isinstance(turn_record.get("state_before"), Mapping) else {}
    )
    prev_scene = _scene_for_actor(state_before, actor)
    if scene_id and scene_id != prev_scene:
        fact_id = f"{cid}:fact:loc-{_slug(actor)}-{turn_no}"
        nodes.append(
            KnowledgeNode(
                id=fact_id, campaign_id=cid, kind="fact", name=f"{actor} location",
                text=f"{actor} is now at {scene_id}.",
                metadata={"subject": actor, "predicate": "located_at", "object": scene_id},
                salience=0.5, updated_turn=turn_no,
            )
        )

    brain._embed_nodes(nodes)
    written = brain.store.upsert_nodes(nodes)
    brain.store.upsert_edges(edges)
    brain.store.set_meta("last_processed_turn_id", turn_id)
    brain.store.set_meta("last_processed_turn_number", str(turn_no))
    return {"nodes": written, "edges": len(edges), "turn_number": turn_no}


def maybe_record_turn(
    campaign: Mapping[str, Any],
    turn_record: Mapping[str, Any],
    *,
    campaigns_dir: str | None = None,
    embedder=None,
) -> dict | None:
    """Flag-gated integration entry. Opens the per-campaign brain, seeds on
    first turn, records the turn. Never raises — a brain problem cannot break
    the turn."""
    if not second_brain_enabled():
        return None
    meta = campaign.get("campaign_meta") if isinstance(campaign, Mapping) else None
    cid = meta.get("campaign_id") if isinstance(meta, Mapping) else None
    if not cid:
        return None
    brain = open_campaign_brain(cid, campaigns_dir=campaigns_dir, embedder=embedder)
    if brain is None:
        return None
    try:
        if brain.store.get_meta("seeded") != "1":
            try:
                seed_brain_from_state(brain, campaign)
            except Exception:  # noqa: BLE001
                brain.store.note_failed_job("seed_on_first_turn_failed")
        return record_turn(brain, cid, turn_record)
    except Exception as exc:  # noqa: BLE001 - brain must never break a turn
        _log.warning("second_brain: write hook failed for %s: %s", cid, exc)
        try:
            brain.store.note_failed_job("write_hook_failed")
        except Exception:  # noqa: BLE001
            pass
        return None
    finally:
        try:
            brain.store.close()
        except Exception:  # noqa: BLE001
            pass
