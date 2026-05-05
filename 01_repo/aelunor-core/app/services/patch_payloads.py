import json
from typing import Any, Dict


def blank_patch() -> Dict[str, Any]:
    return {
        "meta": {},
        "characters": {},
        "items_new": {},
        "plotpoints_add": [],
        "plotpoints_update": [],
        "map_add_nodes": [],
        "map_add_edges": [],
        "events_add": [],
    }


def deep_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def normalize_patch_payload(payload: Any) -> Dict[str, Any]:
    patch = payload if isinstance(payload, dict) else {}
    normalized = blank_patch()

    meta = patch.get("meta")
    if isinstance(meta, dict):
        normalized_meta: Dict[str, Any] = {}
        if meta.get("phase"):
            normalized_meta["phase"] = meta.get("phase")
        time_advance = meta.get("time_advance")
        if isinstance(time_advance, dict):
            normalized_meta["time_advance"] = {
                "days": int(time_advance.get("days", 0) or 0),
                "time_of_day": str(time_advance.get("time_of_day", "") or ""),
                "reason": str(time_advance.get("reason", "") or ""),
            }
        normalized["meta"] = normalized_meta

    for key in ("characters", "items_new"):
        value = patch.get(key)
        normalized[key] = value if isinstance(value, dict) else {}

    for key in ("plotpoints_add", "plotpoints_update", "map_add_nodes", "map_add_edges", "events_add"):
        value = patch.get(key)
        normalized[key] = value if isinstance(value, list) else []

    return normalized


def normalize_patch_semantics(patch: Any) -> Dict[str, Any]:
    normalized = normalize_patch_payload(patch)
    characters = normalized.get("characters") or {}
    for slot_name, upd in characters.items():
        if not isinstance(upd, dict):
            characters[slot_name] = {}
            continue
        scene_set = str(upd.get("scene_set") or "").strip()
        if scene_set and not str(upd.get("scene_id") or "").strip():
            upd["scene_id"] = scene_set
        upd.pop("scene_set", None)
    normalized["characters"] = characters
    return normalized


def merge_character_patch_update(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = deep_copy(base)
    for key, value in incoming.items():
        if key in {
            "bio_set",
            "resources_set",
            "resources_delta",
            "attributes_set",
            "attributes_delta",
            "skills_set",
            "skills_delta",
            "equip_set",
            "equipment_set",
            "inventory_set",
            "progression_set",
            "class_set",
            "class_update",
            "journal_add",
        }:
            target = merged.setdefault(key, {})
            if isinstance(target, dict) and isinstance(value, dict):
                target.update(deep_copy(value))
            else:
                merged[key] = deep_copy(value)
        elif key in {
            "conditions_add",
            "conditions_remove",
            "inventory_add",
            "inventory_remove",
            "abilities_add",
            "abilities_update",
            "potential_add",
            "factions_add",
            "factions_update",
            "injuries_add",
            "injuries_update",
            "injuries_heal",
            "scars_add",
            "appearance_flags_add",
            "effects_add",
            "effects_remove",
            "progression_events",
        }:
            merged.setdefault(key, [])
            if isinstance(value, list):
                merged[key].extend(deep_copy(value))
        else:
            merged[key] = deep_copy(value)
    return merged


def merge_patch_payloads(*patches: Dict[str, Any]) -> Dict[str, Any]:
    combined = blank_patch()
    for patch in patches:
        current = normalize_patch_semantics(patch)
        meta = current.get("meta") or {}
        if meta:
            combined_meta = combined.setdefault("meta", {})
            if "phase" in meta and meta.get("phase"):
                combined_meta["phase"] = meta.get("phase")
            if meta.get("time_advance"):
                combined_meta["time_advance"] = deep_copy(meta["time_advance"])
        for slot_name, upd in (current.get("characters") or {}).items():
            combined["characters"][slot_name] = merge_character_patch_update(
                combined["characters"].get(slot_name, {}),
                upd,
            )
        combined["items_new"].update(deep_copy(current.get("items_new") or {}))
        for key in ("plotpoints_add", "plotpoints_update", "map_add_nodes", "map_add_edges", "events_add"):
            combined[key].extend(deep_copy(current.get(key) or []))
    return combined
