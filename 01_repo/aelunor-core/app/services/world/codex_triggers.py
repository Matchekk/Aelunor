"""Codex trigger detection and application.

Pure world-domain logic extracted from the state runtime core. Detects race/
beast/NPC codex triggers from turn text and applies the resulting knowledge
updates to campaign state. Depends only on codex primitives and config.
"""
import re
from typing import Any, Dict, List, Tuple

from app.config.codex import (
    CODEX_BEAST_TRIGGER_ABILITY,
    CODEX_BEAST_TRIGGER_COMBAT,
    CODEX_BEAST_TRIGGER_DEFEAT,
    CODEX_KIND_BEAST,
    CODEX_KIND_RACE,
    CODEX_KNOWLEDGE_LEVEL_MAX,
    CODEX_KNOWLEDGE_LEVEL_MIN,
    CODEX_RACE_TRIGGER_CONTACT,
    CODEX_RACE_TRIGGER_LORE,
)
from app.core.ids import deep_copy
from app.services.world.codex import (
    build_world_exact_name_index,
    codex_block_order,
    codex_blocks_for_level,
    codex_facts_for_blocks,
    merge_known_facts_stable,
    normalize_codex_alias_text,
    normalize_codex_entry_stable,
    normalize_world_codex_structures,
    resolve_codex_entity_ids,
    stable_sorted_unique_strings,
)
from app.services.world.math_utils import clamp


def contains_any_normalized_token(text: str, tokens: set) -> bool:
    normalized_text = normalize_codex_alias_text(text)
    if not normalized_text:
        return False
    for token in (tokens or set()):
        token_norm = normalize_codex_alias_text(token)
        if not token_norm:
            continue
        if re.search(rf"(?<!\w){re.escape(token_norm)}(?!\w)", normalized_text):
            return True
    return False


def collect_beast_observed_abilities(text: str, beast_profile: Dict[str, Any]) -> List[str]:
    normalized_text = normalize_codex_alias_text(text)
    observed: List[str] = []
    for ability in (beast_profile.get("known_abilities") or []):
        ability_text = str(ability or "").strip()
        if not ability_text:
            continue
        ability_norm = normalize_codex_alias_text(ability_text)
        if ability_norm and re.search(rf"(?<!\w){re.escape(ability_norm)}(?!\w)", normalized_text):
            observed.append(ability_text)
    return observed


