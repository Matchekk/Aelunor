from app.services.characters.derived_stats import calculate_carry_weight
from app.services.items.inventory import infer_item_slot_from_definition, item_matches_equipment_slot


def test_item_with_explicit_weapon_slot_matches_weapon_slot() -> None:
    item = {"name": "Kurze Klinge", "slot": "weapon"}

    assert infer_item_slot_from_definition(item) == "weapon"
    assert item_matches_equipment_slot(item, "weapon")


def test_item_with_weapon_tag_or_keyword_is_currently_inferred_as_weapon() -> None:
    assert infer_item_slot_from_definition({"name": "Alltagsgegenstand", "tags": ["weapon"]}) == "weapon"
    assert infer_item_slot_from_definition({"name": "Rostiges Schwert", "tags": []}) == "weapon"


def test_generic_item_without_slot_or_tags_currently_does_not_match_weapon_chest_or_offhand() -> None:
    item = {"name": "Glatter Kiesel", "tags": []}

    assert infer_item_slot_from_definition(item) == ""
    assert not item_matches_equipment_slot(item, "weapon")
    assert not item_matches_equipment_slot(item, "chest")
    assert not item_matches_equipment_slot(item, "offhand")


def test_ring_slots_currently_accept_ring_trinket_amulet_and_untyped_items_via_ring_key() -> None:
    assert item_matches_equipment_slot({"slot": "ring", "name": "Silberring"}, "ring")
    assert item_matches_equipment_slot({"slot": "trinket", "name": "Talisman"}, "ring")
    assert item_matches_equipment_slot({"slot": "amulet", "name": "Mondamulett"}, "ring")
    assert item_matches_equipment_slot({"name": "Ungetaggter Fund"}, "ring")


def test_ring_slots_currently_do_not_accept_raw_ring_1_equipment_key() -> None:
    assert not item_matches_equipment_slot({"slot": "ring", "name": "Silberring"}, "ring_1")


def test_trinket_and_amulet_current_fallback_rules_are_asymmetric_for_typed_items() -> None:
    assert item_matches_equipment_slot({"name": "Ungetaggter Fund"}, "trinket")
    assert item_matches_equipment_slot({"name": "Ungetaggter Fund"}, "amulet")
    assert item_matches_equipment_slot({"slot": "trinket", "name": "Talisman"}, "amulet")
    assert not item_matches_equipment_slot({"slot": "amulet", "name": "Mondamulett"}, "trinket")


def test_equipped_item_weight_currently_counts_again_when_item_remains_in_inventory() -> None:
    items_db = {"sword": {"weight": 3}}
    character = {
        "inventory": {"items": [{"item_id": "sword", "stack": 1}]},
        "equipment": {"weapon": "sword"},
    }

    assert calculate_carry_weight(character, items_db) == 6
