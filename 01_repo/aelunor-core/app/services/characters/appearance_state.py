import re
from typing import Any, Dict, List

from app.core.ids import deep_copy
from app.services.world.appearance import active_faction_ids, default_appearance_profile
from app.services.world.math_utils import clamp
from app.services.world.progression import normalize_class_current
from app.services.world.text_normalization import normalized_eval_text


def configure(main_globals: Dict[str, Any]) -> None:
    globals().update(main_globals)


def infer_age_years(age_text: str) -> int:
    text = normalized_eval_text(age_text)
    if not text:
        return 22
    explicit = re.search(r"\b(\d{1,3})\b", str(age_text))
    if explicit:
        return max(12, min(90, int(explicit.group(1))))
    if "teen" in text:
        return 18
    if "jung" in text or "young" in text:
        return 22
    if "erwachsen" in text or "adult" in text:
        return 30
    if "alter" in text or "älter" in text or "aelter" in text or "older" in text:
        return 42
    return 22


def derive_age_stage(age_years: int) -> str:
    if age_years <= 19:
        return "teen"
    if age_years <= 29:
        return "young"
    if age_years <= 44:
        return "adult"
    return "older"


def normalize_appearance_state(character: Dict[str, Any]) -> Dict[str, Any]:
    appearance = deep_copy(default_appearance_profile())
    appearance.update(character.get("appearance", {}) or {})
    appearance["eyes"] = {**default_appearance_profile()["eyes"], **(appearance.get("eyes") or {})}
    appearance["hair"] = {**default_appearance_profile()["hair"], **(appearance.get("hair") or {})}
    appearance["skin_marks"] = [str(entry) for entry in (appearance.get("skin_marks") or []) if str(entry).strip()]
    appearance["visual_modifiers"] = [deep_copy(entry) for entry in (appearance.get("visual_modifiers") or []) if isinstance(entry, dict)]
    appearance["scars"] = [deep_copy(entry) for entry in (appearance.get("scars") or []) if isinstance(entry, dict)]
    appearance["height"] = str(appearance.get("height", "average") or "average")
    appearance["build"] = str(appearance.get("build", "neutral") or "neutral")
    appearance["muscle"] = clamp(int(appearance.get("muscle", 0) or 0), 0, 5)
    appearance["fat"] = clamp(int(appearance.get("fat", 0) or 0), 0, 5)
    appearance["aura"] = str(appearance.get("aura", "none") or "none")
    appearance["voice_tone"] = str(appearance.get("voice_tone", "") or "")
    appearance["summary_short"] = str(appearance.get("summary_short", "") or "")
    appearance["summary_full"] = str(appearance.get("summary_full", "") or "")
    return appearance


def normalize_age_fields(character: Dict[str, Any], world_time: Dict[str, Any]) -> None:
    bio = character.setdefault("bio", {})
    aging = character.setdefault(
        "aging",
        {
            "arrival_absolute_day": world_time["absolute_day"],
            "days_since_arrival": 0,
            "last_aged_absolute_day": world_time["absolute_day"],
            "age_effects_applied": [],
        },
    )
    age_years = int(bio.get("age_years", 0) or 0)
    if age_years <= 0:
        age_years = infer_age_years(str(bio.get("age", "") or ""))
    bio["age_years"] = age_years
    bio["age_stage"] = derive_age_stage(age_years)
    aging["arrival_absolute_day"] = max(1, int(aging.get("arrival_absolute_day", world_time["absolute_day"]) or world_time["absolute_day"]))
    aging["last_aged_absolute_day"] = max(aging["arrival_absolute_day"], int(aging.get("last_aged_absolute_day", aging["arrival_absolute_day"]) or aging["arrival_absolute_day"]))
    aging["days_since_arrival"] = max(0, int(world_time["absolute_day"]) - aging["arrival_absolute_day"])
    aging["age_effects_applied"] = [str(entry) for entry in (aging.get("age_effects_applied") or []) if str(entry).strip()]
    if not str(bio.get("age", "")).strip():
        bio["age"] = f"{bio['age_years']} Jahre"


def age_character_if_needed(character: Dict[str, Any], world_time: Dict[str, Any]) -> None:
    bio = character.setdefault("bio", {})
    aging = character.setdefault("aging", {})
    last_aged = max(1, int(aging.get("last_aged_absolute_day", world_time["absolute_day"]) or world_time["absolute_day"]))
    absolute_day = int(world_time["absolute_day"])
    while absolute_day - last_aged >= 360:
        bio["age_years"] = int(bio.get("age_years", 0) or 0) + 1
        last_aged += 360
    aging["last_aged_absolute_day"] = last_aged
    bio["age_stage"] = derive_age_stage(int(bio.get("age_years", 0) or 0))
    bio["age"] = f"{bio['age_years']} Jahre"
    aging["days_since_arrival"] = max(0, absolute_day - int(aging.get("arrival_absolute_day", absolute_day) or absolute_day))


