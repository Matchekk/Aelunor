from app.services.characters.combat_state import calculate_combat_flags
from app.services.characters.derived_stats import calculate_attack_rating, calculate_defense, calculate_initiative


def test_calculate_defense_uses_ten_plus_dex_armor_and_derived_bonus() -> None:
    character = {
        "attributes": {"dex": 3},
        "equipment": {"chest": "armor"},
        "modifiers": {"derived": [{"stat": "defense", "value": 2}]},
    }
    items_db = {"armor": {"modifiers": [{"kind": "armor", "value": 4}]}}

    assert calculate_defense(character, items_db) == 19


def test_calculate_initiative_uses_dex_plus_derived_bonus() -> None:
    character = {
        "attributes": {"dex": 4},
        "equipment": {},
        "modifiers": {"derived": [{"stat": "initiative", "value": 3}]},
    }

    assert calculate_initiative(character, {}) == 7


def test_attack_rating_current_str_weapon_uses_str_athletics_weapon_bonus_and_mainhand_bonus() -> None:
    character = {
        "attributes": {"str": 5, "dex": 2, "int": 1, "wis": 1},
        "equipment": {"weapon": "axe"},
        "modifiers": {"derived": [{"stat": "attack_rating_mainhand", "value": 1}]},
    }
    items_db = {"axe": {"weapon_profile": {"category": "heavy", "attack_bonus": 2}}}

    assert calculate_attack_rating(character, "weapon", items_db, skill_level_value=lambda _c, name: 3 if name == "athletics" else 0) == 11


def test_attack_rating_current_finesse_or_ranged_weapon_uses_dex_and_athletics() -> None:
    character = {"attributes": {"str": 1, "dex": 6}, "equipment": {"weapon": "bow"}}
    items_db = {"bow": {"weapon_profile": {"category": "ranged", "attack_bonus": 1}}}

    assert calculate_attack_rating(character, "weapon", items_db, skill_level_value=lambda _c, name: 2 if name == "athletics" else 0) == 9


def test_attack_rating_current_focus_weapon_uses_int_and_lore_occult_by_default() -> None:
    character = {"attributes": {"int": 7, "wis": 4}, "equipment": {"weapon": "wand"}}
    items_db = {"wand": {"weapon_profile": {"category": "focus", "attack_bonus": 1}}}

    assert calculate_attack_rating(character, "weapon", items_db, skill_level_value=lambda _c, name: 3 if name == "lore_occult" else 0) == 11


def test_attack_rating_current_explicit_wis_scaling_uses_wis_and_lore_occult() -> None:
    character = {"attributes": {"int": 2, "wis": 5}, "equipment": {"weapon": "relic"}}
    items_db = {"relic": {"weapon_profile": {"scaling_stat": "wis", "attack_bonus": 2}}}

    assert calculate_attack_rating(character, "weapon", items_db, skill_level_value=lambda _c, name: 4 if name == "lore_occult" else 0) == 11


def test_combat_flags_current_hp_zero_marks_downed_and_cannot_act() -> None:
    assert calculate_combat_flags({"hp_current": 0}) == {"in_combat": False, "downed": True, "can_act": False}


def test_combat_flags_current_stun_tag_or_category_blocks_action() -> None:
    assert not calculate_combat_flags({"hp_current": 5, "effects": [{"tags": ["stun"]}]})["can_act"]
    assert not calculate_combat_flags({"hp_current": 5, "effects": [{"category": "stun"}]})["can_act"]


def test_combat_flags_current_paralyzed_or_unconscious_without_stun_tag_does_not_block_action() -> None:
    flags = calculate_combat_flags({"hp_current": 5, "effects": [{"category": "paralyzed"}, {"category": "unconscious"}]})

    assert flags == {"in_combat": False, "downed": False, "can_act": True}


def test_combat_flags_current_fresh_or_healing_severe_injury_blocks_action() -> None:
    flags = calculate_combat_flags(
        {
            "hp_current": 5,
            "injuries": [{"id": "inj_1", "title": "Tiefe Wunde", "severity": "schwer", "healing_stage": "heilend"}],
        }
    )

    assert flags == {"in_combat": False, "downed": False, "can_act": False}
