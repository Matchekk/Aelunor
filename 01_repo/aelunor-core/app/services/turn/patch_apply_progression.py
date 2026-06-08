import copy
from typing import Any, Callable, Dict, Optional


def _safe_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
        if not isinstance(progression_set, dict):
            progression_set = {}
        character.setdefault("progression", {}).update(progression_set)

        if "level" in progression_set:
            character["level"] = max(1, _safe_int(progression_set.get("level"), _safe_int(character.get("level"), 1)))
        if "xp_total" in progression_set:
            character["xp_total"] = max(0, _safe_int(progression_set.get("xp_total"), _safe_int(character.get("xp_total"), 0)))
        if "xp_current" in progression_set:
            character["xp_current"] = max(0, _safe_int(progression_set.get("xp_current"), _safe_int(character.get("xp_current"), 0)))
        if "xp_to_next" in progression_set:
            character["xp_to_next"] = max(1, _safe_int(progression_set.get("xp_to_next"), _safe_int(character.get("xp_to_next"), 1)))

        if "class_xp" in progression_set or "class_level" in progression_set:
            current_class = normalize_class_current(character.get("class_current")) or default_class_current()
            if "class_xp" in progression_set:
                current_class["xp"] = max(0, _safe_int(progression_set.get("class_xp"), _safe_int(current_class.get("xp"), 0)))
            if "class_xp_to_next" in progression_set:
                current_class["xp_next"] = max(1, _safe_int(progression_set.get("class_xp_to_next"), _safe_int(current_class.get("xp_next"), 1)))
            if "class_level" in progression_set:
                current_class["level"] = max(1, _safe_int(progression_set.get("class_level"), _safe_int(current_class.get("level"), 1)))
            character["class_current"] = normalize_class_current(current_class)
