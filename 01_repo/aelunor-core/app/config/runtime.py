LEGACY_CHARACTERS = ("Matchek", "Abo", "Beni")
ACTION_TYPES = ("do", "say", "story", "canon")
PHASES = ("lobby", "world_setup", "character_setup_open", "ready_to_start", "active")
MAX_PLAYERS = 6
MAX_TURN_MODEL_ATTEMPTS = 3
CONTINUE_STORY_MARKER = "__CONTINUE_STORY__"
CAMPAIGN_LENGTHS = ("short", "medium", "open")
TARGET_TURNS_DEFAULTS = {"short": 120, "medium": 720, "open": None}
PACING_PROFILE_DEFAULTS = {
    "short": {
        "beats_per_turn": 3,
        "detail_level": "low",
        "plot_density": "high",
        "sideplot_limit": 1,
        "milestone_every_n_turns": 8,
        "min_story_chars": 900,
        "max_story_chars": 2200,
    },
    "medium": {
        "beats_per_turn": 2,
        "detail_level": "medium",
        "plot_density": "medium",
        "sideplot_limit": 3,
        "milestone_every_n_turns": 18,
        "min_story_chars": 800,
        "max_story_chars": 2200,
    },
    "open": {
        "beats_per_turn": 1,
        "detail_level": "high",
        "plot_density": "medium",
        "sideplot_limit": None,
        "milestone_every_n_turns": 35,
        "min_story_chars": 700,
        "max_story_chars": 2200,
    },
}
TIMING_DEFAULTS = {
    "ai_latency_ema_sec": 40.0,
    "player_latency_ema_sec": 25.0,
    "cycle_ema_sec": 65.0,
    "turns_target_est": None,
    "turns_left_est": None,
    "last_response_ready_ts": None,
}
TIMING_EMA_ALPHA = 0.1
AI_LATENCY_CLAMP = (10.0, 90.0)
PLAYER_LATENCY_CLAMP = (5.0, 120.0)
MIN_STORY_REWRITE_ATTEMPTS = 2
MAX_STORY_COMPRESS_ATTEMPTS = 1
EXTRACTION_QUARANTINE_DEFAULT_MAX = 300
EXTRACTION_REASON_GENERIC_LOCATION = "GENERIC_LOCATION"
EXTRACTION_REASON_MISSING_ACQUIRE = "MISSING_ACQUIRE_SIGNAL"
EXTRACTION_REASON_ENV_OBJECT = "ENV_OBJECT_ONLY"
EXTRACTION_REASON_VERB_STYLE_SKILL = "VERB_STYLE_SKILL"
EXTRACTION_REASON_AMBIGUOUS_CLASS = "AMBIGUOUS_CLASS"
EXTRACTION_REASON_DUPLICATE = "DUPLICATE_LIKELY"
EXTRACTION_REASON_LOW_CONFIDENCE = "LOW_CONFIDENCE"
EXTRACTION_REASON_CONFLICT_WITH_LLM = "CONFLICT_WITH_LLM"
