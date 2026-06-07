from app.services.world.entity_guard import (
    assess_beast_name_against_world_bible,
    assess_entity_name_against_world_bible,
    assess_faction_name_against_world_bible,
    assess_item_name_against_world_bible,
    assess_location_name_against_world_bible,
    assess_skill_name_against_world_bible,
    build_entity_guard_report,
    collect_world_bible_name_signals,
    collect_world_naming_examples,
    infer_world_naming_mode,
    looks_like_generic_fantasy_name,
)


def _fantasy_bible():
    return {
        "version": 1,
        "identity": {
            "world_name": "Veyrhal",
            "genre_shape": "Dark Fantasy Isekai",
            "forbidden_generic_feel": ["Magiergilde", "Goblinhöhle"],
        },
        "linguistics": {
            "world_languages": {
                "primary_language": {
                    "common_roots": ["veyr", "karn", "nok", "thar", "ssereth", "vael"],
                    "example_words": {"oath": "karn", "night": "nok"},
                }
            },
            "race_languages": {
                "race_lizardfolk": {
                    "common_roots": {"ssar": "warm", "keth": "stone/place"}
                }
            },
        },
        "naming_rules": {
            "skills": {
                "patterns": ["{root}-{action}", "Eid von {concept}"],
                "examples": ["Karn-Griff", "Nok-Schnitt"],
                "avoid": ["Feuerball", "Schattenklinge"],
            },
            "items": {
                "patterns": [],
                "examples": ["Veyrglas-Klinge"],
                "avoid": ["Heiltrank"],
            },
            "settlements": {"patterns": [], "examples": ["Ssereth-Vael", "Nok-Thar"], "avoid": []},
            "factions": {"patterns": [], "examples": ["Orden des Bluttores"], "avoid": []},
            "titles": {"patterns": [], "examples": ["Bluttor-Hueter"], "avoid": []},
        },
        "metaphysics": {"main_power_name": "Veyr", "power_source": "Eid, Blut und Erinnerung"},
        "elements": {"status_effect_vocabulary": ["Aschebrand", "Veyr-Riss"]},
        "items": {"material_vocabulary": ["Karnstahl", "Veyrglas"]},
        "tone_and_style": {"forbidden_words": ["Power Strike"]},
    }


def _superhero_bible():
    return {
        "identity": {
            "world_name": "Hoshino",
            "genre_shape": "Superhelden-Akademie modern_japanese",
            "core_pitch": "Schüler trainieren Quirks und Heldennamen.",
        },
        "created_from_setup": {"theme": "MHA-artige Hero Academy"},
        "naming_rules": {
            "people": {"patterns": ["Japanese given name + family name"], "examples": ["Akira Tanaka", "Rei Hoshikawa", "Daichi Mori"], "avoid": []},
            "titles": {"patterns": ["Role or class office"], "examples": ["Class Representative"], "avoid": []},
            "factions": {"patterns": ["School or Hero Office"], "examples": ["Hoshino Academy", "Pro Hero Office"], "avoid": []},
            "skills": {"patterns": ["Quirk: {concept}", "{codename} Rush"], "examples": ["Quirk: Glass Nerve", "Zero-Point Grip"], "avoid": ["Magic Sword"]},
        },
    }


def test_missing_world_bible_returns_unknown_without_crashing():
    report = assess_skill_name_against_world_bible("Feuerball", None)

    assert report["status"] == "unknown"
    assert report["score"] == 50
    assert report["requires_review"] is True
    assert "World Bible missing" in report["reasons"][0]


def test_generic_and_avoid_names_are_detected():
    fireball = assess_skill_name_against_world_bible("Feuerball", _fantasy_bible())
    potion = assess_item_name_against_world_bible("Healing Potion", _fantasy_bible())

    assert fireball["status"] == "forbidden"
    assert "Feuerball" in fireball["avoid_terms_found"]
    assert potion["status"] in {"generic", "forbidden"}
    assert potion["requires_review"] is True


def test_world_roots_improve_score_over_generic_name():
    bible = _fantasy_bible()
    rooted = assess_location_name_against_world_bible("Nok-Thar", bible)
    generic = assess_location_name_against_world_bible("Dunkler Wald", bible)

    assert rooted["score"] > generic["score"]
    assert rooted["status"] in {"ok", "weak"}
    assert "nok" in [root.lower() for root in rooted["matched_roots"]]


