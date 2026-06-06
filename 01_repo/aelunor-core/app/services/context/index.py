from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple

from app.services.campaigns.party import campaign_slots, display_name_for_slot
from app.services.characters.resources import resource_name_for_character
from app.services.progression.skills import normalize_dynamic_skill_state
from app.services.context.entries import (
    add_codex_context_entries,
    add_plot_item_scene_context_entries,
    scene_name_from_context_state,
)
from app.services.world.codex import normalize_npc_entry
from app.services.world.npc import normalize_npc_alias
from app.services.world.progression import normalize_class_current


def build_context_knowledge_index(campaign: Dict[str, Any], state: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    world_settings = (((state.get("world") or {}).get("settings") or {}))

    def add_entry(entry: Dict[str, Any]) -> None:
        normalized_aliases = []
        for alias in (entry.get("aliases") or []):
            cleaned = str(alias or "").strip()
            if cleaned:
                normalized_aliases.append(cleaned)
        source_rows = []
        for row in (entry.get("sources") or []):
            if not isinstance(row, dict):
                continue
            source_rows.append(
                {
                    "type": str(row.get("type") or "").strip(),
                    "id": str(row.get("id") or "").strip(),
                    "label": str(row.get("label") or "").strip(),
                }
            )
        facts = [str(fact).strip() for fact in (entry.get("facts") or []) if str(fact).strip()]
        title = str(entry.get("title") or "").strip()
        if not title:
            return
        entries.append(
            {
                "type": str(entry.get("type") or "unknown").strip() or "unknown",
                "id": str(entry.get("id") or "").strip(),
                "title": title,
                "aliases": list(dict.fromkeys(normalized_aliases + [title])),
                "facts": facts[:12],
                "sources": source_rows[:8],
            }
        )

    for slot_name in campaign_slots(campaign):
        character = ((state.get("characters") or {}).get(slot_name) or {})
        display_name = display_name_for_slot(campaign, slot_name)
        class_current = normalize_class_current(character.get("class_current"))
        if class_current:
            class_id = str(class_current.get("id") or class_current.get("name") or f"class_{slot_name}")
            add_entry(
                {
                    "type": "class",
                    "id": f"{slot_name}:{class_id}",
                    "title": str(class_current.get("name") or class_id),
                    "aliases": [class_id, class_current.get("name", ""), display_name],
                    "facts": [
                        f"Tr\u00e4ger: {display_name}",
                        f"Rang: {class_current.get('rank', 'F')}",
                        f"Level: {class_current.get('level', 1)}/{class_current.get('level_max', 10)}",
                        f"Affinit\u00e4ten: {', '.join(class_current.get('affinity_tags', [])) or 'Keine'}",
                        f"Beschreibung: {class_current.get('description', '') or 'Keine Beschreibung.'}",
                    ],
                    "sources": [{"type": "class", "id": f"{slot_name}:{class_id}", "label": f"Klasse von {display_name}"}],
                }
            )
        resource_name = resource_name_for_character(character, world_settings)
        for skill_id, skill_value in ((character.get("skills") or {}).items()):
            skill_state = normalize_dynamic_skill_state(
                skill_value,
                skill_id=skill_id,
                skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
                resource_name=resource_name,
            )
            add_entry(
                {
                    "type": "skill",
                    "id": f"{slot_name}:{skill_state.get('id', skill_id)}",
                    "title": skill_state.get("name", skill_id),
                    "aliases": [skill_state.get("id", skill_id), skill_state.get("name", skill_id), display_name],
                    "facts": [
                        f"Tr\u00e4ger: {display_name}",
                        f"Rang: {skill_state.get('rank', 'F')}",
                        f"Level: {skill_state.get('level', 1)}/{skill_state.get('level_max', 10)}",
                        f"Tags: {', '.join(skill_state.get('tags') or []) or 'Keine'}",
                        f"Beschreibung: {skill_state.get('description', '') or 'Keine Beschreibung.'}",
                    ],
                    "sources": [{"type": "skill", "id": f"{slot_name}:{skill_state.get('id', skill_id)}", "label": f"Skill von {display_name}"}],
                }
            )

    for npc_id, raw_npc in ((state.get("npc_codex") or {}).items()):
        npc = normalize_npc_entry(raw_npc, fallback_npc_id=str(npc_id))
        if not npc:
            continue
        scene_name = scene_name_from_context_state(state, npc.get("last_seen_scene_id", ""))
        add_entry(
            {
                "type": "npc",
                "id": npc.get("npc_id", str(npc_id)),
                "title": npc.get("name", str(npc_id)),
                "aliases": [npc.get("name", ""), npc.get("npc_id", ""), npc.get("role_hint", ""), npc.get("faction", "")],
                "facts": [
                    f"Rasse: {npc.get('race', 'Unbekannt')}",
                    f"Alter: {npc.get('age', 'Unbekannt')}",
                    f"Level: {npc.get('level', 1)}",
                    f"Ziel: {npc.get('goal', '') or 'Unbekannt'}",
                    f"Fraktion: {npc.get('faction', '') or 'Keine'}",
                    f"Status: {npc.get('status', 'active')}",
                    f"Zuletzt gesehen: {scene_name or 'Unbekannt'}",
                    f"Kurz-Backstory: {npc.get('backstory_short', '') or 'Keine'}",
                ],
                "sources": [{"type": "npc", "id": npc.get("npc_id", str(npc_id)), "label": f"NPC-Codex: {npc.get('name', str(npc_id))}"}],
            }
        )

    add_codex_context_entries(entries, state)
    add_plot_item_scene_context_entries(entries, campaign, state)
    return entries


def resolve_context_target(index: List[Dict[str, Any]], target: str) -> Dict[str, Any]:
    normalized_target = normalize_npc_alias(target)
    if not normalized_target:
        return {"status": "not_in_canon", "entry": None, "confidence": "low", "matches": [], "suggestions": []}
    exact_matches: List[Dict[str, Any]] = []
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for entry in index:
        aliases = [normalize_npc_alias(alias) for alias in ([entry.get("title")] + list(entry.get("aliases") or []))]
        aliases = [alias for alias in aliases if alias]
        if normalized_target in aliases:
            exact_matches.append(entry)
            continue
        best = 0.0
        for alias in aliases:
            best = max(best, SequenceMatcher(None, normalized_target, alias).ratio())
        if best > 0:
            scored.append((best, entry))
    if len(exact_matches) == 1:
        return {"status": "found", "entry": exact_matches[0], "confidence": "high", "matches": exact_matches, "suggestions": []}
    if len(exact_matches) > 1:
        suggestions = [entry.get("title", "") for entry in exact_matches[:6] if entry.get("title")]
        return {"status": "ambiguous", "entry": None, "confidence": "medium", "matches": exact_matches, "suggestions": suggestions}
    scored.sort(key=lambda row: row[0], reverse=True)
    if scored and scored[0][0] >= 0.9:
        top_score = scored[0][0]
        close = [entry for score, entry in scored if abs(top_score - score) <= 0.02 and score >= 0.88]
        if len(close) == 1:
            confidence = "high" if top_score >= 0.96 else "medium"
            return {"status": "found", "entry": close[0], "confidence": confidence, "matches": [close[0]], "suggestions": []}
        suggestions = [entry.get("title", "") for entry in close[:6] if entry.get("title")]
        return {"status": "ambiguous", "entry": None, "confidence": "low", "matches": close, "suggestions": suggestions}
    suggestions = [entry.get("title", "") for score, entry in scored if score >= 0.62 and entry.get("title")][:6]
    return {"status": "not_in_canon", "entry": None, "confidence": "low", "matches": [], "suggestions": list(dict.fromkeys(suggestions))}


def build_reduced_context_snippets(index: List[Dict[str, Any]], *, target: str = "", limit: int = 12) -> List[Dict[str, Any]]:
    normalized_target = normalize_npc_alias(target)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for entry in index:
        base_score = 0.2
        if normalized_target:
            aliases = [normalize_npc_alias(alias) for alias in ([entry.get("title")] + list(entry.get("aliases") or []))]
            aliases = [alias for alias in aliases if alias]
            similarity = max((SequenceMatcher(None, normalized_target, alias).ratio() for alias in aliases), default=0.0)
            base_score += similarity
        if entry.get("type") in {"npc", "class", "skill", "plotpoint"}:
            base_score += 0.15
        scored.append((base_score, entry))
    scored.sort(key=lambda row: row[0], reverse=True)
    snippets: List[Dict[str, Any]] = []
    for _, entry in scored[: max(1, int(limit or 1))]:
        snippets.append(
            {
                "type": entry.get("type"),
                "id": entry.get("id"),
                "title": entry.get("title"),
                "facts": list(entry.get("facts") or [])[:4],
                "sources": list(entry.get("sources") or [])[:2],
            }
        )
    return snippets
