from typing import Any, Callable, Dict, Iterable, Optional

from app.config.runtime import (
    AI_LATENCY_CLAMP,
    CAMPAIGN_LENGTHS,
    PACING_PROFILE_DEFAULTS,
    PLAYER_LATENCY_CLAMP,
    TARGET_TURNS_DEFAULTS,
    TIMING_DEFAULTS,
    TIMING_EMA_ALPHA,
)
from app.core.ids import deep_copy
from app.services.world.progression import normalize_resource_name


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def default_meta_timing() -> Dict[str, Any]:
    return deep_copy(TIMING_DEFAULTS)


def default_campaign_length_settings(
    *,
    deep_copy: Callable[[Any], Any] = deep_copy,
    target_turns_defaults: Dict[str, Any] = TARGET_TURNS_DEFAULTS,
    pacing_profile_defaults: Dict[str, Any] = PACING_PROFILE_DEFAULTS,
) -> Dict[str, Any]:
    return {
        "campaign_length": "medium",
        "target_turns": deep_copy(target_turns_defaults),
        "pacing_profile": deep_copy(pacing_profile_defaults),
    }


def normalize_world_settings(
    world_settings: Any,
    *,
    deep_copy: Callable[[Any], Any] = deep_copy,
    default_campaign_length_settings: Optional[Callable[[], Dict[str, Any]]] = None,
    normalize_resource_name: Callable[[Any, str], str] = normalize_resource_name,
    clamp_float: Callable[[float, float, float], float] = clamp_float,
    campaign_lengths: Iterable[str] = CAMPAIGN_LENGTHS,
) -> Dict[str, Any]:
    normalized = deep_copy(world_settings or {})
    defaults_provider = default_campaign_length_settings or globals()["default_campaign_length_settings"]
    defaults = defaults_provider()
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
    normalize_world_settings: Optional[Callable[[Any], Dict[str, Any]]] = None,
    deep_copy: Callable[[Any], Any] = deep_copy,
    campaign_lengths: Iterable[str] = CAMPAIGN_LENGTHS,
    pacing_profile_defaults: Dict[str, Any] = PACING_PROFILE_DEFAULTS,
) -> Dict[str, Any]:
    normalize_settings = normalize_world_settings or globals()["normalize_world_settings"]
    settings = normalize_settings(((state.get("world") or {}).get("settings") or {}))
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
    normalize_meta_timing: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    normalize_world_settings: Optional[Callable[[Any], Dict[str, Any]]] = None,
    target_turns_defaults: Dict[str, Any] = TARGET_TURNS_DEFAULTS,
    timing_defaults: Dict[str, Any] = TIMING_DEFAULTS,
) -> Dict[str, Any]:
    meta = state.setdefault("meta", {})
    normalize_timing = normalize_meta_timing or globals()["normalize_meta_timing"]
    normalize_settings = normalize_world_settings or globals()["normalize_world_settings"]
    timing = normalize_timing(meta)
    settings = normalize_settings(((state.get("world") or {}).get("settings") or {}))
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
    deep_copy: Callable[[Any], Any] = deep_copy,
    default_meta_timing: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    defaults_provider = default_meta_timing or globals()["default_meta_timing"]
    timing = deep_copy(meta.get("timing") or defaults_provider())
    defaults = defaults_provider()
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
    normalize_meta_timing: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    clamp_float: Callable[[float, float, float], float] = clamp_float,
    ai_latency_clamp: tuple[float, float] = AI_LATENCY_CLAMP,
    player_latency_clamp: tuple[float, float] = PLAYER_LATENCY_CLAMP,
    timing_ema_alpha: float = TIMING_EMA_ALPHA,
    timing_defaults: Dict[str, Any] = TIMING_DEFAULTS,
) -> Dict[str, Any]:
    normalize_timing = normalize_meta_timing or globals()["normalize_meta_timing"]
    timing = normalize_timing(state.setdefault("meta", {}))
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


def milestone_state_for_turn(turn_number: int, profile: Dict[str, Any]) -> Dict[str, int | bool]:
    every = max(1, int(profile.get("milestone_every_n_turns", 18) or 18))
    current_turn = max(0, int(turn_number or 0))
    if current_turn <= 0:
        return {"is_milestone": False, "last": 0, "next": every}
    is_milestone = current_turn % every == 0
    last = current_turn if is_milestone else (current_turn // every) * every
    next_turn = current_turn + every if is_milestone else last + every
    return {"is_milestone": is_milestone, "last": last, "next": max(next_turn, every)}


def build_pacing_instruction_block(
    state: Dict[str, Any],
    *,
    active_pacing_profile: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    milestone_state_for_turn: Callable[[int, Dict[str, Any]], Dict[str, int | bool]] = milestone_state_for_turn,
) -> Dict[str, Any]:
    active_profile = active_pacing_profile or globals()["active_pacing_profile"]
    profile = active_profile(state)
    milestone = milestone_state_for_turn(int((state.get("meta") or {}).get("turn", 0) or 0), profile)
    lines = [
        "PACING INSTRUCTIONS:",
        f"- campaign_length={profile.get('campaign_length')}",
        f"- beats_per_turn={int(profile.get('beats_per_turn', 2) or 2)}",
        f"- detail_level={profile.get('detail_level', 'medium')}",
        f"- plot_density={profile.get('plot_density', 'medium')}",
        f"- sideplot_limit={profile.get('sideplot_limit', 'null')}",
        f"- milestone_every_n_turns={int(profile.get('milestone_every_n_turns', 18) or 18)}",
        f"- min_story_chars={int(profile.get('min_story_chars', 800) or 800)}",
        f"- max_story_chars={int(profile.get('max_story_chars', 2200) or 2200)}",
        f"- is_milestone_turn={'yes' if milestone['is_milestone'] else 'no'}",
    ]
    if profile.get("campaign_length") == "short":
        lines.extend(
            [
                "- Für SHORT: 3 Beats zwingend (Setup -> Konsequenz -> Eskalation) mit klar spielbarer Endlage.",
                "- Keine Auswahlmenüs und keine Entscheidungsfragen: beschreibe Konsequenzen und offene Lage, der Spieler entscheidet selbst.",
                "- Weniger Kulissenbeschreibung, mehr sichtbarer Plot-Fortschritt pro Turn.",
            ]
        )
    lines.extend(
        [
            "- Halte die story im Bereich min_story_chars bis max_story_chars Zeichen, überschreite max_story_chars nicht und schließe sie vollständig ab.",
            "- Wiederhole keine vorherigen Absätze.",
            "- Große Progressionssprünge (Ascension, Rank-Sprung, neue A/S-Skills) sind nur auf Milestone-Turns erlaubt.",
        ]
    )
    return {
        "profile": profile,
        "milestone": milestone,
        "text": "\n".join(lines),
    }
