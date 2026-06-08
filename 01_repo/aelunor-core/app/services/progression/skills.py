from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from app.config.feature_flags import ENABLE_LEGACY_SHADOW_WRITEBACK
from app.config.progression import (
    DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
    LEGACY_SKILL_NAME_MAP,
    LEGACY_SKILL_TAGS,
    SKILL_ATTRIBUTE_MAP,
    SKILL_EVOLUTIONS,
    SKILL_FUSIONS,
    SKILL_KEYS,
    SKILL_OUTCOME_XP,
    SKILL_RANK_ORDER,
    SKILL_RANK_THRESHOLDS,
    SKILL_RANKS,
)
from app.core.ids import deep_copy, make_id
from app.services.characters.resources import resource_name_for_character
from app.services.extraction.abilities import clean_extracted_skill_name, split_extracted_skill_names
from app.services.world.math_utils import clamp
from app.services.world.progression import next_character_xp_for_level, normalize_class_current
from app.services.world.skill_costs import normalize_skill_cost as _normalize_skill_cost
from app.services.world.skill_ranks import (
    next_skill_xp_for_level as _next_skill_xp_for_level,
    normalize_skill_rank as _normalize_skill_rank,
    skill_rank_for_level as _skill_rank_for_level,
)
from app.services.world.skill_state import (
    normalize_cooldown_turns as _normalize_cooldown_turns,
    normalize_growth_potential as _normalize_growth_potential,
    normalize_optional_lower_text as _normalize_optional_lower_text,
    normalize_optional_strings as _normalize_optional_strings,
    normalize_optional_text as _normalize_optional_text,
    normalize_optional_unique_strings as _normalize_optional_unique_strings,
    normalize_power_rating as _normalize_power_rating,
    normalize_skill_element_fields as _normalize_skill_element_fields,
    normalize_skill_progression_fields as _normalize_skill_progression_fields,
)
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import ABILITY_UNLOCK_TRIGGER_PATTERNS


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    """Local copy to avoid a circular import with progression.manifestation
    (which imports this module). Mirrors manifestation.clamp_float."""
    try:
        return max(minimum, min(maximum, float(value)))
    except (TypeError, ValueError):
        return minimum


def skill_rank_for_level(level: int) -> str:
    return _skill_rank_for_level(level, skill_rank_thresholds=SKILL_RANK_THRESHOLDS)

def next_skill_xp_for_level(level: int) -> int:
    return _next_skill_xp_for_level(level)

def default_skill_state(skill_name: str) -> Dict[str, Any]:
    return {
        "id": skill_name,
        "level": 0,
        "xp": 0,
        "next_xp": next_skill_xp_for_level(0),
        "rank": "-",
        "mastery": 0,
        "path": "",
        "evolutions": [],
        "fusion_candidates": [],
        "unlocks": [],
        "awakened": False,
    }

def normalize_skill_state(skill_name: str, value: Any) -> Dict[str, Any]:
    skill = default_skill_state(skill_name)
    if isinstance(value, int):
        skill["level"] = clamp(value if value >= 0 else 0, 0, 20)
    elif isinstance(value, dict):
        skill.update({key: deep_copy(val) for key, val in value.items()})
    skill["id"] = skill_name
    skill["level"] = clamp(int(skill.get("level", 0) or 0), 0, 20)
    skill["next_xp"] = max(1, int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"])))
    skill["xp"] = clamp(int(skill.get("xp", 0) or 0), 0, skill["next_xp"])
    skill["rank"] = skill_rank_for_level(skill["level"])
    if skill["level"] <= 0:
        skill["mastery"] = 0
    elif skill["level"] >= 20:
        skill["mastery"] = 100
    else:
        skill["mastery"] = clamp(int((skill["xp"] / skill["next_xp"]) * 100), 0, 100)
    skill["path"] = str(skill.get("path", "") or "")
    skill["evolutions"] = list(skill.get("evolutions", []) or [])
    skill["fusion_candidates"] = list(skill.get("fusion_candidates", []) or [])
    skill["unlocks"] = list(skill.get("unlocks", []) or [])
    skill["awakened"] = bool(skill.get("awakened", False))
    skill["path_choice_available"] = bool(skill.get("path_choice_available", False))
    skill["path_options"] = list(skill.get("path_options", []) or [])
    return skill

def ability_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_eval_text(name)).strip("-")
    slug = slug[:36] or make_id("ability")
    return f"ability_{slug}"

def next_ability_xp_for_level(level: int) -> int:
    return next_skill_xp_for_level(level)

def default_ability_state(ability_id: str = "", ability_name: str = "") -> Dict[str, Any]:
    return {
        "id": ability_id or ability_id_from_name(ability_name or "faehigkeit"),
        "name": ability_name or "Unbenannte Fähigkeit",
        "owner": "",
        "description": "",
        "type": "active",
        "level": 1,
        "xp": 0,
        "next_xp": next_ability_xp_for_level(1),
        "rank": skill_rank_for_level(1),
        "mastery": 0,
        "charges": 0,
        "max_charges": 0,
        "cooldown_turns": 0,
        "cost": {},
        "tags": [],
        "scaling": {},
        "requirements": [],
        "source": "",
        "active": True,
        "awakened": False,
        "unlocks": [],
        "notes": "",
    }

