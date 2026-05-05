from typing import Any, Callable, Dict


def apply_patch_character_inventory_equipment_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    *,
    normalize_equipment_update_payload: Callable[[Any], Dict[str, str]],
) -> None:
    for item_id in upd.get("inventory_add", []) or []:
        if item_id and not any(entry.get("item_id") == item_id for entry in character.get("inventory", {}).get("items", [])):
            character.setdefault("inventory", {}).setdefault("items", []).append({"item_id": item_id, "stack": 1})
    for item_id in upd.get("inventory_remove", []) or []:
        character.setdefault("inventory", {}).setdefault("items", [])
        character["inventory"]["items"] = [entry for entry in character["inventory"]["items"] if entry.get("item_id") != item_id]

    inventory_set = upd.get("inventory_set") or {}
    if inventory_set.get("items") is not None:
        character.setdefault("inventory", {})["items"] = inventory_set.get("items", [])
    if inventory_set.get("quick_slots") is not None:
        character.setdefault("inventory", {})["quick_slots"] = inventory_set.get("quick_slots", {})

    equipment_set = upd.get("equipment_set") or upd.get("equip_set")
    if equipment_set:
        normalized_equipment = character.get("equipment", {})
        normalized_update = normalize_equipment_update_payload(equipment_set)
        for key, value in normalized_update.items():
            normalized_equipment[key] = value
            if value and not any(entry.get("item_id") == value for entry in character.get("inventory", {}).get("items", [])):
                character.setdefault("inventory", {}).setdefault("items", []).append({"item_id": value, "stack": 1})
        character["equipment"] = normalized_equipment
