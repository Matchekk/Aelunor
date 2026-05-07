from typing import Any, Callable, Dict, Optional


def infer_skill_cost_deltas_from_text(
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    combat_context: Optional[Dict[str, Any]] = None,
    resource_name_for_character: Callable[[Dict[str, Any], Dict[str, Any]], str],
    normalized_eval_text: Callable[[Any], str],
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    if action_type == "canon":
        return {"deltas": {}, "skills": []}
    if not source_text or not ((combat_context or {}).get("active") or (combat_context or {}).get("hinted")):
        return {"deltas": {}, "skills": []}
    character = ((state.get("characters") or {}).get(actor) or {})
    world_settings = ((state.get("world") or {}).get("settings") or {})
    resource_name = resource_name_for_character(character, world_settings)
    normalized_text = normalized_eval_text(source_text)
    deltas = {"sta": 0, "res": 0}
    matched_skills: list[str] = []
    usage_hints = {"nutzt", "setzt", "wirkt", "aktiviert", "entfesselt", "kanalisiert", "schlägt", "attackiert"}
    if not any(hint in normalized_text for hint in usage_hints):
        return {"deltas": {}, "skills": []}

    for raw_skill in (character.get("skills") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        skill = normalize_dynamic_skill_state(raw_skill, resource_name=resource_name)
        cost = skill.get("cost")
        if not isinstance(cost, dict):
            continue
        amount = max(0, int(cost.get("amount", 0) or 0))
        if amount <= 0:
            continue
        name_norm = normalized_eval_text(skill.get("name", ""))
        if not name_norm:
            continue
        name_tokens = [token for token in name_norm.split() if len(token) >= 4]
        used = name_norm in normalized_text or (name_tokens and all(token in normalized_text for token in name_tokens[:2]))
        if not used:
            continue
        cost_resource = normalized_eval_text(cost.get("resource", resource_name))
        if cost_resource in {"stamina", "ausdauer", "sta"}:
            deltas["sta"] -= amount
        else:
            deltas["res"] -= amount
        matched_skills.append(str(skill.get("name") or skill.get("id")))
        if len(matched_skills) >= 2:
            break
    return {"deltas": {key: value for key, value in deltas.items() if value}, "skills": matched_skills}


def apply_skill_cost_deltas_to_patch(
    patch: Dict[str, Any],
    actor: str,
    delta_payload: Dict[str, Any],
    *,
    deep_copy: Callable[[Any], Any],
    blank_patch: Callable[[], Dict[str, Any]],
) -> Dict[str, Any]:
    deltas = delta_payload.get("deltas") if isinstance(delta_payload, dict) else {}
    if not isinstance(deltas, dict) or not deltas:
        return patch
    adjusted = deep_copy(patch or blank_patch())
    slot_patch = adjusted.setdefault("characters", {}).setdefault(actor, {})
    resources_delta = slot_patch.setdefault("resources_delta", {})
    for key, value in deltas.items():
        resources_delta[key] = int(resources_delta.get(key, 0) or 0) + int(value or 0)
    return adjusted
