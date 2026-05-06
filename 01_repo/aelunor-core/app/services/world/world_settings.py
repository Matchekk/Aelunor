from typing import Any, Callable, Dict, Iterable


def default_campaign_length_settings(
    *,
    deep_copy: Callable[[Any], Any],
    target_turns_defaults: Dict[str, Any],
    pacing_profile_defaults: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "campaign_length": "medium",
        "target_turns": deep_copy(target_turns_defaults),
        "pacing_profile": deep_copy(pacing_profile_defaults),
    }


def normalize_world_settings(
    world_settings: Any,
    *,
    deep_copy: Callable[[Any], Any],
    default_campaign_length_settings: Callable[[], Dict[str, Any]],
    normalize_resource_name: Callable[[Any, str], str],
    clamp_float: Callable[[float, float, float], float],
    campaign_lengths: Iterable[str],
) -> Dict[str, Any]:
    normalized = deep_copy(world_settings or {})
    defaults = default_campaign_length_settings()
    campaign_length_keys = tuple(campaign_lengths)
    normalized["resource_name"] = normalize_resource_name(normalized.get("resource_name", "Aether"), "Aether")
    normalized["consequence_severity"] = str(normalized.get("consequence_severity", "mittel") or "mittel")
    if normalized["consequence_severity"] not in {"mittel", "hoch", "brutal"}:
        normalized["consequence_severity"] = "mittel"
    normalized["progression_speed"] = str(normalized.get("progression_speed", "normal") or "normal")
    if normalized["progression_speed"] not in {"langsam", "normal", "schnell"}:
        normalized["progression_speed"] = "normal"
    normalized["evolution_cost_policy"] = str(normalized.get("evolution_cost_policy", "leicht") or "leicht")
    if normalized["evolution_cost_policy"] not in {"gratis", "leicht", "hart"}:
        normalized["evolution_cost_policy"] = "leicht"
    normalized["offclass_xp_multiplier"] = clamp_float(float(normalized.get("offclass_xp_multiplier", 0.7) or 0.7), 0.1, 1.0)
    normalized["onclass_xp_multiplier"] = clamp_float(float(normalized.get("onclass_xp_multiplier", 1.0) or 1.0), 0.5, 2.0)
    campaign_length = str(normalized.get("campaign_length") or defaults["campaign_length"]).strip().lower()
    if campaign_length not in campaign_length_keys:
        campaign_length = defaults["campaign_length"]
    normalized["campaign_length"] = campaign_length

    target_turns = deep_copy(defaults["target_turns"])
    for key in campaign_length_keys:
        if key in (normalized.get("target_turns") or {}):
            raw = (normalized.get("target_turns") or {}).get(key)
            target_turns[key] = None if raw is None else max(1, int(raw or target_turns[key] or 1))
    target_turns["open"] = None
    normalized["target_turns"] = target_turns

    pacing = deep_copy(defaults["pacing_profile"])
    existing_pacing = normalized.get("pacing_profile") or {}
    for key in campaign_length_keys:
        row = pacing[key]
        current = existing_pacing.get(key) if isinstance(existing_pacing, dict) else {}
        if not isinstance(current, dict):
            current = {}
        row["beats_per_turn"] = max(1, int(current.get("beats_per_turn", row["beats_per_turn"]) or row["beats_per_turn"]))
        row["detail_level"] = str(current.get("detail_level", row["detail_level"]) or row["detail_level"])
        row["plot_density"] = str(current.get("plot_density", row["plot_density"]) or row["plot_density"])
        sideplot_raw = current.get("sideplot_limit", row["sideplot_limit"])
        row["sideplot_limit"] = None if sideplot_raw is None else max(0, int(sideplot_raw or 0))
        row["milestone_every_n_turns"] = max(1, int(current.get("milestone_every_n_turns", row["milestone_every_n_turns"]) or row["milestone_every_n_turns"]))
        row["min_story_chars"] = max(300, int(current.get("min_story_chars", row["min_story_chars"]) or row["min_story_chars"]))
        row["max_story_chars"] = max(row["min_story_chars"], int(current.get("max_story_chars", row["max_story_chars"]) or row["max_story_chars"]))
    normalized["pacing_profile"] = pacing
    return normalized
