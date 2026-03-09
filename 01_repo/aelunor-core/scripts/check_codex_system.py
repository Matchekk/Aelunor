import importlib
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def prepare_campaign(module: Any) -> Tuple[Dict[str, Any], str]:
    created = module.create_campaign_record("Codex Check", "Host")
    campaign = created["campaign"]
    slot_id = "slot_1"
    campaign["state"].setdefault("characters", {})
    campaign["state"]["characters"][slot_id] = module.blank_character_state(slot_id)
    campaign["state"]["characters"][slot_id].setdefault("bio", {})
    campaign["state"]["characters"][slot_id]["bio"]["name"] = "Matchek"
    campaign["claims"][slot_id] = created["player_id"]
    campaign["setup"]["world"]["completed"] = True
    campaign["setup"]["world"]["summary"] = {
        "theme": "Isekai Hybrid",
        "tone": "Düster",
        "central_conflict": "Grenzkrieg",
        "monsters_density": "Regelmäßig",
    }
    campaign["state"]["meta"]["phase"] = "adventure"
    module.normalize_campaign(campaign)
    return campaign, slot_id


def main() -> None:
    temp_dir = tempfile.mkdtemp(prefix="isekai_codex_checks_")
    os.environ["DATA_DIR"] = temp_dir

    import app.main as main_module

    main_module = importlib.reload(main_module)

    # 1) Weltgenerierung erzeugt mehrere Rassen/Bestien
    campaign, slot_id = prepare_campaign(main_module)
    races = ((campaign.get("state") or {}).get("world") or {}).get("races") or {}
    beasts = ((campaign.get("state") or {}).get("world") or {}).get("beast_types") or {}
    assert 5 <= len(races) <= 7, len(races)
    assert 6 <= len(beasts) <= 12, len(beasts)

    # 2) Kodex initial gesperrt (knowledge_level 0)
    codex_races = (((campaign.get("state") or {}).get("codex") or {}).get("races") or {})
    codex_beasts = (((campaign.get("state") or {}).get("codex") or {}).get("beasts") or {})
    assert codex_races and codex_beasts
    assert all(int((entry or {}).get("knowledge_level", 0) or 0) == 0 for entry in codex_races.values())
    assert all(int((entry or {}).get("knowledge_level", 0) or 0) == 0 for entry in codex_beasts.values())

    # 3) Alias-Varianten robust (inkl. Kurzform/Pluralregel)
    variants = main_module.build_entity_alias_variants("Volk der Schattenwölfe", [])
    assert "schattenwoelfe" in variants, variants
    assert "schattenwoelf" in variants or "schattenwoelfes" in variants or "schattenwoelfen" in variants, variants

    # 4) Ambiguität: alias -> [id1,id2], kein Auto-Unlock
    campaign, slot_id = prepare_campaign(main_module)
    state = campaign["state"]
    state["world"]["races"] = {
        "race_alpha": main_module.normalize_race_profile({"id": "race_alpha", "name": "Alpha Volk", "aliases": ["wandler"]}, fallback_id="race_alpha"),
        "race_beta": main_module.normalize_race_profile({"id": "race_beta", "name": "Beta Volk", "aliases": ["wandler"]}, fallback_id="race_beta"),
    }
    state["world"]["beast_types"] = {}
    main_module.normalize_world_codex_structures(state)
    bundle = main_module.collect_codex_triggers(
        campaign,
        state,
        actor=slot_id,
        action_type="story",
        player_text="Ich treffe einen Wandler am Tor.",
        gm_text="Der Wandler beobachtet euch.",
        patch=main_module.blank_patch(),
        npc_updates=[],
        turn_number=1,
    )
    updates = main_module.apply_codex_triggers(state, bundle, turn_number=1)
    assert any(entry.get("kind") == "ambiguous" for entry in updates), updates
    race_entries = (((state.get("codex") or {}).get("races") or {}))
    assert all(int((entry or {}).get("knowledge_level", 0) or 0) == 0 for entry in race_entries.values()), race_entries

    # 5) Deterministischer eindeutiger Treffer + Fakten dedupe/stable
    campaign, slot_id = prepare_campaign(main_module)
    state = campaign["state"]
    first_race_id = next(iter((state["world"]["races"] or {}).keys()))
    first_race_name = (state["world"]["races"][first_race_id] or {}).get("name") or first_race_id
    bundle = main_module.collect_codex_triggers(
        campaign,
        state,
        actor=slot_id,
        action_type="story",
        player_text=f"Ich begegne den {first_race_name}.",
        gm_text=f"Archivnotizen über {first_race_name} werden gefunden.",
        patch=main_module.blank_patch(),
        npc_updates=[],
        turn_number=2,
    )
    updates = main_module.apply_codex_triggers(state, bundle, turn_number=2)
    assert any(entry.get("kind") == "race" and entry.get("entity_id") == first_race_id for entry in updates), updates
    entry_before = deepcopy((((state.get("codex") or {}).get("races") or {}).get(first_race_id) or {}))
    facts_before = list(entry_before.get("known_facts") or [])
    blocks_before = list(entry_before.get("known_blocks") or [])
    bundle = main_module.collect_codex_triggers(
        campaign,
        state,
        actor=slot_id,
        action_type="story",
        player_text=f"Erneut Hinweise zu {first_race_name}.",
        gm_text=f"Archivnotizen über {first_race_name} werden erneut gefunden.",
        patch=main_module.blank_patch(),
        npc_updates=[],
        turn_number=3,
    )
    main_module.apply_codex_triggers(state, bundle, turn_number=3)
    entry_after = (((state.get("codex") or {}).get("races") or {}).get(first_race_id) or {})
    facts_after = list(entry_after.get("known_facts") or [])
    blocks_after = list(entry_after.get("known_blocks") or [])
    assert len(facts_after) == len(set(main_module.normalize_codex_alias_text(value) for value in facts_after)), facts_after
    assert facts_after[: len(facts_before)] == facts_before, (facts_before, facts_after)
    expected_order = [block for block in main_module.RACE_CODEX_BLOCK_ORDER if block in set(blocks_after)]
    assert blocks_after == expected_order, blocks_after
    assert all(block in blocks_after for block in blocks_before), (blocks_before, blocks_after)

    # 6) Save/Reload Reihenfolge stabil
    campaign, slot_id = prepare_campaign(main_module)
    campaign = main_module.normalize_campaign(campaign)
    before = deepcopy(campaign["state"])
    camp_id = campaign["campaign_meta"]["campaign_id"]
    main_module.save_json(main_module.campaign_path(camp_id), campaign)
    reloaded = main_module.load_campaign(camp_id)
    after = deepcopy(reloaded["state"])
    assert list((((before.get("world") or {}).get("races") or {}).keys())) == list((((after.get("world") or {}).get("races") or {}).keys()))
    assert list((((before.get("world") or {}).get("beast_types") or {}).keys())) == list((((after.get("world") or {}).get("beast_types") or {}).keys()))

    # 7) build_campaign_view bleibt mutierungsfrei
    campaign, slot_id = prepare_campaign(main_module)
    baseline = deepcopy(campaign)
    _ = main_module.build_campaign_view(campaign, campaign["claims"].get(slot_id))
    assert campaign["state"] == baseline["state"], "build_campaign_view mutated state"
    assert campaign["setup"] == baseline["setup"], "build_campaign_view mutated setup"

    # 8) Altkampagne ohne Codex bleibt ladbar
    legacy = {
        "campaign_meta": deepcopy(campaign["campaign_meta"]),
        "players": deepcopy(campaign["players"]),
        "claims": deepcopy(campaign["claims"]),
        "turns": [],
        "boards": deepcopy(campaign["boards"]),
        "setup": deepcopy(campaign["setup"]),
        "state": {
            "meta": {"phase": "adventure", "turn": 0},
            "world": {"settings": {"resource_name": "Aether"}},
            "map": {"nodes": {}, "edges": []},
            "characters": {slot_id: main_module.blank_character_state(slot_id)},
        },
    }
    normalized = main_module.normalize_campaign(legacy)
    assert "codex" in (normalized.get("state") or {})
    assert "races" in (((normalized.get("state") or {}).get("world") or {}))
    assert "beast_types" in (((normalized.get("state") or {}).get("world") or {}))

    print("OK: AP6 Codex-System Checks erfolgreich.")


if __name__ == "__main__":
    main()
