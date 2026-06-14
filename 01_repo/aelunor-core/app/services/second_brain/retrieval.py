"""Pre-narrator retrieval for the Second Brain (read-only).

Builds the bounded ``[RELEVANT_CAMPAIGN_BRAIN]`` block that is injected next to
the existing RAG block before the narrator call. The brain is opened read-only
(``create=False``) so retrieval never creates files; missing brain or the flag
being off yields ``""`` (no block).

Output contract: short memory cards (≤ ~160 chars each), at most a handful,
under a hard token budget (≈ chars/4), no JSONL/evidence dumps, resolved /
superseded threads excluded, and cards that merely repeat the active scene /
character (already in the structured state block) deduped out. The block says
explicitly it is supporting recall — the current structured state wins.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

from app.config.feature_flags import second_brain_enabled

from .locator import open_campaign_brain
from .models import RecallResult

_log = logging.getLogger("aelunor.second_brain")

_HEADER = "[RELEVANT_CAMPAIGN_BRAIN] (supporting recall only; the current structured campaign state wins on any conflict)"
_FOOTER = "[/RELEVANT_CAMPAIGN_BRAIN]"
_RESOLVED = {"resolved", "superseded", "closed", "done"}
_MAX_CARD_CHARS = 160
_CHARS_PER_TOKEN = 4


def _card_snippet(text: str) -> str:
    s = " ".join(str(text or "").split())
    if len(s) > _MAX_CARD_CHARS:
        s = s[: _MAX_CARD_CHARS - 1].rstrip() + "…"
    return s


def _is_resolved(result: RecallResult) -> bool:
    status = str((result.node.metadata or {}).get("status") or "").lower()
    return status in _RESOLVED


def render_brain_block(
    results: list[RecallResult],
    *,
    limit: int = 10,
    token_budget: int = 1800,
    skip_names: frozenset[str] = frozenset(),
) -> str:
    """Render recall results into a bounded block, or ``""`` if nothing fits."""
    char_budget = max(0, int(token_budget)) * _CHARS_PER_TOKEN
    lines = [_HEADER]
    used = len(_HEADER) + len(_FOOTER) + 2
    count = 0
    for result in results:
        if count >= max(1, min(12, limit)):
            break
        node = result.node
        if _is_resolved(result):
            continue
        if node.name and node.name.lower() in skip_names:
            continue
        snippet = _card_snippet(node.text)
        line = f"- ({node.kind}) {node.name}: {snippet}".rstrip(": ").strip()
        if used + len(line) + 1 > char_budget:
            break
        lines.append(line)
        used += len(line) + 1
        count += 1
    if count == 0:
        return ""
    lines.append(_FOOTER)
    return "\n".join(lines)


def get_relevant_brain_context(
    campaign_id: str,
    actor_id: str,
    scene_id: str,
    player_action: str,
    *,
    campaigns_dir: str | None = None,
    embedder=None,
    limit: int = 10,
    token_budget: int = 1800,
    skip_names: frozenset[str] = frozenset(),
) -> str:
    """Open the campaign brain read-only and build the recall block. Returns
    ``""`` when there is no brain or nothing relevant. Never raises."""
    try:
        brain = open_campaign_brain(
            campaign_id, campaigns_dir=campaigns_dir, create=False, embedder=embedder
        )
        if brain is None:
            return ""
        try:
            query = " ".join(p for p in (player_action, scene_id, actor_id) if p).strip()
            entities = tuple(p for p in (actor_id, scene_id) if p)
            results = brain.recall(
                campaign_id,
                query or scene_id or actor_id,
                entities=entities,
                max_results=max(limit * 2, limit),
                graph_hops=1,
            )
            return render_brain_block(
                results, limit=limit, token_budget=token_budget, skip_names=skip_names
            )
        finally:
            brain.store.close()
    except Exception as exc:  # noqa: BLE001 - retrieval must never break a turn
        _log.warning("second_brain: retrieval failed for %s: %s", campaign_id, exc)
        return ""


def _skip_names(working_state: Mapping[str, Any], actor_id: str, scene_id: str) -> frozenset[str]:
    """Names already visible in the structured state block — avoid duplicates."""
    names: set[str] = set()
    chars = working_state.get("characters") if isinstance(working_state, Mapping) else None
    if isinstance(chars, Mapping) and isinstance(chars.get(actor_id), Mapping):
        bio = chars[actor_id].get("bio")
        if isinstance(bio, Mapping):
            name = bio.get("name")
            if isinstance(name, str) and name.strip():
                names.add(name.strip().lower())
    scenes = working_state.get("scenes") if isinstance(working_state, Mapping) else None
    if isinstance(scenes, Mapping) and isinstance(scenes.get(scene_id), Mapping):
        sname = scenes[scene_id].get("name")
        if isinstance(sname, str) and sname.strip():
            names.add(sname.strip().lower())
    return frozenset(names)


def maybe_brain_context_block(
    campaign: Mapping[str, Any],
    working_state: Mapping[str, Any],
    actor: str,
    player_action: str,
    *,
    campaigns_dir: str | None = None,
    embedder=None,
    token_budget: int = 1200,
    limit: int = 8,
) -> str:
    """Flag-gated integration entry for the turn pipeline. Returns the block or
    ``""``. Never raises — retrieval must not break a turn.

    Iteration 1: budget tightened to 1200 tokens / 8 cards (was 1800/10) — the
    A/B benchmark showed the block cost ~+889 narrator prompt tokens with no
    continuity gain and a slight redundancy rise, so the block is bounded
    smaller to keep the prompt lean.
    """
    if not second_brain_enabled():
        return ""
    try:
        meta = campaign.get("campaign_meta") if isinstance(campaign, Mapping) else None
        cid = meta.get("campaign_id") if isinstance(meta, Mapping) else None
        if not cid:
            return ""
        scene_id = ""
        chars = working_state.get("characters") if isinstance(working_state, Mapping) else None
        if isinstance(chars, Mapping) and isinstance(chars.get(actor), Mapping):
            sid = chars[actor].get("scene_id")
            if isinstance(sid, str):
                scene_id = sid.strip()
        return get_relevant_brain_context(
            cid,
            actor,
            scene_id,
            player_action,
            campaigns_dir=campaigns_dir,
            embedder=embedder,
            limit=limit,
            token_budget=token_budget,
            skip_names=_skip_names(working_state, actor, scene_id),
        )
    except Exception:  # noqa: BLE001
        return ""
