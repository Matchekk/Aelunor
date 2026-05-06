from typing import Any, Callable, Dict, List, Tuple


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


def build_element_alias_index(
    elements: Dict[str, Dict[str, Any]],
    *,
    build_entity_alias_variants: Callable[[str, List[str]], List[str]],
    normalize_codex_alias_text: Callable[[Any], str],
    stable_sorted_mapping: Callable[..., Dict[str, List[str]]],
) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for element_id, profile in (elements or {}).items():
        if not isinstance(profile, dict):
            continue
        variants = build_entity_alias_variants(str(profile.get("name") or element_id), profile.get("aliases") or [])
        for alias in variants:
            normalized = normalize_codex_alias_text(alias)
            if not normalized:
                continue
            index.setdefault(normalized, [])
            if element_id not in index[normalized]:
                index[normalized].append(element_id)
    for alias, ids in list(index.items()):
        index[alias] = sorted(set(ids), key=str)
    return stable_sorted_mapping(index, key_fn=lambda item: item[0])
