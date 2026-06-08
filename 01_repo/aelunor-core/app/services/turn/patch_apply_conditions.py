from typing import Any, Dict


def apply_patch_character_condition_effect_updates(character: Dict[str, Any], upd: Dict[str, Any]) -> None:
    conditions = character.get("conditions")
    if not isinstance(conditions, list):
        conditions = []
        character["conditions"] = conditions
    for condition in upd.get("conditions_add", []) or []:
        if condition and condition not in conditions:
            conditions.append(condition)
    for condition in upd.get("conditions_remove", []) or []:
        if condition in conditions:
            conditions.remove(condition)

    effects = character.get("effects")
    if not isinstance(effects, list):
        effects = []
        character["effects"] = effects
    existing_effects = [existing for existing in effects if isinstance(existing, dict)]
    for effect in upd.get("effects_add", []) or []:
        if isinstance(effect, dict) and effect.get("id") and not any(existing.get("id") == effect.get("id") for existing in existing_effects):
            effects.append(effect)
    remove_effect_ids = set(upd.get("effects_remove", []) or [])
    if remove_effect_ids:
        character["effects"] = [effect for effect in effects if not isinstance(effect, dict) or effect.get("id") not in remove_effect_ids]
