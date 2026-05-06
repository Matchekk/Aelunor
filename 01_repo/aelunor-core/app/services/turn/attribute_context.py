from typing import Any, Callable, Dict, Tuple


def build_turn_attribute_context(
    working_state: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    content: str,
    combat_context: Dict[str, Any],
    derive_attribute_relevance: Callable[..., Dict[str, Any]],
    compute_attribute_bias: Callable[..., Dict[str, Any]],
    compose_attribute_prompt_hints: Callable[[Dict[str, Any], Dict[str, Any]], str],
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    actor_character = (working_state.get("characters", {}) or {}).get(actor, {})
    attribute_profile = derive_attribute_relevance(working_state, actor, action_type, content, combat_context)
    attribute_bias = compute_attribute_bias(
        attribute_profile,
        actor_character,
        ((working_state.get("world") or {}).get("settings") or {}),
    )
    if action_type == "canon":
        attribute_profile = {
            "primary_attributes": [],
            "influence_tier": "none",
            "narrative_bias": [],
            "combat_active": bool(combat_context.get("active")),
        }
        attribute_bias = {
            "damage_taken_mult": 1.0,
            "cost_mult": 1.0,
            "complication_mult": 1.0,
            "outgoing_effect_mult": 1.0,
        }
    attribute_prompt_hints = compose_attribute_prompt_hints(attribute_profile, attribute_bias)
    return attribute_profile, attribute_bias, attribute_prompt_hints
