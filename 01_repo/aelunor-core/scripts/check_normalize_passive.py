import importlib
import json
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def build_story_turn(module: Any, slot_id: str, player_id: str, *, idx: int) -> Dict[str, Any]:
    now = module.utc_now()
    return {
        "turn_id": f"turn_seed_{idx}",
        "turn_number": idx,
        "status": "active",
        "actor": slot_id,
        "player_id": player_id,
        "action_type": "story",
        "input_text_raw": "Ich handle.",
        "input_text_display": "Ich handle.",
        "gm_text_raw": (
            "Matchek erlernt Schattenmagie und erhält den Runenkompass. "
            "Die Gruppe erreicht den Wald und betritt danach Eldoria Border."
        ),
        "gm_text_display": (
            "Matchek erlernt Schattenmagie und erhält den Runenkompass. "
            "Die Gruppe erreicht den Wald und betritt danach Eldoria Border."
        ),
        "requests": [],
        "patch": module.blank_patch(),
        "narrator_patch": module.blank_patch(),
        "extractor_patch": module.blank_patch(),
        "source_mode": "story",
        "canon_applied": False,
        "state_before": {},
        "state_after": {},
        "retry_of_turn_id": None,
        "edited_at": None,
        "created_at": now,
        "updated_at": now,
        "edit_history": [],
        "prompt_payload": {"seed": True},
    }


def prepare_campaign(module: Any) -> Dict[str, Any]:
    created = module.create_campaign_record("Normalize Passive Test", "Host")
    campaign = created["campaign"]
    slot_id = "slot_1"
    campaign["state"]["characters"][slot_id] = module.blank_character_state(slot_id)
    campaign["state"]["characters"][slot_id].setdefault("bio", {})
    campaign["state"]["characters"][slot_id]["bio"]["name"] = "Matchek"
    campaign["claims"][slot_id] = created["player_id"]
    campaign["setup"]["world"]["completed"] = True
    campaign["setup"]["characters"][slot_id] = module.default_character_setup_node()
    campaign["setup"]["characters"][slot_id]["completed"] = True
    campaign["state"]["meta"]["phase"] = "adventure"
    campaign["turns"] = [build_story_turn(module, slot_id, created["player_id"], idx=1)]
    return campaign


def canonical_snapshot(campaign: Dict[str, Any]) -> str:
    subset = {
        "state": campaign.get("state"),
        "turns": campaign.get("turns"),
        "claims": campaign.get("claims"),
        "setup": campaign.get("setup"),
        "boards": campaign.get("boards"),
    }
    return json.dumps(subset, ensure_ascii=False, sort_keys=True)


def main() -> None:
    temp_dir = tempfile.mkdtemp(prefix="isekai_normalize_passive_")
    os.environ["DATA_DIR"] = temp_dir
    os.environ["ENABLE_HEURISTIC_NORMALIZE_BACKFILL"] = "false"

    import app.main as main_module

    main_module = importlib.reload(main_module)
    campaign = prepare_campaign(main_module)

    # 1-3) No backfill items/skills/scenes on normalize
    normalized = main_module.normalize_campaign(deepcopy(campaign))
    slot_state = ((normalized.get("state") or {}).get("characters") or {}).get("slot_1") or {}
    assert not (normalized.get("state", {}).get("items") or {}), "normalize created items from history"
    assert not (slot_state.get("skills") or {}), "normalize created skills from history"
    assert not (((normalized.get("state") or {}).get("map") or {}).get("nodes") or {}), "normalize created map nodes from history"
    assert not str(slot_state.get("scene_id") or "").strip(), "normalize assigned scene_id from history"

    # 4) Legacy campaign loadability (missing/old fields)
    legacy_like = {
        "campaign_meta": {"campaign_id": "camp_legacy", "title": "Legacy", "host_player_id": "player_x", "created_at": main_module.utc_now(), "updated_at": main_module.utc_now(), "status": "active", "join_code_hash": "x"},
        "state": {"meta": {"phase": "character_creation"}, "characters": {"slot_1": {"bio": {"name": "Legacy"}}}},
        "players": {"player_x": {"display_name": "Host", "player_token_hash": "x", "joined_at": main_module.utc_now(), "last_seen_at": main_module.utc_now()}},
        "claims": {"slot_1": "player_x"},
        "turns": [],
        "boards": {},
        "setup": {"version": 3},
        "board_revisions": [],
        "legacy_migration": None,
    }
    stabilized = main_module.normalize_campaign(deepcopy(legacy_like))
    assert "state" in stabilized and "setup" in stabilized and "boards" in stabilized, "legacy campaign not stabilized"

    # 5) Idempotence (heuristic no-growth)
    a = main_module.normalize_campaign(deepcopy(campaign))
    b = main_module.normalize_campaign(deepcopy(a))
    a_slot = ((a.get("state") or {}).get("characters") or {}).get("slot_1") or {}
    b_slot = ((b.get("state") or {}).get("characters") or {}).get("slot_1") or {}
    assert len((b.get("state") or {}).get("items") or {}) == len((a.get("state") or {}).get("items") or {}), "idempotence: items grew"
    assert len((b_slot.get("skills") or {})) == len((a_slot.get("skills") or {})), "idempotence: skills grew"
    assert len((((b.get("state") or {}).get("map") or {}).get("nodes") or {})) == len((((a.get("state") or {}).get("map") or {}).get("nodes") or {})), "idempotence: map grew"

    # 6) Save regression (load->normalize->save->reload) without growth
    path = Path(temp_dir) / "campaigns" / "camp_passive.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    main_module.save_json(str(path), main_module.normalize_campaign(deepcopy(campaign)))
    loaded = main_module.load_json(str(path))
    reloaded = main_module.normalize_campaign(loaded)
    rel_slot = ((reloaded.get("state") or {}).get("characters") or {}).get("slot_1") or {}
    assert not (reloaded.get("state", {}).get("items") or {}), "save regression created items"
    assert not (rel_slot.get("skills") or {}), "save regression created skills"
    assert not (((reloaded.get("state") or {}).get("map") or {}).get("nodes") or {}), "save regression created map nodes"

    # 7) View mutability: build_campaign_view must not mutate input campaign
    live_campaign = main_module.normalize_campaign(deepcopy(campaign))
    before = canonical_snapshot(live_campaign)
    _view = main_module.build_campaign_view(live_campaign, None)
    after = canonical_snapshot(live_campaign)
    assert before == after, "build_campaign_view mutated live campaign"

    # 8) Legacy flag behavior (optional backfill path works only when enabled)
    assert not bool(main_module.ENABLE_HEURISTIC_NORMALIZE_BACKFILL), "default backfill flag must be false"
    flagged = deepcopy(campaign)
    main_module.ENABLE_HEURISTIC_NORMALIZE_BACKFILL = True
    flagged_norm = main_module.normalize_campaign(flagged)
    flag_slot = ((flagged_norm.get("state") or {}).get("characters") or {}).get("slot_1") or {}
    maybe_changed = (
        bool((flagged_norm.get("state") or {}).get("items") or {})
        or bool(flag_slot.get("skills") or {})
        or bool((((flagged_norm.get("state") or {}).get("map") or {}).get("nodes") or {}))
        or bool(str(flag_slot.get("scene_id") or "").strip())
    )
    assert maybe_changed, "legacy flag enabled but no heuristic backfill observed"

    print("OK: normalize_campaign is passive by default and build_campaign_view is mutation-free.")


if __name__ == "__main__":
    main()