def collect_codex_triggers(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    player_text: str,
    gm_text: str,
    patch: Dict[str, Any],
    npc_updates: List[str],
    turn_number: int,
) -> Dict[str, Any]:
    normalize_world_codex_structures(state)
    world = state.get("world") or {}
    races = world.get("races") if isinstance(world.get("races"), dict) else {}
    beasts = world.get("beast_types") if isinstance(world.get("beast_types"), dict) else {}
    race_alias_index = world.get("race_alias_index") if isinstance(world.get("race_alias_index"), dict) else {}
    beast_alias_index = world.get("beast_alias_index") if isinstance(world.get("beast_alias_index"), dict) else {}
    exact_name_index = build_world_exact_name_index(world)

    text_parts = [str(player_text or "").strip(), str(gm_text or "").strip()]
    for event in (patch.get("events_add") or []):
        if str(event or "").strip():
            text_parts.append(str(event).strip())
    combined_text = "\n".join(part for part in text_parts if part)

    race_result = resolve_codex_entity_ids(combined_text, race_alias_index, exact_name_index.get("race_names") or {})
    beast_result = resolve_codex_entity_ids(combined_text, beast_alias_index, exact_name_index.get("beast_names") or {})
    triggers_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def merge_trigger(kind: str, entity_id: str, payload: Dict[str, Any]) -> None:
        key = (kind, entity_id)
        existing = triggers_by_key.get(key)
        if not existing:
            triggers_by_key[key] = {
                "kind": kind,
                "entity_id": entity_id,
                "knowledge_target": int(payload.get("knowledge_target", 0) or 0),
                "trigger_type": str(payload.get("trigger_type") or ""),
                "encounter_inc": int(payload.get("encounter_inc", 0) or 0),
                "known_individuals": stable_sorted_unique_strings(payload.get("known_individuals") or [], limit=32),
                "observed_abilities": stable_sorted_unique_strings(payload.get("observed_abilities") or [], limit=32),
                "defeated_inc": int(payload.get("defeated_inc", 0) or 0),
            }
            return
        existing["knowledge_target"] = max(int(existing.get("knowledge_target", 0) or 0), int(payload.get("knowledge_target", 0) or 0))
        existing["encounter_inc"] = int(existing.get("encounter_inc", 0) or 0) + int(payload.get("encounter_inc", 0) or 0)
        existing["defeated_inc"] = int(existing.get("defeated_inc", 0) or 0) + int(payload.get("defeated_inc", 0) or 0)
        existing["known_individuals"] = stable_sorted_unique_strings(
            list(existing.get("known_individuals") or []) + list(payload.get("known_individuals") or []),
            limit=32,
        )
        existing["observed_abilities"] = stable_sorted_unique_strings(
            list(existing.get("observed_abilities") or []) + list(payload.get("observed_abilities") or []),
            limit=32,
        )
        if int(payload.get("knowledge_target", 0) or 0) >= int(existing.get("knowledge_target", 0) or 0):
            existing["trigger_type"] = str(payload.get("trigger_type") or existing.get("trigger_type") or "")

    race_contact = contains_any_normalized_token(combined_text, CODEX_RACE_TRIGGER_CONTACT)
    race_lore = contains_any_normalized_token(combined_text, CODEX_RACE_TRIGGER_LORE)
    beast_combat = contains_any_normalized_token(combined_text, CODEX_BEAST_TRIGGER_COMBAT)
    beast_defeat = contains_any_normalized_token(combined_text, CODEX_BEAST_TRIGGER_DEFEAT)
    beast_ability = contains_any_normalized_token(combined_text, CODEX_BEAST_TRIGGER_ABILITY)

    for race_id in (race_result.get("matched") or []):
        knowledge_target = 1
        trigger_type = "race_first_contact"
        if race_contact:
            knowledge_target = max(knowledge_target, 2)
            trigger_type = "race_first_contact"
        if race_lore:
            knowledge_target = max(knowledge_target, 3)
            trigger_type = "race_lore_discovered"
        merge_trigger(
            CODEX_KIND_RACE,
            race_id,
            {
                "knowledge_target": knowledge_target,
                "trigger_type": trigger_type,
                "encounter_inc": 1,
            },
        )

    for beast_id in (beast_result.get("matched") or []):
        beast_profile = (beasts.get(beast_id) or {}) if isinstance(beasts, dict) else {}
        knowledge_target = 1
        trigger_type = "beast_first_sighting"
        defeated_inc = 0
        if beast_combat:
            knowledge_target = max(knowledge_target, 2)
            trigger_type = "beast_first_sighting"
        if beast_ability:
            knowledge_target = max(knowledge_target, 3)
            trigger_type = "beast_ability_observed"
        if beast_defeat:
            knowledge_target = max(knowledge_target, 3)
            trigger_type = "beast_defeated"
            defeated_inc = 1
        if contains_any_normalized_token(combined_text, CODEX_RACE_TRIGGER_LORE):
            knowledge_target = max(knowledge_target, 4)
            trigger_type = "codex_research_unlock"
        merge_trigger(
            CODEX_KIND_BEAST,
            beast_id,
            {
                "knowledge_target": knowledge_target,
                "trigger_type": trigger_type,
                "encounter_inc": 1,
                "defeated_inc": defeated_inc,
                "observed_abilities": collect_beast_observed_abilities(combined_text, beast_profile),
            },
        )

    npc_codex = state.get("npc_codex") if isinstance(state.get("npc_codex"), dict) else {}
    for npc_id in (npc_updates or []):
        npc = npc_codex.get(npc_id) if isinstance(npc_codex, dict) else None
        if not isinstance(npc, dict):
            continue
        race_name = str(npc.get("race") or "").strip()
        npc_name = str(npc.get("name") or "").strip()
        if not race_name:
            continue
        npc_race_result = resolve_codex_entity_ids(race_name, race_alias_index, exact_name_index.get("race_names") or {})
        for race_id in (npc_race_result.get("matched") or []):
            merge_trigger(
                CODEX_KIND_RACE,
                race_id,
                {
                    "knowledge_target": 2,
                    "trigger_type": "race_first_contact",
                    "encounter_inc": 1,
                    "known_individuals": [npc_name] if npc_name else [],
                },
            )

    return {
        "triggers": list(triggers_by_key.values()),
        "ambiguous": {
            "races": deep_copy(race_result.get("ambiguous") or []),
            "beasts": deep_copy(beast_result.get("ambiguous") or []),
        },
        "source_turn": int(turn_number or 0),
        "actor": actor,
        "action_type": action_type,
    }


