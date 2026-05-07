from typing import Any


def normalize_growth_potential(value: Any) -> str:
    normalized = str(value or "mittel").strip().lower() or "mittel"
    return normalized if normalized in {"niedrig", "mittel", "hoch", "legendär"} else "mittel"
