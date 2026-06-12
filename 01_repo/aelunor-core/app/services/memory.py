import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.prompts.system_prompts import MEMORY_SYSTEM_PROMPT
from app.services.memory_context import (
    RECENT_TURNS_FULL_TEXT_COUNT,
    compact_character_for_turn_context,
    compact_combat_for_turn_context,
    compact_meta_for_turn_context,
    compact_plotpoints_for_turn_context,
    compact_recent_turn_for_turn_context,
    compact_setup_for_turn_context,
    compact_world_for_turn_context,
)


CampaignState = Dict[str, Any]
MOVEMENT_PATTERN = r"\b(?:erreicht|betritt|gelangt|kommt|geht|zieht|befindet sich|steht jetzt|ist jetzt in)\b"


@dataclass(frozen=True)
class MemoryPorts:
    active_turns: Callable[[CampaignState], List[CampaignState]]
    active_party: Callable[[CampaignState], List[str]]
    display_name_for_slot: Callable[[CampaignState, str], str]
    is_slot_id: Callable[[str], bool]
    blank_patch: Callable[[], CampaignState]
    canonical_scene_id: Callable[[str], str]
    derive_scene_name: Callable[[CampaignState, str], str]
    extract_descriptive_scene_name: Callable[[str], str]
    extract_scene_candidates: Callable[[str, str], List[CampaignState]]
    is_generic_scene_identifier: Callable[[str, str], bool]
    normalized_eval_text: Callable[[str], str]
    compact_conditions: Callable[[CampaignState], List[str]]
    normalize_character_state: Callable[..., CampaignState]
    world_attribute_scale: Callable[[CampaignState], CampaignState]
    element_core_names: List[str]
    build_world_element_summary: Callable[..., Any]
    build_race_codex_summary: Callable[..., Any]
    build_beast_codex_summary: Callable[..., Any]
    build_npc_codex_summary: Callable[..., Any]
    call_ollama_text: Callable[[str, str], str]
    utc_now: Callable[[], str]


def build_rules_profile(campaign: CampaignState, *, ports: MemoryPorts) -> CampaignState:
    summary = campaign.get("setup", {}).get("world", {}).get("summary", {})
    world_settings = (((campaign.get("state") or {}).get("world") or {}).get("settings") or {})
    attribute_scale = ports.world_attribute_scale(campaign)
    return {
        "theme": summary.get("theme", ""),
        "tone": summary.get("tone", ""),
        "difficulty": summary.get("difficulty", ""),
        "death_possible": bool(summary.get("death_possible", True)),
        "death_policy": summary.get("death_policy", ""),
        "ruleset": summary.get("ruleset", ""),
        "outcome_model": summary.get("outcome_model", ""),
        "resource_scarcity": summary.get("resource_scarcity", ""),
        "healing_frequency": summary.get("healing_frequency", ""),
        "monsters_density": summary.get("monsters_density", ""),
        "world_laws": summary.get("world_laws", []),
        "attribute_range_label": attribute_scale["label"],
        "attribute_range_min": attribute_scale["min"],
        "attribute_range_max": attribute_scale["max"],
        "resource_name": world_settings.get("resource_name", summary.get("resource_name", "Aether")),
        "consequence_severity": world_settings.get("consequence_severity", summary.get("consequence_severity", "mittel")),
        "progression_speed": world_settings.get("progression_speed", summary.get("progression_speed", "normal")),
        "evolution_cost_policy": world_settings.get("evolution_cost_policy", summary.get("evolution_cost_policy", "leicht")),
        "element_count": len((((campaign.get("state") or {}).get("world") or {}).get("elements") or {})),
        "core_elements": list(ports.element_core_names),
    }


def remember_recent_story(campaign: CampaignState, *, ports: MemoryPorts) -> None:
    campaign["state"]["recent_story"] = [turn["gm_text_display"] for turn in ports.active_turns(campaign)][-20:]


def heuristic_memory_summary(campaign: CampaignState, *, ports: MemoryPorts) -> str:
    turns = ports.active_turns(campaign)
    if not turns:
        return "Noch keine Zusammenfassung vorhanden."
    last_turn = turns[-1]
    actor_name = (
        ports.display_name_for_slot(campaign, last_turn["actor"])
        if ports.is_slot_id(last_turn["actor"])
        else last_turn["actor"]
    )
    parts = [
        f"Aktueller Stand nach Zug {last_turn['turn_number']}.",
        f"Letzte Aktion von {actor_name} ({last_turn['action_type']}): {last_turn['input_text_display']}",
        f"Letzte GM-Antwort: {last_turn['gm_text_display'][:280]}",
    ]
    return " ".join(parts)


def memory_summary_interval() -> int:
    """Alle wie viele Turns die LLM-Memory-Zusammenfassung neu gebaut wird.

    Default 1 (jeden Turn, bisheriges Verhalten). Bei N>1 darf die Summary bis
    zu N-1 Turns nachlaufen; das ist abgedeckt, weil recent_turns im
    CONTEXT_PACKET die letzten 8 Turns ohnehin woertlich enthaelt.
    """
    raw = str(os.getenv("AELUNOR_MEMORY_SUMMARY_INTERVAL", "")).strip()
    try:
        value = int(raw) if raw else 1
    except ValueError:
        return 1
    return max(1, value)


