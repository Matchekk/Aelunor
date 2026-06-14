import os

ENABLED_ENV_VALUES = {"1", "true", "yes", "on"}
DISABLED_ENV_VALUES = {"0", "false", "no", "off"}


def env_flag_enabled(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in ENABLED_ENV_VALUES


ENABLE_HEURISTIC_NORMALIZE_BACKFILL = env_flag_enabled("ENABLE_HEURISTIC_NORMALIZE_BACKFILL")
ENABLE_LEGACY_SHADOW_WRITEBACK = env_flag_enabled("ENABLE_LEGACY_SHADOW_WRITEBACK")


def second_brain_enabled() -> bool:
    """Campaign Second Brain master switch (AELUNOR_SECOND_BRAIN). Default ON.

    Second Brain is part of the default fast runtime (llama.cpp + Second Brain).
    Read at call time (not import time) so tests/benchmarks can toggle it per
    process without re-importing.

    Escape hatch: set ``AELUNOR_SECOND_BRAIN`` to ``0`` / ``false`` / ``off`` /
    ``no`` to turn it off. Unset (or any other value) means ON. When off, the
    brain write/retrieval hooks are complete no-ops and turn behavior is
    unchanged. Brain errors never break the turn (hooks swallow them).
    """
    raw = os.getenv("AELUNOR_SECOND_BRAIN")
    if raw is None or raw.strip() == "":
        return True
    return raw.strip().lower() not in DISABLED_ENV_VALUES
