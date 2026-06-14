"""Phase 6 offline perf guard: deterministic write/retrieval budgets.

The full A/B/C/D LLM benchmark needs local Ollama (see
docs/performance/second-brain-benchmark.md). These checks validate the two
KEEP latency criteria that are measurable offline and deterministically:
deterministic brain write < 250 ms and retrieval < 100 ms, on a brain grown
to a realistic mid-campaign size. Thresholds are the KEEP targets; pure
stdlib sqlite on local storage clears them with large margin.
"""

from __future__ import annotations

import time

from app.services.second_brain import open_campaign_brain, seed_brain_from_state
from app.services.second_brain.write_hook import record_turn


def _campaign(cid: str) -> dict:
    npcs = {f"npc-{i}": {"name": f"NPC {i}", "description": f"person number {i} of the realm"} for i in range(20)}
    locs = {f"loc-{i}": {"name": f"Place {i}", "description": f"location number {i}"} for i in range(15)}
    items = {f"itm-{i}": {"name": f"Item {i}", "description": f"thing {i}"} for i in range(15)}
    return {
        "campaign_meta": {"campaign_id": cid, "title": "Perf"},
        "state": {
            "meta": {"turn": 0},
            "campaign": {"title": "Perf", "summary": "A large mid-campaign world."},
            "world": {"name": "Largeland", "summary": "many places and people"},
            "characters": {"slot_1": {"bio": {"name": "Hero"}, "scene_id": "loc-1"}},
            "npcs": npcs,
            "locations": locs,
            "items": items,
        },
    }


def _turn_record(n: int) -> dict:
    return {
        "turn_id": f"turn_{n}",
        "turn_number": n,
        "actor": "slot_1",
        "action_type": "do",
        "input_text_raw": f"I investigate place {n % 15} and speak with NPC {n % 20}.",
        "gm_text_display": f"NPC {n % 20} reveals a clue about Item {n % 15} near Place {n % 15}.",
        "patch": {"items_new": {f"itm-found-{n}": {"name": f"Found {n}", "description": "a discovery"}}},
        "npc_updates": [{"id": f"npc-{n % 20}", "name": f"NPC {n % 20}", "description": "seen again"}],
        "state_before": {"characters": {"slot_1": {"scene_id": f"loc-{(n - 1) % 15}"}}},
        "state_after": {"characters": {"slot_1": {"scene_id": f"loc-{n % 15}"}}},
    }


def test_write_and_retrieval_stay_within_budget(tmp_path):
    cid = "camp_perf"
    brain = open_campaign_brain(cid, campaigns_dir=str(tmp_path))
    seed_brain_from_state(brain, _campaign(cid))

    # Grow the brain to a realistic mid-campaign size and time each write.
    write_times = []
    for n in range(1, 31):
        t0 = time.perf_counter()
        record_turn(brain, cid, _turn_record(n))
        write_times.append((time.perf_counter() - t0) * 1000)
    brain.store.close()

    max_write_ms = max(write_times)
    assert max_write_ms < 250, f"deterministic write too slow: {max_write_ms:.1f}ms"

    # Retrieval on the grown brain (read path).
    from app.services.second_brain.retrieval import get_relevant_brain_context

    retr_times = []
    for n in range(10):
        t0 = time.perf_counter()
        block = get_relevant_brain_context(
            cid, "slot_1", f"loc-{n % 15}", f"look for NPC {n % 20}", campaigns_dir=str(tmp_path)
        )
        retr_times.append((time.perf_counter() - t0) * 1000)
        assert block  # non-empty on a populated brain

    max_retr_ms = max(retr_times)
    assert max_retr_ms < 100, f"retrieval too slow: {max_retr_ms:.1f}ms"
