from typing import Any, Callable, Dict, Iterable


def apply_patch_character_resource_attribute_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    *,
    world_settings: Dict[str, Any],
    clamp: Callable[[int, int, int], int],
    attribute_cap: int,
    attribute_keys: Iterable[str],
    canonical_resources_set_from_payload: Callable[[Any, Dict[str, Any], Dict[str, Any]], Dict[str, int]],
    legacy_misc_resources_set_from_payload: Callable[[Any], Dict[str, Dict[str, Any]]],
    canonical_resource_deltas_from_update: Callable[[Dict[str, Any]], Dict[str, int]],
    legacy_misc_resource_deltas_from_update: Callable[[Dict[str, Any]], Dict[str, int]],
) -> None:
    if upd.get("resources_set"):
        canonical_set = canonical_resources_set_from_payload(
            upd.get("resources_set"),
            character,
            world_settings,
        )
        for key, value in canonical_set.items():
            character[key] = max(0, int(value or 0))
        misc_resource_set = legacy_misc_resources_set_from_payload(upd.get("resources_set"))
        if misc_resource_set:
            resources_store = character.setdefault("resources", {})
            if not isinstance(resources_store, dict):
                resources_store = {}
                character["resources"] = resources_store
            for misc_key, misc_payload in misc_resource_set.items():
                max_value = max(0, int(misc_payload.get("max", 0) or 0))
                current_value = max(0, int(misc_payload.get("current", 0) or 0))
                resources_store[misc_key] = {
                    "current": clamp(current_value, 0, max_value) if max_value > 0 else current_value,
                    "base_max": max_value,
                    "bonus_max": 0,
                    "max": max_value,
                }
    canonical_resource_deltas = canonical_resource_deltas_from_update(upd)
    if canonical_resource_deltas["hp_current"]:
        character["hp_current"] = int(character.get("hp_current", 0) or 0) + canonical_resource_deltas["hp_current"]
    if canonical_resource_deltas["sta_current"]:
        character["sta_current"] = int(character.get("sta_current", 0) or 0) + canonical_resource_deltas["sta_current"]
    if canonical_resource_deltas["res_current"]:
        character["res_current"] = int(character.get("res_current", 0) or 0) + canonical_resource_deltas["res_current"]
    if canonical_resource_deltas["carry_current"]:
        character["carry_current"] = int(character.get("carry_current", 0) or 0) + canonical_resource_deltas["carry_current"]
    misc_resource_deltas = legacy_misc_resource_deltas_from_update(upd)
    if any(int(misc_resource_deltas.get(key, 0) or 0) != 0 for key in ("stress", "corruption", "wounds")):
        resources_store = character.setdefault("resources", {})
        if not isinstance(resources_store, dict):
            resources_store = {}
            character["resources"] = resources_store
        for misc_key in ("stress", "corruption", "wounds"):
            delta = int(misc_resource_deltas.get(misc_key, 0) or 0)
            if not delta:
                continue
            current_entry = resources_store.get(misc_key) if isinstance(resources_store.get(misc_key), dict) else {}
            max_value = max(0, int(current_entry.get("max", 10 if misc_key != "wounds" else 3) or (10 if misc_key != "wounds" else 3)))
            current_value = int(current_entry.get("current", 0) or 0) + delta
            resources_store[misc_key] = {
                "current": clamp(current_value, 0, max_value),
                "base_max": max(0, int(current_entry.get("base_max", max_value) or max_value)),
                "bonus_max": int(current_entry.get("bonus_max", 0) or 0),
                "max": max_value,
            }

    attribute_key_set = set(attribute_keys)
    if upd.get("attributes_set"):
        character.setdefault("attributes", {}).update(
            {
                key: clamp(int(value or 0), 0, attribute_cap)
                for key, value in upd["attributes_set"].items()
                if key in attribute_key_set
            }
        )
    for key, value in (upd.get("attributes_delta") or {}).items():
        if key in attribute_key_set:
            character.setdefault("attributes", {})[key] = clamp(
                int(character["attributes"].get(key, 0) or 0) + int(value or 0),
                0,
                attribute_cap,
            )
