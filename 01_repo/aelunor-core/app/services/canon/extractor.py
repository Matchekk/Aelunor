from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.adapters.ollama_config import OLLAMA_ADAPTER, OLLAMA_TEMPERATURE, OLLAMA_TIMEOUT_SEC
from app.catalogs.runtime_catalogs import CANON_EXTRACTOR_SCHEMA, RESPONSE_SCHEMA
from app.config.codex import CODEX_KIND_BEAST, CODEX_KIND_RACE
from app.config.errors import ERROR_CODE_JSON_REPAIR
from app.config.runtime import (
    EXTRACTION_QUARANTINE_DEFAULT_MAX,
    EXTRACTION_REASON_AMBIGUOUS_CLASS,
    EXTRACTION_REASON_CONFLICT_WITH_LLM,
    EXTRACTION_REASON_DUPLICATE,
    EXTRACTION_REASON_ENV_OBJECT,
    EXTRACTION_REASON_GENERIC_LOCATION,
    EXTRACTION_REASON_LOW_CONFIDENCE,
    EXTRACTION_REASON_MISSING_ACQUIRE,
    EXTRACTION_REASON_VERB_STYLE_SKILL,
)
from app.core.ids import deep_copy, make_id, utc_now
from app.prompts.system_prompts import CANON_EXTRACTOR_JSON_CONTRACT, CANON_EXTRACTOR_SYSTEM_PROMPT
from app.services.campaigns.party import active_party, campaign_slots, display_name_for_slot
from app.services.characters.resource_maxima import list_inventory_items
from app.services.characters.resources import resource_name_for_character
from app.services.items.inventory import ensure_item_shape, normalize_equipment_update_payload
from app.services.llm.client import LlmClientSettings, call_ollama_schema as _llm_call_ollama_schema
from app.services.extraction.heuristics import (
    build_heuristic_candidates,
    classify_heuristic_candidate,
    merge_safe_patch_additive,
    normalize_dynamic_skill_state,
    resolve_extractor_conflicts,
    safe_candidates_to_patch,
    skill_rank_sort_value,
    split_candidates,
)
from app.services.extraction.quarantine import (
    append_extraction_quarantine,
    default_extraction_quarantine,
    normalize_extraction_quarantine_meta,
)
from app.services.patch_payloads import blank_patch, normalize_patch_semantics
from app.services.state_basics import is_slot_id
from app.services.world.codex import normalize_codex_alias_text, normalize_codex_entry_stable
from app.services.world.math_utils import clamp
from app.services.world.npc import normalize_npc_alias
from app.services.world.progression import normalize_class_current
from app.services.world.scene import canonical_scene_id, extract_scene_candidates, is_generic_scene_identifier
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import (
    AUTO_ITEM_ACQUIRE_PATTERNS,
    AUTO_ITEM_EQUIP_PATTERNS,
    AUTO_ITEM_GENERIC_NAMES,
    ITEM_CHEST_KEYWORDS,
    ITEM_DETAIL_CLAUSE_MARKERS,
    ITEM_OFFHAND_KEYWORDS,
    ITEM_TRINKET_KEYWORDS,
    ITEM_WEAPON_KEYWORDS,
    STORY_LEARN_CUES,
    UNIVERSAL_SKILL_LIKE_NAMES,
)




def _default_call_ollama_schema(system: str, user: str, schema: Dict[str, Any], *, timeout: Optional[int] = None, temperature: float = 0.45) -> Dict[str, Any]:
    settings = LlmClientSettings(
        timeout_sec=OLLAMA_TIMEOUT_SEC,
        temperature=OLLAMA_TEMPERATURE,
        response_schema=RESPONSE_SCHEMA,
        error_code_json_repair=ERROR_CODE_JSON_REPAIR,
    )
    return _llm_call_ollama_schema(
        OLLAMA_ADAPTER,
        settings,
        system,
        user,
        schema,
        timeout=timeout,
        temperature=temperature,
    )


CANON_EXTRACTOR_MODE_FULL = "full"
CANON_EXTRACTOR_MODE_COMPACT = "compact"
CANON_EXTRACTOR_MODE_HEURISTIC_ONLY = "heuristic_only"
_CANON_EXTRACTOR_MODES = {
    CANON_EXTRACTOR_MODE_FULL,
    CANON_EXTRACTOR_MODE_COMPACT,
    CANON_EXTRACTOR_MODE_HEURISTIC_ONLY,
}


