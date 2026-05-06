from typing import Any, Callable, Dict, List, Optional


def normalize_element_id_list(
    values: Any,
    world: Optional[Dict[str, Any]] = None,
    *,
    normalize_codex_alias_text: Callable[[Any], str],
    element_id_from_name: Callable[[str], str],
) -> List[str]:
    ids = set(((world or {}).get("elements") or {}).keys()) if isinstance((world or {}).get("elements"), dict) else set()
    alias_index = ((world or {}).get("element_alias_index") or {}) if isinstance((world or {}).get("element_alias_index"), dict) else {}
    out: List[str] = []
    for raw in (values or []):
        text = str(raw or "").strip()
        if not text:
            continue
        if text in ids:
            out.append(text)
            continue
        normalized = normalize_codex_alias_text(text)
        matched = alias_index.get(normalized) if isinstance(alias_index.get(normalized), list) else []
        if isinstance(matched, list) and len(matched) == 1:
            out.append(str(matched[0]))
            continue
        candidate_id = element_id_from_name(text)
        if candidate_id in ids:
            out.append(candidate_id)
    return list(dict.fromkeys([entry for entry in out if entry]))