def normalize_ability_state(value: Any, owner_slot: str = "") -> Dict[str, Any]:
    ability_name = ""
    if isinstance(value, dict):
        ability_name = str(value.get("name", "") or "")
    elif isinstance(value, str):
        ability_name = value
    ability = default_ability_state(ability_name=ability_name)
    if isinstance(value, str):
        ability["name"] = value.strip() or ability["name"]
    elif isinstance(value, dict):
        ability.update({key: deep_copy(val) for key, val in value.items()})

    ability["id"] = str(ability.get("id") or ability_id_from_name(str(ability.get("name", "") or ""))).strip() or ability_id_from_name(str(ability.get("name", "") or "faehigkeit"))
    ability["name"] = str(ability.get("name", "") or "Unbenannte Fähigkeit").strip() or "Unbenannte Fähigkeit"
    ability["owner"] = str(ability.get("owner") or owner_slot or "").strip()
    ability["description"] = str(ability.get("description", "") or "").strip()
    ability["type"] = str(ability.get("type", "active") or "active").strip() or "active"
    ability["level"] = clamp(int(ability.get("level", 1) or 1), 1, 20)
    ability["next_xp"] = max(1, int(ability.get("next_xp", next_ability_xp_for_level(ability["level"])) or next_ability_xp_for_level(ability["level"])))
    ability["xp"] = clamp(int(ability.get("xp", 0) or 0), 0, ability["next_xp"])
    ability["rank"] = skill_rank_for_level(ability["level"])
    if ability["level"] >= 20:
        ability["mastery"] = 100
    else:
        ability["mastery"] = clamp(int((ability["xp"] / ability["next_xp"]) * 100), 0, 100)
    ability["charges"] = max(0, int(ability.get("charges", 0) or 0))
    ability["max_charges"] = max(ability["charges"], int(ability.get("max_charges", 0) or 0))
    ability["cooldown_turns"] = max(0, int(ability.get("cooldown_turns", 0) or 0))
    raw_cost = ability.get("cost") or {}
    ability["cost"] = {
        str(key): int(val or 0)
        for key, val in raw_cost.items()
        if str(key).strip()
    } if isinstance(raw_cost, dict) else {}
    ability["tags"] = [str(entry).strip() for entry in (ability.get("tags") or []) if str(entry).strip()]
    raw_scaling = ability.get("scaling") or {}
    ability["scaling"] = {
        str(key): str(val).strip()
        for key, val in raw_scaling.items()
        if str(key).strip() and str(val).strip()
    } if isinstance(raw_scaling, dict) else {}
    ability["requirements"] = [deep_copy(entry) for entry in (ability.get("requirements") or []) if entry]
    ability["source"] = str(ability.get("source", "") or "").strip()
    ability["active"] = bool(ability.get("active", True))
    ability["awakened"] = bool(ability.get("awakened", False))
    ability["unlocks"] = [str(entry).strip() for entry in (ability.get("unlocks") or []) if str(entry).strip()]
    ability["notes"] = str(ability.get("notes", "") or "").strip()
    return ability

def skill_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(name)).strip("_")
    slug = slug[:48] or make_id("skill")
    if not slug.startswith("skill_"):
        slug = f"skill_{slug}"
    return slug

def display_skill_name_from_id(skill_id: str) -> str:
    base = str(skill_id or "").strip()
    if base.startswith("skill_"):
        base = base[6:]
    base = base.replace("_", " ").strip()
    if not base:
        return "Unbenannte Technik"
    return " ".join(part.capitalize() for part in base.split())

