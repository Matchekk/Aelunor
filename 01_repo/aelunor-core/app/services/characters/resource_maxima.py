from typing import Any, Dict, List, Optional

from app.config.feature_flags import ENABLE_LEGACY_SHADOW_WRITEBACK
from app.config.progression import RESOURCE_KEYS
from app.core.ids import deep_copy
from app.services.characters.resources import strip_legacy_resource_shadows
from app.services.world.math_utils import clamp
from app.services.world.progression import normalize_class_current
from app.services.world.state_defaults import default_character_modifiers
from app.services.world.text_normalization import normalized_eval_text


def configure(main_globals: Dict[str, Any]) -> None:
    globals().update(main_globals)


def item_weight(item: Dict[str, Any]) -> int:
    try:
        return int(item.get("weight", 0) or 0)
    except (TypeError, ValueError):
        return 0


def item_modifier_value(item: Dict[str, Any], *, kind: str, stat: Optional[str] = None) -> int:
    total = 0
    for modifier in item.get("modifiers", []) or []:
        if modifier.get("kind") != kind:
            continue
        if stat is not None and modifier.get("stat") != stat:
            continue
        try:
            total += int(modifier.get("value", 0) or 0)
        except (TypeError, ValueError):
            continue
    return total


def ensure_character_modifier_shape(character: Dict[str, Any]) -> Dict[str, Any]:
    modifiers = character.setdefault("modifiers", {})
    defaults = default_character_modifiers()
    for key, value in defaults.items():
        modifiers.setdefault(key, deep_copy(value))
    return modifiers


def modifier_resource_key(modifier: Dict[str, Any]) -> str:
    return str(modifier.get("resource") or modifier.get("stat") or "").strip().lower()


def iter_equipped_item_ids(character: Dict[str, Any]) -> List[str]:
    equipment = character.get("equipment", {}) or {}
    return [value for value in equipment.values() if value]


