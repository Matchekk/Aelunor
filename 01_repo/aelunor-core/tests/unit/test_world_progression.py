import copy

from app.services.world import progression


def _default_class_current():
    return {
        "id": "",
        "name": "",
        "rank": "F",
        "path_id": "",
        "path_rank": "F",
        "element_id": "",
        "element_tags": [],
        "level": 1,
        "level_max": 10,
        "xp": 0,
        "xp_next": 100,
        "class_id": "",
        "class_name": "",
        "class_rank": "F",
        "class_level": 1,
        "class_level_max": 10,
        "class_xp": 0,
        "class_xp_to_next": 100,
        "affinity_tags": [],
        "description": "",
        "class_traits": [],
        "class_mastery": 0,
        "ascension": {
            "status": "none",
            "quest_id": None,
            "requirements": [],
            "result_hint": None,
        },
    }


def setup_module() -> None:
    progression.configure(
        {
            "CLASS_ASCENSION_STATUSES": {"none", "available", "active", "completed"},
            "deep_copy": copy.deepcopy,
            "default_class_current": _default_class_current,
            "next_class_xp_for_level": lambda level: 100 + ((max(1, int(level or 1)) - 1) * 50),
            "normalize_skill_rank": lambda value: str(value or "F").strip().upper()
            if str(value or "F").strip().upper() in {"F", "E", "D", "C", "B", "A", "S"}
            else "F",
        }
    )


def test_normalize_resource_name_uses_default_and_length_limit() -> None:
    assert progression.normalize_resource_name("") == "Aether"
    assert progression.normalize_resource_name("  Mana   Core  ") == "Mana Core"
    assert progression.normalize_resource_name("X" * 40) == "X" * 24
    assert progression.normalize_resource_name("", "Essenz") == "Essenz"


def test_next_character_xp_for_level_is_deterministic_and_monotonic() -> None:
    assert progression.next_character_xp_for_level(0) == progression.next_character_xp_for_level(1)
    assert progression.next_character_xp_for_level(1) == 120
    assert progression.next_character_xp_for_level(3) > progression.next_character_xp_for_level(2)


def test_normalize_class_current_normalizes_legacy_fields_and_caps_values() -> None:
    klass = progression.normalize_class_current(
            {
                "class_name": "Feuer Ritter",
                "rank": "b",
                "level": 3,
                "xp": 999,
                "xp_next": 200,
            "affinity_tags": ["Feuer, Klinge", "Mut"],
            "class_traits": ["  Standhaft ", "", "Standhaft"],
            "ascension": {
                "status": "unknown",
                "quest_id": "",
                "requirements": [" Prüfung ", ""],
                "result_hint": "",
            },
        }
    )

    assert klass["id"] == "class_feuer_ritter"
    assert klass["name"] == "Feuer Ritter"
    assert klass["rank"] == "B"
    assert klass["level"] == 3
    assert klass["xp_next"] == 200
    assert klass["xp"] == 200
    assert klass["class_id"] == "class_feuer_ritter"
    assert klass["class_name"] == "Feuer Ritter"
    assert klass["class_rank"] == "B"
    assert klass["class_level"] == 3
    assert klass["class_xp"] == 200
    assert klass["class_xp_to_next"] == 200
    assert klass["affinity_tags"] == ["Feuer", "Klinge", "Mut"]
    assert klass["class_traits"] == ["Standhaft"]
    assert klass["ascension"] == {
        "status": "none",
        "quest_id": None,
        "requirements": ["Prüfung"],
        "result_hint": None,
    }
