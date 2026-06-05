from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional

from app.adapters.ollama_config import OLLAMA_ADAPTER, OLLAMA_TEMPERATURE, OLLAMA_TIMEOUT_SEC
from app.catalogs.runtime_catalogs import RESPONSE_SCHEMA
from app.config.codex import NPC_STATUS_ALLOWED
from app.config.errors import ERROR_CODE_JSON_REPAIR
from app.prompts.system_prompts import NPC_EXTRACTOR_JSON_CONTRACT, NPC_EXTRACTOR_SYSTEM_PROMPT
from app.schemas.llm import NPC_EXTRACTOR_SCHEMA
from app.services.campaigns.party import active_party, campaign_slots, display_name_for_slot
from app.services.canon.extractor import build_npc_codex_summary
from app.services.llm.client import LlmClientSettings, call_ollama_schema as _llm_call_ollama_schema
from app.services.state_basics import is_slot_id
from app.services.world.codex import default_npc_entry, normalize_npc_entry
from app.services.world.math_utils import clamp
from app.services.world.npc import npc_id_from_name, normalize_npc_alias
from app.services.world.progression import normalize_class_current, normalize_resource_name
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import NPC_GENERIC_NAME_TOKENS


def _missing_dependency(name: str) -> Callable[..., Any]:
    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"NPC extractor dependency is not configured: {name}")
    return _missing


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


@dataclass(frozen=True)
class NpcExtractorDependencies:
    call_ollama_schema: Callable[..., Dict[str, Any]] = _default_call_ollama_schema
    class_rank_sort_value: Callable[..., int] = _missing_dependency("class_rank_sort_value")
    normalize_skill_store: Callable[..., Dict[str, Dict[str, Any]]] = _missing_dependency("normalize_skill_store")
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]] = _missing_dependency("normalize_dynamic_skill_state")
    merge_dynamic_skill: Callable[..., Dict[str, Any]] = _missing_dependency("merge_dynamic_skill")


