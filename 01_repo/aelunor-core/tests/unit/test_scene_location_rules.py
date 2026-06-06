from app.services.state import runtime_core
from app.services.world.scene import (
    canonical_scene_id,
    extract_descriptive_scene_name,
    extract_scene_candidates,
    is_generic_scene_identifier,
    is_plausible_scene_name,
)


def test_scene_id_normalization_currently_slugifies_name() -> None:
    assert canonical_scene_id("Alter Turm!") == "scene_alter-turm"


def test_generic_scene_names_and_identifiers_are_currently_rejected() -> None:
    assert not is_plausible_scene_name("Ort")
    assert is_generic_scene_identifier("scene_ort", "Ort")


def test_scene_like_name_with_underscores_is_currently_still_plausible() -> None:
    assert is_plausible_scene_name("scene_alter_turm")


def test_plausible_scene_names_are_currently_accepted() -> None:
    assert is_plausible_scene_name("Alter Turm")


def test_derive_scene_name_current_runtime_path_uses_known_scene_name() -> None:
    campaign = {"state": {"characters": {"slot_1": {"scene_id": "scene_turm"}}, "scenes": {"scene_turm": {"name": "Alter Turm"}}, "map": {"nodes": {}}}}

    assert runtime_core.derive_scene_name(campaign, "slot_1") == "Alter Turm"


def test_derive_scene_name_current_runtime_path_fallbacks_for_missing_and_unknown_scene() -> None:
    missing = {"state": {"characters": {"slot_1": {"scene_id": ""}}, "scenes": {}, "map": {"nodes": {}}}}
    unknown = {"state": {"characters": {"slot_1": {"scene_id": "scene_unbekannt"}}, "scenes": {}, "map": {"nodes": {}}}}

    assert runtime_core.derive_scene_name(missing, "slot_1") == "Kein Ort"
    assert runtime_core.derive_scene_name(unknown, "slot_1") == "scene_unbekannt"


def test_extract_scene_candidates_current_story_example_is_stable() -> None:
    candidates = extract_scene_candidates("Die Gruppe erreicht den Alten Turm. Danach ruht sie.", "Aria")

    assert candidates == [{"scope": "group", "name": "Alten Turm"}]


def test_extract_descriptive_scene_name_currently_finds_lowercase_location_phrase() -> None:
    assert extract_descriptive_scene_name("Aria steht jetzt in einer moosigen Tempelruine.") == "moosigen Tempelruine"
