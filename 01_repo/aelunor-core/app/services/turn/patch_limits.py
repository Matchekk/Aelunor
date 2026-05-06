from typing import Any, Callable, Dict, Iterable, List


def enforce_non_milestone_patch_limits(
    state: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    is_milestone: bool,
    action_type: str,
    deep_copy: Callable[[Any], Any],
    normalize_class_current: Callable[[Any], Dict[str, Any]],
    class_rank_sort_value: Callable[[Any], int],
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]],
    resource_name_for_character: Callable[[Dict[str, Any], Dict[str, Any]], str],
    normalize_skill_rank: Callable[[Any], str],
) -> Dict[str, Any]:
    if is_milestone or action_type == "canon":
        return patch
    limited = deep_copy(patch)
    removed_notes: List[str] = []
    plotpoints_add = limited.get("plotpoints_add") or []
    filtered_plotpoints = []
    for entry in plotpoints_add:
        if isinstance(entry, dict) and str(entry.get("type") or "").strip().lower() == "class_ascension":
            removed_notes.append("Klassenaufstiegs-Quest auf Milestone verschoben.")
            continue
        filtered_plotpoints.append(entry)
    limited["plotpoints_add"] = filtered_plotpoints

    for slot_name, upd in (limited.get("characters") or {}).items():
        if slot_name not in (state.get("characters") or {}):
            continue
        existing_class = normalize_class_current(((state.get("characters", {}).get(slot_name) or {}).get("class_current")))
        existing_rank_value = class_rank_sort_value((existing_class or {}).get("rank", "F"))

        if upd.get("class_set"):
            proposed_class = normalize_class_current(upd.get("class_set"))
            if proposed_class and class_rank_sort_value(proposed_class.get("rank")) > existing_rank_value:
                proposed_class["rank"] = (existing_class or {}).get("rank", "F")
                upd["class_set"] = proposed_class
                removed_notes.append(f"Rank-Sprung für {slot_name} auf Milestone verschoben.")
        if upd.get("class_update"):
            class_update = deep_copy(upd.get("class_update") or {})
            rank_value = class_rank_sort_value(class_update.get("rank", "F"))
            if class_update.get("rank") and rank_value > existing_rank_value:
                class_update.pop("rank", None)
                removed_notes.append(f"Klassen-Rank-Update für {slot_name} auf Milestone verschoben.")
            upd["class_update"] = class_update

        existing_skills = set((((state.get("characters", {}).get(slot_name) or {}).get("skills") or {}).keys()))
        skill_updates = upd.get("skills_set") or {}
        filtered_skills = {}
        for skill_id, skill_value in skill_updates.items():
            if skill_id in existing_skills:
                filtered_skills[skill_id] = skill_value
                continue
            normalized_skill = normalize_dynamic_skill_state(
                skill_value,
                skill_id=str(skill_id),
                skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else str(skill_id),
                resource_name=resource_name_for_character(
                    (state.get("characters", {}).get(slot_name) or {}),
                    ((state.get("world") or {}).get("settings") or {}),
                ),
            )
            if normalize_skill_rank(normalized_skill.get("rank")) in {"A", "S"}:
                removed_notes.append(f"Neuer {normalized_skill.get('rank')}-Skill für {slot_name} auf Milestone verschoben.")
                continue
            filtered_skills[skill_id] = skill_value
        if skill_updates:
            upd["skills_set"] = filtered_skills

    if removed_notes:
        limited.setdefault("events_add", [])
        limited["events_add"].extend(sorted(set(removed_notes)))
    return limited


def enforce_progression_set_mode_limits(
    patch: Dict[str, Any],
    *,
    action_type: str,
    deep_copy: Callable[[Any], Any],
    blank_patch: Callable[[], Dict[str, Any]],
    progression_set_direct_keys: Iterable[str],
) -> Dict[str, Any]:
    if action_type == "canon":
        return patch
    limited = deep_copy(patch or blank_patch())
    blocked_changes: List[str] = []
    for slot_name, upd in (limited.get("characters") or {}).items():
        if not isinstance(upd, dict):
            continue
        progression_set = upd.get("progression_set") if isinstance(upd.get("progression_set"), dict) else {}
        if not progression_set:
            continue
        stripped = False
        for key in progression_set_direct_keys:
            if key in progression_set:
                progression_set.pop(key, None)
                stripped = True
        if stripped:
            blocked_changes.append(slot_name)
        if progression_set:
            upd["progression_set"] = progression_set
        else:
            upd.pop("progression_set", None)
    if blocked_changes:
        limited.setdefault("events_add", [])
        limited["events_add"].append(
            "System: Direkte XP/Level-Setzung ist nur im Modus CANON bindend."
        )
    return limited
