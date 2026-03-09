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
    created = module.create_campaign_record("Element Check", "Host")
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
        "central_conflict": "Elementarsturm",
        "monsters_density": "Regelmäßig",
        "premise": "Relikte der alten Elemente brechen auf",
    }
    campaign["state"]["meta"]["phase"] = "adventure"
    module.normalize_campaign(campaign)
    return campaign, slot_id


def main() -> None:
    temp_dir = tempfile.mkdtemp(prefix="isekai_element_checks_")
    os.environ["DATA_DIR"] = temp_dir

    import app.main as main_module

    main_module = importlib.reload(main_module)

    # 1) Weltgenerierung erzeugt genau 12 Elemente inkl. 6 Anker
    campaign, slot_id = prepare_campaign(main_module)
    world = (campaign.get("state") or {}).get("world") or {}
    elements = world.get("elements") or {}
    assert len(elements) == 12, len(elements)
    names_norm = {main_module.normalize_codex_alias_text((entry or {}).get("name", "")) for entry in elements.values()}
    for anchor_name in main_module.ELEMENT_CORE_NAMES:
        assert main_module.normalize_codex_alias_text(anchor_name) in names_norm, anchor_name

    # 2) Relationen komplett auswertbar, inkl. neutral fallback
    relations = world.get("element_relations") or {}
    for src_id in elements.keys():
        for dst_id in elements.keys():
            relation = main_module.get_element_relation(world, src_id, dst_id)
            assert relation in main_module.ELEMENT_RELATIONS, (src_id, dst_id, relation)
            assert relation == main_module.normalize_element_relation((relations.get(src_id) or {}).get(dst_id, "neutral"))

    # 3) Selbstrelationen existieren standardmäßig neutral
    for element_id in elements.keys():
        relation = main_module.get_element_relation(world, element_id, element_id)
        assert relation == "neutral", (element_id, relation)

    # 4) Pro Element 1-3 Klassenpfade
    paths = world.get("element_class_paths") or {}
    for element_id in elements.keys():
        bucket = paths.get(element_id) or []
        assert 1 <= len(bucket) <= 3, (element_id, len(bucket))
        for path in bucket:
            ranks = (path or {}).get("ranks") or {}
            assert set(ranks.keys()) == set(main_module.ELEMENT_CLASS_PATH_RANKS), (element_id, path.get("id"), ranks.keys())

    # 5) Generierte Elemente sind unterscheidbar
    generated = [entry for entry in elements.values() if str((entry or {}).get("origin") or "") == "generated"]
    assert len(generated) == 6, len(generated)
    core = [entry for entry in elements.values() if str((entry or {}).get("origin") or "") == "core"]
    for candidate in generated:
        too_similar, _reason = main_module.generated_element_too_similar(candidate, core)
        assert not too_similar, candidate.get("name")
    for idx, candidate in enumerate(generated):
        too_similar, _reason = main_module.generated_element_too_similar(candidate, generated[:idx])
        assert not too_similar, candidate.get("name")

    # 6) Pflichtskills je Rang funktionieren (mind. Basisskill)
    state = campaign["state"]
    actor = state["characters"][slot_id]
    first_element_id = next(iter(elements.keys()))
    first_path = ((world.get("element_class_paths") or {}).get(first_element_id) or [])[0]
    rank_f = (((first_path or {}).get("ranks") or {}).get("F") or {})
    actor["class_current"] = main_module.normalize_class_current(
        {
            "id": "class_test",
            "name": rank_f.get("name") or "Element-Novize",
            "rank": "F",
            "level": 1,
            "level_max": 10,
            "path_id": first_path.get("id"),
            "path_rank": "F",
            "element_id": first_element_id,
            "element_tags": [first_element_id],
            "affinity_tags": [main_module.normalize_codex_alias_text((elements[first_element_id] or {}).get("name", ""))],
        }
    )
    actor["skills"] = {}
    messages = main_module.ensure_class_rank_core_skills(actor, world, world.get("settings") or {}, unlock_extra=False)
    assert messages, "expected at least one guaranteed core skill message"
    assert actor["skills"], "expected guaranteed core skill creation"

    # 7) Skill-Manifestation validiert Elementbindung
    manifested = main_module.canonicalize_manifested_skill_payload(
        raw_skill={
            "name": "Funkenlanze",
            "rank": "F",
            "level": 1,
            "description": "Eine fokussierte Elementlanze.",
            "effect_summary": "Stoß aus gebündelter Energie.",
            "elements": [first_element_id],
            "element_primary": first_element_id,
            "cost": {"resource": "Aether", "amount": 1},
        },
        character=actor,
        world=world,
        world_settings=world.get("settings") or {},
    )
    assert manifested is not None
    assert manifested.get("element_primary") == first_element_id
    assert first_element_id in (manifested.get("elements") or [])

    # 8) Combat berücksichtigt Elemente, aber bleibt multi-faktoriell
    second_slot = "slot_2"
    state["characters"][second_slot] = main_module.blank_character_state(second_slot)
    state["characters"][second_slot]["bio"]["name"] = "Gegner"
    state["characters"][second_slot]["scene_id"] = actor.get("scene_id") or "scene_test"
    actor["scene_id"] = state["characters"][second_slot]["scene_id"]
    state["characters"][second_slot]["element_affinities"] = []
    state["characters"][second_slot]["class_current"] = main_module.normalize_class_current({"name": "Dummy", "rank": "F"})
    actor["element_affinities"] = [first_element_id]
    actor["class_current"] = main_module.normalize_class_current({**(actor.get("class_current") or {}), "element_id": first_element_id})
    neutral_ctx = main_module.build_combat_scaling_context(state, slot_id)
    assert float(neutral_ctx.get("element_factor", 1.0) or 1.0) >= 0.8
    target_id = next((eid for eid in elements.keys() if eid != first_element_id), first_element_id)
    state["world"]["element_relations"][first_element_id][target_id] = "strong"
    state["world"]["element_relations"][target_id][first_element_id] = "countered"
    state["characters"][second_slot]["element_affinities"] = [target_id]
    skewed_ctx = main_module.build_combat_scaling_context(state, slot_id)
    assert float(skewed_ctx.get("element_factor", 1.0) or 1.0) != float(neutral_ctx.get("element_factor", 1.0) or 1.0)
    assert float(skewed_ctx.get("weighted_ratio", 1.0) or 1.0) != float(neutral_ctx.get("weighted_ratio", 1.0) or 1.0)

    # 9) NPCs/Bestien mit Elementfeldern laufen durch Normalize
    first_beast_id = next(iter((world.get("beast_types") or {}).keys()))
    world["beast_types"][first_beast_id]["strength_tags"] = [first_element_id]
    state.setdefault("npc_codex", {})
    state["npc_codex"]["npc_test"] = main_module.normalize_npc_entry(
        {
            "npc_id": "npc_test",
            "name": "Valerius",
            "race": "Mensch",
            "element_affinities": [first_element_id],
            "element_resistances": [target_id],
            "element_weaknesses": [],
        },
        fallback_npc_id="npc_test",
    )
    normalized = main_module.normalize_campaign(campaign)
    npc_after = (((normalized.get("state") or {}).get("npc_codex") or {}).get("npc_test") or {})
    assert first_element_id in (npc_after.get("element_affinities") or [])

    # 10) Load -> Normalize -> Save ohne kreative Weltmutation
    before_world = deepcopy(((campaign.get("state") or {}).get("world") or {}))
    camp_id = campaign["campaign_meta"]["campaign_id"]
    main_module.save_json(main_module.campaign_path(camp_id), campaign)
    loaded = main_module.load_campaign(camp_id)
    loaded = main_module.normalize_campaign(loaded)
    after_world = deepcopy(((loaded.get("state") or {}).get("world") or {}))
    assert list((before_world.get("elements") or {}).keys()) == list((after_world.get("elements") or {}).keys())
    assert list((before_world.get("element_class_paths") or {}).keys()) == list((after_world.get("element_class_paths") or {}).keys())

    print("OK: AP6 Element-System Checks erfolgreich.")


if __name__ == "__main__":
    main()
