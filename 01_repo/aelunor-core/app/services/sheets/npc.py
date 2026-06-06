from dataclasses import dataclass
from typing import Any, Callable, Dict

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class NpcSheetPorts:
    normalize_npc_entry: Callable[..., Any]
    scene_name_from_state: Callable[[CampaignState, str], str]
    normalize_class_current: Callable[[Any], Any]
    normalize_resource_name: Callable[[Any, str], str]
    normalize_dynamic_skill_state: Callable[..., CampaignState]
    skill_rank_sort_value: Callable[[Any], int]
    next_character_xp_for_level: Callable[[int], int]


def build_npc_sheet_view(campaign: CampaignState, npc_id: str, *, ports: NpcSheetPorts) -> CampaignState:
    state = campaign.get("state") or {}
    npc_entry = ports.normalize_npc_entry((state.get("npc_codex") or {}).get(npc_id), fallback_npc_id=npc_id)
    if not npc_entry:
        raise HTTPException(status_code=404, detail="NPC nicht gefunden.")
    scene_id = str(npc_entry.get("last_seen_scene_id") or "").strip()
    scene_name = ports.scene_name_from_state(state, scene_id) if scene_id else ""
    history_notes = [str(note).strip() for note in (npc_entry.get("history_notes") or []) if str(note).strip()]
    npc_class = ports.normalize_class_current(npc_entry.get("class_current"))
    npc_resource_name = ports.normalize_resource_name(
        (
            ((npc_entry.get("progression") or {}).get("resource_name"))
            or (((state.get("world") or {}).get("settings") or {}).get("resource_name"))
            or "Aether"
        ),
        "Aether",
    )
    npc_skills = [
        ports.normalize_dynamic_skill_state(
            skill_value,
            skill_id=skill_id,
            skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
            resource_name=npc_resource_name,
        )
        for skill_id, skill_value in ((npc_entry.get("skills") or {}).items())
    ]
    npc_skills.sort(
        key=lambda entry: (ports.skill_rank_sort_value(entry.get("rank")), entry.get("level", 1), entry.get("name", "")),
        reverse=True,
    )
    level = int(npc_entry.get("level", 1) or 1)
    return {
        "npc_id": npc_entry.get("npc_id"),
        "name": npc_entry.get("name"),
        "race": npc_entry.get("race"),
        "age": npc_entry.get("age"),
        "goal": npc_entry.get("goal"),
        "level": npc_entry.get("level"),
        "xp_total": int(npc_entry.get("xp_total", 0) or 0),
        "xp_current": int(npc_entry.get("xp_current", 0) or 0),
        "xp_to_next": int(npc_entry.get("xp_to_next", ports.next_character_xp_for_level(level)) or ports.next_character_xp_for_level(level)),
        "backstory_short": npc_entry.get("backstory_short"),
        "role_hint": npc_entry.get("role_hint"),
        "faction": npc_entry.get("faction"),
        "status": npc_entry.get("status"),
        "last_seen_scene_id": scene_id,
        "last_seen_scene_name": scene_name or "Unbekannt",
        "first_seen_turn": npc_entry.get("first_seen_turn"),
        "last_seen_turn": npc_entry.get("last_seen_turn"),
        "mention_count": npc_entry.get("mention_count"),
        "relevance_score": npc_entry.get("relevance_score"),
        "history_notes": history_notes,
        "tags": npc_entry.get("tags", []),
        "class_current": npc_class,
        "skills": npc_skills,
        "resources": {
            "hp_current": int(npc_entry.get("hp_current", 0) or 0),
            "hp_max": int(npc_entry.get("hp_max", 0) or 0),
            "sta_current": int(npc_entry.get("sta_current", 0) or 0),
            "sta_max": int(npc_entry.get("sta_max", 0) or 0),
            "res_current": int(npc_entry.get("res_current", 0) or 0),
            "res_max": int(npc_entry.get("res_max", 0) or 0),
            "resource_name": npc_resource_name,
        },
        "conditions": npc_entry.get("conditions", []),
        "injuries": npc_entry.get("injuries", []),
        "scars": npc_entry.get("scars", []),
    }