def apply_codex_triggers(state: Dict[str, Any], trigger_bundle: Dict[str, Any], *, turn_number: int) -> List[Dict[str, Any]]:
    normalize_world_codex_structures(state)
    world = state.get("world") or {}
    races = world.get("races") if isinstance(world.get("races"), dict) else {}
    beasts = world.get("beast_types") if isinstance(world.get("beast_types"), dict) else {}
    codex = state.setdefault("codex", {})
    codex_races = codex.setdefault("races", {})
    codex_beasts = codex.setdefault("beasts", {})
    updates: List[Dict[str, Any]] = []

    for trigger in (trigger_bundle.get("triggers") or []):
        kind = str(trigger.get("kind") or "").strip().lower()
        entity_id = str(trigger.get("entity_id") or "").strip()
        if not entity_id:
            continue
        if kind == CODEX_KIND_RACE and entity_id not in races:
            continue
        if kind == CODEX_KIND_BEAST and entity_id not in beasts:
            continue
        profile = races.get(entity_id) if kind == CODEX_KIND_RACE else beasts.get(entity_id)
        if not isinstance(profile, dict):
            continue
        target_map = codex_races if kind == CODEX_KIND_RACE else codex_beasts
        entry_before = normalize_codex_entry_stable(target_map.get(entity_id), kind=kind)
        entry_after = deep_copy(entry_before)
        entry_after["encounter_count"] = int(entry_after.get("encounter_count", 0) or 0) + max(0, int(trigger.get("encounter_inc", 0) or 0))
        entry_after["knowledge_level"] = clamp(
            max(int(entry_after.get("knowledge_level", 0) or 0), int(trigger.get("knowledge_target", 0) or 0)),
            CODEX_KNOWLEDGE_LEVEL_MIN,
            CODEX_KNOWLEDGE_LEVEL_MAX,
        )
        if int(entry_after.get("knowledge_level", 0) or 0) > 0:
            entry_after["discovered"] = True
            if not int(entry_after.get("first_seen_turn", 0) or 0):
                entry_after["first_seen_turn"] = max(0, int(turn_number or 0))
        entry_after["last_updated_turn"] = max(int(entry_after.get("last_updated_turn", 0) or 0), max(0, int(turn_number or 0)))
        derived_blocks = codex_blocks_for_level(kind, int(entry_after.get("knowledge_level", 0) or 0))
        entry_after["known_blocks"] = [block for block in codex_block_order(kind) if block in set((entry_after.get("known_blocks") or []) + derived_blocks)]
        profile_facts = codex_facts_for_blocks(kind, profile, entry_after.get("known_blocks") or [])
        entry_after["known_facts"] = merge_known_facts_stable(entry_after.get("known_facts") or [], profile_facts)

        if kind == CODEX_KIND_RACE:
            entry_after["known_individuals"] = stable_sorted_unique_strings(
                list(entry_after.get("known_individuals") or []) + list(trigger.get("known_individuals") or []),
                limit=64,
            )
        else:
            entry_after["defeated_count"] = int(entry_after.get("defeated_count", 0) or 0) + max(0, int(trigger.get("defeated_inc", 0) or 0))
            entry_after["observed_abilities"] = stable_sorted_unique_strings(
                list(entry_after.get("observed_abilities") or []) + list(trigger.get("observed_abilities") or []),
                limit=64,
            )

        normalized_after = normalize_codex_entry_stable(entry_after, kind=kind)
        target_map[entity_id] = normalized_after
        if normalized_after != entry_before:
            updates.append(
                {
                    "kind": kind,
                    "entity_id": entity_id,
                    "name": str(profile.get("name") or entity_id),
                    "trigger_type": str(trigger.get("trigger_type") or ""),
                    "knowledge_before": int(entry_before.get("knowledge_level", 0) or 0),
                    "knowledge_after": int(normalized_after.get("knowledge_level", 0) or 0),
                    "new_blocks": [
                        block
                        for block in (normalized_after.get("known_blocks") or [])
                        if block not in (entry_before.get("known_blocks") or [])
                    ],
                }
            )

    for ambiguous_kind, rows in ((trigger_bundle.get("ambiguous") or {}).items()):
        for row in (rows or []):
            alias = str((row or {}).get("alias") or "").strip()
            entity_ids = [str(entry).strip() for entry in ((row or {}).get("entity_ids") or []) if str(entry).strip()]
            if not alias or len(entity_ids) < 2:
                continue
            updates.append(
                {
                    "kind": "ambiguous",
                    "entity_kind": ambiguous_kind[:-1] if ambiguous_kind.endswith("s") else ambiguous_kind,
                    "alias": alias,
                    "entity_ids": entity_ids,
                }
            )

    normalize_world_codex_structures(state)
    return updates
