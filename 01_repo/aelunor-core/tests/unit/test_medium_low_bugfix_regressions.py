"""Regression tests for the MEDIUM/LOW bugs found in the full-codebase bug hunt.

Most are robustness fixes: malformed (hostile/LLM-supplied or corrupt-save) input
must not crash the apply/normalize/load paths.
"""

import app.main  # noqa: F401  -- wires configure_dependencies for the submodules below

import copy
from types import SimpleNamespace

import pytest

from app.helpers.setup_finalize import _coerce_player_count
from app.helpers.setup_random import fallback_random_answer_payload, fallback_random_text
from app.repositories.campaign_repository import CampaignRepository
from app.services.canon import npc_extractor, progression_gate
from app.services.characters import normalization as char_norm
from app.services.characters.combat_state import calculate_combat_flags
from app.services.characters.resources import canonical_resource_deltas_from_update
from app.services.campaigns.state_shape import WorldSummaryBoardPorts, apply_world_summary_to_boards
from app.services.extraction import classes as auto_classes
from app.services.llm.json_repair import extract_json_payload
from app.services.patch_payloads import normalize_patch_semantics
from app.services.turn import (
    patch_apply_bio,
    patch_apply_conditions,
    patch_apply_inventory,
    patch_apply_journal_factions,
    patch_apply_progression,
)
from app.services.world.appearance import record_appearance_change


# --- Group A: turn patch apply must not crash on wrong-typed LLM fields -------


def test_setup_random_fallback_text_is_not_mojibake():
    deps = SimpleNamespace(extract_text_answer=lambda value: value.get("selected") if isinstance(value, dict) else "")
    campaign = {"setup": {"world": {"answers": {"theme": {"selected": "Grimdark Fantasy"}}}}}

    central_conflict = fallback_random_text("central_conflict", setup_type="world", campaign=campaign, deps=deps)
    factions = fallback_random_text("factions", setup_type="world", campaign=campaign, deps=deps)

    assert "kämpfen" in central_conflict
    assert "Zöllner" in factions
    assert "Stärke" in factions
    assert "Ã" not in central_conflict + factions


def test_world_summary_authors_note_is_not_mojibake():
    campaign = {
        "setup": {
            "world": {
                "summary": {
                    "theme": "Monster-Hunt",
                    "ruleset": "Dramatisch",
                    "central_conflict": "Freie Enklaven kämpfen weiter.",
                }
            }
        }
    }
    ports = WorldSummaryBoardPorts(make_id=lambda prefix: f"{prefix}_1", utc_now=lambda: "2026-01-01T00:00:00Z")

    apply_world_summary_to_boards(campaign, "player_1", ports=ports)

    content = campaign["boards"]["authors_note"]["content"]
    assert "Erzählrahmen: Dramatisch" in content
    assert "kämpfen" in content
    assert "Ã" not in content

def test_bio_set_non_dict_is_ignored():
    character = {"bio": {"name": "x"}}
    patch_apply_bio.apply_patch_character_bio_updates(character, {"bio_set": "notadict"})
    assert character["bio"] == {"name": "x"}


def test_conditions_and_effects_tolerate_missing_key_and_non_dict_entries():
    character = {}
    patch_apply_conditions.apply_patch_character_condition_effect_updates(
        character, {"conditions_add": ["poison"], "effects_add": ["notadict", {"id": "e1"}]}
    )
    assert "poison" in character["conditions"]
    assert any(isinstance(e, dict) and e.get("id") == "e1" for e in character["effects"])


def test_journal_and_factions_tolerate_non_dict_payloads():
    character = {}
    patch_apply_journal_factions.apply_patch_character_journal_faction_updates(
        character, {"journal_add": "notadict", "factions_add": ["notadict"]}, deep_copy=copy.deepcopy
    )  # must not raise


def test_inventory_set_with_bad_types_stores_safe_containers():
    character = {"inventory": {"items": []}}
    patch_apply_inventory.apply_patch_character_inventory_equipment_updates(
        character, {"inventory_set": {"items": "notalist", "quick_slots": "notadict"}},
        normalize_equipment_update_payload=lambda v: {},
    )
    assert character["inventory"]["items"] == []
    assert character["inventory"]["quick_slots"] == {}


def test_resource_deltas_tolerate_non_numeric_values():
    deltas = canonical_resource_deltas_from_update({"hp_delta": "lots", "resources_delta": {"hp": "bad", "stamina": 3}})
    assert deltas["hp_current"] == 0
    assert deltas["sta_current"] == 3


