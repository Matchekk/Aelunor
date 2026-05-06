import re
from typing import Any, Callable, Dict, Optional


def race_id_from_name(
    name: str,
    *,
    normalize_codex_alias_text: Callable[[str], str],
    make_id: Callable[[str], str],
) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_codex_alias_text(name)).strip("_")
    if not slug:
        slug = make_id("race").split("_", 1)[1]
    return f"race_{slug[:48]}"


def beast_id_from_name(
    name: str,
    *,
    normalize_codex_alias_text: Callable[[str], str],
    make_id: Callable[[str], str],
) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_codex_alias_text(name)).strip("_")
    if not slug:
        slug = make_id("beast").split("_", 1)[1]
    return f"beast_{slug[:48]}"


def default_race_profile(race_id: str, name: str) -> Dict[str, Any]:
    return {
        "id": str(race_id).strip(),
        "name": str(name or "Unbekannte Rasse").strip() or "Unbekannte Rasse",
        "kind": "volk",
        "rarity": "gewöhnlich",
        "description_short": "",
        "appearance": "",
        "homeland": "",
        "culture": "",
        "temperament": "",
        "strength_tags": [],
        "weakness_tags": [],
        "class_affinities": [],
        "skill_affinities": [],
        "social_reputation": "",
        "playable": True,
        "notable_traits": [],
        "aliases": [],
    }


def default_beast_profile(beast_id: str, name: str) -> Dict[str, Any]:
    return {
        "id": str(beast_id).strip(),
        "name": str(name or "Unbekannte Bestie").strip() or "Unbekannte Bestie",
        "category": "bestie",
        "danger_rating": 1,
        "habitat": "",
        "behavior": "",
        "appearance": "",
        "strength_tags": [],
        "weakness_tags": [],
        "combat_style": "",
        "known_abilities": [],
        "loot_tags": [],
        "lore_notes": [],
        "aliases": [],
    }


def normalize_race_profile(
    raw: Any,
    *,
    fallback_id: str = "",
    race_id_from_name: Callable[[str], str],
    default_race_profile: Callable[[str, str], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    race_id = str(raw.get("id") or fallback_id or race_id_from_name(name)).strip()
    if not race_id:
        return None
    profile = default_race_profile(race_id, name)
    profile["kind"] = str(raw.get("kind") or profile["kind"]).strip() or profile["kind"]
    profile["rarity"] = str(raw.get("rarity") or profile["rarity"]).strip() or profile["rarity"]
    profile["description_short"] = str(raw.get("description_short") or "").strip()
    profile["appearance"] = str(raw.get("appearance") or "").strip()
    profile["homeland"] = str(raw.get("homeland") or "").strip()
    profile["culture"] = str(raw.get("culture") or "").strip()
    profile["temperament"] = str(raw.get("temperament") or "").strip()
    profile["social_reputation"] = str(raw.get("social_reputation") or "").strip()
    profile["playable"] = bool(raw.get("playable", True))
    for key in ("strength_tags", "weakness_tags", "class_affinities", "skill_affinities", "notable_traits", "aliases"):
        values = [str(entry).strip() for entry in (raw.get(key) or []) if str(entry).strip()]
        profile[key] = list(dict.fromkeys(values))
    return profile


def normalize_beast_profile(
    raw: Any,
    *,
    fallback_id: str = "",
    beast_id_from_name: Callable[[str], str],
    default_beast_profile: Callable[[str, str], Dict[str, Any]],
    clamp: Callable[[int, int, int], int],
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    beast_id = str(raw.get("id") or fallback_id or beast_id_from_name(name)).strip()
    if not beast_id:
        return None
    profile = default_beast_profile(beast_id, name)
    profile["category"] = str(raw.get("category") or profile["category"]).strip() or profile["category"]
    profile["danger_rating"] = clamp(int(raw.get("danger_rating", 1) or 1), 1, 20)
    profile["habitat"] = str(raw.get("habitat") or "").strip()
    profile["behavior"] = str(raw.get("behavior") or "").strip()
    profile["appearance"] = str(raw.get("appearance") or "").strip()
    profile["combat_style"] = str(raw.get("combat_style") or "").strip()
    for key in ("strength_tags", "weakness_tags", "known_abilities", "loot_tags", "lore_notes", "aliases"):
        values = [str(entry).strip() for entry in (raw.get(key) or []) if str(entry).strip()]
        profile[key] = list(dict.fromkeys(values))
    return profile
