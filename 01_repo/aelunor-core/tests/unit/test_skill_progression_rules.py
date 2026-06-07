from app.services.progression.skills import (
    ability_id_from_name,
    apply_system_xp,
    default_ability_state,
    default_skill_state,
    grant_skill_xp,
    normalize_ability_state,
    normalize_skill_state,
    normalize_skill_store,
    skill_id_from_name,
)
from app.services.progression import classes, manifestation


def test_default_skill_currently_starts_at_level_zero_xp_zero_and_no_rank() -> None:
    skill = default_skill_state("athletics")

    assert skill["level"] == 0
    assert skill["xp"] == 0
    assert skill["rank"] == "-"


def test_default_ability_currently_starts_at_level_one() -> None:
    ability = default_ability_state(ability_name="Funkenwurf")

    assert ability["level"] == 1
    assert ability["rank"] == "F"


def test_normalize_skill_state_currently_clamps_xp_to_zero_and_next_xp() -> None:
    assert normalize_skill_state("athletics", {"level": 2, "xp": -5})["xp"] == 0
    capped = normalize_skill_state("athletics", {"level": 2, "next_xp": 50, "xp": 999})

    assert capped["xp"] == 50
    assert capped["mastery"] == 100


def test_large_xp_in_normalize_skill_state_currently_loses_overflow_by_clamping() -> None:
    skill = normalize_skill_state("athletics", {"level": 1, "next_xp": 100, "xp": 250})

    assert skill["level"] == 1
    assert skill["xp"] == 100
    assert skill["mastery"] == 100


def test_apply_system_xp_currently_levels_character_and_carries_remainder() -> None:
    character = {"level": 1, "xp_current": 90, "xp_total": 90, "xp_to_next": 120, "progression": {}}

    apply_system_xp(character, 50)

    assert character["level"] == 2
    assert character["xp_current"] == 20
    assert character["xp_total"] == 140
    assert character["progression"]["attribute_points"] == 1
    assert character["progression"]["skill_points"] == 1


def test_grant_skill_xp_currently_levels_dynamic_skill_and_carries_remainder() -> None:
    character = {
        "skills": {"skill_funkenwurf": {"id": "skill_funkenwurf", "name": "Funkenwurf", "level": 1, "xp": 95, "next_xp": 100}},
        "progression": {"resource_name": "Aether"},
    }

    messages = grant_skill_xp(character, "Funkenwurf", "small")

    skill = character["skills"]["skill_funkenwurf"]
    assert skill["level"] == 2
    assert skill["xp"] == 5
    assert messages == ["Skill-Fortschritt: Funkenwurf erreicht Lv 2/10."]


def test_skill_id_and_name_dedupe_currently_merge_same_and_prefix_names() -> None:
    assert skill_id_from_name("Funkenwurf") == skill_id_from_name(" funkenwurf ")
    store = normalize_skill_store(
        {
            "a": {"name": "Funkenwurf", "level": 1, "xp": 5},
            "b": {"name": "Funkenwurf stark", "level": 2, "xp": 3},
        },
        resource_name="Aether",
    )

    assert list(store) == ["skill_funkenwurf_stark"]
    assert store["skill_funkenwurf_stark"]["level"] == 2


def test_ability_id_from_name_is_stable_and_normalize_ability_preserves_it() -> None:
    ability_id = ability_id_from_name("Leuchtende Klinge")
    ability = normalize_ability_state({"name": "Leuchtende Klinge"})

    assert ability_id == "ability_leuchtende-klinge"
    assert ability["id"] == ability_id


def test_progression_element_id_ports_resolve_name_without_type_error() -> None:
    world = {"elements": {"elem_feuer_herz": {"name": "Feuer Herz"}}, "element_alias_index": {}}

    assert classes.normalize_element_id_list(["Feuer Herz"], world) == ["elem_feuer_herz"]
    assert manifestation.normalize_element_id_list(["Feuer Herz"], world) == ["elem_feuer_herz"]
