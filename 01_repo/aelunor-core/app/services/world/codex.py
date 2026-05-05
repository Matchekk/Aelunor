"""
Codex-Subsystem fuer Aelunor.

Verantwortlich fuer:
- Normalisierung und Kanonisierung von Codex-Eintraegen
- Alias-Index-Aufbau und Entity-Lookup
- NPC-Codex-Verwaltung
- Welt-Codex-Seeding aus Setup-Daten

Abhaengigkeiten auf globals (temporaer, bis DI-Refactor):
  make_id, utc_now, deep_copy, LOGGER
  -> werden per configure() injiziert wie in state_engine.py
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.world.collections import stable_sorted_mapping
from app.services.world.math_utils import clamp
from app.services.world.naming import strip_name_parenthetical
from app.services.world.npc import npc_id_from_name, normalize_npc_alias
from app.services.world.progression import (
    next_character_xp_for_level,
    normalize_class_current,
    normalize_resource_name,
)
from app.services.world.text_normalization import normalized_eval_text

# -- temporaere Global-Injektion (identisch zu state_engine.py Pattern) --
_CONFIGURED = False


def configure(main_globals: Dict[str, Any]) -> None:
    global _CONFIGURED
    globals().update(main_globals)
    _CONFIGURED = True


@dataclass(frozen=True)
class ElementNormalizationPort:
    normalize_element_profile: Any
    element_sort_key: Any
    build_element_alias_index: Any
    normalize_element_relations: Any
    normalize_element_class_paths: Any
    normalize_element_id_list: Any
    normalize_skill_elements_for_world: Any


@dataclass(frozen=True)
class SkillNormalizationPort:
    normalize_resource_name: Any
    normalize_dynamic_skill_state: Any
    normalize_skill_store: Any


@dataclass(frozen=True)
class CodexRuntimeDependencies:
    deep_copy: Any
    codex_kind_race: str
    codex_kind_beast: str
    codex_knowledge_level_min: int
    codex_knowledge_level_max: int
    race_blocks_by_level: Dict[int, List[str]]
    beast_blocks_by_level: Dict[int, List[str]]
    race_codex_block_order: List[str]
    beast_codex_block_order: List[str]
    normalize_race_profile: Any
    normalize_beast_profile: Any
    element_core_names: Tuple[str, ...]
    element_normalization: ElementNormalizationPort
    skill_normalization: SkillNormalizationPort
    codex_default_meta: Dict[str, Any]
    normalize_class_current: Any
    next_character_xp_for_level: Any
    npc_status_allowed: Set[str]
    npc_id_from_name: Any
    normalize_npc_alias: Any


def _codex_deps() -> CodexRuntimeDependencies:
    runtime = globals()
    return CodexRuntimeDependencies(
        deep_copy=runtime["deep_copy"],
        codex_kind_race=runtime["CODEX_KIND_RACE"],
        codex_kind_beast=runtime["CODEX_KIND_BEAST"],
        codex_knowledge_level_min=runtime["CODEX_KNOWLEDGE_LEVEL_MIN"],
        codex_knowledge_level_max=runtime["CODEX_KNOWLEDGE_LEVEL_MAX"],
        race_blocks_by_level=runtime["RACE_BLOCKS_BY_LEVEL"],
        beast_blocks_by_level=runtime["BEAST_BLOCKS_BY_LEVEL"],
        race_codex_block_order=runtime["RACE_CODEX_BLOCK_ORDER"],
        beast_codex_block_order=runtime["BEAST_CODEX_BLOCK_ORDER"],
        normalize_race_profile=runtime["normalize_race_profile"],
        normalize_beast_profile=runtime["normalize_beast_profile"],
        element_core_names=tuple(runtime["ELEMENT_CORE_NAMES"]),
        element_normalization=ElementNormalizationPort(
            normalize_element_profile=runtime["normalize_element_profile"],
            element_sort_key=runtime["element_sort_key"],
            build_element_alias_index=runtime["build_element_alias_index"],
            normalize_element_relations=runtime["normalize_element_relations"],
            normalize_element_class_paths=runtime["normalize_element_class_paths"],
            normalize_element_id_list=runtime["normalize_element_id_list"],
            normalize_skill_elements_for_world=runtime["normalize_skill_elements_for_world"],
        ),
        skill_normalization=SkillNormalizationPort(
            normalize_resource_name=runtime["normalize_resource_name"],
            normalize_dynamic_skill_state=runtime["normalize_dynamic_skill_state"],
            normalize_skill_store=runtime["normalize_skill_store"],
        ),
        codex_default_meta=runtime["CODEX_DEFAULT_META"],
        normalize_class_current=runtime["normalize_class_current"],
        next_character_xp_for_level=runtime["next_character_xp_for_level"],
        npc_status_allowed=runtime["NPC_STATUS_ALLOWED"],
        npc_id_from_name=runtime["npc_id_from_name"],
        normalize_npc_alias=runtime["normalize_npc_alias"],
    )


# ============================================
# GRUPPE A - Codex-Normalisierung
# ============================================

def codex_block_order(kind: str) -> List[str]:
    if str(kind or "").strip().lower() == CODEX_KIND_RACE:
        return list(RACE_CODEX_BLOCK_ORDER)
    return list(BEAST_CODEX_BLOCK_ORDER)

def codex_blocks_for_level(kind: str, level: int) -> List[str]:
    deps = _codex_deps()
    kind_key = str(kind or "").strip().lower()
    clamped_level = clamp(int(level or 0), deps.codex_knowledge_level_min, deps.codex_knowledge_level_max)
    block_map = deps.race_blocks_by_level if kind_key == deps.codex_kind_race else deps.beast_blocks_by_level
    ordered = deps.race_codex_block_order if kind_key == deps.codex_kind_race else deps.beast_codex_block_order
    unlocked: List[str] = []
    for idx in range(1, clamped_level + 1):
        for block in (block_map.get(idx) or []):
            if block in ordered and block not in unlocked:
                unlocked.append(block)
    return unlocked

def codex_facts_for_blocks(kind: str, profile: Dict[str, Any], blocks: List[str]) -> List[str]:
    kind_key = str(kind or "").strip().lower()
    block_map = race_profile_block_facts(profile) if kind_key == CODEX_KIND_RACE else beast_profile_block_facts(profile)
    ordered_blocks = [block for block in codex_block_order(kind_key) if block in (blocks or [])]
    facts: List[str] = []
    for block in ordered_blocks:
        facts = merge_known_facts_stable(facts, block_map.get(block) or [])
    return facts

def merge_known_facts_stable(existing: Any, incoming: Any) -> List[str]:
    merged: List[str] = []
    seen_keys = set()
    for source in (existing or []), (incoming or []):
        for raw in source:
            fact = str(raw or "").strip()
            if not fact:
                continue
            fact_key = normalize_codex_alias_text(fact)
            if not fact_key or fact_key in seen_keys:
                continue
            seen_keys.add(fact_key)
            merged.append(fact)
    return merged

def normalize_codex_alias_text(text: Any) -> str:
    alias = normalized_eval_text(text)
    alias = (
        alias.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    alias = re.sub(r"\b(der|die|das|ein|eine|einen|einem|einer)\b", " ", alias)
    alias = re.sub(r"[\-_]+", " ", alias)
    alias = re.sub(r"\s+", " ", alias).strip()
    return alias

def normalize_codex_entry_stable(raw_entry: Any, *, kind: str) -> Dict[str, Any]:
    deps = _codex_deps()
    kind_key = str(kind or "").strip().lower()
    base = deps.deep_copy(raw_entry) if isinstance(raw_entry, dict) else {}
    defaults = default_race_codex_entry("") if kind_key == deps.codex_kind_race else default_beast_codex_entry("")
    normalized = deps.deep_copy(defaults)
    normalized["discovered"] = bool(base.get("discovered", defaults["discovered"]))
    normalized["knowledge_level"] = clamp(
        int(base.get("knowledge_level", defaults["knowledge_level"]) or defaults["knowledge_level"]),
        deps.codex_knowledge_level_min,
        deps.codex_knowledge_level_max,
    )
    normalized["encounter_count"] = max(0, int(base.get("encounter_count", defaults["encounter_count"]) or defaults["encounter_count"]))
    normalized["first_seen_turn"] = max(0, int(base.get("first_seen_turn", defaults["first_seen_turn"]) or defaults["first_seen_turn"]))
    normalized["last_updated_turn"] = max(
        normalized["first_seen_turn"],
        int(base.get("last_updated_turn", defaults["last_updated_turn"]) or defaults["last_updated_turn"]),
    )
    order = deps.race_codex_block_order if kind_key == deps.codex_kind_race else deps.beast_codex_block_order
    raw_blocks = [str(block or "").strip() for block in (base.get("known_blocks") or []) if str(block or "").strip()]
    seen_blocks = set()
    known_blocks: List[str] = []
    for block in order:
        if block in raw_blocks and block not in seen_blocks:
            seen_blocks.add(block)
            known_blocks.append(block)
    normalized["known_blocks"] = known_blocks
    normalized["known_facts"] = merge_known_facts_stable(base.get("known_facts") or [], [])

    if kind_key == deps.codex_kind_race:
        normalized["known_individuals"] = stable_sorted_unique_strings(base.get("known_individuals") or [], limit=64)
    else:
        normalized["defeated_count"] = max(0, int(base.get("defeated_count", defaults.get("defeated_count", 0)) or defaults.get("defeated_count", 0)))
        normalized["observed_abilities"] = stable_sorted_unique_strings(base.get("observed_abilities") or [], limit=64)
    return normalized

def normalize_world_codex_structures(state: Dict[str, Any]) -> None:
    deps = _codex_deps()
    elements = deps.element_normalization
    world = state.setdefault("world", {})
    world_races = world.get("races") if isinstance(world.get("races"), dict) else {}
    world_beasts = world.get("beast_types") if isinstance(world.get("beast_types"), dict) else {}
    world_elements = world.get("elements") if isinstance(world.get("elements"), dict) else {}

    cleaned_races: Dict[str, Dict[str, Any]] = {}
    for raw_id, raw_profile in world_races.items():
        # TODO: externe Abhaengigkeit auf state_engine - nach race.py auslagern
        profile = deps.normalize_race_profile(raw_profile, fallback_id=str(raw_id))
        if not profile:
            continue
        cleaned_races[profile["id"]] = profile
    cleaned_races = stable_sorted_mapping(cleaned_races, key_fn=world_codex_sort_key)

    cleaned_beasts: Dict[str, Dict[str, Any]] = {}
    for raw_id, raw_profile in world_beasts.items():
        # TODO: externe Abhaengigkeit auf state_engine - nach beast.py auslagern
        profile = deps.normalize_beast_profile(raw_profile, fallback_id=str(raw_id))
        if not profile:
            continue
        cleaned_beasts[profile["id"]] = profile
    cleaned_beasts = stable_sorted_mapping(cleaned_beasts, key_fn=world_codex_sort_key)

    cleaned_elements: Dict[str, Dict[str, Any]] = {}
    for raw_id, raw_profile in world_elements.items():
        fallback_origin = "core" if normalize_codex_alias_text((raw_profile or {}).get("name", "")) in {
            normalize_codex_alias_text(name) for name in deps.element_core_names
        } else "generated"
        # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
        profile = elements.normalize_element_profile(raw_profile, fallback_id=str(raw_id), fallback_origin=fallback_origin)
        if not profile:
            continue
        cleaned_elements[profile["id"]] = profile
    cleaned_elements = stable_sorted_mapping(cleaned_elements, key_fn=elements.element_sort_key)

    world["races"] = cleaned_races
    world["beast_types"] = cleaned_beasts
    world["elements"] = cleaned_elements
    alias_indexes = build_world_alias_indexes(world)
    world["race_alias_index"] = alias_indexes["race_alias_index"]
    world["beast_alias_index"] = alias_indexes["beast_alias_index"]
    # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
    world["element_alias_index"] = elements.build_element_alias_index(cleaned_elements)
    # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
    world["element_relations"] = elements.normalize_element_relations(world.get("element_relations"), cleaned_elements)
    # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
    world["element_class_paths"] = elements.normalize_element_class_paths(
        world.get("element_class_paths"),
        cleaned_elements,
        ((state.get("setup") or {}).get("world") or {}).get("summary") or {},
    )

    codex = state.setdefault("codex", {})
    codex_meta = codex.get("meta") if isinstance(codex.get("meta"), dict) else {}
    normalized_meta = deps.deep_copy(deps.codex_default_meta)
    normalized_meta.update({str(key): value for key, value in codex_meta.items()})
    codex["meta"] = normalized_meta

    codex_races_raw = codex.get("races") if isinstance(codex.get("races"), dict) else {}
    codex_beasts_raw = codex.get("beasts") if isinstance(codex.get("beasts"), dict) else {}
    normalized_codex_races: Dict[str, Dict[str, Any]] = {}
    normalized_codex_beasts: Dict[str, Dict[str, Any]] = {}
    for race_id in cleaned_races.keys():
        normalized_codex_races[race_id] = normalize_codex_entry_stable(codex_races_raw.get(race_id), kind=deps.codex_kind_race)
    for beast_id in cleaned_beasts.keys():
        normalized_codex_beasts[beast_id] = normalize_codex_entry_stable(codex_beasts_raw.get(beast_id), kind=deps.codex_kind_beast)
    for raw_id, raw_entry in codex_races_raw.items():
        race_id = str(raw_id or "").strip()
        if race_id and race_id not in normalized_codex_races:
            normalized_codex_races[race_id] = normalize_codex_entry_stable(raw_entry, kind=deps.codex_kind_race)
    for raw_id, raw_entry in codex_beasts_raw.items():
        beast_id = str(raw_id or "").strip()
        if beast_id and beast_id not in normalized_codex_beasts:
            normalized_codex_beasts[beast_id] = normalize_codex_entry_stable(raw_entry, kind=deps.codex_kind_beast)

    codex["races"] = stable_sorted_mapping(
        normalized_codex_races,
        key_fn=lambda item: (
            normalize_codex_alias_text(str((((world.get("races") or {}).get(item[0]) or {}).get("name") or item[0]))),
            item[0],
        ),
    )
    codex["beasts"] = stable_sorted_mapping(
        normalized_codex_beasts,
        key_fn=lambda item: (
            normalize_codex_alias_text(str((((world.get("beast_types") or {}).get(item[0]) or {}).get("name") or item[0]))),
            item[0],
        ),
    )

def stable_sorted_unique_strings(values: Any, *, limit: int = 64) -> List[str]:
    cleaned = [str(value or "").strip() for value in (values or []) if str(value or "").strip()]
    deduped = sorted(set(cleaned), key=lambda value: normalize_codex_alias_text(value))
    return deduped[: max(1, int(limit or 1))]

def strip_codex_name_prefix(name: str) -> str:
    cleaned = str(name or "").strip()
    cleaned = re.sub(
        r"^(?:volk|stamm|orden)\s+(?:der|des)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned

def world_codex_sort_key(entry: Tuple[str, Dict[str, Any]]) -> Tuple[str, str]:
    entity_id, payload = entry
    return (normalize_codex_alias_text((payload or {}).get("name", "")), str(entity_id))


# ============================================
# GRUPPE B - Alias-Index & Lookup
# ============================================

def build_entity_alias_variants(name: str, aliases: Optional[List[str]] = None) -> List[str]:
    raw_candidates: List[str] = []
    base = str(name or "").strip()
    if base:
        raw_candidates.append(base)
        base_without_parenthetical = strip_name_parenthetical(base)
        if base_without_parenthetical:
            raw_candidates.append(base_without_parenthetical)
            stripped_prefix = strip_codex_name_prefix(base_without_parenthetical)
            if stripped_prefix:
                raw_candidates.append(stripped_prefix)
    for alias in (aliases or []):
        alias_text = str(alias or "").strip()
        if not alias_text:
            continue
        raw_candidates.append(alias_text)
        alias_without_parenthetical = strip_name_parenthetical(alias_text)
        if alias_without_parenthetical:
            raw_candidates.append(alias_without_parenthetical)

    normalized_variants: List[str] = []
    seen = set()
    for candidate in raw_candidates:
        normalized = normalize_codex_alias_text(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_variants.append(normalized)
        tokens = normalized.split()
        if len(tokens) > 1 and len(tokens[-1]) >= 4:
            short_alias = normalize_codex_alias_text(tokens[-1])
            if short_alias and short_alias not in seen:
                seen.add(short_alias)
                normalized_variants.append(short_alias)
            for short_variant in safe_last_token_variants(tokens[-1], max_variants=4):
                if short_variant and short_variant not in seen:
                    seen.add(short_variant)
                    normalized_variants.append(short_variant)
        if not tokens or len(tokens[-1]) < 4:
            continue
        prefix = tokens[:-1]
        for token_variant in safe_last_token_variants(tokens[-1], max_variants=6):
            rebuilt = " ".join([*prefix, token_variant]).strip()
            normalized_rebuilt = normalize_codex_alias_text(rebuilt)
            if not normalized_rebuilt or normalized_rebuilt in seen:
                continue
            seen.add(normalized_rebuilt)
            normalized_variants.append(normalized_rebuilt)
    return normalized_variants

def build_world_alias_indexes(world: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    race_aliases: Dict[str, set] = {}
    beast_aliases: Dict[str, set] = {}
    for race_id, race in ((world.get("races") or {}).items()):
        if not isinstance(race, dict):
            continue
        variants = build_entity_alias_variants(str(race.get("name") or ""), race.get("aliases") if isinstance(race.get("aliases"), list) else [])
        for alias in variants:
            race_aliases.setdefault(alias, set()).add(str(race_id))
    for beast_id, beast in ((world.get("beast_types") or {}).items()):
        if not isinstance(beast, dict):
            continue
        variants = build_entity_alias_variants(str(beast.get("name") or ""), beast.get("aliases") if isinstance(beast.get("aliases"), list) else [])
        for alias in variants:
            beast_aliases.setdefault(alias, set()).add(str(beast_id))
    race_index = {alias: sorted(ids) for alias, ids in stable_sorted_mapping(race_aliases).items()}
    beast_index = {alias: sorted(ids) for alias, ids in stable_sorted_mapping(beast_aliases).items()}
    return {"race_alias_index": race_index, "beast_alias_index": beast_index}

def build_world_exact_name_index(world: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    race_names: Dict[str, set] = {}
    beast_names: Dict[str, set] = {}
    for race_id, race in ((world.get("races") or {}).items()):
        name_norm = normalize_codex_alias_text((race or {}).get("name", ""))
        if name_norm:
            race_names.setdefault(name_norm, set()).add(str(race_id))
    for beast_id, beast in ((world.get("beast_types") or {}).items()):
        name_norm = normalize_codex_alias_text((beast or {}).get("name", ""))
        if name_norm:
            beast_names.setdefault(name_norm, set()).add(str(beast_id))
    return {
        "race_names": {alias: sorted(ids) for alias, ids in stable_sorted_mapping(race_names).items()},
        "beast_names": {alias: sorted(ids) for alias, ids in stable_sorted_mapping(beast_names).items()},
    }

def resolve_codex_entity_ids(text: str, alias_index: Dict[str, List[str]], exact_names: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
    normalized_text = normalize_codex_alias_text(text)
    if not normalized_text:
        return {"matched": [], "ambiguous": [], "matched_aliases": {}}
    matched_aliases: Dict[str, set] = {}
    ambiguous: List[Dict[str, Any]] = []
    search_space: Dict[str, List[str]] = {}

    for alias, ids in (alias_index or {}).items():
        alias_norm = normalize_codex_alias_text(alias)
        if not alias_norm:
            continue
        dedup_ids = sorted({str(entry).strip() for entry in (ids or []) if str(entry).strip()})
        if dedup_ids:
            search_space[alias_norm] = dedup_ids
    for alias, ids in (exact_names or {}).items():
        alias_norm = normalize_codex_alias_text(alias)
        if not alias_norm or alias_norm in search_space:
            continue
        dedup_ids = sorted({str(entry).strip() for entry in (ids or []) if str(entry).strip()})
        if dedup_ids:
            search_space[alias_norm] = dedup_ids

    for alias in sorted(search_space.keys(), key=lambda value: (-len(value), value)):
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        if not re.search(pattern, normalized_text):
            continue
        ids = search_space[alias]
        if len(ids) == 1:
            matched_aliases.setdefault(ids[0], set()).add(alias)
        else:
            ambiguous.append({"alias": alias, "entity_ids": list(ids)})

    matched_ids = sorted(matched_aliases.keys())
    return {
        "matched": matched_ids,
        "ambiguous": ambiguous,
        "matched_aliases": {entity_id: sorted(aliases) for entity_id, aliases in matched_aliases.items()},
    }

def safe_last_token_variants(token: str, *, max_variants: int = 6) -> List[str]:
    base = normalize_codex_alias_text(token)
    if not base or len(base) < 4:
        return [base] if base else []
    variants: List[str] = [base]
    suffixes = ("s", "e", "en", "er")
    for suffix in suffixes:
        if len(variants) >= max_variants:
            break
        if base.endswith(suffix) and len(base) - len(suffix) >= 3:
            variants.append(base[: -len(suffix)])
    for suffix in suffixes:
        if len(variants) >= max_variants:
            break
        if not base.endswith(suffix):
            variants.append(base + suffix)
    deduped: List[str] = []
    seen = set()
    for variant in variants:
        normalized = normalize_codex_alias_text(variant)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
        if len(deduped) >= max_variants:
            break
    return deduped


# ============================================
# GRUPPE C - NPC-Codex
# ============================================

def default_npc_entry(npc_id: str, name: str) -> Dict[str, Any]:
    return {
        "npc_id": npc_id,
        "name": str(name or "").strip(),
        "race": "Unbekannt",
        "age": "Unbekannt",
        "goal": "",
        "level": 1,
        "backstory_short": "",
        "role_hint": "",
        "faction": "",
        "last_seen_scene_id": "",
        "first_seen_turn": 0,
        "last_seen_turn": 0,
        "mention_count": 1,
        "relevance_score": 0,
        "status": "active",
        "tags": ["npc", "story_relevant"],
        "history_notes": [],
        "class_current": None,
        "skills": {},
        "xp_total": 0,
        "xp_current": 0,
        "xp_to_next": 120,
        "hp_current": 10,
        "hp_max": 10,
        "sta_current": 8,
        "sta_max": 8,
        "res_current": 4,
        "res_max": 4,
        "element_affinities": [],
        "element_resistances": [],
        "element_weaknesses": [],
        "conditions": [],
        "injuries": [],
        "scars": [],
    }

def normalize_npc_codex_state(campaign: Dict[str, Any]) -> None:
    deps = _codex_deps()
    elements = deps.element_normalization
    skills = deps.skill_normalization
    state = campaign.setdefault("state", {})
    state.setdefault("npc_codex", {})
    state.setdefault("npc_alias_index", {})
    cleaned_codex: Dict[str, Dict[str, Any]] = {}
    cleaned_alias: Dict[str, str] = {}
    for raw_id, raw_entry in (state.get("npc_codex") or {}).items():
        normalized_entry = normalize_npc_entry(raw_entry, fallback_npc_id=str(raw_id or "").strip())
        if not normalized_entry:
            continue
        npc_id = normalized_entry["npc_id"]
        # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
        normalized_entry["element_affinities"] = elements.normalize_element_id_list(normalized_entry.get("element_affinities") or [], state.get("world") or {})
        # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
        normalized_entry["element_resistances"] = elements.normalize_element_id_list(normalized_entry.get("element_resistances") or [], state.get("world") or {})
        # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
        normalized_entry["element_weaknesses"] = elements.normalize_element_id_list(normalized_entry.get("element_weaknesses") or [], state.get("world") or {})
        npc_resource_name = skills.normalize_resource_name((((normalized_entry.get("progression") or {}).get("resource_name")) or "Aether"), "Aether")
        normalized_skills: Dict[str, Dict[str, Any]] = {}
        for skill_id, raw_skill in ((normalized_entry.get("skills") or {}).items()):
            # TODO: externe Abhaengigkeit auf state_engine - nach skills.py auslagern
            skill = skills.normalize_dynamic_skill_state(raw_skill, skill_id=str(skill_id), resource_name=npc_resource_name)
            # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
            skill = elements.normalize_skill_elements_for_world(skill, state.get("world") or {})
            normalized_skills[skill["id"]] = skill
        normalized_entry["skills"] = normalized_skills
        cleaned_codex[npc_id] = normalized_entry
        alias = deps.normalize_npc_alias(normalized_entry.get("name", ""))
        if alias:
            cleaned_alias[alias] = npc_id
    for raw_alias, raw_npc_id in (state.get("npc_alias_index") or {}).items():
        alias = deps.normalize_npc_alias(str(raw_alias or ""))
        npc_id = str(raw_npc_id or "").strip()
        if alias and npc_id in cleaned_codex:
            cleaned_alias[alias] = npc_id
    state["npc_codex"] = cleaned_codex
    state["npc_alias_index"] = cleaned_alias

def normalize_npc_entry(raw: Any, *, fallback_npc_id: str = "") -> Optional[Dict[str, Any]]:
    deps = _codex_deps()
    skills = deps.skill_normalization
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    npc_id = str(raw.get("npc_id") or fallback_npc_id or deps.npc_id_from_name(name)).strip()
    if not npc_id:
        return None
    entry = default_npc_entry(npc_id, name)
    entry["race"] = str(raw.get("race") or entry["race"]).strip() or "Unbekannt"
    entry["age"] = str(raw.get("age") or entry["age"]).strip() or "Unbekannt"
    entry["goal"] = str(raw.get("goal") or "").strip()
    entry["level"] = clamp(int(raw.get("level", 1) or 1), 1, 999)
    entry["backstory_short"] = str(raw.get("backstory_short") or "").strip()
    entry["role_hint"] = str(raw.get("role_hint") or "").strip()
    entry["faction"] = str(raw.get("faction") or "").strip()
    entry["last_seen_scene_id"] = str(raw.get("last_seen_scene_id") or "").strip()
    entry["first_seen_turn"] = max(0, int(raw.get("first_seen_turn", 0) or 0))
    entry["last_seen_turn"] = max(entry["first_seen_turn"], int(raw.get("last_seen_turn", 0) or 0))
    entry["mention_count"] = max(1, int(raw.get("mention_count", 1) or 1))
    entry["relevance_score"] = max(0, int(raw.get("relevance_score", 0) or 0))
    status = str(raw.get("status") or "active").strip().lower()
    entry["status"] = status if status in deps.npc_status_allowed else "active"
    tags = [str(tag).strip() for tag in (raw.get("tags") or []) if str(tag).strip()]
    entry["tags"] = list(dict.fromkeys(tags or entry["tags"]))
    history_notes = [str(note).strip() for note in (raw.get("history_notes") or []) if str(note).strip()]
    entry["history_notes"] = history_notes[-20:]
    entry["class_current"] = deps.normalize_class_current(raw.get("class_current"))
    npc_resource_name = skills.normalize_resource_name((((raw.get("progression") or {}).get("resource_name")) or "Aether"), "Aether")
    # TODO: externe Abhaengigkeit auf state_engine - nach skills.py auslagern
    entry["skills"] = skills.normalize_skill_store(raw.get("skills") or {}, resource_name=npc_resource_name)
    entry["xp_total"] = max(0, int(raw.get("xp_total", entry.get("xp_total", 0)) or entry.get("xp_total", 0)))
    entry["xp_to_next"] = max(1, int(raw.get("xp_to_next", entry.get("xp_to_next", deps.next_character_xp_for_level(entry["level"]))) or deps.next_character_xp_for_level(entry["level"])))
    entry["xp_current"] = clamp(int(raw.get("xp_current", entry.get("xp_current", 0)) or entry.get("xp_current", 0)), 0, entry["xp_to_next"])
    entry["hp_max"] = max(1, int(raw.get("hp_max", entry.get("hp_max", 10)) or entry.get("hp_max", 10)))
    entry["hp_current"] = clamp(int(raw.get("hp_current", entry.get("hp_current", entry["hp_max"])) or entry.get("hp_current", entry["hp_max"])), 0, entry["hp_max"])
    entry["sta_max"] = max(0, int(raw.get("sta_max", entry.get("sta_max", 8)) or entry.get("sta_max", 8)))
    entry["sta_current"] = clamp(int(raw.get("sta_current", entry.get("sta_current", entry["sta_max"])) or entry.get("sta_current", entry["sta_max"])), 0, entry["sta_max"])
    entry["res_max"] = max(0, int(raw.get("res_max", entry.get("res_max", 4)) or entry.get("res_max", 4)))
    entry["res_current"] = clamp(int(raw.get("res_current", entry.get("res_current", entry["res_max"])) or entry.get("res_current", entry["res_max"])), 0, entry["res_max"])
    entry["element_affinities"] = [str(value).strip() for value in (raw.get("element_affinities") or []) if str(value).strip()][:8]
    entry["element_resistances"] = [str(value).strip() for value in (raw.get("element_resistances") or []) if str(value).strip()][:8]
    entry["element_weaknesses"] = [str(value).strip() for value in (raw.get("element_weaknesses") or []) if str(value).strip()][:8]
    entry["conditions"] = [str(cond).strip() for cond in (raw.get("conditions") or []) if str(cond).strip()][:12]
    entry["injuries"] = [deps.deep_copy(item) for item in (raw.get("injuries") or []) if isinstance(item, dict)][:16]
    entry["scars"] = [deps.deep_copy(item) for item in (raw.get("scars") or []) if isinstance(item, dict)][:24]
    return entry

def seed_npc_codex_from_story_cards(campaign: Dict[str, Any]) -> None:
    deps = _codex_deps()
    state = campaign.setdefault("state", {})
    codex = state.setdefault("npc_codex", {})
    alias_index = state.setdefault("npc_alias_index", {})
    turn = int(((state.get("meta") or {}).get("turn") or 0))
    for card in (campaign.get("boards", {}).get("story_cards") or []):
        if not isinstance(card, dict) or str(card.get("kind") or "").strip().lower() != "npc":
            continue
        name = str(card.get("title") or "").strip()
        if not name:
            continue
        npc_id = deps.npc_id_from_name(name)
        if npc_id in codex:
            continue
        entry = default_npc_entry(npc_id, name)
        entry["backstory_short"] = str(card.get("content") or "").strip()[:260]
        entry["first_seen_turn"] = turn
        entry["last_seen_turn"] = turn
        entry["relevance_score"] = 2
        entry["history_notes"] = [f"Aus Story-Karte übernommen: {entry['backstory_short'][:120]}"] if entry["backstory_short"] else []
        codex[npc_id] = entry
        alias = deps.normalize_npc_alias(name)
        if alias:
            alias_index[alias] = npc_id


# ============================================
# GRUPPE D - Codex-Seeding & World-Codex
# ============================================

def beast_profile_block_facts(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    return {
        "identity": [
            f"Kategorie: {profile.get('category') or 'Bestie'}",
            f"Gefahrenstufe: {int(profile.get('danger_rating', 1) or 1)}",
        ],
        "appearance": [f"Erscheinung: {profile.get('appearance') or 'Noch unbekannt.'}"],
        "habitat": [f"Lebensraum: {profile.get('habitat') or 'Noch unbekannt.'}"],
        "behavior": [f"Verhalten: {profile.get('behavior') or 'Noch unbekannt.'}"],
        "combat_style": [f"Kampfstil: {profile.get('combat_style') or 'Noch unbekannt.'}"],
        "known_abilities": [f"Bekannte Fähigkeiten: {', '.join(profile.get('known_abilities') or []) or 'Noch keine gesicherten Daten.'}"],
        "strengths": [f"Stärken: {', '.join(profile.get('strength_tags') or []) or 'Noch unbekannt.'}"],
        "weaknesses": [f"Schwächen: {', '.join(profile.get('weakness_tags') or []) or 'Noch unbekannt.'}"],
        "loot": [f"Loot-Hinweise: {', '.join(profile.get('loot_tags') or []) or 'Noch keine Hinweise.'}"],
        "lore": [f"Lore: {', '.join(profile.get('lore_notes') or []) or 'Noch keine Aufzeichnungen.'}"],
    }

def codex_seed_for_state(state: Dict[str, Any]) -> str:
    meta = state.setdefault("meta", {})
    seed = str(meta.get("world_codex_seed") or "").strip()
    if not seed:
        seed = make_id("wseed")
        meta["world_codex_seed"] = seed
    return seed

def default_beast_codex_entry(beast_id: str) -> Dict[str, Any]:
    return {
        "discovered": False,
        "knowledge_level": 0,
        "known_blocks": [],
        "known_facts": [],
        "encounter_count": 0,
        "first_seen_turn": 0,
        "last_updated_turn": 0,
        "defeated_count": 0,
        "observed_abilities": [],
    }

def default_race_codex_entry(race_id: str) -> Dict[str, Any]:
    return {
        "discovered": False,
        "knowledge_level": 0,
        "known_blocks": [],
        "known_facts": [],
        "encounter_count": 0,
        "first_seen_turn": 0,
        "last_updated_turn": 0,
        "known_individuals": [],
    }

def ensure_world_codex_from_setup(state: Dict[str, Any], setup_summary: Dict[str, Any]) -> None:
    world = state.setdefault("world", {})
    seed_hint = codex_seed_for_state(state)
    world_races = world.get("races") if isinstance(world.get("races"), dict) else {}
    world_beasts = world.get("beast_types") if isinstance(world.get("beast_types"), dict) else {}
    setup_summary = setup_summary or {}
    if not str(setup_summary.get("world_name") or "").strip():
        # TODO: externe Abhaengigkeit auf state_engine - nach world/naming.py auslagern
        setup_summary["world_name"] = generate_world_name(setup_summary, seed_hint)
    if not world_races:
        # TODO: externe Abhaengigkeit auf state_engine - nach race.py auslagern
        world["races"] = generate_world_race_profiles(setup_summary, seed_hint=seed_hint)
    if not world_beasts:
        # TODO: externe Abhaengigkeit auf state_engine - nach beast.py auslagern
        world["beast_types"] = generate_world_beast_profiles(setup_summary, seed_hint=seed_hint)
    # TODO: externe Abhaengigkeit auf state_engine - nach element.py auslagern
    ensure_world_element_system_from_setup(state, setup_summary)
    normalize_world_codex_structures(state)

def race_profile_block_facts(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    return {
        "identity": [
            f"Art: {profile.get('kind') or 'Volk'}",
            f"Seltenheit: {profile.get('rarity') or 'gewöhnlich'}",
            f"Kurzprofil: {profile.get('description_short') or 'Noch kein Eintrag.'}",
        ],
        "appearance": [f"Erscheinung: {profile.get('appearance') or 'Noch unbekannt.'}"],
        "culture": [
            f"Kultur: {profile.get('culture') or 'Noch unbekannt.'}",
            f"Temperament: {profile.get('temperament') or 'Noch unbekannt.'}",
        ],
        "homeland": [f"Heimat: {profile.get('homeland') or 'Unbekannt.'}"],
        "class_affinities": [f"Klassen-Affinitäten: {', '.join(profile.get('class_affinities') or []) or 'Keine gesicherten Daten.'}"],
        "skill_affinities": [f"Skill-Affinitäten: {', '.join(profile.get('skill_affinities') or []) or 'Keine gesicherten Daten.'}"],
        "strengths": [f"Stärken: {', '.join(profile.get('strength_tags') or []) or 'Noch unbekannt.'}"],
        "weaknesses": [f"Schwächen: {', '.join(profile.get('weakness_tags') or []) or 'Noch unbekannt.'}"],
        "relations": [f"Sozialer Ruf: {profile.get('social_reputation') or 'Noch unklar.'}"],
        "notable_individuals": [f"Bekannte Merkmale: {', '.join(profile.get('notable_traits') or []) or 'Noch keine bekannten Merkmale.'}"],
    }
