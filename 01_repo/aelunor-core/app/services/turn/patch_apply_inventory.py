from typing import Any, Callable, Dict


def apply_patch_character_inventory_equipment_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    *,
    normalize_equipment_update_payload: Callable[[Any], Dict[str, str]],
) -> None:
    def _items() -> list:
        inventory = character.setdefault("inventory", {})
        if not isinstance(inventory.get("items"), list):
            inventory["items"] = []
        return inventory["items"]

    for item_id in upd.get("inventory_add", []) or []:
        if item_id and not any(isinstance(entry, dict) and entry.get("item_id") == item_id for entry in _items()):
            _items().append({"item_id": item_id, "stack": 1})
    for item_id in upd.get("inventory_remove", []) or []:
        character["inventory"]["items"] = [entry for entry in _items() if not isinstance(entry, dict) or entry.get("item_id") != item_id]

    inventory_set = upd.get("inventory_set")
    if isinstance(inventory_set, dict):
        if inventory_set.get("items") is not None:
            items = inventory_set.get("items")
            character.setdefault("inventory", {})["items"] = items if isinstance(items, list) else []
        if inventory_set.get("quick_slots") is not None:
            quick_slots = inventory_set.get("quick_slots")
            character.setdefault("inventory", {})["quick_slots"] = quick_slots if isinstance(quick_slots, dict) else {}

    equipment_set = upd.get("equipment_set") or upd.get("equip_set")
    if equipment_set:
        normalized_equipment = character.get("equipment", {})
        normalized_update = normalize_equipment_update_payload(equipment_set)
        for key, value in normalized_update.items():
            normalized_equipment[key] = value
            if value and not any(isinstance(entry, dict) and entry.get("item_id") == value for entry in _items()):
                _items().append({"item_id": value, "stack": 1})
        character["equipment"] = normalized_equipment
