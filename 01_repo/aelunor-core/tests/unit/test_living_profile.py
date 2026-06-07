import copy
import json

from app.services.characters import normalization
from app.services.characters.living_profile import (
    build_living_profile_prompt_summary,
    default_living_profile,
    generate_living_profile_fallback,
    normalize_language_profile,
    normalize_living_profile,
    normalize_typical_pattern,
)


def _character():
    return {
        "slot_id": "slot_1",
        "bio": {
            "name": "Mara",
            "personality": ["Humor als Schutz", "loyal"],
            "goal": "niemanden mehr im Stich lassen",
            "strength": "Beschuetzen/Retten",
            "weakness": "Ungeduld/Uebermut",
            "focus": "schnell handeln",
        },
        "class_current": {"id": "class_guard", "name": "Kettenwacht", "rank": "F"},
        "skills": {"guard_step": {"name": "Wachtschritt"}},
    }


def _world_bible():
    return {
        "identity": {"world_name": "Veyrhal", "genre_shape": "Dark Fantasy"},
        "metaphysics": {"main_power_name": "Veyr"},
    }


def test_default_living_profile_has_complete_v1_shape():
    profile = default_living_profile()

    assert profile["version"] == 1
    assert "identity" in profile
    assert "origin_context" in profile
    assert "behavior_model" in profile
    assert "typical_patterns" in profile["behavior_model"]
    assert "speech_model" in profile
    assert profile["roleplay_rules"]["player_controlled"] is True
    assert profile["revision"]["revision_id"] == 1


def test_normalize_living_profile_fills_missing_blocks():
    profile = normalize_living_profile({"identity": {"name": "Aria"}})

    assert profile["identity"]["name"] == "Aria"
    assert profile["origin_context"]["origin_type"] == "custom"
    assert profile["behavior_model"]["typical_patterns"] == []
    assert profile["consistency_controls"]["profile_confidence"] == "medium"


def test_normalize_typical_pattern_and_language_profile_guarantee_shape():
    pattern = normalize_typical_pattern({"trigger": "Gefahr", "reaction": "stellt sich davor", "confidence": "wild"})
    language = normalize_language_profile({"name": "Ssarrek", "comprehension": "weak"})

    assert pattern == {
        "trigger": "Gefahr",
        "reaction": "stellt sich davor",
        "cost": "",
        "tell": "",
        "confidence": "medium",
    }
    assert language["language"] == "Ssarrek"
    assert language["speaking"] == "unknown"
    assert language["notes"] == []


def test_generate_living_profile_fallback_is_deterministic_and_uses_bio():
    character = _character()

    first = generate_living_profile_fallback(character, world_bible=_world_bible())
    second = generate_living_profile_fallback(copy.deepcopy(character), world_bible=copy.deepcopy(_world_bible()))

    assert first == second
    assert first["identity"]["name"] == "Mara"
    assert "Humor als Schutz" in first["personality_model"]["primary_traits"]
    assert first["motivation_model"]["want"] == "niemanden mehr im Stich lassen"
    assert first["self_image"]["what_they_are_proud_of"] == "Beschuetzen/Retten"
    assert first["self_image"]["what_they_hide"] == "Ungeduld/Uebermut"
    assert first["behavior_model"]["typical_patterns"]


def test_fallback_is_genre_open_without_isekai_inputs():
    profile = generate_living_profile_fallback(_character(), world_bible=_world_bible())
    payload = json.dumps(profile, ensure_ascii=False).lower()

    assert profile["origin_context"]["origin_type"] == "custom"
    assert "isekai" not in payload
    assert profile["world_resonance"]["genre_fit"] == "Dark Fantasy"


def test_prompt_summary_contains_core_contract_parts():
    profile = generate_living_profile_fallback(_character(), world_bible=_world_bible())
    summary = build_living_profile_prompt_summary(profile)

    assert "LIVING CHARACTER SUMMARY - Mara" in summary
    assert "Core Contrast:" in summary
    assert "Typical Patterns:" in summary
    assert "AI Control:" in summary
    assert "Spielerentscheidungen nicht ueberschreiben" in summary


def test_character_normalization_adds_living_profile_and_roundtrip_is_stable():
    character = normalization.normalize_character_state(
        _character(),
        "slot_1",
        {},
        None,
        world_bible=_world_bible(),
        setup_answers={},
    )
    first_profile = copy.deepcopy(character["living_profile"])
    again = normalization.normalize_character_state(
        character,
        "slot_1",
        {},
        None,
        world_bible=_world_bible(),
        setup_answers={},
    )

    assert character["living_profile"]["identity"]["name"] == "Mara"
    assert character["living_profile"]["behavior_model"]["typical_patterns"]
    assert again["living_profile"] == first_profile
