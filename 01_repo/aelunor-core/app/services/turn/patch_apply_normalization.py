from typing import Any, Callable, Dict


def apply_patch_character_late_normalization(
    character: Dict[str, Any],
    state: Dict[str, Any],
    slot_name: str,
    *,
    resource_name: str,
    effective_world_time: Any,
    ENABLE_LEGACY_SHADOW_WRITEBACK: bool,
    ensure_progression_shape: Callable,
    ensure_character_progression_core: Callable,
    normalize_skill_store: Callable,
    resolve_injury_healing: Callable,
    rebuild_character_derived: Callable,
    reconcile_canonical_resources: Callable,
    strip_legacy_shadow_fields: Callable,
    write_legacy_shadow_fields: Callable,
    sync_scars_into_appearance: Callable,
) -> None:
    ensure_progression_shape(character)
    ensure_character_progression_core(character)
    character["skills"] = normalize_skill_store(character.get("skills") or {}, resource_name=resource_name)

    new_scars = resolve_injury_healing(character, int(state.get("meta", {}).get("turn", 0) or 0))
    if new_scars:
        state.setdefault("events", [])
        char_name = str(((character.get("bio") or {}).get("name")) or slot_name).strip() or slot_name
        for scar in new_scars:
            state["events"].append(f"{char_name} trägt nun {scar.get('title')}.")

    world_settings = (state.get("world") or {}).get("settings") or {}
    items_state = state.get("items", {})

    rebuild_character_derived(character, items_state, effective_world_time)
    reconcile_canonical_resources(character, world_settings)
    strip_legacy_shadow_fields(character, world_settings)

    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        write_legacy_shadow_fields(character, world_settings)

    sync_scars_into_appearance(character)
