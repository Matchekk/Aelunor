import os

ENABLED_ENV_VALUES = {"1", "true", "yes", "on"}


def env_flag_enabled(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in ENABLED_ENV_VALUES


ENABLE_HEURISTIC_NORMALIZE_BACKFILL = env_flag_enabled("ENABLE_HEURISTIC_NORMALIZE_BACKFILL")
ENABLE_LEGACY_SHADOW_WRITEBACK = env_flag_enabled("ENABLE_LEGACY_SHADOW_WRITEBACK")
