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


def active_pacing_profile(
    state: Dict[str, Any],
    *,
    normalize_world_settings: Callable[[Any], Dict[str, Any]],
    deep_copy: Callable[[Any], Any],
    campaign_lengths: Iterable[str],
    pacing_profile_defaults: Dict[str, Any],
) -> Dict[str, Any]:
    settings = normalize_world_settings(((state.get("world") or {}).get("settings") or {}))
    selected = str(settings.get("campaign_length") or "medium").lower()
    if selected not in tuple(campaign_lengths):
        selected = "medium"
    profile = deep_copy((settings.get("pacing_profile") or {}).get(selected) or pacing_profile_defaults[selected])
    profile["campaign_length"] = selected
    profile["target_turn"] = (settings.get("target_turns") or {}).get(selected)
    return profile


def compute_turn_budget_estimates(
    state: Dict[str, Any],
    *,
    normalize_meta_timing: Callable[[Dict[str, Any]], Dict[str, Any]],
    normalize_world_settings: Callable[[Any], Dict[str, Any]],
    target_turns_defaults: Dict[str, Any],
    timing_defaults: Dict[str, Any],
) -> Dict[str, Any]:
    meta = state.setdefault("meta", {})
    timing = normalize_meta_timing(meta)
    settings = normalize_world_settings(((state.get("world") or {}).get("settings") or {}))
    selected = str(settings.get("campaign_length") or "medium").lower()
    target_lookup = settings.get("target_turns") or {}
    target_turns = target_lookup.get(selected)
    if selected == "open":
        timing["turns_target_est"] = None
        timing["turns_left_est"] = None
    else:
        fallback_target = target_turns_defaults["short"] if selected == "short" else target_turns_defaults["medium"]
        target = max(1, int(target_turns or fallback_target))
        current_turn = int(meta.get("turn", 0) or 0)
        timing["turns_target_est"] = target
        timing["turns_left_est"] = max(0, target - current_turn)
    timing["cycle_ema_sec"] = float(timing.get("ai_latency_ema_sec", timing_defaults["ai_latency_ema_sec"])) + float(
        timing.get("player_latency_ema_sec", timing_defaults["player_latency_ema_sec"])
    )
    return timing


def normalize_meta_timing(
    meta: Dict[str, Any],
    *,
    deep_copy: Callable[[Any], Any],
    default_meta_timing: Callable[[], Dict[str, Any]],
) -> Dict[str, Any]:
    timing = deep_copy(meta.get("timing") or default_meta_timing())
    defaults = default_meta_timing()
    for key in ("ai_latency_ema_sec", "player_latency_ema_sec", "cycle_ema_sec"):
        timing[key] = float(timing.get(key, defaults[key]) or defaults[key])
    for key in ("turns_target_est", "turns_left_est"):
        raw = timing.get(key, defaults[key])
        timing[key] = None if raw is None else max(0, int(raw))
    raw_last = timing.get("last_response_ready_ts", defaults["last_response_ready_ts"])
    timing["last_response_ready_ts"] = None if raw_last in (None, "") else float(raw_last)
    meta["timing"] = timing
    return timing


def update_turn_timing_ema(
    state: Dict[str, Any],
    request_ts: float,
    response_ts: float,
    *,
    normalize_meta_timing: Callable[[Dict[str, Any]], Dict[str, Any]],
    clamp_float: Callable[[float, float, float], float],
    ai_latency_clamp: tuple[float, float],
    player_latency_clamp: tuple[float, float],
    timing_ema_alpha: float,
    timing_defaults: Dict[str, Any],
) -> Dict[str, Any]:
    timing = normalize_meta_timing(state.setdefault("meta", {}))
    ai_latency = clamp_float(float(response_ts - request_ts), ai_latency_clamp[0], ai_latency_clamp[1])
    timing["ai_latency_ema_sec"] = (
        (1.0 - timing_ema_alpha) * float(timing.get("ai_latency_ema_sec", timing_defaults["ai_latency_ema_sec"]))
        + timing_ema_alpha * ai_latency
    )

    last_response = timing.get("last_response_ready_ts")
    if last_response is not None:
        player_latency = clamp_float(float(request_ts - float(last_response)), player_latency_clamp[0], player_latency_clamp[1])
        timing["player_latency_ema_sec"] = (
            (1.0 - timing_ema_alpha) * float(timing.get("player_latency_ema_sec", timing_defaults["player_latency_ema_sec"]))
            + timing_ema_alpha * player_latency
        )
    timing["last_response_ready_ts"] = float(response_ts)
    timing["cycle_ema_sec"] = float(timing.get("ai_latency_ema_sec", 0.0)) + float(timing.get("player_latency_ema_sec", 0.0))
    return timing
