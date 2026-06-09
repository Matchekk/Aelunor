"""Deterministic mapper: structured campaign state -> RAGDocument list.

Pure stdlib, offline. Turns typical structured campaign/world/NPC/location/
quest/turn-summary data into clean RAGDocument objects. It never reads runtime
files, never calls an LLM/HTTP, never mutates the input state, and never maps
raw chat logs. Output (ids, ordering, text) is stable for identical input.
This is only the mapping layer, not the index service or turn wiring.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from . import _mapping_utils as mu
from .models import RAGDocument

# Stable source_type values. Only what is sensibly reachable from state.
SOURCE_CAMPAIGN_SUMMARY = "campaign_summary"
SOURCE_WORLD_SUMMARY = "world_summary"
SOURCE_LORE = "lore"
SOURCE_LOCATION = "location"
SOURCE_NPC = "npc"
SOURCE_QUEST = "quest"
SOURCE_TURN_SUMMARY = "turn_summary"

_DEFAULT_MAX_TEXT_CHARS = 4000
_SLUG_RE = re.compile(r"[^\w]+", re.UNICODE)


def build_rag_document_id(campaign_id: str, source_type: str, stable_key: str) -> str:
    """Build a deterministic document id (no randomness, no timestamps)."""
    slug = _SLUG_RE.sub("-", str(stable_key).strip().lower()).strip("-")
    return f"{campaign_id}:{source_type}:{slug or 'item'}"


_CAMPAIGN_SOURCE_PATHS = (("meta",), ("campaign",), ("setup", "world", "summary"),
                          ("boards", "plot_essentials"))
_CAMPAIGN_FACTS = (("Theme", ("theme",)), ("Tone", ("tone",)),
                   ("Conflict", ("central_conflict", "current_threat", "conflict")),
                   ("Goal", ("current_goal", "goal")))


def _build_campaign_summary(campaign_id: str, state: Mapping[str, Any],
                            cap: int) -> list[RAGDocument]:
    sources = [state] + [n for p in _CAMPAIGN_SOURCE_PATHS
                         if isinstance((n := mu.dig(state, p)), Mapping)]
    title = mu.merged_text(sources, ("title", "name", "campaign_name"))
    summary = mu.merged_text(sources, ("summary", "description", "premise", "synopsis", "overview"))
    facts = [f"{label}: {value}" for label, keys in _CAMPAIGN_FACTS
             if (value := mu.merged_text(sources, keys))]
    if not (summary or facts):
        return []
    metadata: dict[str, Any] = {"kind": SOURCE_CAMPAIGN_SUMMARY, "source_path": "campaign"}
    if title:
        metadata["title"] = metadata["name"] = title
    chronicle = mu.merged_text(sources, ("chronicle_id", "chronicle"))
    if chronicle:
        metadata["chronicle_id"] = chronicle
    text = mu.render_text(title=title or "Campaign", type_label=SOURCE_CAMPAIGN_SUMMARY,
                          summary=summary, facts_lines=facts, max_text_chars=cap)
    return [RAGDocument(
        id=build_rag_document_id(campaign_id, SOURCE_CAMPAIGN_SUMMARY, "campaign"),
        campaign_id=campaign_id, source_type=SOURCE_CAMPAIGN_SUMMARY, text=text,
        metadata=metadata, salience=0.7, canonical=True)]


def _build_world_summary(campaign_id: str, state: Mapping[str, Any],
                         cap: int) -> list[RAGDocument]:
    world = mu.dig(state, ("world",))
    if not isinstance(world, Mapping):
        world = mu.dig(state, ("state", "world"))
    if not isinstance(world, Mapping):
        return []
    name = mu.first_text(world, ("name", "world_name", "title"))
    summary = mu.first_text(world, ("summary", "description", "overview"))
    facts: list[str] = []
    region = mu.first_text(world, ("region", "setting"))
    if region:
        facts.append(f"Region: {region}")
    facts.extend(mu.facts(mu.first_value(world, ("lore", "bible", "facts")),
                          mu.MAX_FACTS - len(facts)))
    if not (summary or facts):
        return []
    metadata: dict[str, Any] = {"kind": SOURCE_WORLD_SUMMARY, "source_path": "world"}
    if name:
        metadata["title"] = metadata["name"] = name
    text = mu.render_text(title=name or "World", type_label=SOURCE_WORLD_SUMMARY,
                          summary=summary, facts_lines=facts, max_text_chars=cap)
    return [RAGDocument(
        id=build_rag_document_id(campaign_id, SOURCE_WORLD_SUMMARY, name or "world"),
        campaign_id=campaign_id, source_type=SOURCE_WORLD_SUMMARY, text=text,
        metadata=metadata, salience=0.6, canonical=True)]


def _build_entities(campaign_id: str, state: Mapping[str, Any], cfg: dict,
                    cap: int) -> list[RAGDocument]:
    container = mu.first_container(state, cfg["containers"])
    source_type = cfg["source_type"]
    docs: list[RAGDocument] = []
    for record, fallback in mu.records(container):
        ident = mu.first_text(record, cfg["id_keys"]) or fallback
        name = mu.first_text(record, cfg["name_keys"])
        title = (f"{cfg['title_prefix']} {name or ident}".strip()
                 if cfg.get("title_prefix") else name)
        summary = mu.first_text(record, cfg["summary_keys"])
        status = mu.first_text(record, cfg.get("status_keys", ()))
        facts: list[str] = []
        for label, keys in cfg.get("labeled_facts", {}).items():
            value = mu.first_text(record, keys)
            if value:
                facts.append(f"{label}: {value}")
        for key in cfg.get("facts_keys", ()):
            facts.extend(mu.facts(record.get(key)))
        facts = mu.dedupe(facts)[:mu.MAX_FACTS]
        related = {label: hits for label, keys in cfg.get("relations", {}).items()
                   if (hits := mu.names(mu.first_value(record, keys)))}
        if not title or not (summary or status or facts or related):
            continue
        metadata: dict[str, Any] = {"kind": source_type, "source_path": cfg["source_path"],
                                    cfg["id_field"]: ident}
        if name:
            metadata["title"] = metadata["name"] = name
        if status:
            metadata["status"] = status
        location_id = mu.first_text(record, cfg.get("location_keys", ()))
        if location_id:
            metadata["location_id"] = location_id
        if cfg.get("index_field"):
            idx = record.get("index")
            metadata["index"] = idx if isinstance(idx, int) else fallback
        entities = mu.dedupe(([name] if name else [])
                             + [n for hits in related.values() for n in hits])[:mu.MAX_LIST_ITEMS]
        if entities:
            metadata["entities"] = entities
        text = mu.render_text(title=title, type_label=source_type, status=status,
                              summary=summary, facts_lines=facts, related=related,
                              max_text_chars=cap)
        docs.append(RAGDocument(
            id=build_rag_document_id(campaign_id, source_type, ident),
            campaign_id=campaign_id, source_type=source_type, text=text,
            metadata=metadata, salience=cfg.get("salience", 0.5), canonical=True))
    return docs


_LORE_CFG = {"source_type": SOURCE_LORE, "source_path": "lore",
    "containers": (("lore",), ("world", "lore_entries"), ("codex", "lore")),
    "id_keys": ("id", "slug", "key"), "id_field": "lore_id",
    "name_keys": ("title", "name", "topic"),
    "summary_keys": ("text", "summary", "description", "content"),
    "facts_keys": ("facts", "details"), "salience": 0.5}
_LOCATION_CFG = {"source_type": SOURCE_LOCATION, "source_path": "locations",
    "containers": (("locations",), ("world", "locations"), ("map", "nodes"), ("scenes",)),
    "id_keys": ("id", "location_id", "slug"), "id_field": "location_id",
    "name_keys": ("name", "title"), "summary_keys": ("description", "summary", "desc"),
    "status_keys": ("status", "state"), "facts_keys": ("facts", "known_facts", "details"),
    "relations": {"NPCs": ("npcs", "characters"), "Quests": ("quests",)}, "salience": 0.55}
_NPC_CFG = {"source_type": SOURCE_NPC, "source_path": "npcs",
    "containers": (("npcs",), ("characters",), ("party",), ("persons",), ("world", "npcs")),
    "id_keys": ("id", "npc_id", "character_id", "slug"), "id_field": "npc_id",
    "name_keys": ("name", "title"), "summary_keys": ("description", "summary", "bio", "background"),
    "status_keys": ("status", "disposition"), "facts_keys": ("facts", "memory", "memories", "notes"),
    "labeled_facts": {"Role": ("role", "occupation"), "Relationship": ("relationship", "relation")},
    "relations": {"Locations": ("location", "locations", "location_id")},
    "location_keys": ("location_id", "location"), "salience": 0.5}
_QUEST_CFG = {"source_type": SOURCE_QUEST, "source_path": "quests",
    "containers": (("quests",), ("objectives",), ("journal", "entries"), ("journal", "quests")),
    "id_keys": ("id", "quest_id", "slug"), "id_field": "quest_id",
    "name_keys": ("title", "name", "objective"), "summary_keys": ("description", "summary", "goal"),
    "status_keys": ("status", "state"), "facts_keys": ("facts", "hooks", "open_hooks", "steps", "notes"),
    "relations": {"NPCs": ("npcs", "characters"), "Locations": ("locations", "location")},
    "salience": 0.55}
_TURN_CFG = {"source_type": SOURCE_TURN_SUMMARY, "source_path": "timeline",
    "containers": (("timeline",), ("turns",), ("turn_summaries",),
                   ("chronicle", "turns"), ("chronicle", "timeline")),
    "id_keys": ("turn_id", "id", "index"), "id_field": "turn_id", "index_field": True,
    "name_keys": (), "title_prefix": "Turn", "summary_keys": ("summary", "text", "recap"),
    "facts_keys": ("events", "objectives", "consequences", "outcomes"),
    "relations": {"NPCs": ("npcs", "characters"), "Locations": ("location", "locations")},
    "location_keys": ("location_id", "location"), "salience": 0.45}

_ENTITY_CONFIGS = (_LORE_CFG, _LOCATION_CFG, _NPC_CFG, _QUEST_CFG, _TURN_CFG)


def build_rag_documents_from_campaign_state(
    campaign_id: str,
    state: Mapping[str, Any],
    *,
    max_text_chars: int = _DEFAULT_MAX_TEXT_CHARS,
) -> list[RAGDocument]:
    """Map structured campaign state into deterministic RAGDocument objects.

    Robust against missing keys, ``None`` and wrong types; unknown shapes are
    ignored rather than raising. The input ``state`` is never mutated, empty
    documents are never produced, and ids/ordering are deterministic.
    """
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        raise ValueError("campaign_id must be a non-empty string")
    if not isinstance(state, Mapping):
        return []
    cap = max(1, int(max_text_chars))
    documents: list[RAGDocument] = []
    documents.extend(_build_campaign_summary(campaign_id, state, cap))
    documents.extend(_build_world_summary(campaign_id, state, cap))
    for cfg in _ENTITY_CONFIGS:
        documents.extend(_build_entities(campaign_id, state, cfg, cap))
    return documents
