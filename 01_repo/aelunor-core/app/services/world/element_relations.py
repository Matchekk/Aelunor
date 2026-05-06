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


def build_default_element_relations(elements: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    relation_map: Dict[str, Dict[str, str]] = {}
    element_ids = list((elements or {}).keys())
    for source_id in element_ids:
        relation_map[source_id] = {}
        for target_id in element_ids:
            relation_map[source_id][target_id] = "neutral"
    return relation_map


def set_element_relation(
    relations: Dict[str, Dict[str, str]],
    source_id: str,
    target_id: str,
    relation: str,
    *,
    normalize_element_relation: Callable[[Any], str],
) -> None:
    if source_id not in relations:
        relations[source_id] = {}
    relations[source_id][target_id] = normalize_element_relation(relation)


def element_pair_rule_ids(
    elements: Dict[str, Dict[str, Any]],
    name_a: str,
    name_b: str,
    *,
    normalize_codex_alias_text: Callable[[Any], str],
) -> Tuple[str, str]:
    wanted_a = normalize_codex_alias_text(name_a)
    wanted_b = normalize_codex_alias_text(name_b)
    found_a = ""
    found_b = ""
    for element_id, profile in (elements or {}).items():
        normalized_name = normalize_codex_alias_text((profile or {}).get("name", ""))
        if not found_a and normalized_name == wanted_a:
            found_a = element_id
        if not found_b and normalized_name == wanted_b:
            found_b = element_id
    return found_a, found_b


def apply_element_anchor_relation_rules(
    elements: Dict[str, Dict[str, Any]],
    relations: Dict[str, Dict[str, str]],
    *,
    element_pair_rule_ids: Callable[[Dict[str, Dict[str, Any]], str, str], Tuple[str, str]],
    set_element_relation: Callable[[Dict[str, Dict[str, str]], str, str, str], None],
) -> None:
    predefined = [
        ("Feuer", "Wasser", "weak"),
        ("Wasser", "Feuer", "strong"),
        ("Feuer", "Erde", "strong"),
        ("Erde", "Feuer", "neutral"),
        ("Luft", "Erde", "strong"),
        ("Erde", "Luft", "weak"),
        ("Licht", "Schatten", "strong"),
        ("Schatten", "Licht", "countered"),
        ("Wasser", "Erde", "weak"),
        ("Erde", "Wasser", "strong"),
        ("Luft", "Wasser", "neutral"),
        ("Wasser", "Luft", "neutral"),
    ]
    for src_name, dst_name, relation in predefined:
        src_id, dst_id = element_pair_rule_ids(elements, src_name, dst_name)
        if src_id and dst_id:
            set_element_relation(relations, src_id, dst_id, relation)


def normalize_element_relations(
    relations: Any,
    elements: Dict[str, Dict[str, Any]],
    *,
    build_default_element_relations: Callable[[Dict[str, Dict[str, Any]]], Dict[str, Dict[str, str]]],
    normalize_element_relation: Callable[[Any], str],
    stable_sorted_mapping: Callable[..., Dict[str, Any]],
) -> Dict[str, Dict[str, str]]:
    element_ids = list((elements or {}).keys())
    normalized = build_default_element_relations(elements)
    raw = relations if isinstance(relations, dict) else {}
    for source_id, target_map in raw.items():
        source = str(source_id or "").strip()
        if source not in normalized or not isinstance(target_map, dict):
            continue
        for target_id, value in target_map.items():
            target = str(target_id or "").strip()
            if target not in normalized[source]:
                continue
            normalized[source][target] = normalize_element_relation(value)
    for element_id in element_ids:
        normalized.setdefault(element_id, {})
        for target_id in element_ids:
            normalized[element_id][target_id] = normalize_element_relation(
                normalized[element_id].get(target_id, "neutral")
            )
    # deterministically set self-relations (default neutral)
    for element_id in element_ids:
        if element_id not in normalized:
            normalized[element_id] = {}
        normalized[element_id][element_id] = normalize_element_relation(
            normalized[element_id].get(element_id, "neutral")
        )
    return stable_sorted_mapping(
        {src: stable_sorted_mapping(dst_map, key_fn=lambda item: item[0]) for src, dst_map in normalized.items()},
        key_fn=lambda item: item[0],
    )


def resolve_element_relation(
    world: Dict[str, Any],
    source_element_id: str,
    target_element_id: str,
    *,
    normalize_element_relation: Callable[[Any], str],
) -> str:
    source = str(source_element_id or "").strip()
    target = str(target_element_id or "").strip()
    if not source or not target:
        return "neutral"
    relations = (world or {}).get("element_relations") if isinstance((world or {}).get("element_relations"), dict) else {}
    source_map = relations.get(source) if isinstance(relations.get(source), dict) else {}
    return normalize_element_relation(source_map.get(target, "neutral"))


def get_element_relation(
    world: Dict[str, Any],
    source_element_id: str,
    target_element_id: str,
    *,
    normalize_element_relation: Callable[[Any], str],
) -> str:
    return resolve_element_relation(
        world,
        source_element_id,
        target_element_id,
        normalize_element_relation=normalize_element_relation,
    )


def generate_element_relations(
    elements: Dict[str, Dict[str, Any]],
    *,
    build_default_element_relations: Callable[[Dict[str, Dict[str, Any]]], Dict[str, Dict[str, str]]],
    apply_element_anchor_relation_rules: Callable[[Dict[str, Dict[str, Any]], Dict[str, Dict[str, str]]], None],
    normalize_codex_alias_text: Callable[[Any], str],
    set_element_relation: Callable[[Dict[str, Dict[str, str]], str, str, str], None],
    normalize_element_relations: Callable[[Dict[str, Dict[str, str]], Dict[str, Dict[str, Any]]], Dict[str, Dict[str, str]]],
) -> Dict[str, Dict[str, str]]:
    relations = build_default_element_relations(elements)
    apply_element_anchor_relation_rules(elements, relations)
    ids_by_name = {
        normalize_codex_alias_text((profile or {}).get("name", "")): element_id
        for element_id, profile in (elements or {}).items()
        if isinstance(profile, dict)
    }
    for source_id, profile in (elements or {}).items():
        if not isinstance(profile, dict):
            continue
        for target_name in (profile.get("strengths_against") or []):
            target_id = ids_by_name.get(normalize_codex_alias_text(target_name))
            if target_id:
                set_element_relation(relations, source_id, target_id, "strong")
        for target_name in (profile.get("weaknesses_against") or []):
            target_id = ids_by_name.get(normalize_codex_alias_text(target_name))
            if target_id:
                set_element_relation(relations, source_id, target_id, "weak")
        for target_name in (profile.get("synergies_with") or []):
            target_id = ids_by_name.get(normalize_codex_alias_text(target_name))
            if target_id and relations.get(source_id, {}).get(target_id) == "neutral":
                set_element_relation(relations, source_id, target_id, "strong")
    return normalize_element_relations(relations, elements)
