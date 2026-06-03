"""Small world-state default helpers."""

from typing import Any, Dict


def default_world_time() -> Dict[str, Any]:
    return {
        "day": 1,
        "month": 1,
        "year": 1,
        "time_of_day": "night",
        "weather": "",
        "absolute_day": 1,
    }


def default_intro_state() -> Dict[str, Any]:
    return {
        "status": "idle",
        "last_error": "",
        "last_attempt_at": "",
        "generated_turn_id": "",
    }


def default_character_modifiers() -> Dict[str, Any]:
    return {
        "resource_max": [],
        "derived": [],
        "appearance_flags": [],
        "skill_effective": [],
    }
