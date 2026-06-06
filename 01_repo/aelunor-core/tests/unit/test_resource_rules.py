from app.config.progression import ATTRIBUTE_KEYS
from app.services.characters import resources
from app.services.turn.patch_apply_resources import apply_patch_character_resource_attribute_updates
from app.services.world.math_utils import clamp


def test_canonical_resource_field_name_current_mapping() -> None:
    expected = {
        "hp": "hp",
        "health": "hp",
        "leben": "hp",
        "stamina": "stamina",
        "ausdauer": "stamina",
        "mana": "aether",
        "aether": "aether",
        "ki": "aether",
        "energie": "aether",
        "stress": "stress",
        "corruption": "corruption",
        "wounds": "wounds",
    }

    assert {key: resources.canonical_resource_field_name(key) for key in expected} == expected


def test_sync_canonical_resources_currently_clamps_runtime_fields() -> None:
    character = {"hp_current": 99, "hp_max": 10, "sta_current": -3, "sta_max": 8, "res_current": 12, "res_max": 5, "carry_current": 12, "carry_max": 7}

    resources.sync_canonical_resources(character)

    assert character["hp_current"] == 10
    assert character["sta_current"] == 0
    assert character["res_current"] == 5
    assert character["carry_current"] == 7


def test_build_compat_resources_view_currently_exposes_hp_stamina_aether_and_named_resource() -> None:
    character = {"hp_current": 3, "hp_max": 10, "sta_current": 4, "sta_max": 8, "res_current": 2, "res_max": 6, "progression": {"resource_name": "Mana"}}

    view = resources.build_compat_resources_view(character)

    assert view["hp"] == {"current": 3, "base_max": 10, "bonus_max": 0, "max": 10}
    assert view["stamina"]["current"] == 4
    assert view["aether"]["current"] == 2
    assert view["mana"] == view["aether"]


def test_legacy_shadow_writeback_flag_currently_controls_shadow_resource_fields(monkeypatch) -> None:
    character = {"hp_current": 3, "hp_max": 10, "sta_current": 4, "sta_max": 8, "res_current": 2, "res_max": 6, "resources": {"hp": {"current": 1, "max": 1}}}

    monkeypatch.setattr(resources, "ENABLE_LEGACY_SHADOW_WRITEBACK", False)
    resources.sync_canonical_resources(character)
    assert "hp" not in character["resources"]
    assert "hp" not in character

    monkeypatch.setattr(resources, "ENABLE_LEGACY_SHADOW_WRITEBACK", True)
    resources.sync_canonical_resources(character)
    assert character["resources"]["hp"]["current"] == 3
    assert character["hp"] == 3


def test_resource_set_payload_with_nested_current_max_is_currently_canonicalized() -> None:
    character = {}
    canonical = resources.canonical_resources_set_from_payload(
        {"hp": {"current": 12, "max": 10}, "stamina": {"current": 3, "max": 8}, "mana": {"current": 9, "max": 4}},
        character,
    )

    assert canonical == {"hp_current": 10, "hp_max": 10, "sta_current": 3, "sta_max": 8, "res_current": 4, "res_max": 4}


def test_resource_delta_payload_and_delta_mapping_remain_stable() -> None:
    assert resources.resource_delta_payload() == {key: 0 for key in ("hp", "stamina", "aether", "stress", "corruption", "wounds")}
    deltas = resources.canonical_resource_deltas_from_update(
        {"hp_delta": -2, "stamina_delta": -1, "resources_delta": {"mana": -3, "carry": 2, "leben": 1}}
    )

    assert deltas == {"hp_current": -1, "sta_current": -1, "res_current": -3, "carry_current": 2}


def test_patch_apply_resources_currently_sets_nested_resources_and_misc_values() -> None:
    character = {"resources": {"stress": {"current": 1, "max": 10}}, "attributes": {"str": 1}}
    update = {"resources_set": {"hp": {"current": 12, "max": 10}, "stress": {"current": 15, "max": 10}}, "attributes_delta": {"str": 20}}

    apply_patch_character_resource_attribute_updates(
        character,
        update,
        world_settings={},
        clamp=clamp,
        attribute_cap=10,
        attribute_keys=ATTRIBUTE_KEYS,
        canonical_resources_set_from_payload=resources.canonical_resources_set_from_payload,
        legacy_misc_resources_set_from_payload=resources.legacy_misc_resources_set_from_payload,
        canonical_resource_deltas_from_update=resources.canonical_resource_deltas_from_update,
        legacy_misc_resource_deltas_from_update=resources.legacy_misc_resource_deltas_from_update,
    )

    assert character["hp_current"] == 10
    assert character["hp_max"] == 10
    assert character["resources"]["stress"] == {"current": 10, "base_max": 10, "bonus_max": 0, "max": 10}
    assert character["attributes"]["str"] == 10
