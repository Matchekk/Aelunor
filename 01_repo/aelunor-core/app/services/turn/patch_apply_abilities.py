from typing import Any, Callable, Dict


def apply_patch_character_ability_potential_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    *,
    slot_name: str,
    skill_store: Dict[str, Any],
    resource_name: str,
    enable_legacy_shadow_writeback: bool,
    make_id: Callable[[str], str],
    normalize_ability_state: Callable[[Any, str], Dict[str, Any]],
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]],
    skill_id_from_name: Callable[[str], str],
    normalize_skill_rank: Callable[[Any], str],
    next_skill_xp_for_level: Callable[[int], int],
    merge_dynamic_skill: Callable[..., Dict[str, Any]],
) -> None:
    for ability in upd.get("abilities_add", []) or []:
        normalized_ability = normalize_ability_state(ability, slot_name)
        normalized_skill = normalize_dynamic_skill_state(
            {
                "id": skill_id_from_name(normalized_ability.get("name", normalized_ability.get("id", ""))),
                "name": normalized_ability.get("name"),
                "rank": normalize_skill_rank(normalized_ability.get("rank")),
                "level": max(1, int(normalized_ability.get("level", 1) or 1)),
                "level_max": 10,
                "tags": list(dict.fromkeys([*(normalized_ability.get("tags") or []), normalized_ability.get("type", "")])),
                "description": normalized_ability.get("description") or f"{normalized_ability.get('name', 'Technik')} wurde gelernt.",
                "cost": None if not normalized_ability.get("cost") else {"resource": resource_name, "amount": sum(int(v or 0) for v in (normalized_ability.get("cost") or {}).values())},
                "price": None,
                "cooldown_turns": normalized_ability.get("cooldown_turns"),
                "unlocked_from": normalized_ability.get("source") or "Patch",
                "synergy_notes": None,
                "xp": int(normalized_ability.get("xp", 0) or 0),
                "next_xp": int(normalized_ability.get("next_xp", next_skill_xp_for_level(max(1, int(normalized_ability.get('level', 1) or 1)))) or next_skill_xp_for_level(max(1, int(normalized_ability.get('level', 1) or 1)))),
                "mastery": int(normalized_ability.get("mastery", 0) or 0),
            },
            resource_name=resource_name,
        )
        existing_skill = skill_store.get(normalized_skill["id"])
        skill_store[normalized_skill["id"]] = merge_dynamic_skill(existing_skill, normalized_skill, resource_name=resource_name) if existing_skill else normalized_skill
    for ability_update in upd.get("abilities_update", []) or []:
        ability_id = skill_id_from_name(str(ability_update.get("id") or ""))
        existing_skill = skill_store.get(ability_id)
        if not existing_skill:
            continue
        skill = normalize_dynamic_skill_state(existing_skill, resource_name=resource_name)
        if "level" in ability_update:
            skill["level"] = max(1, int(ability_update.get("level", 1) or 1))
        if "xp" in ability_update:
            skill["xp"] = max(0, int(ability_update.get("xp", 0) or 0))
        if "cooldown_turns" in ability_update:
            skill["cooldown_turns"] = max(0, int(ability_update.get("cooldown_turns", 0) or 0))
        skill_store[ability_id] = normalize_dynamic_skill_state(skill, resource_name=resource_name)
    if enable_legacy_shadow_writeback:
        character["abilities"] = []
    else:
        character.pop("abilities", None)

    for potential in upd.get("potential_add", []) or []:
        if isinstance(potential, dict):
            existing_ids = {entry.get("id") for entry in character.get("progression", {}).get("potential_cards", [])}
            if potential.get("id") and potential.get("id") not in existing_ids:
                character.setdefault("progression", {}).setdefault("potential_cards", []).append(potential)
        elif potential:
            card = {"id": make_id("potential"), "name": str(potential), "description": "", "tags": [], "requirements": [], "status": "locked"}
            character.setdefault("progression", {}).setdefault("potential_cards", []).append(card)
