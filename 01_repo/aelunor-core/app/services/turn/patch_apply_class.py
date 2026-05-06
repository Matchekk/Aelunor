import copy
from typing import Any, Callable, Dict


def apply_patch_character_class_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    state: Dict[str, Any],
    *,
    deep_copy: Any = None,
    normalize_class_current: Callable,
    default_class_current: Callable,
    resolve_class_element_id: Callable,
    ensure_class_rank_core_skills: Callable,
) -> None:
    """
    Applies updates for character class (class_set, class_update) and triggers core skill manifestations.
    """
    if deep_copy is None:
        deep_copy = copy.deepcopy

    if upd.get("class_set"):
        character["class_current"] = normalize_class_current(upd["class_set"])
    if upd.get("class_update"):
        current_class = normalize_class_current(character.get("class_current")) or default_class_current()
        merged_class = deep_copy(current_class)
        merged_class.update(deep_copy(upd["class_update"]))
        character["class_current"] = normalize_class_current(merged_class)

    character["class_current"] = normalize_class_current(character.get("class_current"))

    if character.get("class_current"):
        world_model = state.get("world") if isinstance(state.get("world"), dict) else {}
        resolved_element = resolve_class_element_id(
            character.get("class_current"),
            world_model,
        )
        class_current = normalize_class_current(character.get("class_current")) or default_class_current()
        if resolved_element:
            class_current["element_id"] = resolved_element
            class_current["element_tags"] = list(
                dict.fromkeys([*(class_current.get("element_tags") or []), resolved_element])
            )
        character["class_current"] = normalize_class_current(class_current)

    world_model = state.get("world") if isinstance(state.get("world"), dict) else {}
    world_settings = (state.get("world") or {}).get("settings") or {}
    core_skill_messages = ensure_class_rank_core_skills(
        character,
        world_model,
        world_settings,
        unlock_extra=False,
    )
    if core_skill_messages:
        state.setdefault("events", [])
        state["events"].extend(core_skill_messages)
