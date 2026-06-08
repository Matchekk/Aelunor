from typing import Any, Dict, Optional

from app.services.characters.derived_stats import skill_effective_bonus as _skill_effective_bonus
from app.services.world.injury_state import normalize_injury_state


def calculate_combat_flags(character: Dict[str, Any]) -> Dict[str, Any]:
    hp_current = int(character.get("hp_current", 0) or 0)
    downed = hp_current <= 0
    in_combat = bool((character.get("combat_state") or {}).get("in_combat", False))
    can_act = not downed
    for effect in character.get("effects", []) or []:
        if not isinstance(effect, dict):
            continue
        effect_tags = set(effect.get("tags", []) or [])
        if "stun" in effect_tags or effect.get("category") == "stun":
            can_act = False
        if effect.get("category") == "combat":
            in_combat = True
    severe_injuries = [
        normalize_injury_state(entry)
        for entry in (character.get("injuries") or [])
        if isinstance(entry, dict)
    ]
    if any(
        injury
        and injury.get("severity") == "schwer"
        and injury.get("healing_stage") in {"frisch", "heilend"}
        for injury in severe_injuries
    ):
        can_act = False
    return {"in_combat": in_combat, "downed": downed, "can_act": can_act}


def skill_effective_bonus(
    character: Dict[str, Any],
    skill_name: str,
    items_db: Optional[Dict[str, Any]] = None,
) -> int:
    return _skill_effective_bonus(character, skill_name, items_db)