def list_inventory_items(character: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = character.get("inventory", {}).get("items", [])
    if isinstance(items, list):
        out = []
        for entry in items:
            if isinstance(entry, dict):
                out.append({"item_id": entry.get("item_id", ""), "stack": max(1, int(entry.get("stack", 1) or 1))})
            elif entry:
                out.append({"item_id": str(entry), "stack": 1})
        return out
    return []


def calculate_base_resource_maxima(character: Dict[str, Any], age_modifiers: Dict[str, Any]) -> Dict[str, int]:
    attrs = character.get("attributes", {}) or {}
    current_class = normalize_class_current(character.get("class_current")) or {}
    class_tags = {normalized_eval_text(tag) for tag in (current_class.get("affinity_tags") or []) if normalized_eval_text(tag)}
    class_level = max(1, int((current_class.get("level", 1) if current_class else 1) or 1))
    class_rank = str((current_class.get("rank", "F") if current_class else "F") or "F").upper()
    rank_bonus = {"F": 0, "E": 1, "D": 2, "C": 3, "B": 4, "A": 5, "S": 7}.get(class_rank, 0)

    hp_skill_bonus = 0
    sta_skill_bonus = 0
    res_skill_bonus = 0
    for raw_skill in (character.get("skills") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        level = max(1, int(raw_skill.get("level", 1) or 1))
        tags = {normalized_eval_text(tag) for tag in (raw_skill.get("tags") or []) if normalized_eval_text(tag)}
        if tags & {"körper", "koerper", "vital", "regeneration", "tank", "defense", "schutz"}:
            hp_skill_bonus += max(0, level // 3)
        if tags & {"ausdauer", "bewegung", "kampf", "technik", "athletik", "endurance"}:
            sta_skill_bonus += max(0, level // 4)
        if tags & {"magie", "aether", "mana", "qi", "rune", "arcane", "shadow", "holy", "zauber"}:
            res_skill_bonus += max(0, level // 4)

    class_hp_bonus = rank_bonus + (class_level // 4 if class_tags & {"körper", "koerper", "schutz", "kampf", "tank"} else 0)
    class_sta_bonus = rank_bonus + (class_level // 4 if class_tags & {"bewegung", "kampf", "technik", "ausdauer", "athletik"} else 0)
    class_res_bonus = rank_bonus + (class_level // 4 if class_tags & {"magie", "rune", "arcane", "shadow", "holy", "focus"} else 0)

    return {
        "hp": max(
            1,
            8
            + (int(attrs.get("con", 0) or 0) * 2)
            + int(age_modifiers["resource_deltas"].get("hp_max", 0) or 0)
            + class_hp_bonus
            + hp_skill_bonus,
        ),
        "stamina": max(
            1,
            8
            + int(attrs.get("con", 0) or 0)
            + int(attrs.get("dex", 0) or 0)
            + int(age_modifiers["resource_deltas"].get("stamina_max", 0) or 0)
            + class_sta_bonus
            + sta_skill_bonus,
        ),
        "aether": max(
            1,
            4
            + int(attrs.get("int", 0) or 0)
            + int(round(int(attrs.get("wis", 0) or 0) * 0.5))
            + class_res_bonus
            + res_skill_bonus,
        ),
        "stress": 10,
        "corruption": 100 if int((((character.get("resources") or {}).get("corruption") or {}).get("max", 0)) or 0) > 10 else 10,
        "wounds": 3,
    }


def calculate_bonus_resource_maxima(character: Dict[str, Any], items_db: Dict[str, Any]) -> Dict[str, int]:
    bonuses = {key: 0 for key in RESOURCE_KEYS}
    modifiers = ensure_character_modifier_shape(character)
    for entry in modifiers.get("resource_max", []) or []:
        if not isinstance(entry, dict):
            continue
        resource_key = modifier_resource_key(entry)
        if resource_key not in bonuses:
            continue
        bonuses[resource_key] += int(entry.get("value", 0) or 0)
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        for modifier in item.get("modifiers", []) or []:
            if modifier.get("kind") != "resource_max":
                continue
            resource_key = modifier_resource_key(modifier)
            if resource_key not in bonuses:
                continue
            bonuses[resource_key] += int(modifier.get("value", 0) or 0)
    for effect in character.get("effects", []) or []:
        for modifier in effect.get("modifiers", []) or []:
            if modifier.get("kind") != "resource_max":
                continue
            resource_key = modifier_resource_key(modifier)
            if resource_key not in bonuses:
                continue
            bonuses[resource_key] += int(modifier.get("value", 0) or 0)
    return bonuses


def migrate_legacy_resource_bonus_modifiers(
    character: Dict[str, Any],
    base_maxima: Dict[str, int],
    known_bonus: Dict[str, int],
    layer_presence: Dict[str, Dict[str, bool]],
) -> None:
    modifiers = ensure_character_modifier_shape(character)
    existing_entries = modifiers.setdefault("resource_max", [])
    by_resource = {
        entry.get("resource"): entry
        for entry in existing_entries
        if isinstance(entry, dict) and entry.get("source") == "legacy:max"
    }
    resources = character.get("resources", {}) or {}
    for resource_key in ("hp", "stamina", "aether"):
        resource = resources.get(resource_key, {}) or {}
        presence = layer_presence.get(resource_key, {})
        if presence.get("base_max") or presence.get("bonus_max"):
            continue
        existing_max = int(resource.get("max", 0) or 0)
        inferred_bonus = max(0, existing_max - (int(base_maxima.get(resource_key, 0) or 0) + int(known_bonus.get(resource_key, 0) or 0)))
        if inferred_bonus <= 0:
            continue
        if resource_key in by_resource:
            by_resource[resource_key]["value"] = inferred_bonus
        else:
            existing_entries.append(
                {
                    "resource": resource_key,
                    "value": inferred_bonus,
                    "source": "legacy:max",
                }
            )


def rebuild_resource_maxima(character: Dict[str, Any], items_db: Dict[str, Any], age_modifiers: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    existing_resources = character.get("resources", {}) if isinstance(character.get("resources"), dict) else {}
    layer_presence: Dict[str, Dict[str, bool]] = {}
    for resource_key in RESOURCE_KEYS:
        resource = existing_resources.get(resource_key) if isinstance(existing_resources.get(resource_key), dict) else {}
        layer_presence[resource_key] = {
            "base_max": "base_max" in resource,
            "bonus_max": "bonus_max" in resource,
        }

    base_maxima = calculate_base_resource_maxima(character, age_modifiers)
    known_bonus = calculate_bonus_resource_maxima(character, items_db)
    migrate_legacy_resource_bonus_modifiers(character, base_maxima, known_bonus, layer_presence)
    total_bonus = calculate_bonus_resource_maxima(character, items_db)

    runtime_layers: Dict[str, Dict[str, int]] = {}
    for resource_key in RESOURCE_KEYS:
        existing_layer = existing_resources.get(resource_key) if isinstance(existing_resources.get(resource_key), dict) else {}
        base_max = max(0, int(base_maxima.get(resource_key, existing_layer.get("base_max", existing_layer.get("max", 0))) or 0))
        bonus_max = int(total_bonus.get(resource_key, existing_layer.get("bonus_max", 0)) or 0)
        max_value = max(0, base_max + bonus_max)
        current_seed = int(existing_layer.get("current", 0) or 0)
        runtime_layers[resource_key] = {
            "current": clamp(current_seed, 0, max_value),
            "base_max": base_max,
            "bonus_max": bonus_max,
            "max": max_value,
        }

    hp_layer = runtime_layers.get("hp", {"current": 10, "max": 10})
    sta_layer = runtime_layers.get("stamina", {"current": 10, "max": 10})
    res_layer = runtime_layers.get("aether", {"current": 5, "max": 5})
    character["hp_max"] = max(1, int(hp_layer.get("max", character.get("hp_max", 10)) or character.get("hp_max", 10) or 10))
    character["sta_max"] = max(0, int(sta_layer.get("max", character.get("sta_max", 10)) or character.get("sta_max", 10) or 10))
    character["res_max"] = max(0, int(res_layer.get("max", character.get("res_max", 5)) or character.get("res_max", 5) or 5))
    character["hp_current"] = clamp(int(character.get("hp_current", hp_layer.get("current", character["hp_max"])) or hp_layer.get("current", character["hp_max"]) or character["hp_max"]), 0, character["hp_max"])
    character["sta_current"] = clamp(int(character.get("sta_current", sta_layer.get("current", character["sta_max"])) or sta_layer.get("current", character["sta_max"]) or character["sta_max"]), 0, character["sta_max"])
    character["res_current"] = clamp(int(character.get("res_current", res_layer.get("current", character["res_max"])) or res_layer.get("current", character["res_max"]) or character["res_max"]), 0, character["res_max"])

    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        character.setdefault("resources", {})
        for key in RESOURCE_KEYS:
            character["resources"][key] = deep_copy(runtime_layers[key])
    else:
        resources_shadow = character.setdefault("resources", {})
        if not isinstance(resources_shadow, dict):
            resources_shadow = {}
            character["resources"] = resources_shadow
        for key in ("stress", "corruption", "wounds"):
            resources_shadow[key] = deep_copy(runtime_layers.get(key, {"current": 0, "base_max": 0, "bonus_max": 0, "max": 0}))
        strip_legacy_resource_shadows(character)

    return runtime_layers
