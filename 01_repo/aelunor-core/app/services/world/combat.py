from typing import Any, Callable, Dict, List, Optional


def skill_rank_power_weight(rank: str, *, normalize_skill_rank: Callable[[Any], str]) -> int:
    return {"F": 1, "E": 2, "D": 3, "C": 4, "B": 5, "A": 7, "S": 9}.get(normalize_skill_rank(rank), 1)


def compute_character_combat_score(
    character: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]] = None,
    *,
    normalize_class_current: Callable[[Any], Optional[Dict[str, Any]]],
    skill_rank_power_weight: Callable[[str], int],
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]],
    resource_name_for_character: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], str],
    normalize_injury_state: Callable[[Any], Optional[Dict[str, Any]]],
) -> int:
    attrs = character.get("attributes") or {}
    level = max(1, int(character.get("level", 1) or 1))
    class_current = normalize_class_current(character.get("class_current")) or {}
    class_level = max(1, int(class_current.get("level", 1) or 1))
    class_weight = skill_rank_power_weight(class_current.get("rank", "F"))
    hp_ratio = int(round((int(character.get("hp_current", 0) or 0) / max(1, int(character.get("hp_max", 1) or 1))) * 100))
    sta_ratio = int(round((int(character.get("sta_current", 0) or 0) / max(1, int(character.get("sta_max", 1) or 1))) * 100))
    res_ratio = int(round((int(character.get("res_current", 0) or 0) / max(1, int(character.get("res_max", 1) or 1))) * 100))
    base_stats = (
        int(attrs.get("str", 0) or 0)
        + int(attrs.get("dex", 0) or 0)
        + int(attrs.get("con", 0) or 0)
        + int(attrs.get("int", 0) or 0)
        + int(attrs.get("wis", 0) or 0)
        + int(attrs.get("luck", 0) or 0)
    )
    skill_power = 0
    for raw_skill in (character.get("skills") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        skill = normalize_dynamic_skill_state(raw_skill, resource_name=resource_name_for_character(character, world_settings))
        skill_power += max(1, int(skill.get("level", 1) or 1)) * skill_rank_power_weight(skill.get("rank", "F"))
    injury_penalty = 0
    for raw_injury in (character.get("injuries") or []):
        injury = normalize_injury_state(raw_injury)
        if not injury:
            continue
        if injury.get("severity") == "schwer":
            injury_penalty += 14
        elif injury.get("severity") == "mittel":
            injury_penalty += 7
        else:
            injury_penalty += 3
    condition_penalty = max(0, len(character.get("conditions") or []) * 2)
    resource_factor = int(round((hp_ratio * 0.45) + (sta_ratio * 0.3) + (res_ratio * 0.25)))
    score = (
        (level * 9)
        + (class_level * (2 + class_weight))
        + base_stats
        + int(skill_power * 0.65)
        + int(resource_factor * 0.35)
        - injury_penalty
        - condition_penalty
    )
    return max(1, score)


def compute_npc_combat_score(
    npc_entry: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]] = None,
    *,
    normalize_class_current: Callable[[Any], Optional[Dict[str, Any]]],
    skill_rank_power_weight: Callable[[str], int],
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]],
    normalize_resource_name: Callable[[Any, str], str],
) -> int:
    level = max(1, int(npc_entry.get("level", 1) or 1))
    class_current = normalize_class_current(npc_entry.get("class_current")) or {}
    class_level = max(1, int(class_current.get("level", level) or level))
    class_weight = skill_rank_power_weight(class_current.get("rank", "F"))
    hp_ratio = int(round((int(npc_entry.get("hp_current", 0) or 0) / max(1, int(npc_entry.get("hp_max", 1) or 1))) * 100))
    sta_ratio = int(round((int(npc_entry.get("sta_current", 0) or 0) / max(1, int(npc_entry.get("sta_max", 1) or 1))) * 100))
    res_ratio = int(round((int(npc_entry.get("res_current", 0) or 0) / max(1, int(npc_entry.get("res_max", 1) or 1))) * 100))
    skill_power = 0
    for raw_skill in (npc_entry.get("skills") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        skill = normalize_dynamic_skill_state(raw_skill, resource_name=normalize_resource_name((((npc_entry.get("progression") or {}).get("resource_name")) or "Aether"), "Aether"))
        skill_power += max(1, int(skill.get("level", 1) or 1)) * skill_rank_power_weight(skill.get("rank", "F"))
    score = (
        (level * 9)
        + (class_level * (2 + class_weight))
        + int(skill_power * 0.65)
        + int(((hp_ratio * 0.45) + (sta_ratio * 0.3) + (res_ratio * 0.25)) * 0.35)
    )
    return max(1, score)
