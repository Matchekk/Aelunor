"""Character effect/condition compatibility helpers.

Pure character-domain logic extracted from the state runtime core.
"""
from typing import Any, Dict

from app.core.ids import make_id


def migrate_effects_from_conditions(character: Dict[str, Any]) -> None:
    effects = character.get("effects")
    if not isinstance(effects, list):
        effects = []
        character["effects"] = effects
    existing = {effect.get("name") for effect in effects if isinstance(effect, dict)}
    for condition in character.get("conditions", []) or []:
        if condition and condition not in existing:
            effects.append(
                {
                    "id": make_id("effect"),
                    "name": condition,
                    "category": "condition",
                    "tags": [],
                    "description": condition,
                    "duration_turns": 0,
                    "intensity": 1,
                    "modifiers": [],
                    "source": "legacy_condition",
                    "visible": True,
                }
            )
