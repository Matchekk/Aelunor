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


def _dark_fantasy_setup():
    return {
        "theme": "Dark fantasy survival world with invented languages, cursed relics, dangerous magic costs and Echsenvoelker.",
        "tone": "sakral, kalt, koerperlich, bedrohlich",
        "difficulty": "hart",
        "resource_name": "Veyr",
        "world_structure": "zerbrochene Stadtstaaten an alten Eidstrassen",
        "world_laws": ["Magie entsteht aus Erinnerung, Blut und Eid."],
        "central_conflict": "Echsenvoelker bewahren alte Ortsnamen wie Ssereth-Vael.",
        "factions_raw": "Eidwacht; Ssar-Keth-Keeper",
        "taboos": "kostenlose Heilung, generische Magiergilden",
    }


def _superhero_setup():
    return {
        "theme": "Modern Japanese superhero academy with students, hero names, quirks, support gear and public rankings.",
        "tone": "energiegeladen, kompetitiv, warm",
        "difficulty": "mittel",
        "resource_name": "Drive",
        "world_structure": "moderne Akademien, Trainingsarenen, Agenturen und Stadtbezirke",
        "world_laws": ["Kraefte sind persoenlich und koerperlich begrenzt."],
        "central_conflict": "Schueler muessen Ruhm, Sicherheit und Verantwortung ausbalancieren.",
        "factions_raw": "Hoshino Academy; Klasse 1-B; Support Lab",
        "taboos": "Fantasy-Rassen erzwingen, generische Zauber",
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


def test_fallback_world_bible_fills_naming_examples_for_dark_fantasy():
    bible = generate_world_bible_fallback(_dark_fantasy_setup())

    assert bible["naming_rules"]["settlements"]["examples"][:3] == ["Ssereth-Vael", "Nok-Thar", "Karnvar"]
    assert "Karn-Griff" in bible["naming_rules"]["skills"]["examples"]
    assert "Veyrglas-Klinge" in bible["naming_rules"]["items"]["examples"]
    assert "Aschenmaul" in bible["naming_rules"]["beasts"]["examples"]


def test_fallback_world_bible_fills_modern_superhero_examples_without_fantasy_bias():
    bible = generate_world_bible_fallback(_superhero_setup())

    assert "Akira Tanaka" in bible["naming_rules"]["people"]["examples"]
    assert "Hoshino Academy" in bible["naming_rules"]["factions"]["examples"]
    assert "Support Gear" in bible["naming_rules"]["items"]["examples"]
    assert "Pro Hero" in bible["naming_rules"]["titles"]["examples"]
    assert "Veyrglas-Klinge" not in bible["naming_rules"]["items"]["examples"]


def test_fallback_race_language_exists_for_race_relevant_dark_fantasy():
    bible = generate_world_bible_fallback(_dark_fantasy_setup())
    language = bible["linguistics"]["race_languages"]["race_lizardfolk"]

    assert language["language_name"] == "Ssarrek"
    assert language["self_name_for_race"] == "Ssar-Keth"
    assert "ssar" in language["common_roots"]
    assert language["translation_behavior"]["partial_understanding_creates_wrong_category"] is True


def test_fallback_language_roots_are_controlled_not_english_setup_fillers():
    bible = generate_world_bible_fallback(_dark_fantasy_setup())
    roots = []
    for language in bible["linguistics"]["world_languages"].values():
        roots.extend(language["common_roots"])

    lowered = {str(root).lower() for root in roots}
    assert not {"world", "with", "survi"} & lowered
    assert {"ssar", "vael", "karn"} & lowered


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
