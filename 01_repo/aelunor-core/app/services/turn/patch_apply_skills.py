from typing import Any, Callable, Dict


def apply_patch_character_skill_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    state: Dict[str, Any],
    *,
    resource_name_for_character: Callable,
    normalize_dynamic_skill_state: Callable,
    normalize_skill_elements_for_world: Callable,
    normalized_eval_text: Callable,
    merge_dynamic_skill: Callable,
    effective_skill_progress_multiplier: Callable,
    clamp: Callable,
    next_skill_xp_for_level: Callable,
    DEFAULT_DYNAMIC_SKILL_LEVEL_MAX: int,
    DEFAULT_NUMERIC_SKILL_DELTA_XP: int,
) -> None:
    """
    Applies updates for skills (skills_set, skills_delta) from a patch onto a character.
    """
    skill_store = character.setdefault("skills", {})
    world_model = state.get("world") if isinstance(state.get("world"), dict) else {}
    world_settings = world_model.get("settings") or {}
    resource_name = resource_name_for_character(character, world_settings)

    if upd.get("skills_set"):
        for key, value in (upd.get("skills_set") or {}).items():
            skill_key = str(key or "").strip()
            if not skill_key:
                continue
            normalized_skill = normalize_dynamic_skill_state(
                value,
                skill_id=skill_key,
                skill_name=(value or {}).get("name", skill_key) if isinstance(value, dict) else skill_key,
                resource_name=resource_name,
                unlocked_from="Patch",
            )
            normalized_skill = normalize_skill_elements_for_world(
                normalized_skill,
                world_model,
            )
            existing_skill = skill_store.get(normalized_skill["id"])
            if not existing_skill:
                existing_skill = next(
                    (
                        skill_value
                        for skill_value in skill_store.values()
                        if isinstance(skill_value, dict)
                        and normalized_eval_text(skill_value.get("name", "")) == normalized_eval_text(normalized_skill.get("name", ""))
                    ),
                    None,
                )
            skill_store[normalized_skill["id"]] = merge_dynamic_skill(existing_skill, normalized_skill, resource_name=resource_name) if existing_skill else normalized_skill
            if existing_skill:
                duplicate_ids = [
                    existing_id
                    for existing_id, skill_value in list(skill_store.items())
                    if existing_id != normalized_skill["id"]
                    and isinstance(skill_value, dict)
                    and normalized_eval_text(skill_value.get("name", "")) == normalized_eval_text(normalized_skill.get("name", ""))
                ]
                for duplicate_id in duplicate_ids:
                    skill_store.pop(duplicate_id, None)

    for key, value in (upd.get("skills_delta") or {}).items():
        skill_key = str(key or "").strip()
        if not skill_key:
            continue
        existing_skill = skill_store.get(skill_key)
        if not existing_skill:
            existing_skill = normalize_dynamic_skill_state(
                {"id": skill_key, "name": skill_key, "level": 1, "rank": "F", "level_max": 10, "tags": [], "description": f"{skill_key} wurde im Abenteuer aktiviert.", "unlocked_from": "Patch"},
                resource_name=resource_name,
            )
        skill = normalize_dynamic_skill_state(existing_skill, skill_id=skill_key, skill_name=(existing_skill or {}).get("name", skill_key), resource_name=resource_name)
        skill = normalize_skill_elements_for_world(
            skill,
            world_model,
        )
        if isinstance(value, dict):
            if "xp" in value:
                multiplier = effective_skill_progress_multiplier(character, skill, world_settings)
                skill["xp"] = max(0, int(skill.get("xp", 0) or 0) + int(round(float(value.get("xp", 0) or 0) * multiplier)))
            if "level" in value:
                level_max = max(1, int(skill.get("level_max", DEFAULT_DYNAMIC_SKILL_LEVEL_MAX) or DEFAULT_DYNAMIC_SKILL_LEVEL_MAX))
                skill["level"] = clamp(int(skill.get("level", 1) or 1) + int(value.get("level", 0) or 0), 1, level_max)
            if "description" in value and str(value.get("description") or "").strip():
                skill["description"] = str(value.get("description")).strip()
            if "elements" in value:
                skill["elements"] = list(dict.fromkeys([str(entry).strip() for entry in (value.get("elements") or []) if str(entry).strip()]))
            if "element_primary" in value:
                skill["element_primary"] = str(value.get("element_primary") or "").strip() or None
            if "element_synergies" in value:
                skill["element_synergies"] = list(dict.fromkeys([str(entry).strip() for entry in (value.get("element_synergies") or []) if str(entry).strip()])) or None
        else:
            multiplier = effective_skill_progress_multiplier(character, skill, world_settings)
            raw_delta = int(value or 0)
            xp_gain = int(round(raw_delta * DEFAULT_NUMERIC_SKILL_DELTA_XP * multiplier))
            skill["xp"] = max(0, int(skill.get("xp", 0) or 0) + xp_gain)
        while skill["xp"] >= int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"])) and skill["level"] < int(skill.get("level_max", DEFAULT_DYNAMIC_SKILL_LEVEL_MAX) or DEFAULT_DYNAMIC_SKILL_LEVEL_MAX):
            next_xp = int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"]))
            skill["xp"] = max(0, skill["xp"] - next_xp)
            skill["level"] += 1
        skill["next_xp"] = next_skill_xp_for_level(skill["level"])
        skill["xp"] = clamp(int(skill.get("xp", 0) or 0), 0, skill["next_xp"])
        skill_store[skill["id"]] = normalize_skill_elements_for_world(
            normalize_dynamic_skill_state(skill, resource_name=resource_name),
            world_model,
        )