def build_age_modifiers(character: Dict[str, Any]) -> Dict[str, Any]:
    stage = str(((character.get("bio") or {}).get("age_stage", "young")) or "young")
    modifiers = {
        "stage": stage,
        "resource_deltas": {"hp_max": 0, "stamina_max": 0},
        "skill_bonuses": {},
        "notes": [],
    }
    if stage == "teen":
        modifiers["resource_deltas"]["stamina_max"] = 1
        modifiers["notes"].append("Jugendliche Ausdauer")
    elif stage == "adult":
        modifiers["resource_deltas"]["stamina_max"] = -1
        modifiers["skill_bonuses"]["willpower"] = 1
        modifiers["notes"].append("Reifere Entschlossenheit")
    elif stage == "older":
        modifiers["resource_deltas"]["stamina_max"] = -2
        if int((character.get("attributes") or {}).get("con", 0) or 0) < 3:
            modifiers["resource_deltas"]["hp_max"] = -1
        modifiers["skill_bonuses"]["willpower"] = 1
        modifiers["skill_bonuses"]["intimidation"] = 1
        modifiers["notes"].append("Alternde Ausdauer")
        modifiers["notes"].append("Erfahrene Präsenz")
    return modifiers


def build_stat_based_appearance(character: Dict[str, Any], appearance: Dict[str, Any]) -> Dict[str, Any]:
    attrs = character.get("attributes", {}) or {}
    strength = int(attrs.get("str", 0) or 0)
    dexterity = int(attrs.get("dex", 0) or 0)
    constitution = int(attrs.get("con", 0) or 0)
    muscle = 0
    if strength >= 12:
        muscle = 5
    elif strength >= 10:
        muscle = 4
    elif strength >= 8:
        muscle = 3
    elif strength >= 6:
        muscle = 2
    elif strength >= 4:
        muscle = 1
    build = "neutral"
    if constitution >= 4:
        build = "robust"
    if dexterity >= 4 and build == "neutral":
        build = "lean"
    if dexterity >= 8 and strength < 8:
        build = "lean"
    if strength >= 10:
        build = "broad"
    elif strength >= 8 and build == "robust":
        build = "broad"
    return {
        "height": appearance.get("height", "average") or "average",
        "build": build,
        "muscle": muscle,
        "fat": clamp(int(appearance.get("fat", 0) or 0), 0, 5),
    }


def corruption_bucket(corruption_value: int) -> int:
    if corruption_value >= 80:
        return 4
    if corruption_value >= 60:
        return 3
    if corruption_value >= 40:
        return 2
    if corruption_value >= 20:
        return 1
    return 0


def build_corruption_visuals(character: Dict[str, Any], appearance: Dict[str, Any]) -> List[Dict[str, Any]]:
    current = int((((character.get("resources") or {}).get("corruption") or {}).get("current", 0)) or 0)
    bucket = corruption_bucket(current)
    modifiers: List[Dict[str, Any]] = []
    if bucket <= 0:
        return modifiers
    aura_by_bucket = {1: "faint", 2: "dark", 3: "ominous", 4: "abyssal"}
    eyes_by_bucket = {
        1: "mit einem schwachen violetten Schimmer",
        2: "zu dunkel und schattenumrandet",
        3: "unruhig dunkel, als würde Licht darin versinken",
        4: "abgründig schwarz mit kaltem Restglanz",
    }
    skin_by_bucket = {
        2: "feine dunkle Linien unter der Haut",
        3: "deutliche Schattenadern am Hals",
        4: "schwarze Risslinien entlang der Haut",
    }
    voice_by_bucket = {
        2: "rauer",
        3: "hohl",
        4: "unheimlich ruhig",
    }
    modifiers.append({"source_type": "corruption", "source_id": f"corruption_{bucket}", "kind": "aura", "value": aura_by_bucket[bucket], "active": True})
    modifiers.append({"source_type": "corruption", "source_id": f"corruption_{bucket}", "kind": "eyes", "value": eyes_by_bucket[bucket], "active": True})
    if bucket in skin_by_bucket:
        modifiers.append({"source_type": "corruption", "source_id": f"corruption_{bucket}", "kind": "skin_mark", "value": skin_by_bucket[bucket], "active": True})
    if bucket in voice_by_bucket:
        modifiers.append({"source_type": "corruption", "source_id": f"corruption_{bucket}", "kind": "voice_tone", "value": voice_by_bucket[bucket], "active": True})
    return modifiers


def build_faction_visuals(character: Dict[str, Any]) -> List[Dict[str, Any]]:
    visuals = []
    for membership in character.get("faction_memberships", []) or []:
        if not membership.get("active", True):
            continue
        faction_id = membership.get("faction_id", "")
        for modifier in membership.get("visual_modifiers", []) or []:
            if not isinstance(modifier, dict):
                continue
            visuals.append({"source_type": "faction", "source_id": faction_id, "kind": modifier.get("kind", ""), "value": modifier.get("value", ""), "active": True})
    return visuals


def build_class_visuals(character: Dict[str, Any]) -> List[Dict[str, Any]]:
    class_state = normalize_class_current(character.get("class_current")) or {}
    visuals = []
    class_id = class_state.get("id", "")
    for modifier in class_state.get("visual_modifiers", []) or []:
        if not isinstance(modifier, dict):
            continue
        visuals.append({"source_type": "class", "source_id": class_id, "kind": modifier.get("kind", ""), "value": modifier.get("value", ""), "active": True})
    return visuals
