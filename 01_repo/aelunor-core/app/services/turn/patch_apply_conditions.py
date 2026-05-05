from typing import Any, Dict


def apply_patch_character_condition_effect_updates(character: Dict[str, Any], upd: Dict[str, Any]) -> None:
    for condition in upd.get("conditions_add", []) or []:
        if condition and condition not in character["conditions"]:
            character["conditions"].append(condition)
    for condition in upd.get("conditions_remove", []) or []:
        if condition in character["conditions"]:
            character["conditions"].remove(condition)

    for effect in upd.get("effects_add", []) or []:
        if effect.get("id") and not any(existing.get("id") == effect.get("id") for existing in character.get("effects", [])):
            character.setdefault("effects", []).append(effect)
    remove_effect_ids = set(upd.get("effects_remove", []) or [])
    if remove_effect_ids:
        character["effects"] = [effect for effect in character.get("effects", []) if effect.get("id") not in remove_effect_ids]
