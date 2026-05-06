from typing import Any, Callable, Dict, List, Optional


def default_combat_meta(*, utc_now: Callable[[], str]) -> Dict[str, Any]:
    return {
        "active": False,
        "combat_id": "",
        "round": 0,
        "phase": "idle",
        "action_queue": [],
        "participants": [],
        "last_resolution": {},
        "updated_at": utc_now(),
    }


def normalize_combat_meta(
    meta: Dict[str, Any],
    *,
    default_combat_meta: Callable[[], Dict[str, Any]],
    deep_copy: Callable[[Any], Any],
    action_types: set[str],
    utc_now: Callable[[], str],
) -> Dict[str, Any]:
    combat = deep_copy(meta.get("combat") or default_combat_meta())
    defaults = default_combat_meta()
    combat["active"] = bool(combat.get("active", defaults["active"]))
    combat["combat_id"] = str(combat.get("combat_id") or "").strip()
    combat["round"] = max(0, int(combat.get("round", defaults["round"]) or defaults["round"]))
    phase = str(combat.get("phase") or defaults["phase"]).strip().lower()
    combat["phase"] = phase if phase in {"idle", "collecting", "resolving", "ended"} else defaults["phase"]
    combat["participants"] = [str(entry).strip() for entry in (combat.get("participants") or []) if str(entry).strip()]
    queue_entries: List[Dict[str, Any]] = []
    for raw in (combat.get("action_queue") or []):
        if not isinstance(raw, dict):
            continue
        actor = str(raw.get("actor") or "").strip()
        action_type = str(raw.get("action_type") or "").strip().lower()
        if not actor or action_type not in action_types:
            continue
        queue_entries.append(
            {
                "turn": max(0, int(raw.get("turn", 0) or 0)),
                "actor": actor,
                "action_type": action_type,
                "summary": str(raw.get("summary") or "").strip(),
                "created_at": str(raw.get("created_at") or utc_now()),
            }
        )
    combat["action_queue"] = queue_entries[-20:]
    combat["last_resolution"] = deep_copy(combat.get("last_resolution") or {})
    combat["updated_at"] = str(combat.get("updated_at") or utc_now())
    meta["combat"] = combat
    return combat


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


def infer_combat_context(
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    text: str,
    *,
    normalized_eval_text: Callable[[Any], str],
    normalize_combat_meta: Callable[[Dict[str, Any]], Dict[str, Any]],
    combat_narrative_hints: tuple[str, ...],
) -> Dict[str, Any]:
    normalized_text = normalized_eval_text(text)
    meta_combat = normalize_combat_meta(state.setdefault("meta", {}))
    actor_char = ((state.get("characters") or {}).get(actor) or {})
    actor_in_combat = bool((((actor_char.get("derived") or {}).get("combat_flags") or {}).get("in_combat", False)))
    hinted = any(keyword in normalized_text for keyword in combat_narrative_hints)
    return {
        "active": bool(meta_combat.get("active") or actor_in_combat),
        "hinted": hinted,
        "actor_in_combat": actor_in_combat,
        "phase": meta_combat.get("phase", "idle"),
        "action_type": action_type,
    }


def patch_has_combat_signal(patch: Dict[str, Any]) -> bool:
    for upd in (patch.get("characters") or {}).values():
        if not isinstance(upd, dict):
            continue
        if int(upd.get("hp_delta", 0) or 0) < 0:
            return True
        if int(upd.get("stamina_delta", 0) or 0) < 0:
            return True
        resources_delta = upd.get("resources_delta") if isinstance(upd.get("resources_delta"), dict) else {}
        if any(int(resources_delta.get(key, 0) or 0) < 0 for key in ("hp", "stamina", "sta", "res", "aether")):
            return True
        for effect in (upd.get("effects_add") or []):
            if isinstance(effect, dict) and str(effect.get("category") or "").strip().lower() == "combat":
                return True
    return False


def update_combat_meta_after_turn(
    state: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    input_text: str,
    story_text: str,
    patch: Dict[str, Any],
    combat_context: Dict[str, Any],
    resolution_summary: Dict[str, Any],
    normalize_combat_meta: Callable[[Dict[str, Any]], Dict[str, Any]],
    utc_now: Callable[[], str],
    normalized_eval_text: Callable[[Any], str],
    patch_has_combat_signal: Callable[[Dict[str, Any]], bool],
    combat_narrative_hints: tuple[str, ...],
    combat_end_hints: tuple[str, ...],
    make_id: Callable[[str], str],
    first_sentences: Callable[[str, int], str],
    deep_copy: Callable[[Any], Any],
) -> Dict[str, Any]:
    meta = state.setdefault("meta", {})
    combat = normalize_combat_meta(meta)
    turn_number = int(meta.get("turn", 0) or 0)
    now = utc_now()

    story_norm = normalized_eval_text(story_text)
    hinted = bool(combat_context.get("hinted")) or patch_has_combat_signal(patch) or any(
        keyword in story_norm for keyword in combat_narrative_hints
    )
    ended = any(keyword in story_norm for keyword in combat_end_hints)
    participants = [
        slot_name
        for slot_name, character in (state.get("characters") or {}).items()
        if bool((((character.get("derived") or {}).get("combat_flags") or {}).get("in_combat", False)))
    ]

    if not combat.get("active") and hinted:
        combat["active"] = True
        combat["combat_id"] = combat.get("combat_id") or make_id("cmb")
        combat["round"] = max(1, int(combat.get("round", 0) or 0) + 1)
        combat["phase"] = "resolving"
    elif combat.get("active"):
        combat["phase"] = "resolving"
        combat["round"] = max(1, int(combat.get("round", 0) or 0) + 1)

    if combat.get("active"):
        summary = str(first_sentences(story_text, 1) or "").strip()
        combat.setdefault("action_queue", []).append(
            {
                "turn": turn_number,
                "actor": actor,
                "action_type": action_type,
                "summary": summary[:220],
                "created_at": now,
            }
        )
        combat["action_queue"] = (combat.get("action_queue") or [])[-20:]
        combat["participants"] = participants or [actor]
        combat["last_resolution"] = deep_copy(resolution_summary or {})
        if ended and not patch_has_combat_signal(patch):
            combat["active"] = False
            combat["phase"] = "ended"
            combat["participants"] = []
        else:
            combat["phase"] = "collecting"
    else:
        combat["phase"] = "idle"
        combat["participants"] = []

    combat["updated_at"] = now
    meta["combat"] = combat
    return combat
