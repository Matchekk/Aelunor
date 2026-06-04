from typing import Any, Dict

from app.services.characters.appearance_state import (
    build_class_visuals,
    build_corruption_visuals,
    build_faction_visuals,
    build_stat_based_appearance,
    normalize_appearance_state,
)


def build_appearance_summary_short(character: Dict[str, Any]) -> str:
    appearance = character.get("appearance", {}) or {}
    parts = []
    build = appearance.get("build")
    if build == "lean":
        parts.append("drahtig")
    elif build == "robust":
        parts.append("robust")
    elif build == "broad":
        parts.append("breit gebaut")
    elif build == "frail":
        parts.append("schmächtig")
    if int(appearance.get("muscle", 0) or 0) >= 3:
        parts.append("breitere Schultern")
    scars = [entry for entry in (appearance.get("scars") or []) if entry.get("visible", True)]
    if scars:
        parts.append(f"{len(scars)} Narben")
    aura = appearance.get("aura", "none")
    if aura and aura != "none":
        aura_labels = {
            "faint": "schwache Schattenaura",
            "grim": "düstere Aura",
            "dark": "dunkle Aura",
            "ominous": "unheilvolle Aura",
            "abyssal": "abyssale Aura",
        }
        parts.append(aura_labels.get(aura, aura))
    extra_mark = next(
        (
            modifier.get("value", "")
            for modifier in (appearance.get("visual_modifiers") or [])
            if modifier.get("kind") == "skin_mark"
        ),
        "",
    )
    if extra_mark:
        parts.append(extra_mark)
    return ", ".join(part for part in parts if part) or "unauffällig"


def build_appearance_summary_full(character: Dict[str, Any]) -> str:
    appearance = character.get("appearance", {}) or {}
    parts = [build_appearance_summary_short(character)]
    if appearance.get("eyes", {}).get("current"):
        parts.append(f"Augen: {appearance['eyes']['current']}")
    if appearance.get("hair", {}).get("current"):
        parts.append(f"Haare: {appearance['hair']['current']}")
    if appearance.get("voice_tone"):
        parts.append(f"Stimme: {appearance['voice_tone']}")
    skin_marks = [str(entry) for entry in (appearance.get("skin_marks") or []) if str(entry).strip()]
    if skin_marks:
        parts.append(f"Hautzeichen: {', '.join(skin_marks)}")
    return " • ".join(part for part in parts if part)


def rebuild_character_appearance(character: Dict[str, Any], world_time: Dict[str, Any]) -> None:
    appearance = normalize_appearance_state(character)
    stat_layer = build_stat_based_appearance(character, appearance)
    modifiers = build_corruption_visuals(character, appearance) + build_class_visuals(character) + build_faction_visuals(character)
    appearance["height"] = stat_layer["height"]
    appearance["build"] = stat_layer["build"]
    appearance["muscle"] = stat_layer["muscle"]
    appearance["fat"] = stat_layer["fat"]
    appearance["visual_modifiers"] = modifiers
    eye_base = str((appearance.get("eyes") or {}).get("base", "") or "")
    eye_suffix = next((entry.get("value", "") for entry in modifiers if entry.get("kind") == "eyes"), "")
    appearance["eyes"]["current"] = (
        f"{eye_base} {eye_suffix}".strip()
        if eye_base and eye_suffix
        else eye_suffix or eye_base
    )
    hair = appearance.get("hair", {}) or {}
    appearance["hair"]["current"] = ", ".join(part for part in [hair.get("color", ""), hair.get("style", "")] if part).strip(", ")
    appearance["aura"] = next((entry.get("value", "none") for entry in modifiers if entry.get("kind") == "aura"), "none")
    appearance["voice_tone"] = next((entry.get("value", "") for entry in modifiers if entry.get("kind") == "voice_tone"), appearance.get("voice_tone", ""))
    appearance["summary_short"] = build_appearance_summary_short({"appearance": appearance})
    appearance["summary_full"] = build_appearance_summary_full({"appearance": appearance})
    character["appearance"] = appearance