def canon_extractor_mode() -> str:
    """Steuert den LLM-Pfad des Canon-Extractors (AELUNOR_CANON_EXTRACTOR_MODE).

    full           -> altes Verhalten: LLM-Call mit komplettem STATE_PACKET
    compact        -> LLM-Call mit kompaktem Packet (Szene/Akteur/Delta statt Voll-State)
    heuristic_only -> kein LLM-Call, nur deterministische Heuristik-Kandidaten

    Default ist heuristic_only: Auf langen Kampagnen überschreitet das volle
    STATE_PACKET num_ctx (gemessen 33k Tokens bei 32k Fenster), Ollama truncated
    still und das Modell halluziniert dann Patches aus dem Nichts (z. B.
    meta.phase="lobby", erfundene Charaktere) — siehe
    docs/performance/iteration-log.md, Iteration 1.
    """
    raw = str(os.getenv("AELUNOR_CANON_EXTRACTOR_MODE", "")).strip().lower()
    return raw if raw in _CANON_EXTRACTOR_MODES else CANON_EXTRACTOR_MODE_HEURISTIC_ONLY


@dataclass(frozen=True)
class CanonExtractorDependencies:
    call_ollama_schema: Callable[..., Dict[str, Any]] = _default_call_ollama_schema


_DEPS = CanonExtractorDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def call_ollama_schema(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.call_ollama_schema(*args, **kwargs)































def sorted_npc_codex_entries(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    codex = (state.get("npc_codex") or {})
    entries = [entry for entry in codex.values() if isinstance(entry, dict) and entry.get("name")]
    entries.sort(
        key=lambda entry: (
            int(entry.get("relevance_score", 0) or 0),
            int(entry.get("last_seen_turn", 0) or 0),
            int(entry.get("mention_count", 0) or 0),
            str(entry.get("name", "")),
        ),
        reverse=True,
    )
    return entries

def build_npc_codex_summary(state: Dict[str, Any], *, limit: int = 16) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    for entry in sorted_npc_codex_entries(state)[: max(1, int(limit or 1))]:
        summary.append(
            {
                "npc_id": entry.get("npc_id"),
                "name": entry.get("name"),
                "race": entry.get("race"),
                "goal": entry.get("goal"),
                "level": entry.get("level"),
                "class_name": ((normalize_class_current(entry.get("class_current")) or {}).get("name") or ""),
                "class_rank": ((normalize_class_current(entry.get("class_current")) or {}).get("rank") or ""),
                "faction": entry.get("faction"),
                "role_hint": entry.get("role_hint"),
                "status": entry.get("status"),
                "scene_id": entry.get("last_seen_scene_id"),
                "last_seen_turn": entry.get("last_seen_turn"),
                "mention_count": entry.get("mention_count"),
                "relevance_score": entry.get("relevance_score"),
            }
        )
    return summary

def sorted_world_profiles(state: Dict[str, Any], *, kind: str) -> List[Tuple[str, Dict[str, Any]]]:
    world = state.get("world") or {}
    source = world.get("races") if kind == CODEX_KIND_RACE else world.get("beast_types")
    if not isinstance(source, dict):
        return []
    rows = [(str(entity_id), profile) for entity_id, profile in source.items() if isinstance(profile, dict)]
    rows.sort(key=lambda row: (normalize_codex_alias_text((row[1] or {}).get("name", "")), row[0]))
    return rows

def build_race_codex_summary(state: Dict[str, Any], *, limit: int = 32) -> List[Dict[str, Any]]:
    codex_races = (((state.get("codex") or {}).get("races") or {})
                   if isinstance(((state.get("codex") or {}).get("races") or {}), dict) else {})
    summary: List[Dict[str, Any]] = []
    for race_id, profile in sorted_world_profiles(state, kind=CODEX_KIND_RACE)[: max(1, int(limit or 1))]:
        entry = normalize_codex_entry_stable(codex_races.get(race_id), kind=CODEX_KIND_RACE)
        summary.append(
            {
                "race_id": race_id,
                "name": str((profile or {}).get("name") or race_id),
                "knowledge_level": int(entry.get("knowledge_level", 0) or 0),
                "discovered": bool(entry.get("discovered")),
                "known_blocks": deep_copy(entry.get("known_blocks") or []),
                "known_facts": deep_copy(entry.get("known_facts") or []),
                "encounter_count": int(entry.get("encounter_count", 0) or 0),
            }
        )
    return summary

def build_beast_codex_summary(state: Dict[str, Any], *, limit: int = 40) -> List[Dict[str, Any]]:
    codex_beasts = (((state.get("codex") or {}).get("beasts") or {})
                    if isinstance(((state.get("codex") or {}).get("beasts") or {}), dict) else {})
    summary: List[Dict[str, Any]] = []
    for beast_id, profile in sorted_world_profiles(state, kind=CODEX_KIND_BEAST)[: max(1, int(limit or 1))]:
        entry = normalize_codex_entry_stable(codex_beasts.get(beast_id), kind=CODEX_KIND_BEAST)
        summary.append(
            {
                "beast_id": beast_id,
                "name": str((profile or {}).get("name") or beast_id),
                "knowledge_level": int(entry.get("knowledge_level", 0) or 0),
                "discovered": bool(entry.get("discovered")),
                "known_blocks": deep_copy(entry.get("known_blocks") or []),
                "known_facts": deep_copy(entry.get("known_facts") or []),
                "encounter_count": int(entry.get("encounter_count", 0) or 0),
                "defeated_count": int(entry.get("defeated_count", 0) or 0),
            }
        )
    return summary

def build_world_element_summary(state: Dict[str, Any], *, limit: int = 16) -> List[Dict[str, Any]]:
    world = state.get("world") if isinstance(state.get("world"), dict) else {}
    rows = []
    for element_id, profile in ((world.get("elements") or {}).items()):
        if not isinstance(profile, dict):
            continue
        rows.append(
            {
                "id": element_id,
                "name": str(profile.get("name") or element_id),
                "origin": str(profile.get("origin") or "generated"),
                "theme": str(profile.get("theme") or ""),
                "status_effect_tags": deep_copy(profile.get("status_effect_tags") or []),
                "class_affinities": deep_copy(profile.get("class_affinities") or []),
                "skill_affinities": deep_copy(profile.get("skill_affinities") or []),
            }
        )
    rows.sort(key=lambda entry: (normalize_codex_alias_text(entry.get("name", "")), entry.get("id", "")))
    return rows[: max(1, int(limit or 1))]

def build_extractor_context_packet(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    source: str,
) -> str:
    world_settings = ((state.get("world") or {}).get("settings") or {})
    payload = {
        "source": source,
        "action_type": action_type,
        "actor": actor,
        "actor_display": display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor,
        "active_party": active_party(campaign),
        "display_party": [
            {"slot_id": slot_name, "display_name": display_name_for_slot(campaign, slot_name)}
            for slot_name in active_party(campaign)
        ],
        "characters": {
            slot_name: {
                "display_name": display_name_for_slot(campaign, slot_name),
                "scene_id": ((state.get("characters") or {}).get(slot_name) or {}).get("scene_id", ""),
                "element_affinities": ((state.get("characters") or {}).get(slot_name) or {}).get("element_affinities", []),
                "element_resistances": ((state.get("characters") or {}).get(slot_name) or {}).get("element_resistances", []),
                "element_weaknesses": ((state.get("characters") or {}).get(slot_name) or {}).get("element_weaknesses", []),
                "class_current": normalize_class_current(((state.get("characters") or {}).get(slot_name) or {}).get("class_current")),
                "skills": [
                    {
                        "id": skill.get("id"),
                        "name": skill.get("name"),
                        "rank": skill.get("rank"),
                        "level": skill.get("level"),
                        "tags": skill.get("tags", []),
                        "elements": skill.get("elements", []),
                        "element_primary": skill.get("element_primary"),
                    }
                    for skill in sorted(
                        [
                            normalize_dynamic_skill_state(
                                skill_value,
                                skill_id=skill_id,
                                skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
                                resource_name=resource_name_for_character(((state.get("characters") or {}).get(slot_name) or {}), world_settings),
                            )
                            for skill_id, skill_value in ((((state.get("characters") or {}).get(slot_name) or {}).get("skills") or {}).items())
                        ],
                        key=lambda entry: (skill_rank_sort_value(entry.get("rank")), entry.get("level", 1), entry.get("name", "")),
                        reverse=True,
                    )
                ],
                "inventory_names": [
                    ((state.get("items", {}) or {}).get(entry.get("item_id"), {}) or {}).get("name", "")
                    for entry in list_inventory_items(((state.get("characters") or {}).get(slot_name) or {}))
                ],
            }
            for slot_name in campaign_slots(campaign)
        },
        "known_scenes": {
            scene_id: scene.get("name", scene_id)
            for scene_id, scene in (state.get("scenes") or {}).items()
        },
        "known_items": {
            item_id: item.get("name", "")
            for item_id, item in (state.get("items") or {}).items()
        },
        "world_races": {
            race_id: {
                "name": race.get("name", race_id),
                "aliases": race.get("aliases", []),
            }
            for race_id, race in ((state.get("world") or {}).get("races") or {}).items()
        },
        "world_beast_types": {
            beast_id: {
                "name": beast.get("name", beast_id),
                "aliases": beast.get("aliases", []),
            }
            for beast_id, beast in ((state.get("world") or {}).get("beast_types") or {}).items()
        },
        "world_elements": {
            element_id: {
                "name": element.get("name", element_id),
                "origin": element.get("origin", "generated"),
                "aliases": element.get("aliases", []),
            }
            for element_id, element in ((state.get("world") or {}).get("elements") or {}).items()
        },
        "world_element_relations": (state.get("world") or {}).get("element_relations", {}),
        "world_element_paths": (state.get("world") or {}).get("element_class_paths", {}),
        "world_element_summary": build_world_element_summary(state, limit=18),
        "race_codex_summary": build_race_codex_summary(state, limit=20),
        "beast_codex_summary": build_beast_codex_summary(state, limit=20),
        "npc_codex_summary": build_npc_codex_summary(state, limit=18),
        "npc_codex": (state.get("npc_codex") or {}) if len((state.get("npc_codex") or {})) <= 24 else {},
        "source_text": source_text,
    }
    return json.dumps(payload, ensure_ascii=False)

def build_compact_extractor_context_packet(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    source: str,
) -> str:
    """Kompaktes Extractor-Packet: nur Grounding-Namen statt Voll-State.

    Der Extractor soll Fakten aus source_text gegen bekannte Entitaeten
    aufloesen — dafuer reichen Namenslisten und die aktive Party. Volle
    Codex-Profile, Element-Relationen und der komplette NPC-Codex haben
    das volle Packet auf >32k Tokens aufgeblasen (Truncation, Halluzination).
    """
    characters = state.get("characters") or {}
    world = state.get("world") or {}
    world_settings = world.get("settings") or {}
    party = active_party(campaign)
    actor_state = (characters.get(actor) or {}) if is_slot_id(actor) else {}
    scene_id = str(actor_state.get("scene_id") or "")
    scenes = state.get("scenes") or {}
    payload = {
        "source": source,
        "action_type": action_type,
        "actor": actor,
        "actor_display": display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor,
        "active_party": [
            {"slot_id": slot_name, "display_name": display_name_for_slot(campaign, slot_name)}
            for slot_name in party
        ],
        "characters": {
            slot_name: {
                "display_name": display_name_for_slot(campaign, slot_name),
                "scene_id": (characters.get(slot_name) or {}).get("scene_id", ""),
                "class_name": (normalize_class_current((characters.get(slot_name) or {}).get("class_current")) or {}).get("name", ""),
                "skill_names": sorted(
                    str((skill or {}).get("name") or skill_id)
                    for skill_id, skill in (((characters.get(slot_name) or {}).get("skills") or {}).items())
                ),
                "inventory_names": [
                    ((state.get("items", {}) or {}).get(entry.get("item_id"), {}) or {}).get("name", "")
                    for entry in list_inventory_items(characters.get(slot_name) or {})
                ],
                "resource_name": resource_name_for_character(characters.get(slot_name) or {}, world_settings),
            }
            for slot_name in party
        },
        "current_scene": {"scene_id": scene_id, "name": (scenes.get(scene_id) or {}).get("name", scene_id)},
        "known_scenes": {sid: (scene or {}).get("name", sid) for sid, scene in scenes.items()},
        "known_items": sorted(
            str((item or {}).get("name") or "")
            for item in (state.get("items") or {}).values()
            if (item or {}).get("name")
        )[:80],
        "known_npcs": [
            {
                "name": entry.get("name"),
                "race": entry.get("race"),
                "status": entry.get("status"),
                "scene_id": entry.get("scene_id"),
            }
            for entry in build_npc_codex_summary(state, limit=12)
        ],
        "known_races": sorted(
            str((race or {}).get("name") or race_id)
            for race_id, race in (world.get("races") or {}).items()
        )[:40],
        "known_beasts": sorted(
            str((beast or {}).get("name") or beast_id)
            for beast_id, beast in (world.get("beast_types") or {}).items()
        )[:40],
        "known_elements": sorted(
            str((element or {}).get("name") or element_id)
            for element_id, element in (world.get("elements") or {}).items()
        )[:24],
        "source_text": source_text,
    }
    return json.dumps(payload, ensure_ascii=False)


def normalize_extractor_output_patch(payload: Any) -> Dict[str, Any]:
    candidate = payload.get("patch") if isinstance(payload, dict) and "patch" in payload else payload
    return normalize_patch_semantics(candidate)












def call_canon_extractor(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    source: str,
) -> Dict[str, Any]:
    if not str(source_text or "").strip():
        return blank_patch()
    heuristic_candidates = build_heuristic_candidates(campaign, state, actor, action_type, source_text, source=source)
    classified_candidates = [
        classify_heuristic_candidate(candidate, campaign, state, actor, source_text)
        for candidate in heuristic_candidates
    ]
    safe_candidates, review_candidates, reject_candidates = split_candidates(classified_candidates)
    append_extraction_quarantine(state, review_candidates + reject_candidates)
    llm_patch = blank_patch()
    mode = canon_extractor_mode()
    if mode != CANON_EXTRACTOR_MODE_HEURISTIC_ONLY:
        packet_builder = (
            build_compact_extractor_context_packet
            if mode == CANON_EXTRACTOR_MODE_COMPACT
            else build_extractor_context_packet
        )
        context_packet = packet_builder(campaign, state, actor, action_type, source_text, source=source)
        user_prompt = (
            "STATE_PACKET(JSON):\n"
            + context_packet
            + "\n\nOUTPUT-KONTRAKT:\n"
            + CANON_EXTRACTOR_JSON_CONTRACT
            + "\n\nExtrahiere nur kanonische Fakten aus source_text als Patch. Keine Prosa. Keine Erklärungen."
        )
        try:
            payload = call_ollama_schema(
                CANON_EXTRACTOR_SYSTEM_PROMPT,
                user_prompt,
                CANON_EXTRACTOR_SCHEMA,
                timeout=120,
                temperature=0.1,
            )
            llm_patch = normalize_extractor_output_patch(payload)
        except Exception:
            llm_patch = blank_patch()
    safe_patch = safe_candidates_to_patch(safe_candidates, campaign, state, actor)
    merged_patch, merge_conflicts = merge_safe_patch_additive(llm_patch, safe_patch, state)
    if merge_conflicts:
        conflict_candidates: List[Dict[str, Any]] = []
        for conflict in merge_conflicts:
            conflict_candidates.append(
                {
                    "candidate_id": make_id("xc"),
                    "source": source,
                    "actor": actor,
                    "turn": max(0, int(((state.get("meta") or {}).get("turn", 0) or 0))),
                    "entity_type": str(conflict.get("entity_type") or "unknown"),
                    "operation": "merge_conflict",
                    "label": str(conflict.get("label") or "").strip(),
                    "normalized_key": f"conflict:{normalized_eval_text(str(conflict.get('label') or ''))}",
                    "evidence_text": str(source_text or ""),
                    "payload": deep_copy(conflict.get("payload") or {}),
                    "confidence": 0.35,
                    "status": "review",
                    "reason_code": EXTRACTION_REASON_CONFLICT_WITH_LLM,
                    "created_at": utc_now(),
                }
            )
        append_extraction_quarantine(state, conflict_candidates)
    return resolve_extractor_conflicts(campaign, state, actor, action_type, source_text, merged_patch, source=source)
