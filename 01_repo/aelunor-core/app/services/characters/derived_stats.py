from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.config.progression import RESISTANCE_KEYS, SKILL_ATTRIBUTE_MAP
from app.services.characters.resource_maxima import (
    ensure_character_modifier_shape,
    item_modifier_value,
    item_weight,
    iter_equipped_item_ids,
    list_inventory_items,
)


def calculate_carry_limit(character: Dict[str, Any]) -> int:
    return 10 + (int((character.get("attributes") or {}).get("str", 0) or 0) * 2)


def calculate_carry_weight(character: Dict[str, Any], items_db: Dict[str, Any]) -> int:
    total = 0
    for entry in list_inventory_items(character):
        total += item_weight(items_db.get(entry["item_id"], {})) * entry["stack"]
    for item_id in iter_equipped_item_ids(character):
        total += item_weight(items_db.get(item_id, {}))
    return total


def calculate_resistances(character: Dict[str, Any], items_db: Dict[str, Any]) -> Dict[str, int]:
    res = {key: 0 for key in RESISTANCE_KEYS}
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        for key in RESISTANCE_KEYS:
            res[key] += item_modifier_value(item, kind="resistance", stat=key)
    for effect in character.get("effects", []) or []:
        for modifier in effect.get("modifiers", []) or []:
            if modifier.get("kind") == "resistance" and modifier.get("stat") in res:
                res[modifier["stat"]] += int(modifier.get("value", 0) or 0)
    for modifier in (ensure_character_modifier_shape(character).get("derived") or []):
        if not isinstance(modifier, dict):
            continue
        stat_name = str(modifier.get("stat", "") or "")
        if not stat_name.startswith("resistance:"):
            continue
        resistance_key = stat_name.split(":", 1)[1]
        if resistance_key in res:
            res[resistance_key] += int(modifier.get("value", 0) or 0)
    return res


def calculate_derived_bonus(character: Dict[str, Any], items_db: Dict[str, Any], stat_name: str) -> int:
    total = 0
    modifiers = ensure_character_modifier_shape(character)
    for modifier in modifiers.get("derived", []) or []:
        if not isinstance(modifier, dict):
            continue
        if str(modifier.get("stat", "") or "") != stat_name:
            continue
        total += int(modifier.get("value", 0) or 0)
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        total += item_modifier_value(item, kind=stat_name)
        if stat_name.startswith("attack_rating_"):
            total += item_modifier_value(item, kind="attack", stat=stat_name)
    for effect in character.get("effects", []) or []:
        for modifier in effect.get("modifiers", []) or []:
            kind = str(modifier.get("kind", "") or "")
            if kind == stat_name:
                total += int(modifier.get("value", 0) or 0)
            if stat_name.startswith("attack_rating_") and kind == "attack":
                mod_stat = str(modifier.get("stat", "") or "")
                if mod_stat in ("", stat_name):
                    total += int(modifier.get("value", 0) or 0)
    if stat_name == "initiative":
        for ability in character.get("abilities", []) or []:
            if ability.get("active") and ability.get("type") == "passive":
                total += int((ability.get("initiative_bonus") or 0))
    return total


def calculate_skill_modifier_bonus(character: Dict[str, Any], items_db: Dict[str, Any], skill_name: str) -> int:
    total = 0
    modifiers = ensure_character_modifier_shape(character)
    for modifier in modifiers.get("skill_effective", []) or []:
        if not isinstance(modifier, dict):
            continue
        if str(modifier.get("skill", modifier.get("stat", "")) or "") != skill_name:
            continue
        total += int(modifier.get("value", 0) or 0)
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        total += item_modifier_value(item, kind="skill", stat=skill_name)
        total += item_modifier_value(item, kind="skill_effective", stat=skill_name)
    for effect in character.get("effects", []) or []:
        for modifier in effect.get("modifiers", []) or []:
            kind = str(modifier.get("kind", "") or "")
            stat = str(modifier.get("stat", "") or "")
            if kind in ("skill", "skill_effective") and stat == skill_name:
                total += int(modifier.get("value", 0) or 0)
    total += int((((character.get("derived") or {}).get("age_modifiers") or {}).get("skill_bonuses") or {}).get(skill_name, 0) or 0)
    return total


def calculate_armor(character: Dict[str, Any], items_db: Dict[str, Any]) -> int:
    armor = 0
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        armor += item_modifier_value(item, kind="armor")
        weapon_profile = item.get("weapon_profile", {}) or {}
        armor += int(weapon_profile.get("armor_bonus", 0) or 0)
    return armor


def calculate_defense(character: Dict[str, Any], items_db: Dict[str, Any]) -> int:
    dex = int((character.get("attributes") or {}).get("dex", 0) or 0)
    defense = 10 + dex + calculate_armor(character, items_db)
    return defense + calculate_derived_bonus(character, items_db, "defense")


def calculate_initiative(character: Dict[str, Any], items_db: Dict[str, Any]) -> int:
    dex = int((character.get("attributes") or {}).get("dex", 0) or 0)
    return dex + calculate_derived_bonus(character, items_db, "initiative")


def calculate_attack_rating(
    character: Dict[str, Any],
    hand: str,
    items_db: Dict[str, Any],
    *,
    skill_level_value: Callable[[Dict[str, Any], str], int],
) -> int:
    equipment = character.get("equipment", {}) or {}
    item = items_db.get(equipment.get(hand, ""), {})
    weapon_profile = item.get("weapon_profile", {}) or {}
    scaling_stat = weapon_profile.get("scaling_stat")
    if not scaling_stat:
        category = weapon_profile.get("category", "")
        if category in ("finesse", "ranged"):
            scaling_stat = "dex"
        elif category == "focus":
            scaling_stat = "int"
        else:
            scaling_stat = "str"
    base = int((character.get("attributes") or {}).get(scaling_stat, 0) or 0)
    bonus = int(weapon_profile.get("attack_bonus", 0) or 0)
    if scaling_stat == "dex":
        skill_bonus = skill_level_value(character, "athletics")
    elif scaling_stat in ("int", "wis"):
        skill_bonus = skill_level_value(character, "lore_occult")
    else:
        skill_bonus = skill_level_value(character, "athletics")
    effect_bonus = calculate_derived_bonus(character, items_db, f"attack_rating_{'mainhand' if hand == 'weapon' else 'offhand'}")
    return base + bonus + skill_bonus + effect_bonus


def skill_effective_bonus(
    character: Dict[str, Any],
    skill_name: str,
    items_db: Optional[Dict[str, Any]] = None,
    *,
    normalize_skill_state: Callable[[str, Any], Dict[str, Any]],
    default_skill_state: Callable[[str], Dict[str, Any]],
) -> int:
    skill_data = normalize_skill_state(skill_name, (character.get("skills") or {}).get(skill_name, default_skill_state(skill_name)))
    skill_rank = int(skill_data.get("level", 1) or 1)
    if skill_rank <= 0:
        return 0
    stat_name = SKILL_ATTRIBUTE_MAP.get(skill_name, "int")
    stat_value = int((character.get("attributes") or {}).get(stat_name, 0) or 0)
    bonus = skill_rank + stat_value
    return bonus + calculate_skill_modifier_bonus(character, items_db or {}, skill_name)
