import copy
from typing import Any, Callable, Dict, Optional


def apply_patch_character_progression_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    *,
    deep_copy: Any = None,
    normalize_class_current: Callable[[Any], Optional[Dict[str, Any]]],
    default_class_current: Callable[[], Dict[str, Any]],
) -> None:
    """
    Applies updates for progression fields from a patch onto a character.
    """
    if deep_copy is None:
        deep_copy = copy.deepcopy

    if upd.get("progression_set"):
        progression_set = deep_copy(upd["progression_set"] or {})
        character.setdefault("progression", {}).update(progression_set)

        if "level" in progression_set:
            character["level"] = max(1, int(progression_set.get("level", character.get("level", 1)) or character.get("level", 1)))
        if "xp_total" in progression_set:
            character["xp_total"] = max(0, int(progression_set.get("xp_total", character.get("xp_total", 0)) or character.get("xp_total", 0)))
        if "xp_current" in progression_set:
            character["xp_current"] = max(0, int(progression_set.get("xp_current", character.get("xp_current", 0)) or character.get("xp_current", 0)))
        if "xp_to_next" in progression_set:
            character["xp_to_next"] = max(1, int(progression_set.get("xp_to_next", character.get("xp_to_next", 1)) or character.get("xp_to_next", 1)))

        if "class_xp" in progression_set or "class_level" in progression_set:
            current_class = normalize_class_current(character.get("class_current")) or default_class_current()
            if "class_xp" in progression_set:
                current_class["xp"] = max(0, int(progression_set.get("class_xp", current_class.get("xp", 0)) or current_class.get("xp", 0)))
            if "class_xp_to_next" in progression_set:
                current_class["xp_next"] = max(1, int(progression_set.get("class_xp_to_next", current_class.get("xp_next", 1)) or current_class.get("xp_next", 1)))
            if "class_level" in progression_set:
                current_class["level"] = max(1, int(progression_set.get("class_level", current_class.get("level", 1)) or current_class.get("level", 1)))
            character["class_current"] = normalize_class_current(current_class)
