"""Phase 8 tests: read-only debug overview + router.

The overview exposes only aggregate counts/meta (no node text or secrets),
is campaign-scoped, and never 500s: flag off -> enabled False, no brain ->
exists False.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.brain import build_brain_router
from app.services.second_brain import brain_overview, open_campaign_brain, record_turn


def _turn_record(n: int, cid: str) -> dict:
    return {
        "turn_id": f"turn_{n}",
        "turn_number": n,
        "actor": "slot_1",
        "input_text_raw": f"secret password is hunter2 action {n}",
        "gm_text_display": f"a clue at place {n}",
        "patch": {"items_new": {f"itm-{n}": {"name": f"Item {n}", "description": "thing"}}},
        "npc_updates": [{"id": f"npc-{n}", "name": f"NPC {n}", "description": "person"}],
        "state_before": {"characters": {"slot_1": {"scene_id": "loc-0"}}},
        "state_after": {"characters": {"slot_1": {"scene_id": f"loc-{n}"}}},
    }


def _populate(tmp_path, cid="camp_dbg01", turns=3):
    brain = open_campaign_brain(cid, campaigns_dir=str(tmp_path))
    for n in range(1, turns + 1):
        record_turn(brain, cid, _turn_record(n, cid))
    brain.store.close()
    return cid


def test_overview_flag_off_is_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("AELUNOR_SECOND_BRAIN", raising=False)
    cid = _populate(tmp_path)
    ov = brain_overview(cid, campaigns_dir=str(tmp_path))
    assert ov["enabled"] is False
    assert ov["exists"] is True  # brain file is still inspectable


def test_overview_no_brain_exists_false(tmp_path):
    ov = brain_overview("camp_none", campaigns_dir=str(tmp_path))
    assert ov["exists"] is False
    assert ov["counts"]["event"] == 0


def test_overview_counts_populated_brain(tmp_path):
    cid = _populate(tmp_path, turns=3)
    ov = brain_overview(cid, campaigns_dir=str(tmp_path))
    assert ov["exists"] is True
    assert ov["counts"]["event"] == 3
    assert ov["counts"]["entity"] >= 3  # items + npcs
    assert ov["counts"]["edge"] >= 3
    assert ov["last_processed_turn"] == "3"
    assert ov["schema_version"] >= 1


def test_overview_is_campaign_scoped(tmp_path):
    _populate(tmp_path, cid="camp_a", turns=2)
    _populate(tmp_path, cid="camp_b", turns=5)
    a = brain_overview("camp_a", campaigns_dir=str(tmp_path))
    b = brain_overview("camp_b", campaigns_dir=str(tmp_path))
    assert a["counts"]["event"] == 2
    assert b["counts"]["event"] == 5


def test_overview_leaks_no_node_text_or_secrets(tmp_path):
    cid = _populate(tmp_path)
    ov = brain_overview(cid, campaigns_dir=str(tmp_path))
    blob = repr(ov)
    assert "hunter2" not in blob  # no player input / node text leaks
    assert "clue at place" not in blob
    # Only counts + meta keys are exposed.
    assert set(ov["counts"]) == {"event", "fact", "entity", "edge", "open_thread", "memory_card", "by_kind"}


def test_overview_unsafe_id_is_safe(tmp_path):
    ov = brain_overview("../escape", campaigns_dir=str(tmp_path))
    assert ov["exists"] is False
    assert "invalid campaign_id" in ov["warnings"]


def test_brain_router_returns_overview(tmp_path):
    cid = _populate(tmp_path, turns=2)
    app = FastAPI()
    app.include_router(
        build_brain_router(brain_overview=lambda c: brain_overview(c, campaigns_dir=str(tmp_path)))
    )
    client = TestClient(app)
    resp = client.get(f"/api/campaigns/{cid}/brain")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid
    assert body["exists"] is True
    assert body["counts"]["event"] == 2
