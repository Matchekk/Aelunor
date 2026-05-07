from typing import Any, Callable


def normalize_growth_potential(value: Any) -> str:
    normalized = str(value or "mittel").strip().lower() or "mittel"
    return normalized if normalized in {"niedrig", "mittel", "hoch", "legendär"} else "mittel"


def normalize_cooldown_turns(value: Any) -> int | None:
    return None if value in (None, "", False) else max(0, int(value or 0))


def normalize_skill_element_fields(elements: Any, element_primary: Any) -> tuple[list[str], str | None]:
    normalized_elements = list(dict.fromkeys([str(tag).strip() for tag in (elements or []) if str(tag).strip()]))
    normalized_primary = str(element_primary or "").strip()
    if normalized_primary and normalized_primary not in normalized_elements:
        normalized_elements.insert(0, normalized_primary)
    return normalized_elements, normalized_primary or (normalized_elements[0] if normalized_elements else None)


def normalize_optional_unique_strings(value: Any) -> list[str] | None:
    normalized = [str(tag).strip() for tag in (value or []) if str(tag).strip()]
    return list(dict.fromkeys(normalized)) or None


def normalize_optional_strings(value: Any) -> list[str] | None:
    normalized = [str(tag).strip() for tag in (value or []) if str(tag).strip()]
    return normalized or None


def normalize_optional_text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def normalize_optional_lower_text(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized or None


def normalize_power_rating(
    value: Any,
    *,
    rank: str,
    level: int,
    skill_rank_sort_value: Callable[[str], int],
    clamp: Callable[[int, int, int], int],
) -> int:
    fallback = max(1, (skill_rank_sort_value(rank) + 1) * 5 + int(level or 1))
    raw_value = value if value is not None else fallback
    return clamp(int(raw_value or 1), 1, 999)


def normalize_skill_progression_fields(
    skill: dict[str, Any],
    *,
    next_skill_xp_for_level: Callable[[int], int],
    clamp: Callable[[int, int, int], int],
) -> tuple[int, int, int]:
    level = int(skill.get("level", 1) or 1)
    xp = max(0, int(skill.get("xp", 0) or 0))
    next_xp = max(1, int(skill.get("next_xp", next_skill_xp_for_level(level)) or next_skill_xp_for_level(level)))
    if xp > next_xp:
        xp = next_xp
    mastery = clamp(int(skill.get("mastery", int((xp / max(next_xp, 1)) * 100)) or 0), 0, 100)
    return xp, next_xp, mastery
