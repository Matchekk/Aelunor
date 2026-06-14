import os

ENABLED_ENV_VALUES = {"1", "true", "yes", "on"}


def env_flag_enabled(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in ENABLED_ENV_VALUES


ENABLE_HEURISTIC_NORMALIZE_BACKFILL = env_flag_enabled("ENABLE_HEURISTIC_NORMALIZE_BACKFILL")
ENABLE_LEGACY_SHADOW_WRITEBACK = env_flag_enabled("ENABLE_LEGACY_SHADOW_WRITEBACK")


def second_brain_enabled() -> bool:
    """Campaign Second Brain master switch (AELUNOR_SECOND_BRAIN). Default OFF.

    Read at call time (not import time) so tests and benchmarks can toggle it
    per process without re-importing. When off, the brain write/retrieval hooks
    are complete no-ops and turn behavior is unchanged.
    """
    return env_flag_enabled("AELUNOR_SECOND_BRAIN")
