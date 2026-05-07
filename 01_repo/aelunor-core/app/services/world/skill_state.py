from typing import Any


def normalize_growth_potential(value: Any) -> str:
    normalized = str(value or "mittel").strip().lower() or "mittel"
    return normalized if normalized in {"niedrig", "mittel", "hoch", "legendär"} else "mittel"


def normalize_cooldown_turns(value: Any) -> int | None:
    return None if value in (None, "", False) else max(0, int(value or 0))