def test_progression_set_non_dict_and_non_numeric_are_safe():
    character = {}
    patch_apply_progression.apply_patch_character_progression_updates(
        character, {"progression_set": "x"}, normalize_class_current=lambda v: v, default_class_current=dict,
    )
    character2 = {}
    patch_apply_progression.apply_patch_character_progression_updates(
        character2, {"progression_set": {"level": "bad", "xp_total": "huge"}},
        normalize_class_current=lambda v: v or {}, default_class_current=dict,
    )
    assert character2["level"] == 1


# --- Group B: character normalization must survive corrupt saved state --------

@pytest.mark.parametrize("corrupt", [
    {"combat_state": None},
    {"effects": "notalist"},
    {"skills": ["athletics"]},
])
def test_normalize_character_state_survives_corrupt_fields(corrupt):
    character = {"bio": {"name": "x"}, "attributes": {"con": 5}, **corrupt}
    result = char_norm.normalize_character_state(character, "slot_1", {}, None)
    assert result["slot_id"] == "slot_1"


def test_rebuild_character_derived_survives_non_dict_corruption():
    char_norm.rebuild_character_derived({"bio": {"name": "x"}, "attributes": {}, "resources": {"corruption": "bad"}}, {})


def test_combat_flags_skip_non_dict_effects_and_null_combat_state():
    flags = calculate_combat_flags({"effects": ["notadict"], "combat_state": None, "hp_current": 5})
    assert flags["downed"] is False


# --- Group C: canon robustness ------------------------------------------------

def test_skill_coverage_checks_all_skills_not_just_first():
    coverage = progression_gate.progression_claim_coverage_for_actor_patch(
        {"characters": {"a": {"skills_set": {"s1": {"level": 1}, "s2": {"level": 5}}}}}, "a"
    )
    assert "skill_level_claim" in coverage


def test_canon_coverage_tolerates_non_numeric_level():
    progression_gate.progression_claim_coverage_for_actor_patch(
        {"characters": {"a": {"skills_set": {"s": {"level": "bad"}}}}}, "a"
    )  # must not raise


def test_npc_relevance_and_level_tolerate_non_numeric():
    assert npc_extractor.npc_relevance_score({"relevance_score": "high"}, "text") == 0


def test_empty_actor_display_does_not_misattribute_class():
    assert auto_classes.extract_auto_class_change("Das Dorf wird zum Schmied Aric.", "") is None


def test_clean_auto_class_name_preserves_name_like_s_endings():
    assert auto_classes.clean_auto_class_name("Erebos") == "Erebos"
    assert auto_classes.clean_auto_class_name("Kriegers") == "Krieger"


# --- Group D: LLM json extraction ---------------------------------------------

def test_extract_json_payload_only_returns_dicts():
    assert extract_json_payload('{"a": 1}') == {"a": 1}
    assert extract_json_payload('garbage {"x": 5} tail') == {"x": 5}
    for non_object in ("[1,2,3]", '"hi"', "null"):
        with pytest.raises(RuntimeError):
            extract_json_payload(non_object)


# --- Group E: persistence / security ------------------------------------------

def test_campaign_path_blocks_traversal_and_accepts_valid_ids(tmp_path):
    repo = CampaignRepository(data_dir=str(tmp_path), campaigns_dir=str(tmp_path / "campaigns"))
    assert repo.campaign_path("camp_smoke").endswith("camp_smoke.json")
    for bad in ("../../etc/passwd", "a/b", "a\\b", "..", ""):
        with pytest.raises(ValueError):
            repo.campaign_path(bad)


def test_list_campaign_ids_skips_staging_files(tmp_path):
    repo = CampaignRepository(data_dir=str(tmp_path), campaigns_dir=str(tmp_path / "campaigns"))
    repo.ensure_storage()
    (tmp_path / "campaigns" / "camp_a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "campaigns" / ".campaign-tmp123.json").write_text("{}", encoding="utf-8")
    assert repo.list_campaign_ids() == ["camp_a"]


# --- Group F: misc ------------------------------------------------------------

def test_random_multiselect_tolerates_min_greater_than_options():
    payload = fallback_random_answer_payload(
        {}, {"id": "q", "type": "multiselect", "min_selected": 3, "max_selected": 5, "options": ["a", "b"]},
        setup_type="world", deps=None, slot_name=None,
    )
    assert set(payload["selected"]) <= {"a", "b"}


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_coerce_player_count_handles_non_finite_floats(value):
    assert _coerce_player_count(value) == 1


def test_record_appearance_change_tolerates_non_dict_history():
    event = record_appearance_change(
        {"bio": {"name": "x"}, "appearance_history": ["legacy note"]},
        slot_name="s", turn_number=0, absolute_day=0, kind="hair", source="src", old_value="old", new_value="new",
    )
    assert event is not None


def test_normalize_patch_semantics_does_not_mutate_input():
    original = {"characters": {"s": {"scene_set": "cave"}}}
    normalize_patch_semantics(original)
    assert original["characters"]["s"] == {"scene_set": "cave"}
