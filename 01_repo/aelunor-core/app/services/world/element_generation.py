from typing import Any, Callable, Dict, List, Tuple


def generated_element_too_similar(
    candidate: Dict[str, Any],
    existing: List[Dict[str, Any]],
    *,
    normalize_codex_alias_text: Callable[[Any], str],
    element_similarity_blacklist: Dict[str, List[str]],
) -> Tuple[bool, str]:
    name_norm = normalize_codex_alias_text(candidate.get("name", ""))
    theme_norm = normalize_codex_alias_text(candidate.get("theme", ""))
    if not name_norm:
        return True, "EMPTY_NAME"
    for core_norm, terms in element_similarity_blacklist.items():
        if name_norm == core_norm:
            return True, "TOO_SIMILAR_TO_CORE"
        if any(term in name_norm for term in terms):
            return True, "TOO_SIMILAR_TO_CORE"
        if theme_norm and any(term in theme_norm for term in terms):
            return True, "TOO_SIMILAR_TO_CORE"
    for entry in existing:
        existing_name_norm = normalize_codex_alias_text(entry.get("name", ""))
        existing_theme_norm = normalize_codex_alias_text(entry.get("theme", ""))
        if not existing_name_norm:
            continue
        if name_norm == existing_name_norm:
            return True, "DUPLICATE_NAME"
        if name_norm.startswith(existing_name_norm) or existing_name_norm.startswith(name_norm):
            return True, "DUPLICATE_THEME"
        if theme_norm and existing_theme_norm and (
            theme_norm == existing_theme_norm
            or theme_norm in existing_theme_norm
            or existing_theme_norm in theme_norm
        ):
            return True, "DUPLICATE_THEME"
    return False, ""
