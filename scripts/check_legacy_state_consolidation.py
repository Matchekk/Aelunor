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


def prepare_campaign(module: Any, *, title: str = "Legacy Consolidation Check") -> Tuple[Dict[str, Any], str, str]:
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
    return campaign, slot_id, created["player_id"]


def main() -> None:
    temp_dir = tempfile.mkdtemp(prefix="isekai_legacy_consolidation_")
    os.environ["DATA_DIR"] = temp_dir
    os.environ["ENABLE_LEGACY_SHADOW_WRITEBACK"] = "false"

    import backend.main as main_module

    main_module = importlib.reload(main_module)

    # 1) Legacy abilities ladbar -> skills werden befuellt
    campaign, slot_id, _player_id = prepare_campaign(main_module, title="Legacy Abilities")
    campaign["state"]["characters"][slot_id] = {
        "bio": {"name": "Matchek"},
        "abilities": [
            {
                "id": "ab_shadow",
                "name": "Schattenstoß",
                "owner": slot_id,
                "rank": "D",
                "level": 2,
                "tags": ["schatten", "kampf"],
                "type": "active",
            }
        ],
        "skills": {},
    }
    normalized = main_module.normalize_campaign(deepcopy(campaign))
    skills = (((normalized.get("state") or {}).get("characters") or {}).get(slot_id) or {}).get("skills") or {}
    assert skills, "Legacy abilities wurden nicht in skills migriert"

    # 2) Moderne Skill-Aenderung schreibt kein abilities shadow (flag off)
    state = normalized["state"]
    patch = main_module.blank_patch()
    patch["characters"][slot_id] = {
        "skills_set": {
            "skill_feuerklinge": {
                "id": "skill_feuerklinge",
                "name": "Feuerklinge",
                "rank": "C",
                "level": 1,
                "level_max": 10,
                "tags": ["magie", "kampf"],
                "description": "Lodernde Klingenbahn.",
                "cost": {"resource": "Aether", "amount": 2},
                "price": None,
                "cooldown_turns": None,
                "unlocked_from": "Story",
                "synergy_notes": None,
            }
        }
    }
    main_module.apply_patch(state, patch)
    char_after_skill = (state.get("characters") or {}).get(slot_id) or {}
    assert "abilities" not in char_after_skill, "abilities shadow wurde trotz flag off aktiv gepflegt"

    # 3) Legacy resources lesbar, Canon bleibt primaer
    campaign, slot_id, _ = prepare_campaign(main_module, title="Legacy Resources")
    legacy_char = main_module.blank_character_state(slot_id)
    legacy_char.pop("hp_current", None)
    legacy_char.pop("hp_max", None)
    legacy_char.pop("sta_current", None)
    legacy_char.pop("sta_max", None)
    legacy_char.pop("res_current", None)
    legacy_char.pop("res_max", None)
    legacy_char["resources"] = {
        "hp": {"current": 7, "max": 12},
        "stamina": {"current": 4, "max": 9},
        "aether": {"current": 3, "max": 8},
        "stress": {"current": 2, "max": 10},
        "corruption": {"current": 1, "max": 10},
        "wounds": {"current": 0, "max": 3},
    }
    campaign["state"]["characters"][slot_id] = legacy_char
    normalized = main_module.normalize_campaign(campaign)
    ch = ((normalized.get("state") or {}).get("characters") or {}).get(slot_id) or {}
    assert int(ch.get("hp_current", 0) or 0) == 7 and int(ch.get("hp_max", 0) or 0) == 12, "Legacy hp nicht korrekt nach Canon migriert"
    assert int(ch.get("sta_current", 0) or 0) == 4 and int(ch.get("sta_max", 0) or 0) == 9, "Legacy stamina nicht korrekt nach Canon migriert"
    assert int(ch.get("res_current", 0) or 0) == 3 and int(ch.get("res_max", 0) or 0) == 8, "Legacy resource nicht korrekt nach Canon migriert"
    resources_shadow = ch.get("resources") if isinstance(ch.get("resources"), dict) else {}
    assert "hp" not in resources_shadow and "stamina" not in resources_shadow and "aether" not in resources_shadow, "Core resource shadow wurde nicht entfernt"

    # 4) class_current bleibt primaer gegen alte Rollen/Class-State Felder
    campaign, slot_id, _ = prepare_campaign(main_module, title="Class Priority")
    campaign["state"]["characters"][slot_id]["class_current"] = {
        "id": "class_schattenkrieger",
        "name": "Schattenkrieger",
        "rank": "B",
        "level": 4,
        "level_max": 10,
        "xp": 50,
        "xp_next": 100,
        "affinity_tags": ["schatten", "kampf"],
        "description": "Aktive Klasse",
        "ascension": {"status": "none", "quest_id": None, "requirements": [], "result_hint": None},
    }
    campaign["state"]["characters"][slot_id]["bio"]["party_role"] = "Frontline"
    campaign["state"]["characters"][slot_id]["class_state"] = {"class_id": "class_legacy", "class_name": "LegacyClass"}
    normalized = main_module.normalize_campaign(campaign)
    class_current = (((normalized.get("state") or {}).get("characters") or {}).get(slot_id) or {}).get("class_current") or {}
    assert class_current.get("id") == "class_schattenkrieger", "class_current wurde von Legacy-Feldern ueberschrieben"

    # 5) Legacy equip wird gemappt, aber nicht als aktive zweite Wahrheit behalten (flag off)
    campaign, slot_id, _ = prepare_campaign(main_module, title="Equip Migration")
    campaign["state"]["characters"][slot_id]["equip"] = {"weapon": "itm_sword", "armor": "itm_chain", "trinket": "itm_ring"}
    normalized = main_module.normalize_campaign(campaign)
    ch = ((normalized.get("state") or {}).get("characters") or {}).get(slot_id) or {}
    equipment = ch.get("equipment") or {}
    assert equipment.get("weapon") == "itm_sword" and equipment.get("chest") == "itm_chain", "Legacy equip wurde nicht korrekt gemappt"
    assert "equip" not in ch, "Legacy equip shadow wurde trotz flag off beibehalten"

    # 6) Load -> normalize -> save -> reload stabilisiert Parallelwahrheit
    campaign = main_module.normalize_campaign(campaign)
    campaign_id = campaign["campaign_meta"]["campaign_id"]
    main_module.save_json(main_module.campaign_path(campaign_id), campaign)
    reloaded = main_module.normalize_campaign(main_module.load_json(main_module.campaign_path(campaign_id)))
    ch_reload = ((reloaded.get("state") or {}).get("characters") or {}).get(slot_id) or {}
    resources_reload = ch_reload.get("resources") if isinstance(ch_reload.get("resources"), dict) else {}
    assert "hp" not in resources_reload and "stamina" not in resources_reload and "aether" not in resources_reload, "Save/Reload hat Core shadow wiederbelebt"

    # 7) Regression moderne Kampagne bleibt funktionsfaehig
    campaign, slot_id, _ = prepare_campaign(main_module, title="Modern Regression")
    campaign = main_module.normalize_campaign(campaign)
    patch = main_module.blank_patch()
    patch["characters"][slot_id] = {"resources_delta": {"hp": -2, "stamina": -1, "res": -1}, "scene_id": "scene_test"}
    campaign["state"].setdefault("scenes", {})["scene_test"] = {"name": "Testszene", "danger": 1, "notes": ""}
    main_module.validate_patch(campaign["state"], patch)
    main_module.apply_patch(campaign["state"], patch)
    ch = ((campaign.get("state") or {}).get("characters") or {}).get(slot_id) or {}
    assert int(ch.get("hp_current", 0) or 0) >= 0 and int(ch.get("sta_current", 0) or 0) >= 0, "Moderne Kampagne regressiert bei Canon-Ressourcen"

    # 8) Flag-Verhalten: off = kein shadow writeback, on = shadow writeback vorhanden
    main_module.ENABLE_LEGACY_SHADOW_WRITEBACK = False
    campaign = main_module.normalize_campaign(campaign)
    ch = ((campaign.get("state") or {}).get("characters") or {}).get(slot_id) or {}
    assert "abilities" not in ch and "equip" not in ch and "hp" not in ch, "Flag off schreibt Legacy-Shadows"

    main_module.ENABLE_LEGACY_SHADOW_WRITEBACK = True
    campaign = main_module.normalize_campaign(campaign)
    ch = ((campaign.get("state") or {}).get("characters") or {}).get(slot_id) or {}
    assert "abilities" in ch and "equip" in ch and "hp" in ch, "Flag on erzeugt keine Legacy-Shadows"

    print("OK: Legacy-State Konsolidierung (AP4) erfolgreich geprueft.")


if __name__ == "__main__":
    main()
