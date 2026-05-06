from typing import Any, Callable


def skill_rank_power_weight(rank: str, *, normalize_skill_rank: Callable[[Any], str]) -> int:
    return {"F": 1, "E": 2, "D": 3, "C": 4, "B": 5, "A": 7, "S": 9}.get(normalize_skill_rank(rank), 1)
