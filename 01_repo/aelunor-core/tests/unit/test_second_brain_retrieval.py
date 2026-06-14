"""Phase 5 tests: pre-narrator retrieval + RELEVANT_CAMPAIGN_BRAIN block.

Read-only retrieval builds a bounded block of memory cards; it excludes
resolved threads, honors the token budget, and yields nothing when the flag
is off or no brain exists.
"""

from __future__ import annotations

from app.services.second_brain import (
    KnowledgeEdge,
    KnowledgeNode,
    get_relevant_brain_context,
    maybe_brain_context_block,
    open_campaign_brain,
)
from app.services.second_brain.retrieval import render_brain_block
from app.services.second_brain.models import RecallResult


def _seed_brain(tmp_path, cid="camp_ret01"):
    brain = open_campaign_brain(cid, campaigns_dir=str(tmp_path))
    brain.store.upsert_nodes(
        [
            KnowledgeNode(id=f"{cid}:location:loc-harbor", campaign_id=cid, kind="location",
                          name="Harbor", text="a storm-lashed harbor with a tall beacon", updated_turn=1),
            KnowledgeNode(id=f"{cid}:npc:mira", campaign_id=cid, kind="npc",
                          name="Mira", text="the dockmaster who guards the harbor", updated_turn=2),
            KnowledgeNode(id=f"{cid}:thread:smugglers", campaign_id=cid, kind="open_thread",
                          name="Smugglers' Route", text="follow the torn map", metadata={"status": "open"},
                          salience=0.6, updated_turn=2),
            KnowledgeNode(id=f"{cid}:thread:old", campaign_id=cid, kind="open_thread",
                          name="The Old Debt", text="a debt at the harbor, long since paid",
                          metadata={"status": "resolved"}, salience=0.1, updated_turn=1),
        ]
    )
    brain.store.upsert_edges(
        [KnowledgeEdge(cid, f"{cid}:location:loc-harbor", f"{cid}:npc:mira", "has_npc", 1.0)]
    )
    brain.store.close()
    return cid


def test_retrieval_finds_scene_relevant_cards(tmp_path):
    cid = _seed_brain(tmp_path)
    block = get_relevant_brain_context(cid, "slot_1", "loc-harbor", "I look around the harbor", campaigns_dir=str(tmp_path))
    assert block.startswith("[RELEVANT_CAMPAIGN_BRAIN]")
    assert block.endswith("[/RELEVANT_CAMPAIGN_BRAIN]")
    assert "Harbor" in block


def test_retrieval_excludes_resolved_threads(tmp_path):
    cid = _seed_brain(tmp_path)
    block = get_relevant_brain_context(cid, "slot_1", "loc-harbor", "harbor debt old", campaigns_dir=str(tmp_path))
    assert "The Old Debt" not in block  # resolved -> excluded
    assert "Smugglers' Route" in block or "Harbor" in block


def test_retrieval_no_brain_returns_empty(tmp_path):
    assert get_relevant_brain_context("camp_none", "slot_1", "loc-x", "hi", campaigns_dir=str(tmp_path)) == ""


def test_graph_only_neighbor_can_appear(tmp_path):
    cid = "camp_graph"
    brain = open_campaign_brain(cid, campaigns_dir=str(tmp_path))
    brain.store.upsert_nodes(
        [
            KnowledgeNode(id=f"{cid}:a", campaign_id=cid, kind="location", name="Beaconhold",
                          text="a starlight beacon on the cliff", updated_turn=1),
            KnowledgeNode(id=f"{cid}:b", campaign_id=cid, kind="npc", name="Quenby",
                          text="quiet keeper of distant tides", updated_turn=1),
        ]
    )
    brain.store.upsert_edges([KnowledgeEdge(cid, f"{cid}:a", f"{cid}:b", "keeper", 1.0)])
    brain.store.close()
    block = get_relevant_brain_context(cid, "slot_1", "", "starlight beacon", campaigns_dir=str(tmp_path))
    assert "Beaconhold" in block
    assert "Quenby" in block  # surfaced via graph neighbor, not lexical


def test_token_budget_is_respected():
    results = [
        RecallResult(
            node=KnowledgeNode(id=f"c:n{i}", campaign_id="c", kind="event", name=f"Event {i}",
                               text="x" * 300, updated_turn=i),
            score=1.0 - i * 0.01,
        )
        for i in range(40)
    ]
    block = render_brain_block(results, limit=12, token_budget=200)
    assert len(block) <= 200 * 4  # hard char budget (chars ~= tokens*4)
    # And never more than the card cap.
    assert block.count("\n- ") <= 12


def test_render_empty_when_nothing_fits():
    assert render_brain_block([], token_budget=1800) == ""


def test_maybe_block_off_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", "0")  # explicit off (default is now ON)
    cid = _seed_brain(tmp_path)
    campaign = {"campaign_meta": {"campaign_id": cid}}
    state = {"characters": {"slot_1": {"bio": {"name": "Kael"}, "scene_id": "loc-harbor"}}}
    assert maybe_brain_context_block(campaign, state, "slot_1", "look around", campaigns_dir=str(tmp_path)) == ""


def test_maybe_block_on_returns_block(tmp_path, monkeypatch):
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", "1")
    cid = _seed_brain(tmp_path)
    campaign = {"campaign_meta": {"campaign_id": cid}}
    state = {
        "characters": {"slot_1": {"bio": {"name": "Kael"}, "scene_id": "loc-harbor"}},
        "scenes": {"loc-harbor": {"name": "Harbor"}},
    }
    block = maybe_brain_context_block(campaign, state, "slot_1", "I look for Mira", campaigns_dir=str(tmp_path))
    assert "[RELEVANT_CAMPAIGN_BRAIN]" in block
    # "Harbor" is the active scene name -> deduped against the structured state.
    assert "Mira" in block
    assert "(location) Harbor:" not in block
