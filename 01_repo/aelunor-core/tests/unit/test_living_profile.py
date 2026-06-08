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


def test_normalize_living_profile_sets_living_engine_blocks():
    profile = normalize_living_profile({"identity": {"name": "Aria"}})

    for block in ("embodiment_model", "needs_model", "expectation_model", "attachment_model", "body_state", "behavior_policy", "dialogue_policy"):
        assert block in profile
    assert profile["body_state"]["energy"] == "normal"
    assert profile["body_state"]["hunger"] == "unknown"
    weights = profile["behavior_policy"]["decision_weights"]
    assert set(weights) == {"need_relief", "threat_reduction", "value_fit", "relationship_protection", "role_compliance", "identity_consistency"}
    assert all(isinstance(value, float) and 0.0 <= value <= 1.0 for value in weights.values())
    assert profile["dialogue_policy"]["forbidden_shortcuts"]


def test_legacy_profile_without_living_engine_stays_compatible():
    legacy = {"version": 1, "identity": {"name": "Old"}, "behavior_model": {"typical_patterns": []}}

    profile = normalize_living_profile(copy.deepcopy(legacy))

    assert profile["identity"]["name"] == "Old"
    assert profile["body_state"]["energy"] == "normal"
    assert profile["roleplay_rules"]["ai_may_not_override_major_choices"] is True


def test_behavior_policy_coerces_non_numeric_weights():
    profile = normalize_living_profile({"identity": {"name": "X"}, "behavior_policy": {"decision_weights": {"need_relief": "0.4", "threat_reduction": "kaputt", "value_fit": 1.9}}})

    weights = profile["behavior_policy"]["decision_weights"]
    assert weights["need_relief"] == 0.4
    assert weights["threat_reduction"] == 0.0
    assert weights["value_fit"] == 1.0


def test_fallback_living_engine_derives_body_state_from_isekai_price():
    character = _character()
    character["bio"]["isekai_price"] = "verlorene Stimme"

    profile = generate_living_profile_fallback(character, world_bible=_world_bible())

    assert profile["body_state"]["energy"] == "erschoepft"
    assert profile["body_state"]["notes"]
    assert any("Ankunftspreis" in note for note in profile["body_state"]["notes"])
    # never leak the english setup key name into player-facing state
    assert "isekai" not in json.dumps(profile, ensure_ascii=False).lower()


def test_fallback_weakness_paranoia_yields_cautious_hints_not_diagnosis():
    character = _character()
    character["bio"]["weakness"] = "Paranoia"

    profile = generate_living_profile_fallback(character, world_bible=_world_bible())

    threats = profile["expectation_model"]["threat_interpretations"]
    assert threats
    assert any("Gefahr" in entry for entry in threats)
    payload = json.dumps(profile, ensure_ascii=False).lower()
    for clinical in ("diagnose", "stoerung", "ptsd", "krankheit", "syndrom"):
        assert clinical not in payload


def test_fallback_living_engine_neutral_character_has_no_false_string_leak():
    # Regression: boolean short-circuit (`flag and "text"`) used to inject the
    # literal string "False" into list fields when the flag was False.
    character = {
        "slot_id": "slot_x",
        "bio": {"name": "Neutral", "personality": ["ruhig"], "strength": "klug", "weakness": "stolz", "goal": "reich werden", "focus": "planen"},
        "class_current": {"name": "Buchhalter"},
        "skills": {},
    }

    profile = generate_living_profile_fallback(character, world_bible=_world_bible())

    leaky_lists = (
        profile["behavior_policy"]["default_strategies"]
        + profile["behavior_policy"]["override_conditions"]
        + profile["dialogue_policy"]["stress_modulation"]
    )
    assert all(isinstance(entry, str) for entry in leaky_lists)
    assert "False" not in leaky_lists
    assert "True" not in leaky_lists


def test_summary_survives_non_string_expectation_entries():
    # Regression: numeric entries survived `_list` normalization and crashed the
    # summary on `part.rstrip(".")`.
    profile = normalize_living_profile({"identity": {"name": "X"}, "expectation_model": {"threat_interpretations": [5]}})

    summary = build_living_profile_prompt_summary(profile)

    assert "Expectations:" in summary


def test_fallback_living_engine_is_deterministic():
    character = _character()
    character["bio"]["isekai_price"] = "verlorene Stimme"

    first = generate_living_profile_fallback(character, world_bible=_world_bible())
    second = generate_living_profile_fallback(copy.deepcopy(character), world_bible=copy.deepcopy(_world_bible()))

    assert first == second


def test_summary_contains_living_engine_lines_but_stays_compact():
    profile = generate_living_profile_fallback(_character(), world_bible=_world_bible())
    summary = build_living_profile_prompt_summary(profile)

    assert "Body/Needs:" in summary
    assert "Expectations:" in summary
    assert "Stress/Voice:" in summary
    assert summary.count("\n") < 24
    assert "{" not in summary


def test_roleplay_rules_protect_major_choices_after_engine_normalization():
    profile = generate_living_profile_fallback(_character(), world_bible=_world_bible())

    assert profile["roleplay_rules"]["ai_may_not_override_major_choices"] is True
    assert "keine grosse Spielerentscheidung ueberschreiben" in profile["dialogue_policy"]["forbidden_shortcuts"]


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
