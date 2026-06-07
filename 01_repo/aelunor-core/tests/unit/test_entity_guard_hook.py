import copy
import inspect

from app.services import turn_engine
from app.services.turn.entity_guard_hook import (
    build_patch_entity_guard_report,
    collect_patch_entities_for_guard,
    compact_entity_guard_report,
    entity_guard_report_has_findings,
)
from app.services.turn.records import build_turn_record_payload


def _bible():
    return {
        "identity": {"genre_shape": "Dark Fantasy", "forbidden_generic_feel": ["Magiergilde", "Goblinhöhle"]},
        "linguistics": {"world_languages": {"primary_language": {"common_roots": ["nok", "thar", "veyr"]}}},
        "naming_rules": {
            "skills": {"examples": ["Nok-Schnitt"], "avoid": ["Feuerball"]},
            "items": {"examples": ["Veyrglas-Klinge"], "avoid": ["Heiltrank"]},
        },
        "items": {"material_vocabulary": ["Veyrglas"]},
    }


def _patch():
    return {
        "items_new": {"item_1": {"name": "Heiltrank"}},
        "character_updates": {
            "slot_1": {
                "skills_set": {"skill_fireball": {"name": "Feuerball"}},
                "class_set": {"name": "Kriegerklasse"},
                "faction_join": {"name": "Magiergilde"},
            }
        },
        "map": {"nodes_add": [{"id": "loc_1", "name": "Dunkler Wald"}]},
        "plotpoints_add": [{"id": "plot_1", "title": "Die Magiergilde"}],
        "factions_add": [{"id": "fac_1", "name": "Magiergilde"}],
    }


def test_collect_patch_entities_for_guard_handles_none():
    assert collect_patch_entities_for_guard(None) == []


def test_collect_patch_entities_for_guard_collects_core_entities():
    entities = collect_patch_entities_for_guard(_patch())
    lookup = {(entry["entity_type"], entry["name"]) for entry in entities}

    assert ("item", "Heiltrank") in lookup
    assert ("skill", "Feuerball") in lookup
    assert ("class", "Kriegerklasse") in lookup
    assert ("location", "Dunkler Wald") in lookup
    assert ("plotpoint", "Die Magiergilde") in lookup
    assert ("faction", "Magiergilde") in lookup


def test_collect_patch_entities_for_guard_supports_real_patch_shapes_and_dedupe():
    patch = {
        "items_new": [{"id": "item_a", "name": "Veyrglas-Klinge"}],
        "characters": {
            "slot_1": {
                "skills_set": {"skill_nok": {"name": "Nok-Schnitt"}},
                "skills_add": [{"name": "Nok-Schnitt"}],
                "class_update": {"name": "Eidwacht"},
                "faction_memberships": [{"name": "Karnbund"}],
            }
        },
        "map_add_nodes": [{"label": "Nok-Thar"}],
    }

    entities = collect_patch_entities_for_guard(patch)
    names = [entry["name"] for entry in entities]
    nok = next(entry for entry in entities if entry["name"] == "Nok-Schnitt")

    assert names.count("Nok-Schnitt") == 1
    assert len(nok["source_paths"]) == 2
    assert "Veyrglas-Klinge" in names
    assert "Nok-Thar" in names
    assert "Eidwacht" in names
    assert "Karnbund" in names


def test_collect_patch_entities_does_not_treat_moment_titles_as_items():
    patch = {
        "items_new": {
            "moment_1": {"name": "Hand zurueck - zu spaet", "kind": "event"},
            "item_veyr": {"name": "Veyrglas-Klinge"},
            "item_support": {"name": "Support Gear", "tags": ["training"]},
        }
    }

    entities = collect_patch_entities_for_guard(patch)
    lookup = {(entry["entity_type"], entry["name"]) for entry in entities}

    assert ("item", "Hand zurueck - zu spaet") not in lookup
    assert ("plotpoint", "Hand zurueck - zu spaet") in lookup
    assert ("item", "Veyrglas-Klinge") in lookup
    assert ("item", "Support Gear") in lookup


def test_build_patch_entity_guard_report_returns_summary_and_missing_bible_is_safe():
    report = build_patch_entity_guard_report(_patch(), _bible())
    missing = build_patch_entity_guard_report(_patch(), None)

    assert report["summary"]["total"] >= 6
    assert report["summary"]["forbidden"] >= 2
    assert entity_guard_report_has_findings(report) is True
    assert missing["summary"]["unknown"] == missing["summary"]["total"]


def test_compact_entity_guard_report_limits_reports_and_reasons():
    report = {
        "summary": {"total": 2, "ok": 0, "weak": 0, "generic": 2, "forbidden": 0, "needs_review": 0, "unknown": 0},
        "reports": [
            {
                "entity_type": "skill",
                "name": "Feuerball",
                "status": "generic",
                "score": 30,
                "reasons": ["a", "b", "c", "d"],
                "forbidden_terms_found": [],
                "avoid_terms_found": ["Feuerball"],
                "matched_roots": ["nok", "thar", "veyr", "extra", "more", "six", "seven"],
                "source_paths": ["path.one"],
                "requires_review": True,
            },
            {"entity_type": "item", "name": "Heiltrank", "status": "generic", "score": 20, "reasons": ["x"], "requires_review": True},
        ],
    }

    compact = compact_entity_guard_report(report, max_reports=1)

    assert compact["summary"]["stored_reports"] == 1
    assert len(compact["reports"]) == 1
    assert compact["reports"][0]["reasons"] == ["a", "b", "c"]
    assert len(compact["reports"][0]["matched_roots"]) == 6


def test_turn_record_can_store_entity_guard_report_without_rejecting():
    entity_guard = build_patch_entity_guard_report(_patch(), _bible())
    turn_record = build_turn_record_payload(
        campaign={"turns": []},
        actor="slot_1",
        player_id="player_1",
        action_type="play",
        content="Ich gehe los.",
        gm_text_display="GM text",
        requests_payload=[],
        skill_requests=[],
        patch={},
        narrator_patch={},
        extractor_patch={},
        canon_applied=False,
        attribute_profile={},
        combat_resolution={},
        resource_deltas_applied={},
        progression_result={},
        canon_gate_meta={},
        npc_updates=[],
        codex_updates=[],
        updated_combat={},
        state_before={"meta": {"turn": 0}},
        state_after={"meta": {"turn": 1}},
        retry_of_turn_id=None,
        prompt_payload={"system": "s", "entity_guard": entity_guard},
        entity_guard=entity_guard,
        make_id=lambda prefix: f"{prefix}_1",
        utc_now=lambda: "2026-06-07T00:00:00+00:00",
        deep_copy=copy.deepcopy,
        normalize_requests_payload=lambda payload, **_kwargs: payload,
        is_continue_story_content=lambda _value: False,
    )

    assert turn_record["entity_guard"]["summary"]["total"] >= 1
    assert turn_record["prompt_payload"]["entity_guard"]["summary"]["total"] >= 1


def test_turn_engine_wires_entity_guard_without_llm_flow():
    source = inspect.getsource(turn_engine.create_turn_record)

    assert "build_patch_entity_guard_report" in source
    assert '"narrator": build_patch_entity_guard_report' in source
    assert '"merged": build_patch_entity_guard_report' in source
    assert "entity_guard=entity_guard" in source
