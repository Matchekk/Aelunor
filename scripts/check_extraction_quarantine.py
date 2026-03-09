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


def prepare_campaign(module: Any, *, character_name: str = "Matchek") -> Tuple[Dict[str, Any], str]:
    created = module.create_campaign_record("Extraction Check", "Host")
    campaign = created["campaign"]
    slot_id = "slot_1"
    campaign["state"].setdefault("characters", {})
    campaign["state"]["characters"][slot_id] = module.blank_character_state(slot_id)
    campaign["state"]["characters"][slot_id].setdefault("bio", {})
    campaign["state"]["characters"][slot_id]["bio"]["name"] = character_name
    campaign["claims"][slot_id] = created["player_id"]
    campaign["setup"]["world"]["completed"] = True
    campaign["setup"]["characters"][slot_id] = module.default_character_setup_node()
    campaign["setup"]["characters"][slot_id]["completed"] = True
    campaign["state"]["meta"]["phase"] = "adventure"
    module.normalize_campaign(campaign)
    return campaign, slot_id


def latest_quarantine_reasons(state: Dict[str, Any]) -> Dict[str, int]:
    reasons: Dict[str, int] = {}
    entries = (((state.get("meta") or {}).get("extraction_quarantine") or {}).get("entries") or [])
    for entry in entries:
        reason = str((entry or {}).get("reason_code") or "").strip()
        reasons[reason] = reasons.get(reason, 0) + 1
    return reasons


