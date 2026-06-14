"""Phase 4 tests: deterministic post-turn write hook.

The hook mirrors a turn into the brain (event card, entities, edges, facts),
is flag-gated, and never breaks a turn even when the brain is broken.
"""

from __future__ import annotations

from app.services.second_brain import (
    SecondBrain,
    maybe_record_turn,
    record_turn,
)


def _campaign() -> dict:
    return {
        "campaign_meta": {"campaign_id": "camp_wh01", "title": "Write Hook"},
        "state": {
            "meta": {"turn": 1},
            "campaign": {"title": "Write Hook", "summary": "A test campaign."},
            "characters": {"slot_1": {"bio": {"name": "Kael"}, "scene_id": "loc-harbor"}},
            "locations": {"loc-harbor": {"name": "Harbor", "description": "the docks"}},
        },
    }


def _turn_record(**over) -> dict:
    rec = {
        "turn_id": "turn_abc",
        "turn_number": 2,
        "actor": "slot_1",
        "action_type": "do",
        "input_text_raw": "I search the abandoned warehouse for clues.",
        "gm_text_display": "You find a torn map hinting at the smugglers' route.",
        "patch": {
            "items_new": {"itm-map": {"name": "Torn Map", "description": "smugglers' route"}},
            "plotpoints_add": [{"title": "The Smugglers' Route", "notes": "follow the map", "status": "open"}],
        },
        "npc_updates": [{"id": "npc-bren", "name": "Bren", "description": "a nervous informant"}],
        "state_before": {"characters": {"slot_1": {"scene_id": "loc-square"}}},
        "state_after": {"characters": {"slot_1": {"scene_id": "loc-harbor"}}},
    }
    rec.update(over)
    return rec


def test_record_turn_writes_event_and_entities():
    brain = SecondBrain()
    summary = record_turn(brain, "camp_wh01", _turn_record())
    assert summary["nodes"] >= 4
    counts = brain.store.counts("camp_wh01")
    assert counts.get("event", 0) == 1
    assert counts.get("item", 0) >= 1
    assert counts.get("npc", 0) >= 1
    assert counts.get("open_thread", 0) >= 1
    assert counts.get("fact", 0) >= 1  # scene change vs prior turn
    assert counts.get("edges", 0) >= 3  # involves + at + mentions


def test_record_turn_creates_co_mention_edges():
    brain = SecondBrain()
    record_turn(brain, "camp_wh01", _turn_record())
    edges = brain.store.get_edges("camp_wh01")
    relations = {e.relation for e in edges}
    assert "involves" in relations and "mentions" in relations
    # The event node is the hub of the co-mention edges.
    event_edges = [e for e in edges if e.src_id == "camp_wh01:event:turn_abc"]
    assert len(event_edges) >= 3


def test_record_turn_updates_last_processed_meta():
    brain = SecondBrain()
    record_turn(brain, "camp_wh01", _turn_record())
    assert brain.store.get_meta("last_processed_turn_id") == "turn_abc"
    assert brain.store.get_meta("last_processed_turn_number") == "2"


def test_plotpoint_update_demotes_resolved_thread():
    brain = SecondBrain()
    record_turn(brain, "camp_wh01", _turn_record())
    before = brain.store.get_node("camp_wh01", "camp_wh01:thread:the-smugglers-route")
    assert before is not None and before.salience >= 0.5
    # A later turn resolves the thread.
    record_turn(
        brain,
        "camp_wh01",
        _turn_record(
            turn_id="turn_def",
            turn_number=3,
            patch={"plotpoints_update": [{"title": "The Smugglers' Route", "status": "resolved"}]},
        ),
    )
    after = brain.store.get_node("camp_wh01", "camp_wh01:thread:the-smugglers-route")
    assert after.metadata.get("status") == "resolved"
    assert after.salience < before.salience


def test_maybe_record_turn_off_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AELUNOR_SECOND_BRAIN", raising=False)
    assert maybe_record_turn(_campaign(), _turn_record(), campaigns_dir=str(tmp_path)) is None
    # No brain file created when the flag is off.
    assert not (tmp_path / "camp_wh01" / "brain" / "brain.sqlite").exists()


def test_maybe_record_turn_on_seeds_and_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", "1")
    result = maybe_record_turn(_campaign(), _turn_record(), campaigns_dir=str(tmp_path))
    assert result is not None
    assert (tmp_path / "camp_wh01" / "brain" / "brain.sqlite").exists()


def test_brain_write_failure_does_not_raise(monkeypatch):
    # An unsafe campaign id makes open_campaign_brain return None; the hook must
    # still complete without raising and without a brain.
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", "1")
    bad = {"campaign_meta": {"campaign_id": "../escape"}}
    assert maybe_record_turn(bad, _turn_record()) is None


def test_record_turn_keeps_cards_short():
    brain = SecondBrain()
    long_action = "x" * 5000
    long_gm = "y" * 5000
    record_turn(
        brain,
        "camp_wh01",
        _turn_record(input_text_raw=long_action, gm_text_display=long_gm),
    )
    event = brain.store.get_node("camp_wh01", "camp_wh01:event:turn_abc")
    # No long evidence blobs: the card stays bounded.
    assert len(event.text) < 500