def rebuild_memory_summary(campaign: CampaignState, *, ports: MemoryPorts) -> None:
    turns = ports.active_turns(campaign)
    summary_turn = turns[-1]["turn_number"] if turns else 0
    if not turns:
        campaign["boards"]["memory_summary"] = {
            "content": "Noch keine Zusammenfassung vorhanden.",
            "updated_through_turn": 0,
            "updated_at": ports.utc_now(),
        }
        return
    existing = (campaign.get("boards") or {}).get("memory_summary") or {}
    updated_through = int(existing.get("updated_through_turn", 0) or 0)
    has_real_summary = bool(str(existing.get("content") or "").strip()) and updated_through > 0
    if has_real_summary and 1 <= summary_turn - updated_through < memory_summary_interval():
        return

    recent_turns = [
        {
            "turn_number": turn["turn_number"],
            "actor": ports.display_name_for_slot(campaign, turn["actor"])
            if ports.is_slot_id(turn["actor"])
            else turn["actor"],
            "action_type": turn["action_type"],
            "player": turn["input_text_display"],
            "gm": turn["gm_text_display"],
        }
        for turn in turns[-12:]
    ]
    payload = {
        "campaign": campaign["campaign_meta"]["title"],
        "world_summary": campaign["setup"]["world"].get("summary", {}),
        "characters": {
            slot_name: {
                "display_name": ports.display_name_for_slot(campaign, slot_name),
                "scene_id": data["scene_id"],
                "hp": int(data.get("hp_current", 0) or 0),
                "stamina": int(data.get("sta_current", 0) or 0),
                "resource": int(data.get("res_current", 0) or 0),
                "conditions": ports.compact_conditions(data),
            }
            for slot_name, data in campaign["state"]["characters"].items()
        },
        "recent_turns": recent_turns,
    }
    try:
        content = ports.call_ollama_text(
            MEMORY_SYSTEM_PROMPT,
            "Fasse diese Kampagne kompakt zusammen:\n" + json.dumps(payload, ensure_ascii=False),
        )
    except Exception:
        content = heuristic_memory_summary(campaign, ports=ports)
    campaign["boards"]["memory_summary"] = {
        "content": content or heuristic_memory_summary(campaign, ports=ports),
        "updated_through_turn": summary_turn,
        "updated_at": ports.utc_now(),
    }


def build_context_packet(campaign: CampaignState, state: CampaignState, actor: str, action_type: str, *, ports: MemoryPorts) -> str:
    normalized_characters = {}
    for slot_name, character in (state.get("characters") or {}).items():
        normalized_characters[slot_name] = compact_character_for_turn_context(
            ports.normalize_character_state(
                character,
                slot_name,
                state.get("items", {}) or {},
            )
        )
    recent = []
    window = ports.active_turns(campaign)[-8:]
    full_text_from = max(0, len(window) - RECENT_TURNS_FULL_TEXT_COUNT)
    for index, turn in enumerate(window):
        entry = {
            "turn_number": turn["turn_number"],
            "actor": turn["actor"],
            "actor_display": ports.display_name_for_slot(campaign, turn["actor"])
            if ports.is_slot_id(turn["actor"])
            else turn["actor"],
            "action_type": turn["action_type"],
            "player_text": turn["input_text_display"],
            "gm_text": turn["gm_text_display"],
            "requests": turn.get("requests", []),
        }
        recent.append(compact_recent_turn_for_turn_context(entry, full_text=index >= full_text_from))
    packet = {
        "meta": compact_meta_for_turn_context(state["meta"]),
        "combat": compact_combat_for_turn_context((state.get("meta") or {}).get("combat", {})),
        "attribute_influence": (state.get("meta") or {}).get("attribute_influence", {}),
        "setup": compact_setup_for_turn_context(campaign.get("setup", {})),
        "rules_profile": build_rules_profile(campaign, ports=ports),
        "active_party": ports.active_party(campaign),
        "display_party": [
            {"slot_id": slot_name, "display_name": ports.display_name_for_slot(campaign, slot_name)}
            for slot_name in ports.active_party(campaign)
        ],
        "world": compact_world_for_turn_context(state["world"]),
        "map": state["map"],
        "plotpoints": compact_plotpoints_for_turn_context(state.get("plotpoints", [])),
        "scenes": state.get("scenes", {}),
        "characters": normalized_characters,
        "items": state.get("items", {}),
        "world_races": {},
        "world_beast_types": {},
        "world_elements": {},
        "world_element_relations": {},
        "world_element_paths": {},
        "world_element_summary": ports.build_world_element_summary(state, limit=24),
        "race_codex_summary": ports.build_race_codex_summary(state, limit=24),
        "beast_codex_summary": ports.build_beast_codex_summary(state, limit=24),
        "npc_codex_summary": ports.build_npc_codex_summary(state, limit=20),
        "npc_codex": (state.get("npc_codex") or {}) if len((state.get("npc_codex") or {})) <= 24 else {},
        "boards": campaign["boards"],
        "recent_turns": recent,
        "claims": campaign.get("claims", {}),
        "actor": actor,
        "action_type": action_type,
    }
    return json.dumps(packet, ensure_ascii=False)


