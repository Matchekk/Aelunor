from typing import Any, Callable, Dict, List, Optional


def normalize_skill_elements_for_world(
    skill: Dict[str, Any],
    world: Optional[Dict[str, Any]],
    *,
    deep_copy: Callable[[Any], Any],
    normalize_element_id_list: Callable[[Any, Optional[Dict[str, Any]]], List[str]],
) -> Dict[str, Any]:
    normalized = deep_copy(skill or {})
    normalized["elements"] = normalize_element_id_list(normalized.get("elements") or [], world or {})
    primary_candidates = normalize_element_id_list([normalized.get("element_primary")], world or {})
    normalized["element_primary"] = primary_candidates[0] if primary_candidates else (normalized["elements"][0] if normalized["elements"] else None)
    if normalized.get("element_primary") and normalized["element_primary"] not in (normalized.get("elements") or []):
        normalized["elements"] = [normalized["element_primary"], *(normalized.get("elements") or [])]
    normalized["element_synergies"] = normalize_element_id_list(normalized.get("element_synergies") or [], world or {}) or None
    return normalized
