import copy
from typing import Any, Dict

def apply_patch_character_injury_appearance_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    *,
    deep_copy: Any = None,
) -> None:
    """
    Applies updates for injuries, scars and appearance flags from a patch onto a character.
    """
    if deep_copy is None:
        deep_copy = copy.deepcopy

    injuries = character.setdefault("injuries", [])
    if upd.get("injuries_add"):
        existing_injury_ids = {entry.get("id") for entry in injuries if isinstance(entry, dict)}
        for injury in upd.get("injuries_add", []) or []:
            if injury.get("id") not in existing_injury_ids:
                injuries.append(injury)
                existing_injury_ids.add(injury.get("id"))
    if upd.get("injuries_update"):
        injury_index = {entry.get("id"): entry for entry in injuries if isinstance(entry, dict)}
        for injury_update in upd.get("injuries_update", []) or []:
            target = injury_index.get(injury_update.get("id"))
            if target:
                target.update(deep_copy(injury_update))
    if upd.get("injuries_heal"):
        heal_ids = {str(entry) for entry in (upd.get("injuries_heal") or [])}
        for injury in injuries:
            if isinstance(injury, dict) and injury.get("id") in heal_ids:
                injury["healing_stage"] = "geheilt"

    scars_store = character.setdefault("scars", [])
    if upd.get("scars_add"):
        existing_scar_ids = {entry.get("id") for entry in scars_store if isinstance(entry, dict)}
        for scar in upd.get("scars_add", []) or []:
            if scar.get("id") not in existing_scar_ids:
                scars_store.append(scar)
                existing_scar_ids.add(scar.get("id"))

    for flag in upd.get("appearance_flags_add", []) or []:
        if not flag:
            continue
        character.setdefault("appearance", {}).setdefault("visual_modifiers", []).append(
            {
                "source_type": "story",
                "source_id": "story_flag",
                "kind": "skin_mark",
                "value": str(flag),
                "active": True,
            }
        )