def build_scene_patch_from_text(campaign: CampaignState, state: CampaignState, actor: str, text: str, *, ports: MemoryPorts) -> CampaignState:
    actor_display = ports.display_name_for_slot(campaign, actor)
    candidates = ports.extract_scene_candidates(text, actor_display)
    if not candidates:
        return ports.blank_patch()
    patch = ports.blank_patch()
    known_scene_ids = set((state.get("scenes") or {}).keys()) | set(((state.get("map") or {}).get("nodes") or {}).keys())
    scene_was_set = False
    for candidate in candidates:
        if candidate["scope"] == "mention":
            continue
        scene_name = candidate["name"]
        scene_id = ports.canonical_scene_id(scene_name)
        if scene_id not in known_scene_ids and not any(node.get("id") == scene_id for node in patch["map_add_nodes"]):
            patch["map_add_nodes"].append(
                {
                    "id": scene_id,
                    "name": scene_name,
                    "type": "location",
                    "danger": 1,
                    "discovered": True,
                }
            )
        targets = ports.active_party(campaign) if candidate["scope"] == "group" and ports.active_party(campaign) else [actor]
        for slot_name in targets:
            patch["characters"].setdefault(slot_name, {})["scene_id"] = scene_id
            scene_was_set = True
        patch["events_add"].append(f"{'Die Gruppe' if candidate['scope'] == 'group' else actor_display} erreicht {scene_name}.")
    if not scene_was_set:
        current_scene = str((((state.get("characters") or {}).get(actor) or {}).get("scene_id") or "")).strip()
        if not current_scene:
            descriptor_scene = ports.extract_descriptive_scene_name(text)
            if descriptor_scene and re.search(MOVEMENT_PATTERN, ports.normalized_eval_text(text)):
                scene_id = ports.canonical_scene_id(descriptor_scene)
                patch["map_add_nodes"].append(
                    {
                        "id": scene_id,
                        "name": descriptor_scene,
                        "type": "location",
                        "danger": 1,
                        "discovered": True,
                    }
                )
                patch["characters"].setdefault(actor, {})["scene_id"] = scene_id
                patch["events_add"].append(f"{actor_display} befindet sich nun bei {descriptor_scene}.")
    return patch


def infer_scene_name_from_recent_story(campaign: CampaignState, slot_name: str, *, ports: MemoryPorts) -> Optional[str]:
    actor_display = ports.display_name_for_slot(campaign, slot_name)
    turns = list(reversed(campaign.get("turns") or []))
    for turn in turns:
        if turn.get("status") != "active":
            continue
        if turn.get("actor") != slot_name:
            continue
        story_text = str(turn.get("gm_text_display") or "")
        if not story_text.strip():
            continue
        candidates = ports.extract_scene_candidates(story_text, actor_display)
        for candidate in candidates:
            if candidate["scope"] in {"actor", "group"}:
                if not ports.is_generic_scene_identifier(ports.canonical_scene_id(candidate["name"]), candidate["name"]):
                    return candidate["name"]
        fallback = ports.extract_descriptive_scene_name(story_text)
        if fallback and re.search(MOVEMENT_PATTERN, ports.normalized_eval_text(story_text)):
            return fallback
    return None


def reconcile_scene_ids_with_story(campaign: CampaignState, *, ports: MemoryPorts) -> None:
    state = campaign.get("state") or {}
    characters = state.get("characters") or {}
    scenes = state.setdefault("scenes", {})
    map_nodes = (state.setdefault("map", {})).setdefault("nodes", {})
    for slot_name, character in characters.items():
        current_scene_id = str((character or {}).get("scene_id") or "").strip()
        current_scene_name = ports.derive_scene_name(campaign, slot_name)
        if current_scene_id and not ports.is_generic_scene_identifier(current_scene_id, current_scene_name):
            continue
        inferred_name = infer_scene_name_from_recent_story(campaign, slot_name, ports=ports)
        if not inferred_name:
            continue
        inferred_scene_id = ports.canonical_scene_id(inferred_name)
        if ports.is_generic_scene_identifier(inferred_scene_id, inferred_name):
            continue
        character["scene_id"] = inferred_scene_id
        scenes.setdefault(
            inferred_scene_id,
            {"name": inferred_name, "tone": "", "danger": 1, "notes": ""},
        )
        map_nodes.setdefault(
            inferred_scene_id,
            {"id": inferred_scene_id, "name": inferred_name, "type": "location", "danger": 1, "discovered": True},
        )
