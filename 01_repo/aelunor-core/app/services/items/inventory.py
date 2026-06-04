from __future__ import annotations

from typing import Any, Dict

from app.text.patterns import (
    EQUIPMENT_CANONICAL_SLOTS,
    EQUIPMENT_SLOT_ALIASES,
    ITEM_CHEST_KEYWORDS,
    ITEM_OFFHAND_KEYWORDS,
    ITEM_TRINKET_KEYWORDS,
    ITEM_WEAPON_KEYWORDS,
)
from app.core.ids import deep_copy
from app.services.characters.resource_maxima import item_weight
from app.services.world.text_normalization import normalized_eval_text


def item_by_id(state: Dict[str, Any], item_id: str) -> Dict[str, Any]:
    return deep_copy((state.get("items") or {}).get(item_id) or {})


def ensure_item_shape(item_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "id": item_id,
        "name": item.get("name", item_id),
        "rarity": item.get("rarity", "common"),
        "slot": item.get("slot", ""),
        "weight": item_weight(item),
        "stackable": bool(item.get("stackable", False)),
        "max_stack": int(item.get("max_stack", 1) or 1),
        "weapon_profile": item.get("weapon_profile", {}),
        "modifiers": item.get("modifiers", []) or [],
        "effects": item.get("effects", []) or [],
        "durability": item.get("durability", {"current": 100, "max": 100}),
        "cursed": bool(item.get("cursed", False)),
        "curse_text": item.get("curse_text", ""),
        "tags": item.get("tags", []) or [],
    }
    if not normalized["slot"]:
        normalized["slot"] = ""
    return normalized


def normalize_equipment_slot_key(slot_name: Any) -> str:
    normalized = normalized_eval_text(slot_name)
    if not normalized:
        return ""
    return EQUIPMENT_SLOT_ALIASES.get(normalized, normalized if normalized in EQUIPMENT_CANONICAL_SLOTS else "")


def normalize_equipment_update_payload(payload: Any) -> Dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    normalized: Dict[str, str] = {}
    for raw_slot, raw_value in payload.items():
        slot = normalize_equipment_slot_key(raw_slot)
        if not slot:
            continue
        normalized[slot] = str(raw_value or "").strip()
    return normalized


def infer_item_slot_from_definition(item: Dict[str, Any]) -> str:
    slot = normalize_equipment_slot_key(item.get("slot"))
    if slot:
        return slot
    tags = {normalized_eval_text(tag) for tag in (item.get("tags") or []) if normalized_eval_text(tag)}
    name = normalized_eval_text(item.get("name", ""))
    if "weapon" in tags or any(keyword in name for keyword in ITEM_WEAPON_KEYWORDS):
        return "weapon"
    if "offhand" in tags or any(keyword in name for keyword in ITEM_OFFHAND_KEYWORDS):
        return "offhand"
    if "armor" in tags or any(keyword in name for keyword in ITEM_CHEST_KEYWORDS):
        return "chest"
    if "trinket" in tags or any(keyword in name for keyword in ITEM_TRINKET_KEYWORDS):
        return "trinket"
    return ""


def item_matches_equipment_slot(item: Dict[str, Any], equip_slot: str) -> bool:
    slot = normalize_equipment_slot_key(equip_slot)
    if not slot:
        return False
    if slot in {"ring_1", "ring_2"}:
        return infer_item_slot_from_definition(item) in {"ring_1", "ring_2", "trinket", "amulet", ""}
    inferred = infer_item_slot_from_definition(item)
    if not inferred:
        return slot in {"trinket", "amulet"}
    if slot == "amulet":
        return inferred in {"amulet", "trinket"}
    return inferred == slot