_DEPS = NpcExtractorDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def call_ollama_schema(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.call_ollama_schema(*args, **kwargs)


def class_rank_sort_value(*args: Any, **kwargs: Any) -> int:
    return _DEPS.class_rank_sort_value(*args, **kwargs)


def normalize_skill_store(*args: Any, **kwargs: Any) -> Dict[str, Dict[str, Any]]:
    return _DEPS.normalize_skill_store(*args, **kwargs)


def normalize_dynamic_skill_state(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.normalize_dynamic_skill_state(*args, **kwargs)


def merge_dynamic_skill(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.merge_dynamic_skill(*args, **kwargs)

def scene_name_from_state(state: Dict[str, Any], scene_id: str) -> str:
    sid = str(scene_id or "").strip()
    if not sid:
        return ""
    scenes = state.get("scenes") or {}
    if sid in scenes:
        return str((scenes.get(sid) or {}).get("name") or sid).strip()
    map_nodes = ((state.get("map") or {}).get("nodes") or {})
    if sid in map_nodes:
        return str((map_nodes.get(sid) or {}).get("name") or sid).strip()
    return sid

def existing_pc_aliases(campaign: Dict[str, Any], state: Dict[str, Any]) -> set:
    aliases = set()
    for slot_name in campaign_slots(campaign):
        aliases.add(normalize_npc_alias(slot_name))
        aliases.add(normalize_npc_alias(display_name_for_slot(campaign, slot_name)))
        character = ((state.get("characters") or {}).get(slot_name) or {})
        aliases.add(normalize_npc_alias(str((character.get("bio") or {}).get("name") or "")))
    for player in (campaign.get("players") or {}).values():
        aliases.add(normalize_npc_alias(str((player or {}).get("display_name") or "")))
    aliases.discard("")
    return aliases

def is_generic_npc_name(name: str) -> bool:
    normalized = normalize_npc_alias(name)
    if not normalized:
        return True
    tokens = [token for token in normalized.split(" ") if token]
    if not tokens:
        return True
    if len(tokens) == 1 and tokens[0] in NPC_GENERIC_NAME_TOKENS:
        return True
    if len(tokens) <= 2 and all(token in NPC_GENERIC_NAME_TOKENS for token in tokens):
        return True
    return False

def resolve_npc_scene_hint(state: Dict[str, Any], scene_hint: str) -> str:
    hint = str(scene_hint or "").strip()
    if not hint:
        return ""
    scenes = state.get("scenes") or {}
    map_nodes = ((state.get("map") or {}).get("nodes") or {})
    if hint in scenes or hint in map_nodes:
        return hint
    normalized_hint = normalized_eval_text(hint)
    for scene_id, entry in scenes.items():
        if normalized_eval_text(str((entry or {}).get("name") or scene_id)) == normalized_hint:
            return scene_id
    for scene_id, entry in map_nodes.items():
        if normalized_eval_text(str((entry or {}).get("name") or scene_id)) == normalized_hint:
            return scene_id
    return ""

def best_matching_npc_id(state: Dict[str, Any], name: str) -> str:
    alias_index = state.get("npc_alias_index") or {}
    codex = state.get("npc_codex") or {}
    alias = normalize_npc_alias(name)
    if alias and alias in alias_index and alias_index[alias] in codex:
        return alias_index[alias]
    best_ratio = 0.0
    best_id = ""
    for npc_id, entry in codex.items():
        existing_alias = normalize_npc_alias(str((entry or {}).get("name") or ""))
        if not existing_alias:
            continue
        ratio = SequenceMatcher(None, alias, existing_alias).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_id = npc_id
    if best_ratio >= 0.9:
        return best_id
    return ""

def npc_relevance_score(upsert: Dict[str, Any], source_text: str) -> int:
    explicit = upsert.get("relevance_score")
    if explicit is not None:
        return max(0, int(explicit or 0))
    score = 0
    if str(upsert.get("goal") or "").strip():
        score += 2
    if str(upsert.get("faction") or "").strip() or str(upsert.get("role_hint") or "").strip():
        score += 2
    if str(upsert.get("backstory_short") or "").strip():
        score += 1
    if int(upsert.get("level", 0) or 0) > 0:
        score += 1
    name = str(upsert.get("name") or "").strip()
    normalized_source = normalized_eval_text(source_text)
    if name and normalized_eval_text(name) in normalized_source:
        score += 1
    if name and normalized_source.count(normalized_eval_text(name)) > 1:
        score += 1
    return score

def pick_more_specific_text(current: str, incoming: str) -> str:
    cur = str(current or "").strip()
    inc = str(incoming or "").strip()
    if not inc:
        return cur
    if not cur:
        return inc
    if normalized_eval_text(cur) in {"unbekannt", "unknown", "?"}:
        return inc
    if len(inc) > len(cur) + 6:
        return inc
    return cur

def apply_npc_upserts(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    npc_upserts: List[Dict[str, Any]],
    *,
    source_text: str,
    turn_number: int,
) -> List[str]:
    if not npc_upserts:
        return []
    state.setdefault("npc_codex", {})
    state.setdefault("npc_alias_index", {})
    codex = state["npc_codex"]
    alias_index = state["npc_alias_index"]
    pc_aliases = existing_pc_aliases(campaign, state)
    npc_resource_name = normalize_resource_name(str((((state.get("world") or {}).get("settings") or {}).get("resource_name") or "Aether")), "Aether")
    touched: List[str] = []
    for raw in npc_upserts:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        alias = normalize_npc_alias(name)
        if not alias or alias in pc_aliases or is_generic_npc_name(name):
            continue
        relevance = npc_relevance_score(raw, source_text)
        if relevance < 2:
            continue
        existing_id = best_matching_npc_id(state, name)
        npc_id = existing_id or npc_id_from_name(name)
        existing = normalize_npc_entry(codex.get(npc_id), fallback_npc_id=npc_id) if npc_id in codex else None
        entry = existing or default_npc_entry(npc_id, name)
        entry["name"] = pick_more_specific_text(entry.get("name", ""), name)
        entry["race"] = pick_more_specific_text(entry.get("race", "Unbekannt"), raw.get("race") or "")
        entry["age"] = pick_more_specific_text(entry.get("age", "Unbekannt"), raw.get("age") or "")
        entry["goal"] = pick_more_specific_text(entry.get("goal", ""), raw.get("goal") or "")
        entry["backstory_short"] = pick_more_specific_text(entry.get("backstory_short", ""), raw.get("backstory_short") or "")
        entry["role_hint"] = pick_more_specific_text(entry.get("role_hint", ""), raw.get("role_hint") or "")
        entry["faction"] = pick_more_specific_text(entry.get("faction", ""), raw.get("faction") or "")
        entry["level"] = clamp(
            max(int(entry.get("level", 1) or 1), int(raw.get("level", 0) or 0)),
            1,
            999,
        )
        entry["status"] = str(raw.get("status") or entry.get("status") or "active").strip().lower()
        if entry["status"] not in NPC_STATUS_ALLOWED:
            entry["status"] = "active"
        incoming_class = normalize_class_current(raw.get("class_current"))
        if incoming_class:
            existing_class = normalize_class_current(entry.get("class_current"))
            if not existing_class:
                entry["class_current"] = incoming_class
            else:
                merged_class = deep_copy(existing_class)
                merged_class["rank"] = (
                    incoming_class.get("rank")
                    if class_rank_sort_value(incoming_class.get("rank")) >= class_rank_sort_value(existing_class.get("rank"))
                    else existing_class.get("rank")
                )
                merged_class["level"] = max(
                    int(existing_class.get("level", 1) or 1),
                    int(incoming_class.get("level", 1) or 1),
                )
                merged_class["level_max"] = max(
                    int(existing_class.get("level_max", 10) or 10),
                    int(incoming_class.get("level_max", 10) or 10),
                )
                merged_class["xp"] = max(
                    int(existing_class.get("xp", 0) or 0),
                    int(incoming_class.get("xp", 0) or 0),
                )
                merged_class["xp_next"] = max(
                    1,
                    int(existing_class.get("xp_next", 1) or 1),
                    int(incoming_class.get("xp_next", 1) or 1),
                )
                merged_class["name"] = pick_more_specific_text(existing_class.get("name", ""), incoming_class.get("name", ""))
                merged_class["description"] = pick_more_specific_text(
                    existing_class.get("description", ""),
                    incoming_class.get("description", ""),
                )
                merged_class["affinity_tags"] = list(
                    dict.fromkeys(
                        [str(tag).strip() for tag in (existing_class.get("affinity_tags") or []) if str(tag).strip()]
                        + [str(tag).strip() for tag in (incoming_class.get("affinity_tags") or []) if str(tag).strip()]
                    )
                )
                incoming_asc = incoming_class.get("ascension") if isinstance(incoming_class.get("ascension"), dict) else {}
                existing_asc = merged_class.get("ascension") if isinstance(merged_class.get("ascension"), dict) else {}
                if incoming_asc and str(incoming_asc.get("status") or "none").strip().lower() != "none":
                    merged_class["ascension"] = deep_copy(incoming_asc)
                elif existing_asc:
                    merged_class["ascension"] = existing_asc
                entry["class_current"] = normalize_class_current(merged_class)

        incoming_skills = raw.get("skills") if isinstance(raw.get("skills"), dict) else {}
        if incoming_skills:
            existing_skill_store = normalize_skill_store(entry.get("skills") or {}, resource_name=npc_resource_name)
            for raw_skill_id, raw_skill_value in incoming_skills.items():
                incoming_skill = normalize_dynamic_skill_state(
                    raw_skill_value,
                    skill_id=str(raw_skill_id),
                    skill_name=(raw_skill_value or {}).get("name", raw_skill_id) if isinstance(raw_skill_value, dict) else str(raw_skill_id),
                    resource_name=npc_resource_name,
                    unlocked_from="NPCCodex",
                )
                existing_skill = existing_skill_store.get(incoming_skill["id"])
                existing_skill_store[incoming_skill["id"]] = (
                    merge_dynamic_skill(existing_skill, incoming_skill, resource_name=npc_resource_name)
                    if existing_skill
                    else incoming_skill
                )
            entry["skills"] = existing_skill_store
        entry["mention_count"] = int(entry.get("mention_count", 0) or 0) + 1
        entry["relevance_score"] = max(int(entry.get("relevance_score", 0) or 0), relevance)
        entry["last_seen_turn"] = max(int(entry.get("last_seen_turn", 0) or 0), int(turn_number or 0))
        if not entry.get("first_seen_turn"):
            entry["first_seen_turn"] = int(turn_number or 0)
        scene_id = resolve_npc_scene_hint(state, str(raw.get("scene_hint") or ""))
        if scene_id:
            entry["last_seen_scene_id"] = scene_id
        history_note = str(raw.get("history_note") or "").strip()
        if history_note:
            note = f"Turn {int(turn_number or 0)}: {history_note[:220]}"
            history = [str(item).strip() for item in (entry.get("history_notes") or []) if str(item).strip()]
            if not history or history[-1] != note:
                history.append(note)
            entry["history_notes"] = history[-24:]
        tags = [str(tag).strip() for tag in (entry.get("tags") or []) if str(tag).strip()]
        entry["tags"] = list(dict.fromkeys(tags + ["npc", "story_relevant"]))
        normalized_entry = normalize_npc_entry(entry, fallback_npc_id=npc_id)
        if not normalized_entry:
            continue
        codex[npc_id] = normalized_entry
        alias_index[normalize_npc_alias(normalized_entry["name"])] = npc_id
        touched.append(npc_id)
        if not existing:
            state.setdefault("events", []).append(
                f"NPC-Codex: {normalized_entry['name']} ({normalized_entry.get('race') or 'Unbekannt'}) wurde erfasst."
            )
    return list(dict.fromkeys(touched))

def build_npc_extractor_context_packet(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    gm_text: str,
) -> str:
    payload = {
        "actor": actor,
        "actor_display": display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor,
        "action_type": action_type,
        "active_party": [
            {"slot_id": slot_name, "display_name": display_name_for_slot(campaign, slot_name)}
            for slot_name in active_party(campaign)
        ],
        "known_npcs": build_npc_codex_summary(state, limit=28),
        "known_scenes": {
            scene_id: scene.get("name", scene_id)
            for scene_id, scene in (state.get("scenes") or {}).items()
        },
        "player_text": str(player_text or ""),
        "gm_text": str(gm_text or ""),
    }
    return json.dumps(payload, ensure_ascii=False)

def call_npc_extractor(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    gm_text: str,
) -> List[Dict[str, Any]]:
    if not str(player_text or "").strip() and not str(gm_text or "").strip():
        return []
    context_packet = build_npc_extractor_context_packet(campaign, state, actor, action_type, player_text, gm_text)
    user_prompt = (
        "STATE_PACKET(JSON):\n"
        + context_packet
        + "\n\nOUTPUT-KONTRAKT:\n"
        + NPC_EXTRACTOR_JSON_CONTRACT
    )
    try:
        payload = call_ollama_schema(
            NPC_EXTRACTOR_SYSTEM_PROMPT,
            user_prompt,
            NPC_EXTRACTOR_SCHEMA,
            timeout=120,
            temperature=0.15,
        )
        raw_entries = payload.get("npc_upserts") if isinstance(payload, dict) else []
        if not isinstance(raw_entries, list):
            return []
        return [entry for entry in raw_entries if isinstance(entry, dict)]
    except Exception:
        return []
