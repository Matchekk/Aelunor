from typing import Any, Dict

from app.config.runtime import CAMPAIGN_LENGTHS, PACING_PROFILE_DEFAULTS, TARGET_TURNS_DEFAULTS
from app.core.ids import deep_copy
from app.services.setup.answers import extract_text_answer


def normalize_answer_summary_defaults() -> Dict[str, Any]:
    return {
        "premise": "",
        "tone": "",
        "difficulty": "",
        "death_policy": "",
        "death_possible": True,
        "ruleset": "",
        "outcome_model": "",
        "world_structure": "",
        "world_laws": [],
        "central_conflict": "",
        "factions": [],
        "taboos": "",
        "player_count": 0,
        "resource_scarcity": "",
        "healing_frequency": "",
        "monsters_density": "",
        "theme": "",
        "attribute_range_label": "1-10",
        "attribute_range_min": 1,
        "attribute_range_max": 10,
        "resource_name": "Aether",
        "consequence_severity": "hoch",
        "progression_speed": "normal",
        "evolution_cost_policy": "leicht",
        "offclass_xp_multiplier": 0.7,
        "onclass_xp_multiplier": 1.0,
        "campaign_length": "medium",
        "target_turns": deep_copy(TARGET_TURNS_DEFAULTS),
        "pacing_profile": deep_copy(PACING_PROFILE_DEFAULTS),
    }


def normalize_ruleset_choice(raw_value: Any) -> str:
    text = str(extract_text_answer(raw_value) or raw_value or "").strip()
    mapping = {
        "1W20": "Konsequent",
        "2W6": "Dramatisch",
        "Ohne Wuerfel (nur Entscheidungen)": "Konsequent",
        "Ohne Würfel (nur Entscheidungen)": "Konsequent",
    }
    return mapping.get(text, text)


def normalize_campaign_length_choice(raw_value: Any) -> str:
    text = str(extract_text_answer(raw_value) or raw_value or "").strip().lower()
    if not text:
        return "medium"
    mapping = {
        "short": "short",
        "kurz": "short",
        "mittel": "medium",
        "medium": "medium",
        "open": "open",
        "unbestimmt": "open",
        "offen": "open",
    }
    normalized = mapping.get(text, text)
    if normalized not in CAMPAIGN_LENGTHS:
        return "medium"
    return normalized
