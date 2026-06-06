from typing import Any, Callable, Dict, List, Optional

from app.config.elements import ELEMENT_RELATION_SCORE
from app.services.world.element_runtime import normalize_element_id_list, resolve_element_relation
from app.services.world.progression import normalize_class_current


def entity_element_profile_for_character(
    character: Dict[str, Any],
    world: Dict[str, Any],
    *,
    normalize_class_current: Callable[[Any], Optional[Dict[str, Any]]] = normalize_class_current,
    resolve_class_element_id: Optional[Callable[[Optional[Dict[str, Any]], Dict[str, Any]], Optional[str]]] = None,
    normalize_element_id_list: Callable[[Any, Optional[Dict[str, Any]]], List[str]] = normalize_element_id_list,
) -> Dict[str, List[str]]:
    class_current = normalize_class_current(character.get("class_current")) or {}
    if resolve_class_element_id is None:
        from app.services.world.element_runtime import resolve_class_element_id

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
    normalize_class_current: Callable[[Any], Optional[Dict[str, Any]]] = normalize_class_current,
    resolve_class_element_id: Optional[Callable[[Optional[Dict[str, Any]], Dict[str, Any]], Optional[str]]] = None,
    normalize_element_id_list: Callable[[Any, Optional[Dict[str, Any]]], List[str]] = normalize_element_id_list,
) -> Dict[str, List[str]]:
    class_current = normalize_class_current(npc_entry.get("class_current")) or {}
    if resolve_class_element_id is None:
        from app.services.world.element_runtime import resolve_class_element_id

    class_element = resolve_class_element_id(class_current, world)
    affinities = normalize_element_id_list(
        [*(npc_entry.get("element_affinities") or []), *(class_current.get("element_tags") or []), class_element],
        world,
    )
    resistances = normalize_element_id_list(npc_entry.get("element_resistances") or [], world)
    weaknesses = normalize_element_id_list(npc_entry.get("element_weaknesses") or [], world)
    return {"affinities": affinities, "resistances": resistances, "weaknesses": weaknesses}


def element_matchup_multiplier(
    world: Dict[str, Any],
    attacker_profile: Dict[str, List[str]],
    defender_profile: Dict[str, List[str]],
    *,
    resolve_element_relation: Callable[[Dict[str, Any], str, str], str] = resolve_element_relation,
    element_relation_score: Dict[str, float] = ELEMENT_RELATION_SCORE,
) -> float:
    attacker = attacker_profile.get("affinities") or []
    defender_affinities = defender_profile.get("affinities") or []
    defender_resistances = set(defender_profile.get("resistances") or [])
    defender_weaknesses = set(defender_profile.get("weaknesses") or [])
    if not attacker:
        return 1.0
    multipliers: List[float] = []
    for source in attacker:
        for target in defender_affinities:
            relation = resolve_element_relation(world, source, target)
            multipliers.append(element_relation_score.get(relation, 1.0))
        if source in defender_resistances:
            multipliers.append(0.85)
        if source in defender_weaknesses:
            multipliers.append(1.15)
    if not multipliers:
        return 1.0
    avg = sum(multipliers) / max(1, len(multipliers))
    return max(0.72, min(1.35, avg))