def test_race_roots_and_material_vocabulary_are_recognized():
    race = assess_location_name_against_world_bible("Ssar-Keth", _fantasy_bible())
    item = assess_item_name_against_world_bible("Veyrglas-Klinge", _fantasy_bible())

    assert "ssar" in [root.lower() for root in race["matched_roots"]]
    assert race["score"] >= 70
    assert "Veyrglas-Klinge" in item["matched_examples"]
    assert item["status"] == "ok"


def test_build_entity_guard_report_returns_summary_and_reports():
    report = build_entity_guard_report(
        [
            {"entity_type": "skill", "name": "Feuerball"},
            {"entity_type": "item", "name": "Veyrglas-Klinge"},
            {"entity_type": "location", "name": "Nok-Thar"},
        ],
        _fantasy_bible(),
    )

    assert report["summary"]["total"] == 3
    assert report["summary"]["ok"] >= 1
    assert report["summary"]["forbidden"] >= 1
    assert len(report["reports"]) == 3


def test_status_score_and_wrappers_are_deterministic():
    first = assess_beast_name_against_world_bible("Eisdrache", _fantasy_bible())
    second = assess_faction_name_against_world_bible("Eisdrache", _fantasy_bible())

    assert first == assess_beast_name_against_world_bible("Eisdrache", _fantasy_bible())
    assert second["entity_type"] == "faction"
    assert assess_entity_name_against_world_bible("Karn-Griff", "skills", _fantasy_bible())["entity_type"] == "skill"


def test_superhero_academy_accepts_japanese_and_school_names():
    bible = _superhero_bible()
    person = assess_entity_name_against_world_bible("Akira Tanaka", "person", bible)
    faction = assess_faction_name_against_world_bible("Hoshino Academy", bible)

    assert infer_world_naming_mode(bible) == "superhero_academy"
    assert person["status"] in {"ok", "weak"}
    assert person["score"] >= 60
    assert faction["score"] >= 70
    assert faction["status"] == "ok"


def test_dark_fantasy_survival_is_not_inferred_as_post_apocalyptic():
    bible = _fantasy_bible()
    bible["created_from_setup"] = {
        "theme": "Dark fantasy survival world with cursed magic, races, beasts and invented languages.",
        "world_structure": "ruins and dangerous Eidstrassen",
    }

    assert infer_world_naming_mode(bible) == "dark_fantasy"


def test_plotpoint_names_are_recognized_and_scored_from_world_signals():
    fantasy = assess_entity_name_against_world_bible("Geluebde des Tores von Ssereth-Vael", "plotpoint", _fantasy_bible())
    rescue = assess_entity_name_against_world_bible("Rettung von Rei Hoshikawa", "plotpoint", _superhero_bible())
    attention = assess_entity_name_against_world_bible("Daichi Moris Aufmerksamkeit", "plotpoint", _superhero_bible())

    assert fantasy["entity_type"] == "plotpoint"
    assert "Entity type is not recognized by the guard." not in fantasy["reasons"]
    assert fantasy["score"] >= 70
    assert rescue["score"] >= 70
    assert attention["score"] >= 60


def test_modern_name_in_fantasy_is_not_rewarded_without_bible_permission():
    fantasy = assess_entity_name_against_world_bible("Akira Tanaka", "person", _fantasy_bible())
    superhero = assess_entity_name_against_world_bible("Akira Tanaka", "person", _superhero_bible())

    assert superhero["score"] > fantasy["score"]
    assert fantasy["status"] in {"weak", "generic", "needs_review"}


def test_explicit_examples_override_generic_fallback_terms():
    bible = _superhero_bible()
    bible["naming_rules"]["skills"]["examples"].append("Fireball")

    report = assess_skill_name_against_world_bible("Fireball", bible)

    assert looks_like_generic_fantasy_name("Fireball")
    assert report["status"] in {"ok", "weak"}
    assert report["forbidden_terms_found"] == []
    assert report["avoid_terms_found"] == []


def test_collect_signal_helpers_expose_examples_and_roots():
    signals = collect_world_bible_name_signals(_fantasy_bible())
    examples = collect_world_naming_examples(_fantasy_bible(), "skill")

    assert "karn" in [root.lower() for root in signals["roots"]]
    assert "ssar" in [root.lower() for root in signals["race_roots"]]
    assert "Karn-Griff" in examples
