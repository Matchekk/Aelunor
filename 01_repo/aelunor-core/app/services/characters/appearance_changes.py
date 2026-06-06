"""Derive appearance-change events by diffing a character before/after a turn.

Pure character-domain logic extracted from the state runtime core. Lives outside
``world.appearance`` to avoid an import cycle (``appearance_state`` already imports
from ``world.appearance``).
"""
from typing import Any, Dict, List

from app.services.characters.appearance_state import corruption_bucket, normalize_appearance_state
from app.services.characters.appearance_summary import build_appearance_summary_short
from app.services.world.appearance import active_faction_ids, record_appearance_change
from app.services.world.progression import normalize_class_current


def sync_appearance_changes(
    before_character: Dict[str, Any],
    after_character: Dict[str, Any],
    *,
    slot_name: str,
    turn_number: int,
    absolute_day: int,
) -> List[Dict[str, Any]]:
    generated = []
    before_app = normalize_appearance_state(before_character)
    after_app = normalize_appearance_state(after_character)
    before_bio = before_character.get("bio", {}) or {}
    after_bio = after_character.get("bio", {}) or {}
    if before_bio.get("age_stage") != after_bio.get("age_stage"):
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="aging_stage",
            source="age_stage",
            old_value=str(before_bio.get("age_stage", "")),
            new_value=str(after_bio.get("age_stage", "")),
        )
        if event:
            generated.append(event)
    before_corruption = corruption_bucket(int((((before_character.get("resources") or {}).get("corruption") or {}).get("current", 0)) or 0))
    after_corruption = corruption_bucket(int((((after_character.get("resources") or {}).get("corruption") or {}).get("current", 0)) or 0))
    if before_corruption != after_corruption:
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="corruption_threshold",
            source="corruption",
            old_value=str(before_app.get("aura", "none")),
            new_value=str(after_app.get("summary_short", "")),
        )
        if event:
            generated.append(event)
    if before_app.get("build") != after_app.get("build") or before_app.get("muscle") != after_app.get("muscle"):
        source = "str"
        if (before_character.get("attributes") or {}).get("dex") != (after_character.get("attributes") or {}).get("dex"):
            source = "dex"
        elif (before_character.get("attributes") or {}).get("con") != (after_character.get("attributes") or {}).get("con"):
            source = "con"
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="stat_threshold",
            source=source,
            old_value=build_appearance_summary_short({"appearance": before_app}),
            new_value=build_appearance_summary_short({"appearance": after_app}),
        )
        if event:
            generated.append(event)
    before_class = ((normalize_class_current(before_character.get("class_current")) or {}).get("id", ""))
    after_class = ((normalize_class_current(after_character.get("class_current")) or {}).get("id", ""))
    if before_class != after_class and after_class:
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="class_visual",
            source=after_class,
            old_value=before_class,
            new_value=after_app.get("summary_short", ""),
        )
        if event:
            generated.append(event)
    before_factions = active_faction_ids(before_character)
    after_factions = active_faction_ids(after_character)
    if before_factions != after_factions and after_factions:
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="faction_visual",
            source="faction",
            old_value=", ".join(sorted(before_factions)),
            new_value=after_app.get("summary_short", ""),
        )
        if event:
            generated.append(event)
    before_scars = {entry.get("label") for entry in (before_app.get("scars") or [])}
    after_scars = {entry.get("label") for entry in (after_app.get("scars") or [])}
    for scar_label in sorted(after_scars - before_scars):
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="scar_added",
            source="scar",
            old_value="",
            new_value=scar_label,
        )
        if event:
            generated.append(event)
    return generated