def main() -> None:
    temp_dir = tempfile.mkdtemp(prefix="isekai_extract_checks_")
    os.environ["DATA_DIR"] = temp_dir

    import backend.main as main_module

    main_module = importlib.reload(main_module)
    original_call_ollama_schema = main_module.call_ollama_schema

    def fake_ollama_schema(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return {"patch": main_module.blank_patch()}

    try:
        main_module.call_ollama_schema = fake_ollama_schema

        # 1) Generischer Ort -> kein map live, Quarantäne GENERIC_LOCATION
        campaign, slot_id = prepare_campaign(main_module)
        state = campaign["state"]
        patch = main_module.call_canon_extractor(
            campaign, state, slot_id, "story", "Die Gruppe erreicht den Wald.", source="narrator"
        )
        assert not patch.get("map_add_nodes"), patch
        assert not ((patch.get("characters") or {}).get(slot_id) or {}).get("scene_id"), patch
        reasons = latest_quarantine_reasons(state)
        assert reasons.get(main_module.EXTRACTION_REASON_GENERIC_LOCATION, 0) >= 1, reasons

        # 2) Umgebungsgegenstand -> kein inventory_add, Quarantäne ENV_OBJECT_ONLY
        campaign, slot_id = prepare_campaign(main_module)
        state = campaign["state"]
        patch = main_module.call_canon_extractor(
            campaign, state, slot_id, "story", "Neben ihm liegt ein Schwert an der Wand.", source="narrator"
        )
        inventory_add = (((patch.get("characters") or {}).get(slot_id) or {}).get("inventory_add") or [])
        assert not inventory_add, patch
        reasons = latest_quarantine_reasons(state)
        assert reasons.get(main_module.EXTRACTION_REASON_ENV_OBJECT, 0) >= 1, reasons

        # 3) Aktionsverb -> kein skill live, Quarantäne VERB_STYLE_SKILL
        campaign, slot_id = prepare_campaign(main_module)
        state = campaign["state"]
        patch = main_module.call_canon_extractor(
            campaign, state, slot_id, "story", "Er kämpft schneller und aggressiver.", source="narrator"
        )
        skills_set = (((patch.get("characters") or {}).get(slot_id) or {}).get("skills_set") or {})
        assert not skills_set, patch
        reasons = latest_quarantine_reasons(state)
        assert reasons.get(main_module.EXTRACTION_REASON_VERB_STYLE_SKILL, 0) >= 1, reasons

        # 4) Explizit gelernter Skill -> skill entsteht
        campaign, slot_id = prepare_campaign(main_module, character_name="Matchek")
        state = campaign["state"]
        patch = main_module.call_canon_extractor(
            campaign, state, slot_id, "story", "Matchek erlernt Schattenmagie.", source="narrator"
        )
        skills_set = (((patch.get("characters") or {}).get(slot_id) or {}).get("skills_set") or {})
        assert skills_set, patch

        # 5) Explizit erhaltenes Item -> items_new + inventory_add
        campaign, slot_id = prepare_campaign(main_module, character_name="Matchek")
        state = campaign["state"]
        patch = main_module.call_canon_extractor(
            campaign, state, slot_id, "story", "Matchek erhält den Runenkompass und steckt ihn ein.", source="narrator"
        )
        items_new = patch.get("items_new") or {}
        inventory_add = (((patch.get("characters") or {}).get(slot_id) or {}).get("inventory_add") or [])
        assert items_new and inventory_add, patch

        # 6) Additiver Merge: LLM scene_id bleibt, SAFE darf nicht überschreiben
        campaign, slot_id = prepare_campaign(main_module)
        state = campaign["state"]
        llm_patch = main_module.blank_patch()
        llm_patch["characters"][slot_id] = {"scene_id": "scene_llm_keep"}
        safe_patch = main_module.blank_patch()
        safe_patch["characters"][slot_id] = {"scene_id": "scene_safe_skip"}
        merged, conflicts = main_module.merge_safe_patch_additive(llm_patch, safe_patch, state)
        assert (((merged.get("characters") or {}).get(slot_id) or {}).get("scene_id") or "") == "scene_llm_keep", merged
        assert conflicts, conflicts

        # 7) Normalize-Passivität: kein story-abgeleitetes Wachstum auf load/normalize/save
        campaign, slot_id = prepare_campaign(main_module, character_name="Matchek")
        campaign = main_module.normalize_campaign(campaign)
        base_state = deepcopy(campaign["state"])
        now = main_module.utc_now()
        campaign.setdefault("turns", []).append(
            {
                "turn_id": "turn_fake_1",
                "turn_number": 1,
                "status": "active",
                "actor": slot_id,
                "player_id": campaign["claims"].get(slot_id),
                "action_type": "story",
                "input_text_display": "Matchek erlernt Schattenmagie.",
                "gm_text_display": "Matchek erhält den Runenkompass und erreicht Eldoria Border.",
                "requests": [],
                "patch": main_module.blank_patch(),
                "created_at": now,
                "updated_at": now,
            }
        )
        campaign = main_module.normalize_campaign(campaign)
        after_state = campaign["state"]
        assert len(after_state.get("items") or {}) == len(base_state.get("items") or {}), "items changed unexpectedly"
        assert len(((after_state.get("map") or {}).get("nodes") or {})) == len(((base_state.get("map") or {}).get("nodes") or {})), "map nodes changed unexpectedly"
        assert len((((after_state.get("characters") or {}).get(slot_id) or {}).get("skills") or {})) == len((((base_state.get("characters") or {}).get(slot_id) or {}).get("skills") or {})), "skills changed unexpectedly"
        before_class = (((base_state.get("characters") or {}).get(slot_id) or {}).get("class_current"))
        after_class = (((after_state.get("characters") or {}).get(slot_id) or {}).get("class_current"))
        assert before_class == after_class, "class changed unexpectedly"

        # 8) Quarantäne-Cap
        campaign, slot_id = prepare_campaign(main_module)
        state = campaign["state"]
        main_module.normalize_extraction_quarantine_meta(state.setdefault("meta", {}))
        state["meta"]["extraction_quarantine"]["max_entries"] = 10
        bulk = []
        for idx in range(35):
            bulk.append(
                {
                    "candidate_id": f"xc_bulk_{idx}",
                    "source": "history",
                    "actor": slot_id,
                    "turn": idx + 1,
                    "entity_type": "item",
                    "operation": "add_item",
                    "label": f"Objekt {idx}",
                    "normalized_key": f"item:bulk:{idx}",
                    "evidence_text": "bulk",
                    "payload": {"n": idx},
                    "confidence": 0.2,
                    "status": "reject",
                    "reason_code": main_module.EXTRACTION_REASON_LOW_CONFIDENCE,
                    "created_at": now,
                }
            )
        main_module.append_extraction_quarantine(state, bulk)
        entries = (((state.get("meta") or {}).get("extraction_quarantine") or {}).get("entries") or [])
        assert len(entries) == 10, len(entries)

        print("OK: Arbeitspaket-2-Prüfungen erfolgreich.")
    finally:
        main_module.call_ollama_schema = original_call_ollama_schema


if __name__ == "__main__":
    main()
