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


def prepare_campaign(module: Any, *, title: str = "Progression Check") -> Tuple[Dict[str, Any], str]:
    created = module.create_campaign_record(title, "Host")
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
    campaign = module.normalize_campaign(campaign)
    return campaign, slot_id


def apply_patch_and_progress(
    module: Any,
    campaign: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    actor: str,
    action_type: str = "story",
) -> Dict[str, Any]:
    state_before = deepcopy(campaign["state"])
    campaign["state"] = module.apply_patch(campaign["state"], deepcopy(patch))
    result = module.apply_progression_events(
        campaign,
        state_before,
        campaign["state"],
        patch,
        actor=actor,
        action_type=action_type,
    )
    return result


def main() -> None:
    temp_dir = tempfile.mkdtemp(prefix="isekai_progression_check_")
    os.environ["DATA_DIR"] = temp_dir
    os.environ["ENABLE_LEGACY_SHADOW_WRITEBACK"] = "false"

    import app.main as main_module

    main_module = importlib.reload(main_module)

    # 1) Character XP + Level-Up via milestone progression events
    campaign, slot_id = prepare_campaign(main_module, title="Character XP")
    patch = main_module.blank_patch()
    patch["characters"][slot_id] = {
        "progression_events": [
            {"type": "milestone_progress", "severity": "high", "reason": "Reliktpfad I"},
            {"type": "milestone_progress", "severity": "high", "reason": "Reliktpfad II"},
            {"type": "milestone_progress", "severity": "high", "reason": "Reliktpfad III"},
        ]
    }
    apply_patch_and_progress(main_module, campaign, patch, actor=slot_id)
    ch = campaign["state"]["characters"][slot_id]
    assert int(ch.get("xp_total", 0) or 0) > 0, "Character XP wurde nicht vergeben"
    assert int(ch.get("level", 1) or 1) > 1, "Character Level-Up blieb aus"

    # 2) Class XP + Class-Level-Up
    campaign, slot_id = prepare_campaign(main_module, title="Class XP")
    campaign["state"]["characters"][slot_id]["class_current"] = {
        "id": "class_runenkrieger",
        "name": "Runenkrieger",
        "rank": "D",
        "level": 1,
        "level_max": 10,
        "xp": 0,
        "xp_next": 100,
        "affinity_tags": ["rune", "kampf"],
        "description": "Bindet Runen in Nahkampftechnik.",
        "ascension": {"status": "none", "quest_id": None, "requirements": [], "result_hint": None},
    }
    patch = main_module.blank_patch()
    patch["characters"][slot_id] = {
        "progression_events": [
            {"type": "class_breakthrough", "severity": "high", "reason": "Runenresonanz"},
            {"type": "class_breakthrough", "severity": "high", "reason": "Zweiter Durchbruch"},
        ]
    }
    apply_patch_and_progress(main_module, campaign, patch, actor=slot_id)
    klass = main_module.normalize_class_current(campaign["state"]["characters"][slot_id].get("class_current")) or {}
    assert int(klass.get("xp", 0) or 0) > 0, "Class XP wurde nicht vergeben"
    assert int(klass.get("level", 1) or 1) > 1, "Class Level-Up blieb aus"

    # 3) Skill XP + Skill-Level-Up
    campaign, slot_id = prepare_campaign(main_module, title="Skill XP")
    campaign["state"]["characters"][slot_id]["skills"] = {
        "skill_runenstoss": main_module.normalize_dynamic_skill_state(
            {
                "id": "skill_runenstoss",
                "name": "Runenstoß",
                "rank": "D",
                "level": 1,
                "level_max": 10,
                "tags": ["rune", "kampf"],
                "description": "Ein komprimierter Runenimpuls.",
                "cost": {"resource": "Aether", "amount": 1},
            },
            resource_name="Aether",
        )
    }
    patch = main_module.blank_patch()
    patch["characters"][slot_id] = {
        "progression_events": [
            {"type": "skill_mastery_use", "severity": "high", "target_skill_id": "skill_runenstoss", "reason": "harte Nutzung I"},
            {"type": "skill_mastery_use", "severity": "high", "target_skill_id": "skill_runenstoss", "reason": "harte Nutzung II"},
            {"type": "skill_mastery_use", "severity": "high", "target_skill_id": "skill_runenstoss", "reason": "harte Nutzung III"},
            {"type": "skill_mastery_use", "severity": "high", "target_skill_id": "skill_runenstoss", "reason": "harte Nutzung IV"},
        ]
    }
    apply_patch_and_progress(main_module, campaign, patch, actor=slot_id)
    skill = (campaign["state"]["characters"][slot_id].get("skills") or {}).get("skill_runenstoss") or {}
    assert int(skill.get("xp", 0) or 0) >= 0, "Skill XP fehlt"
    assert int(skill.get("level", 1) or 1) > 1, "Skill Level-Up blieb aus"

    # 4) on-class/off-class Multiplikator wirkt
    campaign, slot_id = prepare_campaign(main_module, title="Affinity Multiplier")
    campaign["state"]["world"]["settings"]["onclass_xp_multiplier"] = 1.0
    campaign["state"]["world"]["settings"]["offclass_xp_multiplier"] = 0.5
    campaign["state"]["characters"][slot_id]["class_current"] = {
        "id": "class_runenklinge",
        "name": "Runenklinge",
        "rank": "C",
        "level": 1,
        "level_max": 10,
        "xp": 0,
        "xp_next": 100,
        "affinity_tags": ["rune"],
        "description": "Runenfokus.",
        "ascension": {"status": "none", "quest_id": None, "requirements": [], "result_hint": None},
    }
    campaign["state"]["characters"][slot_id]["skills"] = {
        "skill_runenfokus": main_module.normalize_dynamic_skill_state(
            {"id": "skill_runenfokus", "name": "Runenfokus", "tags": ["rune"], "description": "On-class Skill"},
            resource_name="Aether",
        ),
        "skill_klingenwirbel": main_module.normalize_dynamic_skill_state(
            {"id": "skill_klingenwirbel", "name": "Klingenwirbel", "tags": ["stahl"], "description": "Off-class Skill"},
            resource_name="Aether",
        ),
    }
    ch = campaign["state"]["characters"][slot_id]
    ch["skills"]["skill_runenfokus"]["xp"] = 0
    ch["skills"]["skill_klingenwirbel"]["xp"] = 0
    main_module.grant_skill_xp(ch, "skill_runenfokus", "normal", world_settings=campaign["state"]["world"]["settings"])
    main_module.grant_skill_xp(ch, "skill_klingenwirbel", "normal", world_settings=campaign["state"]["world"]["settings"])
    on_xp = int(ch["skills"]["skill_runenfokus"].get("xp", 0) or 0)
    off_xp = int(ch["skills"]["skill_klingenwirbel"].get("xp", 0) or 0)
    assert on_xp > off_xp, f"on-class/off-class Multiplikator greift nicht (on={on_xp}, off={off_xp})"

    # 5) Skill-Manifestation erzeugt valides Skill-Objekt
    campaign, slot_id = prepare_campaign(main_module, title="Skill Manifestation")
    patch = main_module.blank_patch()
    patch["characters"][slot_id] = {
        "progression_events": [
            {
                "type": "skill_manifestation",
                "severity": "medium",
                "reason": "Runenresonanz",
                "skill": {
                    "name": "Runenimpuls",
                    "rank": "C",
                    "level": 1,
                    "level_max": 10,
                    "tags": ["rune", "magie"],
                    "description": "Stoßwelle aus verdichteten Runenlinien.",
                    "cost": {"resource": "Aether", "amount": 2},
                },
            }
        ]
    }
    result = apply_patch_and_progress(main_module, campaign, patch, actor=slot_id)
    manifest_event = next((entry for entry in (result.get("events") or []) if entry.get("type") == "skill_manifestation"), None)
    assert manifest_event and manifest_event.get("target_skill_id"), "Manifestation hat keinen target_skill_id erzeugt"
    skill_id = str(manifest_event.get("target_skill_id"))
    manifested = (campaign["state"]["characters"][slot_id].get("skills") or {}).get(skill_id) or {}
    for required_key in ("id", "name", "rank", "level", "xp", "next_xp", "cost", "tags", "description", "effect_summary", "power_rating", "growth_potential"):
        assert required_key in manifested, f"Manifestierter Skill fehlt Pflichtfeld {required_key}"

    # 6) Bloße Nutzung erzeugt keinen neuen Skill
    campaign, slot_id = prepare_campaign(main_module, title="No Auto Skill Creation")
    campaign["state"]["characters"][slot_id]["skills"] = {
        "skill_bestehend": main_module.normalize_dynamic_skill_state(
            {"id": "skill_bestehend", "name": "Bestehende Technik", "description": "Schon vorhanden."},
            resource_name="Aether",
        )
    }
    before_count = len(campaign["state"]["characters"][slot_id]["skills"])
    patch = main_module.blank_patch()
    patch["characters"][slot_id] = {
        "progression_events": [
            {"type": "skill_mastery_use", "severity": "medium", "target_skill_id": "skill_bestehend", "reason": "Einsatz im Kampf"}
        ]
    }
    apply_patch_and_progress(main_module, campaign, patch, actor=slot_id)
    after_count = len(campaign["state"]["characters"][slot_id]["skills"])
    assert before_count == after_count, "Skill-Nutzung hat unerwartet einen neuen Skill erzeugt"

    # 7) NPC/Gegner-Level beeinflusst Combat-Skalierung
    campaign, slot_id = prepare_campaign(main_module, title="Combat Scaling NPC")
    campaign["state"]["characters"][slot_id]["scene_id"] = "scene_arena"
    campaign["state"]["scenes"]["scene_arena"] = {"name": "Arena", "danger": 6, "notes": ""}
    campaign["state"]["npc_codex"] = {
        "npc_low": {"npc_id": "npc_low", "name": "Söldner Novize", "level": 1, "last_seen_scene_id": "scene_arena"},
    }
    main_module.normalize_npc_codex_state(campaign)
    ctx_low = main_module.build_combat_scaling_context(campaign["state"], slot_id)
    campaign["state"]["npc_codex"] = {
        "npc_high": {"npc_id": "npc_high", "name": "Veteranenklinge", "level": 12, "last_seen_scene_id": "scene_arena"},
    }
    main_module.normalize_npc_codex_state(campaign)
    ctx_high = main_module.build_combat_scaling_context(campaign["state"], slot_id)
    assert int(ctx_high.get("threat_score", 0) or 0) > int(ctx_low.get("threat_score", 0) or 0), "Höherer NPC-Level erhöht threat_score nicht"
    assert float(ctx_high.get("ratio", 1.0) or 1.0) < float(ctx_low.get("ratio", 1.0) or 1.0), "Combat-Ratio reagiert nicht auf stärkeren Gegner"

    # 8) Moderne Kampagne bleibt kompatibel (Smoke)
    campaign, slot_id = prepare_campaign(main_module, title="Regression Smoke")
    patch = main_module.blank_patch()
    patch["characters"][slot_id] = {"resources_delta": {"hp": -2, "res": -1}}
    main_module.validate_patch(campaign["state"], patch)
    campaign["state"] = main_module.apply_patch(campaign["state"], patch)
    assert int(campaign["state"]["characters"][slot_id].get("hp_current", 0) or 0) >= 0

    print("OK: AP5 Progression-System erfolgreich geprüft.")


if __name__ == "__main__":
    main()
