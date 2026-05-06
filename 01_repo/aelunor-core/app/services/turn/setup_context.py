from typing import Any, Callable, Dict, Tuple


def prepare_turn_working_state(
    campaign: Dict[str, Any],
    *,
    deep_copy: Callable[[Any], Any],
    normalize_world_settings: Callable[[Dict[str, Any]], Dict[str, Any]],
    compute_turn_budget_estimates: Callable[[Dict[str, Any]], None],
    build_pacing_instruction_block: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], int, int]:
    state_before = deep_copy(campaign["state"])
    working_state = deep_copy(campaign["state"])
    working_state["meta"]["turn"] += 1
    working_state.setdefault("world", {}).setdefault("settings", {})
    working_state["world"]["settings"] = normalize_world_settings(working_state["world"].get("settings") or {})
    compute_turn_budget_estimates(working_state)
    pacing_block = build_pacing_instruction_block(working_state)
    pacing_profile = pacing_block["profile"]
    milestone_info = pacing_block["milestone"]
    min_story_chars = int(pacing_profile.get("min_story_chars", 800) or 800)
    max_story_chars = int(pacing_profile.get("max_story_chars", 2200) or 2200)
    return state_before, working_state, pacing_block, pacing_profile, milestone_info, min_story_chars, max_story_chars
