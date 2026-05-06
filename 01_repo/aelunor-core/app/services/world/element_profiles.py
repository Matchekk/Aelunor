import re
from typing import Any, Callable, Dict, Optional


def element_id_from_name(
    name: str,
    *,
    normalize_codex_alias_text: Callable[[str], str],
    make_id: Callable[[str], str],
) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_codex_alias_text(name)).strip("_")
    if not slug:
        slug = make_id("element").split("_", 1)[1]
    return f"elem_{slug[:48]}"


def default_element_profile(element_id: str, name: str, *, origin: str = "generated") -> Dict[str, Any]:
    return {
        "id": str(element_id).strip(),
        "name": str(name or "Unbenanntes Element").strip() or "Unbenanntes Element",
        "rarity": "gewöhnlich",
        "description": "",
        "theme": "",
        "origin": origin if origin in {"core", "generated", "emergent"} else "generated",
        "strengths_against": [],
        "weaknesses_against": [],
        "synergies_with": [],
        "status_effect_tags": [],
        "class_affinities": [],
        "skill_affinities": [],
        "discoverable": True,
        "lore_notes": [],
        "visual_motif": "",
        "temperament": "",
        "environment_bias": "",
        "aliases": [],
    }


def normalize_element_profile(
    raw: Any,
    *,
    fallback_id: str = "",
    fallback_origin: str = "generated",
    element_id_from_name: Callable[[str], str],
    default_element_profile: Callable[..., Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    element_id = str(raw.get("id") or fallback_id or element_id_from_name(name)).strip()
    if not element_id:
        return None
    profile = default_element_profile(element_id, name, origin=fallback_origin)
    profile.update({k: v for k, v in raw.items() if k in profile})
    profile["id"] = element_id
    profile["name"] = str(profile.get("name") or name).strip() or name
    profile["rarity"] = str(profile.get("rarity") or "gewöhnlich").strip() or "gewöhnlich"
    profile["description"] = str(profile.get("description") or "").strip()
    profile["theme"] = str(profile.get("theme") or "").strip()
    origin = str(profile.get("origin") or fallback_origin).strip().lower()
    profile["origin"] = origin if origin in {"core", "generated", "emergent"} else fallback_origin
    for key in (
        "strengths_against",
        "weaknesses_against",
        "synergies_with",
        "status_effect_tags",
        "class_affinities",
        "skill_affinities",
        "lore_notes",
        "aliases",
    ):
        profile[key] = list(dict.fromkeys([str(entry).strip() for entry in (profile.get(key) or []) if str(entry).strip()]))
    profile["discoverable"] = bool(profile.get("discoverable", True))
    profile["visual_motif"] = str(profile.get("visual_motif") or "").strip()
    profile["temperament"] = str(profile.get("temperament") or "").strip()
    profile["environment_bias"] = str(profile.get("environment_bias") or "").strip()
    return profile
