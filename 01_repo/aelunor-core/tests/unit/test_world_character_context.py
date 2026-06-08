import inspect

from app.services import turn_engine
from app.services.turn.prompt_payloads import build_turn_user_prompt
from app.services.turn.world_character_context import (
    build_living_character_context_block,
    build_party_living_context_block,
    build_style_consistency_guard_block,
    build_world_bible_context_block,
    build_world_character_context_packet,
)


def _profile(name: str, archetype: str, trigger: str) -> dict:
    return {
        "identity": {"name": name, "archetype": archetype, "core_contrast": "wirkt ruhig, handelt aber impulsiv"},
        "behavior_model": {
            "typical_patterns": [
                {
                    "trigger": trigger,
                    "reaction": "stellt sich dazwischen",
                    "cost": "riskiert eigene Sicherheit",
                    "tell": "wird leise",
                    "confidence": "high",
                }
            ],
            "anti_patterns": ["keine beliebige Drift"],
        },
        "speech_model": {"voice_summary": "kurz und trocken", "sentence_style": "knapp"},
        "motivation_model": {"want": "niemanden im Stich lassen"},
        "conflict_model": {"shame_points": ["frueheres Versagen"]},
        "roleplay_rules": {"player_controlled": True},
    }


def _campaign() -> dict:
    return {
        "state": {
            "world": {
                "bible": {
                    "identity": {
                        "world_name": "Veyrhal",
                        "world_epithet": "die Welt der Eide",
                        "core_pitch": "Eide haben Kosten.",
                        "dominant_mood": "kalt und sakral",
                        "forbidden_generic_feel": ["Feuerball"],
                    },
                    "metaphysics": {"main_power_name": "Veyr", "main_power_description": "Eidkraft mit Preis"},
                    "linguistics": {
                        "world_languages": {
                            "primary_language": {"common_roots": ["veyr", "keth"], "role": "common"},
                        }
                    },
                    "naming_rules": {"skills": {"patterns": ["Root + Preis"], "examples": [], "avoid": []}, "items": {"patterns": ["Material + Herkunft"], "examples": [], "avoid": []}},
                }
            },
            "characters": {
                "slot_1": {"bio": {"name": "Mara"}, "living_profile": _profile("Mara", "lockere Beschuetzerin", "jemand wird bedroht")},
                "slot_2": {"bio": {"name": "Taro"}, "living_profile": _profile("Taro", "vorsichtiger Analyst", "Autoritaet luegt")},
            },
        }
    }


def test_world_bible_context_block_returns_summary_and_missing_bible_is_safe():
    block = build_world_bible_context_block(_campaign())
    missing = build_world_bible_context_block({"state": {"world": {}}})

    assert "WORLD BIBLE SUMMARY:" in block
    assert "Veyrhal" in block
    assert "Keine World Bible verfuegbar" in missing


def test_living_character_context_block_uses_active_character_and_missing_is_safe():
    block = build_living_character_context_block(_campaign(), "slot_1")
    missing = build_living_character_context_block({"state": {"characters": {"slot_1": {"bio": {"name": "Mara"}}}}}, "slot_1")

    assert "ACTIVE CHARACTER LIVING SUMMARY" in block
    assert "Mara" in block
    assert "jemand wird bedroht" in block
    assert "Kein Living Profile verfuegbar" in missing


def test_party_living_context_block_contains_other_characters_compactly():
    block = build_party_living_context_block(_campaign(), "slot_1")

    assert "PARTY LIVING SUMMARY:" in block
    assert "Taro" in block
    assert "Mara" not in block
    assert "Autoritaet luegt" in block


def test_style_consistency_guard_protects_world_bible_and_player_control():
    block = build_style_consistency_guard_block(_campaign(), "slot_1")

    assert "World Bible als verbindliche Quelle" in block
    assert "Vermeide generische Fantasy-/RPG-Begriffe" in block
    assert "Spielercharaktere duerfen nicht" in block
    assert "Keine grosse Entscheidung" in block


def test_style_consistency_guard_includes_living_world_and_character_rules():
    block = build_style_consistency_guard_block(_campaign(), "slot_1")

    assert "Ripple Effects" in block
    assert "Ressource, Angst, Status" in block
    assert "Emotionen ueber Koerper" in block
    assert "strikt trennen" in block
    assert "keine Spezies-Stereotype" in block
    # player control guard must remain intact
    assert "Spielercharaktere duerfen nicht" in block


def test_world_character_context_packet_combines_and_respects_max_length():
    packet = build_world_character_context_packet(_campaign(), "slot_1", max_chars=900)

    assert packet["combined_text"]
    assert "WORLD AND CHARACTER CONSISTENCY CONTEXT" in packet["combined_text"]
    assert "WORLD BIBLE SUMMARY:" in packet["combined_text"]
    assert len(packet["combined_text"]) <= 900


def test_turn_user_prompt_contains_consistency_context():
    packet = build_world_character_context_packet(_campaign(), "slot_1", max_chars=1200)
    user_prompt, _actor_display, _actor_resolution_hint = build_turn_user_prompt(
        campaign={"slots": {"slot_1": {"character_name": "Mara"}}},
        actor="slot_1",
        action_type="play",
        content="Ich gehe vor.",
        context='{"state": "ok"}',
        turn_mode_guide={"play": "Spielzug"},
        turn_response_json_contract='{"story": "string"}',
        display_name_for_slot=lambda _campaign, _actor: "Mara",
        is_slot_id=lambda value: value.startswith("slot_"),
        is_first_person_action=lambda text: "Ich" in text,
        consistency_context=packet["combined_text"],
    )

    assert "CONTEXT_PACKET(JSON):" in user_prompt
    assert "WORLD AND CHARACTER CONSISTENCY CONTEXT" in user_prompt
    assert "ACTIVE CHARACTER LIVING SUMMARY" in user_prompt
    assert "OUTPUT-KONTRAKT:" in user_prompt


def test_turn_engine_wires_world_character_context_into_prompt_payload():
    source = inspect.getsource(turn_engine.create_turn_record)

    assert "build_world_character_context_packet" in source
    assert 'consistency_context=world_character_context["combined_text"]' in source
    assert '"world_character_context": world_character_context' in source
