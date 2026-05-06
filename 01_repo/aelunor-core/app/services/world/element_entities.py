from typing import Any, Callable, Dict, List, Optional


def entity_element_profile_for_character(
    character: Dict[str, Any],
    world: Dict[str, Any],
    *,
    normalize_class_current: Callable[[Any], Optional[Dict[str, Any]]],
    resolve_class_element_id: Callable[[Optional[Dict[str, Any]], Dict[str, Any]], Optional[str]],
    normalize_element_id_list: Callable[[Any, Optional[Dict[str, Any]]], List[str]],
) -> Dict[str, List[str]]:
    class_current = normalize_class_current(character.get("class_current")) or {}
    class_element = resolve_class_element_id(class_current, world)
    affinities = normalize_element_id_list(
        [*(character.get("element_affinities") or []), *(class_current.get("element_tags") or []), class_element],
        world,
    )
    resistances = normalize_element_id_list(character.get("element_resistances") or [], world)
    weaknesses = normalize_element_id_list(character.get("element_weaknesses") or [], world)
    return {"affinities": affinities, "resistances": resistances, "weaknesses": weaknesses}


def entity_element_profile_for_npc(
    npc_entry: Dict[str, Any],
    world: Dict[str, Any],
    *,
    normalize_class_current: Callable[[Any], Optional[Dict[str, Any]]],
    resolve_class_element_id: Callable[[Optional[Dict[str, Any]], Dict[str, Any]], Optional[str]],
    normalize_element_id_list: Callable[[Any, Optional[Dict[str, Any]]], List[str]],
) -> Dict[str, List[str]]:
    class_current = normalize_class_current(npc_entry.get("class_current")) or {}
    class_element = resolve_class_element_id(class_current, world)
    affinities = normalize_element_id_list(
        [*(npc_entry.get("element_affinities") or []), *(class_current.get("element_tags") or []), class_element],
        world,
    )
    resistances = normalize_element_id_list(npc_entry.get("element_resistances") or [], world)
    weaknesses = normalize_element_id_list(npc_entry.get("element_weaknesses") or [], world)
    return {"affinities": affinities, "resistances": resistances, "weaknesses": weaknesses}
