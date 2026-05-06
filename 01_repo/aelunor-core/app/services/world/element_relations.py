from typing import Any, Callable, Dict, Tuple


def element_sort_key(
    entry: Tuple[str, Dict[str, Any]],
    *,
    normalize_codex_alias_text: Callable[[Any], str],
) -> Tuple[str, str]:
    element_id, payload = entry
    return (normalize_codex_alias_text((payload or {}).get("name", "")), str(element_id))


def relation_sort_value(value: str) -> int:
    order = {"countered": 0, "weak": 1, "neutral": 2, "strong": 3, "dominant": 4}
    return order.get(str(value or "neutral").strip().lower(), 2)


def normalize_element_relation(value: Any, *, element_relations: set[str]) -> str:
    relation = str(value or "neutral").strip().lower()
    return relation if relation in element_relations else "neutral"