def infer_skill_name_from_description(raw_name: str, description: str) -> str:
    base_name = clean_extracted_skill_name(raw_name) or str(raw_name or "").strip()
    base_norm = normalized_eval_text(base_name)
    if not description.strip():
        return base_name
    candidates: List[str] = []
    direct_magic_match = re.search(r"\b([A-ZÄÖÜa-zäöüß][A-Za-zÄÖÜäöüß\-]{2,40}magie)\b", description, flags=re.IGNORECASE)
    if direct_magic_match:
        candidates.extend(split_extracted_skill_names(direct_magic_match.group(1)))
    for explicit_match in re.findall(
        r"(?:technik|zauber|ritual|kunst|fähigkeit|faehigkeit)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,60})",
        description,
        flags=re.IGNORECASE,
    ):
        candidates.extend(split_extracted_skill_names(explicit_match))
    for pattern in ABILITY_UNLOCK_TRIGGER_PATTERNS:
        for match in pattern.findall(description):
            candidates.extend(split_extracted_skill_names(match))
    deduped: List[str] = []
    seen = set()
    for candidate in candidates:
        normalized = normalized_eval_text(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(candidate)
    if not deduped:
        return base_name
    if base_norm:
        related = [
            candidate
            for candidate in deduped
            if normalized_eval_text(candidate).startswith(base_norm) or base_norm.startswith(normalized_eval_text(candidate))
        ]
        if related:
            return max(related, key=len)
    if len(deduped) == 1 and (not base_norm or len(base_norm) <= 9 or base_name.startswith("skill_")):
        return deduped[0]
    return base_name

def normalize_skill_store(skills: Any, *, resource_name: str) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for raw_key, raw_value in (skills or {}).items():
        guessed_name = ""
        description = ""
        if isinstance(raw_value, dict):
            guessed_name = str(raw_value.get("name") or "").strip()
            description = str(raw_value.get("description") or "").strip()
        raw_key_text = str(raw_key or "").strip()
        if not guessed_name:
            guessed_name = display_skill_name_from_id(raw_key_text)
        if guessed_name.startswith("skill_"):
            guessed_name = display_skill_name_from_id(guessed_name)
        guessed_name = infer_skill_name_from_description(guessed_name, description)
        guessed_name = clean_extracted_skill_name(guessed_name) or guessed_name
        normalized_skill = normalize_dynamic_skill_state(
            raw_value,
            skill_id=skill_id_from_name(guessed_name or raw_key_text),
            skill_name=guessed_name or raw_key_text,
            resource_name=resource_name,
            unlocked_from=(raw_value or {}).get("unlocked_from", "Story") if isinstance(raw_value, dict) else "Story",
        )
        normalized_skill["name"] = infer_skill_name_from_description(
            normalized_skill.get("name", ""),
            str(normalized_skill.get("description", "") or ""),
        )
        normalized_skill["name"] = clean_extracted_skill_name(normalized_skill.get("name", "")) or display_skill_name_from_id(normalized_skill["id"])
        normalized_skill["id"] = skill_id_from_name(normalized_skill["name"])
        existing = merged.get(normalized_skill["id"])
        merged[normalized_skill["id"]] = merge_dynamic_skill(existing, normalized_skill, resource_name=resource_name) if existing else normalized_skill
    consolidated: Dict[str, Dict[str, Any]] = {}
    for skill in sorted(merged.values(), key=lambda entry: len(str(entry.get("name", "") or "")), reverse=True):
        skill_name_norm = normalized_eval_text(skill.get("name", ""))
        matched_id = None
        for existing_id, existing_skill in consolidated.items():
            existing_name_norm = normalized_eval_text(existing_skill.get("name", ""))
            if not skill_name_norm or not existing_name_norm:
                continue
            if (
                skill_name_norm == existing_name_norm
                or skill_name_norm.startswith(existing_name_norm)
                or existing_name_norm.startswith(skill_name_norm)
            ):
                matched_id = existing_id
                break
        if matched_id:
            consolidated[matched_id] = merge_dynamic_skill(consolidated[matched_id], skill, resource_name=resource_name)
            consolidated[matched_id]["id"] = skill_id_from_name(consolidated[matched_id]["name"])
        else:
            consolidated[skill["id"]] = skill
    return consolidated

def dynamic_skill_default(skill_id: str = "", skill_name: str = "", resource_name: str = "Aether") -> Dict[str, Any]:
    clean_id = str(skill_id or skill_id_from_name(skill_name or "technik")).strip()
    clean_name = str(skill_name or display_skill_name_from_id(clean_id)).strip()
    return {
        "id": clean_id,
        "name": clean_name or "Unbenannte Technik",
        "rank": "F",
        "level": 1,
        "level_max": DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
        "tags": [],
        "description": "",
        "effect_summary": "",
        "power_rating": 5,
        "growth_potential": "mittel",
        "manifestation_source": None,
        "category": None,
        "class_affinity": None,
        "elements": [],
        "element_primary": None,
        "element_synergies": None,
        "cost": None,
        "price": None,
        "cooldown_turns": None,
        "unlocked_from": None,
        "synergy_notes": None,
        "xp": 0,
        "next_xp": next_skill_xp_for_level(1),
        "mastery": 0,
    }

def normalize_skill_rank(value: Any) -> str:
    return _normalize_skill_rank(value, skill_ranks=SKILL_RANKS)

def normalize_dynamic_skill_state(
    value: Any,
    *,
    skill_id: str = "",
    skill_name: str = "",
    resource_name: str = "Aether",
    unlocked_from: Optional[str] = None,
) -> Dict[str, Any]:
    if isinstance(value, int):
        payload: Dict[str, Any] = {"level": value}
    elif isinstance(value, str):
        payload = {"name": value}
    elif isinstance(value, dict):
        payload = deep_copy(value)
    else:
        payload = {}
    payload_name = str(payload.get("name") or "").strip()
    provided_name = str(skill_name or "").strip()
    fallback_name = str(payload_name or provided_name or display_skill_name_from_id(skill_id) or "Unbenannte Technik").strip()
    if provided_name:
        payload_name_norm = normalized_eval_text(payload_name)
        provided_name_norm = normalized_eval_text(provided_name)
        if (
            not payload_name
            or payload_name.startswith("skill_")
            or (
                payload_name_norm
                and provided_name_norm
                and (
                    provided_name_norm.startswith(payload_name_norm)
                    or payload_name_norm.startswith(provided_name_norm)
                )
                and len(provided_name) > len(payload_name)
            )
        ):
            fallback_name = provided_name
    if fallback_name.startswith("skill_"):
        fallback_name = display_skill_name_from_id(fallback_name)
    fallback_name = clean_extracted_skill_name(fallback_name) or fallback_name
    fallback_id = str(payload.get("id") or skill_id or skill_id_from_name(fallback_name)).strip()
    skill = dynamic_skill_default(fallback_id, fallback_name, resource_name)
    skill.update(payload)
    skill_name_value = str(skill.get("name") or fallback_name).strip() or fallback_name
    fallback_name_norm = normalized_eval_text(fallback_name)
    skill_name_norm = normalized_eval_text(skill_name_value)
    if (
        fallback_name
        and skill_name_value
        and (
            fallback_name_norm.startswith(skill_name_norm)
            or skill_name_norm.startswith(fallback_name_norm)
        )
        and len(fallback_name) > len(skill_name_value)
    ):
        skill_name_value = fallback_name
    if skill_name_value.startswith("skill_") or normalized_eval_text(skill_name_value) == normalized_eval_text(str(skill.get("id") or fallback_id)):
        skill_name_value = display_skill_name_from_id(str(skill.get("id") or fallback_id))
    skill_name_value = clean_extracted_skill_name(skill_name_value) or skill_name_value
    skill["name"] = skill_name_value
    skill["id"] = skill_id_from_name(skill_name_value or fallback_name)
    skill["rank"] = normalize_skill_rank(skill.get("rank"))
    skill["level_max"] = clamp(
        int(skill.get("level_max", DEFAULT_DYNAMIC_SKILL_LEVEL_MAX) or DEFAULT_DYNAMIC_SKILL_LEVEL_MAX),
        1,
        DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
    )
    skill["level"] = clamp(int(skill.get("level", 1) or 1), 1, skill["level_max"])
    skill["tags"] = [str(tag).strip() for tag in (skill.get("tags") or []) if str(tag).strip()]
    skill["description"] = str(skill.get("description", "") or "").strip() or f"{skill['name']} ist Teil der aktuellen Entwicklung."
    skill["effect_summary"] = str(skill.get("effect_summary", "") or "").strip() or skill["description"][:180]
    skill["growth_potential"] = _normalize_growth_potential(skill.get("growth_potential"))
    skill["power_rating"] = _normalize_power_rating(
        skill.get("power_rating"),
        rank=skill["rank"],
        level=int(skill.get("level", 1) or 1),
        skill_rank_sort_value=skill_rank_sort_value,
        clamp=clamp,
    )
    skill["manifestation_source"] = _normalize_optional_text(skill.get("manifestation_source"))
    skill["category"] = _normalize_optional_lower_text(skill.get("category"))
    skill["class_affinity"] = _normalize_optional_strings(skill.get("class_affinity"))
    skill["elements"], skill["element_primary"] = _normalize_skill_element_fields(skill.get("elements"), skill.get("element_primary"))
    skill["element_synergies"] = _normalize_optional_unique_strings(skill.get("element_synergies"))
    skill["cost"] = _normalize_skill_cost(skill.get("cost"), resource_name=resource_name)
    skill["price"] = str(skill.get("price", "") or "").strip() or None
    skill["cooldown_turns"] = _normalize_cooldown_turns(skill.get("cooldown_turns"))
    skill["unlocked_from"] = str(skill.get("unlocked_from") or unlocked_from or "Story").strip() or "Story"
    skill["synergy_notes"] = _normalize_optional_text(skill.get("synergy_notes"))
    skill["xp"], skill["next_xp"], skill["mastery"] = _normalize_skill_progression_fields(
        skill,
        next_skill_xp_for_level=next_skill_xp_for_level,
        clamp=clamp,
    )
    return skill

def merge_dynamic_skill(existing: Dict[str, Any], incoming: Dict[str, Any], *, resource_name: str) -> Dict[str, Any]:
    base = normalize_dynamic_skill_state(existing, resource_name=resource_name)
    new_data = normalize_dynamic_skill_state(
        incoming,
        skill_id=str(incoming.get("id") or base.get("id") or ""),
        skill_name=str(incoming.get("name") or base.get("name") or ""),
        resource_name=resource_name,
        unlocked_from=str(incoming.get("unlocked_from") or base.get("unlocked_from") or "Story"),
    )
    base_name_norm = normalized_eval_text(base.get("name", ""))
    new_name_norm = normalized_eval_text(new_data.get("name", ""))
    if new_data.get("name"):
        if not base.get("name"):
            base["name"] = new_data["name"]
        elif base_name_norm == new_name_norm:
            base["name"] = new_data["name"] if len(new_data["name"]) >= len(base["name"]) else base["name"]
        elif base_name_norm.startswith(new_name_norm) or new_name_norm.startswith(base_name_norm):
            base["name"] = new_data["name"] if len(new_data["name"]) >= len(base["name"]) else base["name"]
        else:
            base["name"] = new_data["name"]
    base["rank"] = new_data["rank"] if new_data["rank"] != "F" or base.get("rank") == "F" else base["rank"]
    base["level"] = max(int(base.get("level", 1) or 1), int(new_data.get("level", 1) or 1))
    base["level_max"] = max(int(base.get("level_max", 10) or 10), int(new_data.get("level_max", 10) or 10))
    base["tags"] = list(dict.fromkeys([*(base.get("tags") or []), *(new_data.get("tags") or [])]))
    if new_data.get("description"):
        base["description"] = new_data["description"]
    if new_data.get("effect_summary"):
        base["effect_summary"] = new_data["effect_summary"]
    if new_data.get("growth_potential"):
        base["growth_potential"] = new_data["growth_potential"]
    if int(new_data.get("power_rating", 0) or 0) > 0:
        base["power_rating"] = max(int(base.get("power_rating", 1) or 1), int(new_data.get("power_rating", 1) or 1))
    if new_data.get("manifestation_source"):
        base["manifestation_source"] = new_data["manifestation_source"]
    if new_data.get("category"):
        base["category"] = new_data["category"]
    if new_data.get("class_affinity"):
        base["class_affinity"] = list(dict.fromkeys([*(base.get("class_affinity") or []), *(new_data.get("class_affinity") or [])]))
    if new_data.get("elements"):
        base["elements"] = list(dict.fromkeys([*(base.get("elements") or []), *(new_data.get("elements") or [])]))
    if new_data.get("element_primary"):
        base["element_primary"] = new_data.get("element_primary")
        if base["element_primary"] and base["element_primary"] not in (base.get("elements") or []):
            base["elements"] = [base["element_primary"], *(base.get("elements") or [])]
    if new_data.get("element_synergies"):
        base["element_synergies"] = list(dict.fromkeys([*(base.get("element_synergies") or []), *(new_data.get("element_synergies") or [])]))
    if new_data.get("cost"):
        base["cost"] = new_data["cost"]
    if new_data.get("price"):
        base["price"] = new_data["price"]
    if new_data.get("cooldown_turns") is not None:
        base["cooldown_turns"] = new_data["cooldown_turns"]
    if new_data.get("synergy_notes"):
        base["synergy_notes"] = new_data["synergy_notes"]
    if new_data.get("unlocked_from"):
        base["unlocked_from"] = new_data["unlocked_from"]
    base["xp"] = max(int(base.get("xp", 0) or 0), int(new_data.get("xp", 0) or 0))
    base["next_xp"] = max(int(base.get("next_xp", 1) or 1), int(new_data.get("next_xp", 1) or 1))
    base["mastery"] = clamp(int(base.get("mastery", 0) or 0), 0, 100)
    return normalize_dynamic_skill_state(base, resource_name=resource_name)

def skill_rank_sort_value(rank: str) -> int:
    return SKILL_RANK_ORDER.get(str(rank or "F").upper(), -1)

def extract_skill_entries_for_character(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    resource_name = resource_name_for_character(character, world_settings)
    normalized: Dict[str, Any] = {}
    raw_skills = character.get("skills", {}) or {}
    for raw_key, raw_value in raw_skills.items():
        if raw_key in SKILL_KEYS:
            legacy = normalize_skill_state(raw_key, raw_value)
            if int(legacy.get("level", 0) or 0) <= 0:
                continue
            normalized[skill_id_from_name(LEGACY_SKILL_NAME_MAP.get(raw_key, skill_display_name(raw_key)))] = normalize_dynamic_skill_state(
                {
                    "id": skill_id_from_name(LEGACY_SKILL_NAME_MAP.get(raw_key, skill_display_name(raw_key))),
                    "name": LEGACY_SKILL_NAME_MAP.get(raw_key, skill_display_name(raw_key)),
                    "rank": normalize_skill_rank(legacy.get("rank")),
                    "level": max(1, int(legacy.get("level", 1) or 1)),
                    "level_max": 10,
                    "tags": LEGACY_SKILL_TAGS.get(raw_key, []),
                    "description": f"{LEGACY_SKILL_NAME_MAP.get(raw_key, skill_display_name(raw_key))} stammt aus einem älteren Spielstand.",
                    "cost": None,
                    "price": None,
                    "cooldown_turns": None,
                    "unlocked_from": "Legacy",
                    "synergy_notes": None,
                    "xp": int(legacy.get("xp", 0) or 0),
                    "next_xp": int(legacy.get("next_xp", next_skill_xp_for_level(max(1, int(legacy.get('level', 1) or 1)))) or next_skill_xp_for_level(max(1, int(legacy.get('level', 1) or 1)))),
                    "mastery": int(legacy.get("mastery", 0) or 0),
                },
                resource_name=resource_name,
            )
            continue
        skill = normalize_dynamic_skill_state(raw_value, skill_id=str(raw_key), skill_name=str((raw_value or {}).get("name") or raw_key), resource_name=resource_name)
        normalized[skill["id"]] = skill

    for ability in (character.get("abilities") or []):
        legacy_ability = normalize_ability_state(ability, str(character.get("slot_id", "") or ""))
        skill = normalize_dynamic_skill_state(
            {
                "id": skill_id_from_name(legacy_ability.get("name", legacy_ability.get("id", ""))),
                "name": legacy_ability.get("name"),
                "rank": normalize_skill_rank(legacy_ability.get("rank")),
                "level": max(1, int(legacy_ability.get("level", 1) or 1)),
                "level_max": 10,
                "tags": list(dict.fromkeys([*(legacy_ability.get("tags") or []), legacy_ability.get("type", "")])),
                "description": legacy_ability.get("description") or legacy_ability.get("notes") or f"{legacy_ability.get('name', 'Technik')} wurde aus einer älteren Fähigkeit migriert.",
                "cost": None if not legacy_ability.get("cost") else {"resource": resource_name, "amount": sum(int(v or 0) for v in (legacy_ability.get("cost") or {}).values())},
                "price": None,
                "cooldown_turns": legacy_ability.get("cooldown_turns"),
                "unlocked_from": legacy_ability.get("source") or "Legacy",
                "synergy_notes": None,
                "xp": int(legacy_ability.get("xp", 0) or 0),
                "next_xp": int(legacy_ability.get("next_xp", next_skill_xp_for_level(max(1, int(legacy_ability.get('level', 1) or 1)))) or next_skill_xp_for_level(max(1, int(legacy_ability.get('level', 1) or 1)))),
                "mastery": int(legacy_ability.get("mastery", 0) or 0),
            },
            resource_name=resource_name,
        )
        current = normalized.get(skill["id"])
        normalized[skill["id"]] = merge_dynamic_skill(current, skill, resource_name=resource_name) if current else skill
    return normalized

def build_skill_fusion_hints(skills: Dict[str, Any], *, resource_name: str) -> List[Dict[str, Any]]:
    entries = [
        normalize_dynamic_skill_state(
            value,
            skill_id=skill_id,
            skill_name=(value or {}).get("name", skill_id),
            resource_name=resource_name,
        )
        for skill_id, value in (skills or {}).items()
    ]
    maxed = [entry for entry in entries if int(entry.get("level", 1) or 1) >= int(entry.get("level_max", 10) or 10)]
    hints: List[Dict[str, Any]] = []
    for index, left in enumerate(maxed):
        left_tags = {normalized_eval_text(tag) for tag in (left.get("tags") or []) if normalized_eval_text(tag)}
        for right in maxed[index + 1 :]:
            right_tags = {normalized_eval_text(tag) for tag in (right.get("tags") or []) if normalized_eval_text(tag)}
            overlap = sorted(left_tags & right_tags)
            if not overlap:
                continue
            result_rank = left["rank"] if skill_rank_sort_value(left["rank"]) >= skill_rank_sort_value(right["rank"]) else right["rank"]
            hints.append(
                {
                    "with_id": right["id"],
                    "with_name": right["name"],
                    "tags_overlap": overlap,
                    "result_rank": result_rank,
                    "label": f"Fusion möglich: {left['name']} + {right['name']}",
                }
            )
    return hints

def skill_display_name(skill_name: str) -> str:
    return skill_name.replace("_", " ").title()

def skill_level_value(character: Dict[str, Any], skill_name: str) -> int:
    skills = character.get("skills", {}) or {}
    if skill_name in skills:
        raw_value = skills.get(skill_name)
        if isinstance(raw_value, dict) and "level" in raw_value:
            return int(raw_value.get("level", 0) or 0)
    for entry in skills.values():
        if not isinstance(entry, dict):
            continue
        if normalized_eval_text(entry.get("name", "")) == normalized_eval_text(skill_name):
            return int(entry.get("level", 0) or 0)
    legacy = normalize_skill_state(skill_name, skills.get(skill_name, default_skill_state(skill_name)))
    return int(legacy.get("level", 0) or 0)

def class_affinity_match(skill_tags: List[str], class_affinity_tags: List[str]) -> bool:
    skill_set = {normalized_eval_text(tag) for tag in (skill_tags or []) if normalized_eval_text(tag)}
    class_set = {normalized_eval_text(tag) for tag in (class_affinity_tags or []) if normalized_eval_text(tag)}
    return bool(skill_set & class_set)

def effective_skill_progress_multiplier(character: Dict[str, Any], skill: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> float:
    world_settings = world_settings or {}
    current_class = normalize_class_current(character.get("class_current"))
    if not current_class:
        return float(world_settings.get("onclass_xp_multiplier", 1.0) or 1.0)
    if class_affinity_match(skill.get("tags") or [], current_class.get("affinity_tags") or []):
        return float(world_settings.get("onclass_xp_multiplier", 1.0) or 1.0)
    return float(world_settings.get("offclass_xp_multiplier", 0.7) or 0.7)

def ensure_progression_shape(character: Dict[str, Any]) -> None:
    progression = character.setdefault("progression", {})
    progression.setdefault("rank", 1)
    progression.setdefault("xp", 0)
    progression.setdefault("next_xp", 100)
    progression.setdefault("system_level", 1)
    progression.setdefault("system_xp", 0)
    progression.setdefault("next_system_xp", 100)
    progression.setdefault("resource_name", "Aether")
    progression.setdefault("resource_current", 5)
    progression.setdefault("resource_max", 5)
    progression.setdefault("system_fragments", 0)
    progression.setdefault("system_cores", 0)
    progression.setdefault("attribute_points", 0)
    progression.setdefault("skill_points", 0)
    progression.setdefault("talent_points", 0)
    progression.setdefault("paths", [])
    progression.setdefault("potential_cards", [])

def ensure_character_progression_core(character: Dict[str, Any]) -> None:
    level = max(1, int(character.get("level", 1) or 1))
    xp_to_next = max(1, int(character.get("xp_to_next", next_character_xp_for_level(level)) or next_character_xp_for_level(level)))
    xp_current = clamp(int(character.get("xp_current", 0) or 0), 0, xp_to_next)
    xp_total = max(xp_current, int(character.get("xp_total", xp_current) or xp_current))
    character["level"] = level
    character["xp_to_next"] = xp_to_next
    character["xp_current"] = xp_current
    character["xp_total"] = xp_total
    recent = character.get("recent_progression_events")
    if not isinstance(recent, list):
        character["recent_progression_events"] = []
    else:
        character["recent_progression_events"] = [deep_copy(entry) for entry in recent if isinstance(entry, dict)][-40:]
    seeds = character.get("class_path_seeds")
    if not isinstance(seeds, list):
        character["class_path_seeds"] = []
    else:
        normalized_seeds: List[Dict[str, Any]] = []
        seen_ids = set()
        for seed in seeds:
            if not isinstance(seed, dict):
                continue
            seed_id = str(seed.get("id") or "").strip()
            if not seed_id or seed_id in seen_ids:
                continue
            seen_ids.add(seed_id)
            normalized_seeds.append(
                {
                    "id": seed_id,
                    "name": str(seed.get("name") or "").strip() or seed_id,
                    "theme_tags": [str(tag).strip() for tag in (seed.get("theme_tags") or []) if str(tag).strip()][:8],
                    "source_turn": max(0, int(seed.get("source_turn", 0) or 0)),
                    "confidence": clamp_float(seed.get("confidence", 0.0), 0.0, 1.0),
                    "status": str(seed.get("status") or "latent").strip().lower() if str(seed.get("status") or "").strip().lower() in {"latent", "confirmed", "unlocked"} else "latent",
                    "related_skill_ids": [str(value).strip() for value in (seed.get("related_skill_ids") or []) if str(value).strip()][:6],
                }
            )
        character["class_path_seeds"] = normalized_seeds[-20:]

def progression_speed_multiplier(world_settings: Optional[Dict[str, Any]] = None) -> float:
    speed = str(((world_settings or {}).get("progression_speed") or "normal")).strip().lower()
    if speed == "langsam":
        return 0.82
    if speed == "schnell":
        return 1.22
    return 1.0

def append_recent_progression_event(character: Dict[str, Any], event: Dict[str, Any]) -> None:
    recent = character.setdefault("recent_progression_events", [])
    if not isinstance(recent, list):
        recent = []
        character["recent_progression_events"] = recent
    recent.append(
        {
            "type": str(event.get("type") or ""),
            "severity": str(event.get("severity") or "medium"),
            "source_turn": int(event.get("source_turn", 0) or 0),
            "reason": str(event.get("reason") or "").strip(),
            "target_skill_id": str(event.get("target_skill_id") or "").strip(),
            "target_class_id": str(event.get("target_class_id") or "").strip(),
            "target_element_id": str(event.get("target_element_id") or "").strip(),
        }
    )
    if len(recent) > 40:
        del recent[:-40]

def resolve_skill_id_for_event(character: Dict[str, Any], raw_skill_id: str) -> str:
    skill_store = character.get("skills") or {}
    if raw_skill_id in skill_store:
        return raw_skill_id
    normalized = normalized_eval_text(raw_skill_id)
    if not normalized:
        return ""
    normalized_compact = re.sub(r"[^a-z0-9]+", "", normalized)
    for skill_id, skill_value in skill_store.items():
        skill_name = str((skill_value or {}).get("name") or skill_id)
        candidate_ids = {
            normalized_eval_text(skill_id),
            normalized_eval_text(skill_name),
            normalized_eval_text(skill_id_from_name(skill_name)),
        }
        if normalized in candidate_ids:
            return skill_id
        candidate_compact = {re.sub(r"[^a-z0-9]+", "", entry) for entry in candidate_ids if entry}
        if normalized_compact and normalized_compact in candidate_compact:
            return skill_id
        for candidate in candidate_ids:
            if candidate and normalized and (
                candidate.startswith(normalized)
                or normalized.startswith(candidate)
                or SequenceMatcher(None, candidate, normalized).ratio() >= 0.92
            ):
                return skill_id
        if normalized_eval_text(skill_name) == normalized:
            return skill_id
    return ""

def apply_system_xp(character: Dict[str, Any], amount: int) -> None:
    if amount <= 0:
        return
    ensure_progression_shape(character)
    ensure_character_progression_core(character)
    progression = character["progression"]
    xp_gain = max(0, int(amount or 0))
    character["xp_total"] = int(character.get("xp_total", 0) or 0) + xp_gain
    character["xp_current"] = int(character.get("xp_current", 0) or 0) + xp_gain
    progression["system_xp"] = int(progression.get("system_xp", 0) or 0) + max(1, xp_gain // 3)
    while character["xp_current"] >= int(character.get("xp_to_next", next_character_xp_for_level(character["level"])) or next_character_xp_for_level(character["level"])):
        required = int(character.get("xp_to_next", next_character_xp_for_level(character["level"])) or next_character_xp_for_level(character["level"]))
        character["xp_current"] = max(0, int(character.get("xp_current", 0) or 0) - required)
        character["level"] = int(character.get("level", 1) or 1) + 1
        character["xp_to_next"] = next_character_xp_for_level(character["level"])
        progression["attribute_points"] = int(progression.get("attribute_points", 0) or 0) + 1
        progression["skill_points"] = int(progression.get("skill_points", 0) or 0) + 1
    while progression["system_xp"] >= int(progression.get("next_system_xp", 100) or 100):
        progression["system_xp"] -= int(progression.get("next_system_xp", 100) or 100)
        progression["system_level"] = int(progression.get("system_level", 1) or 1) + 1
        progression["talent_points"] = int(progression.get("talent_points", 0) or 0) + 1
        progression["next_system_xp"] = 100 + ((int(progression["system_level"]) - 1) * 50)
    character["xp_current"] = clamp(int(character.get("xp_current", 0) or 0), 0, int(character.get("xp_to_next", 1) or 1))

def refresh_skill_progression(character: Dict[str, Any]) -> None:
    ensure_progression_shape(character)
    ensure_character_progression_core(character)
    resource_name = resource_name_for_character(character)
    character["skills"] = {
        skill_id: normalize_dynamic_skill_state(
            skill_value,
            skill_id=skill_id,
            skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
            resource_name=resource_name,
            unlocked_from=(skill_value or {}).get("unlocked_from", "Story") if isinstance(skill_value, dict) else "Story",
        )
        for skill_id, skill_value in (character.get("skills") or {}).items()
    }
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        character["abilities"] = []
    else:
        character.pop("abilities", None)

def grant_skill_xp(
    character: Dict[str, Any],
    skill_name: str,
    outcome: str,
    *,
    world_settings: Optional[Dict[str, Any]] = None,
) -> List[str]:
    skill_store = character.setdefault("skills", {})
    if not skill_store:
        return []
    resolved_skill_id = resolve_skill_id_for_event(character, skill_name) or skill_id_from_name(skill_name)
    if resolved_skill_id not in skill_store:
        return []
    outcome_key = str(outcome or "normal").strip().lower()
    base_xp = {
        "minor": 8,
        "small": 10,
        "normal": 16,
        "major": 28,
        "critical": 40,
    }.get(outcome_key, 16)
    resource_name = resource_name_for_character(character)
    skill = normalize_dynamic_skill_state(skill_store[resolved_skill_id], skill_id=resolved_skill_id, resource_name=resource_name)
    multiplier = effective_skill_progress_multiplier(character, skill, world_settings or {})
    gained = max(1, int(round(base_xp * multiplier)))
    skill["xp"] = int(skill.get("xp", 0) or 0) + gained
    leveled = False
    while skill["level"] < skill["level_max"] and skill["xp"] >= int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"])):
        required = int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"]))
        skill["xp"] = max(0, int(skill.get("xp", 0) or 0) - required)
        skill["level"] += 1
        skill["next_xp"] = next_skill_xp_for_level(skill["level"])
        leveled = True
    skill["mastery"] = clamp(int((int(skill.get("xp", 0) or 0) / max(1, int(skill.get("next_xp", 1) or 1))) * 100), 0, 100)
    skill_store[resolved_skill_id] = normalize_dynamic_skill_state(skill, resource_name=resource_name)
    messages: List[str] = []
    if leveled:
        messages.append(f"Skill-Fortschritt: {skill['name']} erreicht Lv {skill['level']}/{skill['level_max']}.")
    return messages

def parse_skill_event(campaign: Dict[str, Any], event_text: str) -> Optional[Dict[str, str]]:
    text = str(event_text or "").strip()
    if not text:
        return None
    marker = re.match(r"SKILL_XP\[(slot_[0-9]+):([^:\]]+):([^:\]]+)\]", text, flags=re.IGNORECASE)
    if marker:
        return {
            "actor": marker.group(1).strip(),
            "skill": marker.group(2).strip(),
            "outcome": marker.group(3).strip().lower(),
        }
    return None

def apply_skill_events(campaign: Dict[str, Any], state: Dict[str, Any], events: List[str]) -> List[str]:
    messages: List[str] = []
    for event_text in (events or []):
        parsed = parse_skill_event(campaign, str(event_text or ""))
        if not parsed:
            continue
        actor = parsed.get("actor", "")
        skill_name = parsed.get("skill", "")
        outcome = parsed.get("outcome", "normal")
        if actor not in (state.get("characters") or {}):
            continue
        character = (state.get("characters") or {}).get(actor) or {}
        messages.extend(grant_skill_xp(character, skill_name, outcome, world_settings=((state.get("world") or {}).get("settings") or {})))
        (state.get("characters") or {})[actor] = character
    return messages
