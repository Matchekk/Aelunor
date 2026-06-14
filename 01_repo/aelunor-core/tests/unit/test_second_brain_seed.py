"""Phase 3 tests: deterministic first-run seed.

The seed mirrors existing campaign data into the brain without any LLM, is
idempotent, captures the active scene/actor, and only runs through the
flag-gated entry point when AELUNOR_SECOND_BRAIN is on.
"""

from __future__ import annotations

from app.services.second_brain import (
    SecondBrain,
    seed_brain_from_state,
    seed_campaign_brain,
)


def _campaign() -> dict:
    return {
        "campaign_meta": {"campaign_id": "camp_seed01", "title": "Tides of Ruin"},
        "state": {
            "meta": {"turn": 0},
            "campaign": {"title": "Tides of Ruin", "summary": "A harbor town under threat."},
            "world": {"name": "Brackmoor", "summary": "A storm-wracked coast."},
            "characters": {
                "slot_1": {"bio": {"name": "Kael", "goal": "find the relic"}, "scene_id": "loc-harbor"}
            },
            "npcs": {"npc-mira": {"name": "Mira", "description": "the dockmaster at the harbor"}},
            "locations": {"loc-harbor": {"name": "Harbor", "description": "busy storm-lashed docks"}},
            "items": {"itm1": {"name": "Rusty Key", "description": "opens an old lock", "rarity": "common"}},
            "plotpoints": [{"title": "The Missing Captain", "notes": "the captain vanished", "status": "open"}],
        },
        "boards": {
            "plot_essentials": {
                "active_scene": "loc-harbor",
                "open_loops": ["Who sabotaged the ship?"],
                "tone": "grim nautical",
            }
        },
    }


def test_seed_writes_expected_kinds():
    brain = SecondBrain()
    result = seed_brain_from_state(brain, _campaign())
    assert result["seeded"] is True
    counts = result["counts"]
    assert counts.get("item", 0) >= 1
    assert counts.get("open_thread", 0) >= 2  # plotpoint + open_loop
    assert counts.get("character", 0) >= 1
    assert counts.get("npc", 0) >= 1
    assert counts.get("location", 0) >= 1


def test_seed_captures_active_scene_and_actor():
    brain = SecondBrain()
    result = seed_brain_from_state(brain, _campaign())
    assert result["active_actor"] == "slot_1"
    assert result["active_scene"] == "loc-harbor"
    assert brain.store.get_meta("tone") == "grim nautical"
    assert brain.store.get_meta("active_scene") == "loc-harbor"
    assert brain.store.get_meta("seeded") == "1"


def test_seed_is_idempotent():
    brain = SecondBrain()
    first = seed_brain_from_state(brain, _campaign())["counts"]
    second = seed_brain_from_state(brain, _campaign())["counts"]
    assert first == second  # stable ids -> upsert, no duplicates


def test_seed_campaign_brain_disabled_when_flag_off(tmp_path, monkeypatch):
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", "0")  # explicit off (default is now ON)
    assert seed_campaign_brain(_campaign(), campaigns_dir=str(tmp_path)) is None


def test_seed_campaign_brain_runs_when_flag_on(tmp_path, monkeypatch):
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", "1")
    brain = seed_campaign_brain(_campaign(), campaigns_dir=str(tmp_path))
    assert brain is not None
    counts = brain.store.counts("camp_seed01")
    assert counts.get("item", 0) >= 1 and counts.get("character", 0) >= 1
    # Retrieval works on the seeded brain.
    results = brain.recall("camp_seed01", "the missing captain")
    assert any("captain" in r.node.text.lower() for r in results)
    brain.store.close()
