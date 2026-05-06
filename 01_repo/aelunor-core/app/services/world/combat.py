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


def build_combat_scaling_context(
    state: Dict[str, Any],
    actor: str,
    *,
    compute_character_combat_score: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], int],
    compute_npc_combat_score: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], int],
    entity_element_profile_for_character: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, List[str]]],
    entity_element_profile_for_npc: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, List[str]]],
    element_matchup_multiplier: Callable[[Dict[str, Any], Dict[str, List[str]], Dict[str, List[str]]], float],
    sorted_npc_codex_entries: Callable[[Dict[str, Any]], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    world_settings = ((state.get("world") or {}).get("settings") or {})
    world_model = state.get("world") if isinstance(state.get("world"), dict) else {}
    actor_character = ((state.get("characters") or {}).get(actor) or {})
    actor_scene = str(actor_character.get("scene_id") or "").strip()
    actor_score = compute_character_combat_score(actor_character, world_settings)
    actor_element_profile = entity_element_profile_for_character(actor_character, world_model)
    threat_scores: List[int] = []
    element_matchups: List[float] = []

    for slot_name, character in (state.get("characters") or {}).items():
        if slot_name == actor:
            continue
        if actor_scene and str(character.get("scene_id") or "").strip() != actor_scene:
            continue
        threat_scores.append(compute_character_combat_score(character, world_settings))
        enemy_profile = entity_element_profile_for_character(character, world_model)
        forward = element_matchup_multiplier(world_model, actor_element_profile, enemy_profile)
        reverse = element_matchup_multiplier(world_model, enemy_profile, actor_element_profile)
        element_matchups.append(max(0.72, min(1.35, (forward / max(0.72, reverse)))))

    for raw_npc in sorted_npc_codex_entries(state):
        npc_scene = str(raw_npc.get("last_seen_scene_id") or "").strip()
        if actor_scene and npc_scene and npc_scene != actor_scene:
            continue
        if str(raw_npc.get("status") or "active").strip().lower() == "gone":
            continue
        threat_scores.append(compute_npc_combat_score(raw_npc, world_settings))
        enemy_profile = entity_element_profile_for_npc(raw_npc, world_model)
        forward = element_matchup_multiplier(world_model, actor_element_profile, enemy_profile)
        reverse = element_matchup_multiplier(world_model, enemy_profile, actor_element_profile)
        element_matchups.append(max(0.72, min(1.35, (forward / max(0.72, reverse)))))

    threat_score = max(1, int(round(sum(threat_scores) / max(1, len(threat_scores))))) if threat_scores else actor_score
    ratio = float(actor_score) / float(max(1, threat_score))
    element_factor = max(0.8, min(1.2, (sum(element_matchups) / max(1, len(element_matchups))))) if element_matchups else 1.0
    weighted_ratio = ratio * element_factor
    pressure = "high" if weighted_ratio <= 0.78 else "medium" if weighted_ratio <= 1.24 else "low"
    return {
        "actor_score": actor_score,
        "threat_score": threat_score,
        "ratio": round(ratio, 3),
        "weighted_ratio": round(weighted_ratio, 3),
        "pressure": pressure,
        "threat_count": len(threat_scores),
        "element_factor": round(element_factor, 3),
        "element_affinities": actor_element_profile.get("affinities") or [],
    }


def apply_combat_scaling_to_patch(
    patch: Dict[str, Any],
    *,
    actor: str,
    combat_context: Dict[str, Any],
    scaling_context: Dict[str, Any],
    action_type: str,
    deep_copy: Callable[[Any], Any],
    blank_patch: Callable[[], Dict[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if action_type == "canon":
        return patch, {"applied": False, "multiplier": 1.0}
    if not bool(combat_context.get("active") or combat_context.get("hinted")):
        return patch, {"applied": False, "multiplier": 1.0}
    pressure = str(scaling_context.get("pressure") or "medium").lower()
    if pressure == "high":
        multiplier = 1.28
    elif pressure == "low":
        multiplier = 0.82
    else:
        multiplier = 1.0
    element_factor = float(scaling_context.get("element_factor", 1.0) or 1.0)
    element_adjusted = max(0.72, min(1.35, (multiplier * (1.0 / element_factor))))
    updated = deep_copy(patch or blank_patch())
    actor_patch = (updated.get("characters") or {}).get(actor)
    if not isinstance(actor_patch, dict):
        return updated, {
            "applied": False,
            "multiplier": multiplier,
            "element_factor": round(element_factor, 3),
            "effective_multiplier": round(element_adjusted, 3),
        }
    applied = False
    for key in ("hp_delta", "stamina_delta"):
        if key in actor_patch and int(actor_patch.get(key, 0) or 0) < 0:
            scaled = int(round(int(actor_patch.get(key, 0) or 0) * element_adjusted))
            if scaled == 0:
                scaled = -1
            actor_patch[key] = scaled
            applied = True
    resources_delta = actor_patch.get("resources_delta") if isinstance(actor_patch.get("resources_delta"), dict) else {}
    if resources_delta:
        for key in ("hp", "stamina", "sta", "res", "aether"):
            raw = int(resources_delta.get(key, 0) or 0)
            if raw < 0:
                scaled = int(round(raw * element_adjusted))
                if scaled == 0:
                    scaled = -1
                resources_delta[key] = scaled
                applied = True
        actor_patch["resources_delta"] = resources_delta
    updated.setdefault("characters", {})[actor] = actor_patch
    return updated, {
        "applied": applied,
        "multiplier": multiplier,
        "element_factor": round(element_factor, 3),
        "effective_multiplier": round(element_adjusted, 3),
    }
