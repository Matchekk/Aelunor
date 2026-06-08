"""Regression tests for the HIGH-severity bugs found in the full-codebase bug hunt.

Each test pins down one concrete defect so it cannot silently return.
"""

import copy

import pytest

from app.services import state_engine
from app.services.canon import progression_gate
from app.services.characters import normalization as char_norm
from app.services.progression import skills
from app.services.state.dependencies import StateEngineDependencies
from app.services.world import scene


@pytest.fixture(autouse=True)
def _configure_state_engine():
    state_engine.configure_dependencies(StateEngineDependencies())


# --- Bug 1: downed/dead characters were "resurrected" to full resources -------

def test_zero_current_resources_are_preserved_not_restored_to_max():
    character = char_norm.normalize_character_state(
        {"bio": {"name": "Downed"}, "attributes": {"con": 5}, "hp_current": 0, "hp_max": 18, "sta_current": 0, "res_current": 0},
        "slot_1",
        {},
        None,
    )
    assert character["hp_current"] == 0
    assert character["sta_current"] == 0
    assert character["res_current"] == 0
    # a non-zero current still round-trips unchanged
    alive = char_norm.normalize_character_state(
        {"bio": {"name": "Alive"}, "attributes": {"con": 5}, "hp_current": 7, "hp_max": 18},
        "slot_1",
        {},
        None,
    )
    assert alive["hp_current"] == 7


def test_zero_hp_survives_normalize_roundtrip():
    base = {"bio": {"name": "Z"}, "attributes": {"con": 5}, "hp_current": 0, "hp_max": 18}
    once = char_norm.normalize_character_state(copy.deepcopy(base), "slot_1", {}, None)
    twice = char_norm.normalize_character_state(copy.deepcopy(once), "slot_1", {}, None)
    assert once["hp_current"] == 0
    assert twice["hp_current"] == 0


# --- Bug 4: resource maxima were non-idempotent across normalize --------------

def test_resource_maxima_are_idempotent_across_normalize():
    base = {"bio": {"name": "Fresh"}, "attributes": {"con": 5, "dex": 3}}
    p1 = char_norm.normalize_character_state(copy.deepcopy(base), "slot_1", {}, None)
    p2 = char_norm.normalize_character_state(copy.deepcopy(p1), "slot_1", {}, None)
    p3 = char_norm.normalize_character_state(copy.deepcopy(p2), "slot_1", {}, None)
    assert p1["hp_max"] == p2["hp_max"] == p3["hp_max"]
    assert p1["sta_max"] == p2["sta_max"] == p3["sta_max"]


# --- Bug 2: NameError clamp_float on characters with class_path_seeds ----------

def test_class_path_seeds_normalize_without_nameerror():
    character = {"level": 1, "class_path_seeds": [{"id": "s1", "confidence": 0.5}]}
    skills.ensure_character_progression_core(character)
    assert character["class_path_seeds"][0]["confidence"] == 0.5
    # non-numeric / out-of-range confidence is coerced, not crashed
    for raw, expected in (("bad", 0.0), (None, 0.0), (1.7, 1.0), (-0.3, 0.0)):
        c = {"level": 1, "class_path_seeds": [{"id": "s", "confidence": raw}]}
        skills.ensure_character_progression_core(c)
        assert c["class_path_seeds"][0]["confidence"] == expected


def test_apply_system_xp_does_not_crash_on_seeded_character():
    character = {"level": 1, "class_path_seeds": [{"id": "s2", "confidence": "bad"}]}
    skills.apply_system_xp(character, 10)  # must not raise NameError/ValueError


# --- Bug 3: corrupt/partial campaign JSON (null containers) crashed load -------

_NULL_CAMPAIGNS = {
    "state": {"campaign_meta": {"campaign_id": "c1", "host_player_id": "h"}, "players": {"h": {"display_name": "H"}}, "state": None},
    "boards": {"campaign_meta": {"campaign_id": "c1", "host_player_id": "h"}, "players": {"h": {"display_name": "H"}}, "state": {"meta": {}, "world": {}, "characters": {}}, "boards": None},
    "meta": {"campaign_meta": {"campaign_id": "c1", "host_player_id": "h"}, "players": {"h": {"display_name": "H"}}, "state": {"meta": None, "world": {}, "characters": {}}},
    "world": {"campaign_meta": {"campaign_id": "c1", "host_player_id": "h"}, "players": {"h": {"display_name": "H"}}, "state": {"meta": {}, "world": None, "characters": {}}},
    "setup": {"campaign_meta": {"campaign_id": "c1", "host_player_id": "h"}, "players": {"h": {"display_name": "H"}}, "state": {"meta": {}, "world": {}, "characters": {}}, "setup": None},
    "setup.world": {"campaign_meta": {"campaign_id": "c1", "host_player_id": "h"}, "players": {"h": {"display_name": "H"}}, "state": {"meta": {}, "world": {}, "characters": {}}, "setup": {"version": 4, "world": None, "characters": {}}},
    "player_null": {"campaign_meta": {"campaign_id": "c1", "host_player_id": "h"}, "players": {"h": None}},
}


@pytest.mark.parametrize("name", sorted(_NULL_CAMPAIGNS))
def test_corrupt_null_campaign_normalizes_without_crash(name):
    campaign = copy.deepcopy(_NULL_CAMPAIGNS[name])
    result = state_engine.normalize_campaign(campaign)
    assert isinstance(result["state"], dict)
    assert isinstance(result["boards"], dict)


# --- Bug 5: scene.py mojibake dropped/truncated umlaut location names ----------

def test_umlaut_scene_names_are_extracted_fully():
    a = scene.extract_scene_candidates("Die Gruppe erreicht Nachtmühle und ruht.", "Held")
    assert a and a[0]["name"] == "Nachtmühle"
    b = scene.extract_scene_candidates("Die Gruppe betritt Wölfenheim.", "Held")
    assert b and b[0]["name"] == "Wölfenheim"
    # ascii names still work
    c = scene.extract_scene_candidates("Die Gruppe erreicht Sturmfeste.", "Held")
    assert c and c[0]["name"] == "Sturmfeste"


# --- Bug 6: non-numeric source_turn crashed the whole turn --------------------

def test_progression_merge_tolerates_non_numeric_source_turn():
    events = [{"type": "class_breakthrough", "actor": "slot_1", "source_turn": "bald"}]
    # must not raise ValueError
    progression_gate.merge_progression_patch_additive(
        base_patch={},
        actor="slot_1",
        supplement_character_patch={"progression_events": events},
        state_after={"characters": {"slot_1": {}}},
    )
    normalized = progression_gate.normalize_progression_event(events[0], actor="slot_1", source_turn=3)
    assert normalized["source_turn"] == 3  # falls back to the provided default
    good = progression_gate.normalize_progression_event(
        {"type": "class_breakthrough", "actor": "slot_1", "source_turn": 7}, actor="slot_1", source_turn=3
    )
    assert good["source_turn"] == 7
