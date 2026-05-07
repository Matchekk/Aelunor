from typing import Iterable


def normalize_skill_rank(value: object, *, skill_ranks: Iterable[str]) -> str:
    rank = str(value or "F").strip().upper()
    return rank if rank in set(skill_ranks) else "F"


def skill_rank_for_level(level: int, *, skill_rank_thresholds: Iterable[tuple[str, int]]) -> str:
    normalized = int(level or 0)
    if normalized <= 0:
        return "-"
    for rank, min_level in skill_rank_thresholds:
        if normalized >= min_level:
            return rank
    return "-"


def next_skill_xp_for_level(level: int) -> int:
    normalized = int(level or 0)
    if normalized <= 0:
        return 60
    return 100 + ((normalized - 1) * 35)
