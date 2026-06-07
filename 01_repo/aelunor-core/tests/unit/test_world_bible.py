import copy

from app.services import state_engine
from app.services.state.dependencies import StateEngineDependencies
from app.services.world.world_bible import (
    build_world_bible_prompt_summary,
    default_world_bible,
    generate_world_bible_fallback,
    normalize_place_name_alias,
    normalize_race_language,
    normalize_world_bible,
)


def _setup_summary():
    return {
        "theme": "Gebrochene Eide unter einer kalten Sonne",
        "tone": "sakral, kalt, bedrohlich",
        "difficulty": "brutal",
        "resource_name": "Veyr",
        "world_structure": "Inselreiche auf lebenden Knochen",
        "world_laws": ["Eide binden Blut", "Namen koennen Schuld tragen"],
        "central_conflict": "Ein alter Eidkrieg erwacht in den Grenzstaedten.",
        "factions": [{"name": "Orden der Kette", "goal": "Eide bewahren", "methods": "Brandmale"}],
        "taboos": "Namen der Toten nicht nachts sprechen",
    }


def test_default_world_bible_has_complete_v1_shape():
    bible = default_world_bible()

    assert bible["version"] == 1
    assert "created_from_setup" in bible
    assert "identity" in bible
    assert "race_languages" in bible["linguistics"]
    assert "place_name_aliases" in bible["linguistics"]
    assert "skills" in bible["naming_rules"]
    assert "rarity_language" in bible["items"]
    assert bible["runtime_controls"]["require_bible_derived_names"] is True


def test_normalize_world_bible_fills_missing_blocks():
    bible = normalize_world_bible({"identity": {"world_name": "Veyrhal"}})

    assert bible["identity"]["world_name"] == "Veyrhal"
    assert bible["linguistics"]["world_languages"]["primary_language"]["role"] == "common"
    assert bible["naming_rules"]["items"]["patterns"] == []
    assert bible["revision"]["revision_id"] == 1


def test_fallback_world_bible_is_deterministic_and_uses_setup_values():
    setup = _setup_summary()

    first = generate_world_bible_fallback(setup)
    second = generate_world_bible_fallback(copy.deepcopy(setup))

    assert first == second
    assert first["created_from_setup"]["theme"] == setup["theme"]
    assert first["created_from_setup"]["tone"] == setup["tone"]
    assert first["created_from_setup"]["world_laws"] == setup["world_laws"]
    assert first["metaphysics"]["main_power_name"] == "Veyr"
    assert "Veyr" in first["items"]["material_vocabulary"]


def test_normalize_race_language_supports_endonyms_roots_and_patterns():
    language = normalize_race_language(
        {
            "language_name": "Ssarrek",
            "self_name_for_race": "Ssar",
            "external_name_for_race": "Echsenmenschen",
            "common_roots": {"ssar": "warm/lebendig", "keth": "Stein/Ort"},
            "naming_patterns": {"settlements": ["Ssar-{Ortroot}"], "skills": ["Root + Biss + Preis"]},
        },
        fallback_race_id="race_lizardfolk",
    )

    assert language["race_id"] == "race_lizardfolk"
    assert language["self_name_for_race"] == "Ssar"
    assert language["common_roots"]["keth"] == "Stein/Ort"
    assert language["naming_patterns"]["settlements"] == ["Ssar-{Ortroot}"]
    assert language["translation_behavior"]["partial_understanding_creates_wrong_category"] is True


def test_normalize_place_name_alias_supports_multilingual_names():
    alias = normalize_place_name_alias(
        {
            "common_name": "Koenigsfurt",
            "aliases": [
                {
                    "language": "Ssarrek",
                    "name": "Ssar-Keth",
                    "literal_meaning": "warmer lebender Ort",
                    "cultural_meaning": "dieselbe Stadt aus Echsenmenschen-Sicht",
                    "used_by": ["race_lizardfolk"],
                    "misleading_for": ["common_weak"],
                    "likely_wrong_interpretation": "heiliger Stein statt Stadt",
                }
            ],
        },
        fallback_location_id="loc_koenigsfurt",
    )

    assert alias["canonical_id"] == "loc_koenigsfurt"
    assert alias["aliases"][0]["name"] == "Ssar-Keth"
    assert alias["aliases"][0]["likely_wrong_interpretation"] == "heiliger Stein statt Stadt"


def test_prompt_summary_contains_core_contract_parts():
    bible = generate_world_bible_fallback(_setup_summary())
    summary = build_world_bible_prompt_summary(bible)

    assert bible["identity"]["world_name"] in summary
    assert "Main Power: Veyr" in summary
    assert "Naming:" in summary
    assert "Race Languages:" in summary
    assert "Forbidden:" in summary


def test_campaign_normalize_roundtrip_preserves_generated_bible():
    state_engine.configure_dependencies(StateEngineDependencies())
    campaign = {
        "campaign_meta": {"campaign_id": "camp_bible", "host_player_id": "player_host"},
        "players": {"player_host": {"display_name": "Host"}},
        "setup": {"version": 4, "world": {"completed": True, "summary": _setup_summary()}, "characters": {}},
        "state": {"meta": {"phase": "world_setup", "turn": 0}, "world": {"settings": {}}, "characters": {}},
    }

    first = state_engine.normalize_campaign(campaign)
    first_bible = copy.deepcopy(first["state"]["world"]["bible"])
    second = state_engine.normalize_campaign(first)

    assert first_bible["metaphysics"]["main_power_name"] == "Veyr"
    assert second["state"]["world"]["bible"] == first_bible
