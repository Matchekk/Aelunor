import importlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def prepare_campaign(module: Any) -> Dict[str, str]:
    created = module.create_campaign_record("Trace-Test", "Host")
    campaign = created["campaign"]
    campaign_id = campaign["campaign_meta"]["campaign_id"]
    player_id = created["player_id"]
    player_token = created["player_token"]

    slot_id = "slot_1"
    campaign["state"].setdefault("characters", {})
    campaign["state"]["characters"][slot_id] = module.blank_character_state(slot_id)
    campaign.setdefault("claims", {})[slot_id] = player_id
    campaign.setdefault("setup", {}).setdefault("world", {})["completed"] = True
    campaign["setup"].setdefault("characters", {})[slot_id] = module.default_character_setup_node()
    campaign["setup"]["characters"][slot_id]["completed"] = True
    campaign["state"].setdefault("meta", {})["phase"] = "adventure"
    now = module.utc_now()
    campaign["turns"] = [
        {
            "turn_id": "turn_seed",
            "turn_number": 1,
            "status": "active",
            "actor": slot_id,
            "player_id": player_id,
            "action_type": "story",
            "input_text_display": "Seed",
            "gm_text_display": "Seed",
            "requests": [],
            "patch": module.blank_patch(),
            "created_at": now,
            "updated_at": now,
        }
    ]
    module.save_campaign(campaign, reason="seed")
    return {
        "campaign_id": campaign_id,
        "player_id": player_id,
        "player_token": player_token,
        "slot_id": slot_id,
    }


def post_turn(client: TestClient, info: Dict[str, str], text: str = "Testzug") -> Any:
    return client.post(
        f"/api/campaigns/{info['campaign_id']}/turns",
        json={"actor": info["slot_id"], "mode": "TUN", "text": text},
        headers={
            "x-player-id": info["player_id"],
            "x-player-token": info["player_token"],
        },
    )


def main() -> None:
    temp_dir = tempfile.mkdtemp(prefix="isekai_turn_checks_")
    os.environ["DATA_DIR"] = temp_dir

    import app.main as main_module

    main_module = importlib.reload(main_module)
    info = prepare_campaign(main_module)
    client = TestClient(main_module.app)

    original_create_turn_record = main_module.create_turn_record
    original_save_json = main_module.save_json

    try:
        # Case 1: kaputte Modellantwort / JSON_REPAIR_ERROR
        def fake_turn_json_error(**kwargs: Any) -> Dict[str, Any]:
            raise main_module.TurnFlowError(
                error_code=main_module.ERROR_CODE_JSON_REPAIR,
                phase="narrator_json_parse_repair",
                trace_id=str((kwargs.get("trace_ctx") or {}).get("trace_id") or "trace_fake"),
                user_message=main_module.user_message_for_error_code(main_module.ERROR_CODE_JSON_REPAIR),
                cause_class="RuntimeError",
                cause_message="Model returned non-JSON content",
            )

        main_module.create_turn_record = fake_turn_json_error
        response = post_turn(client, info, "Kaputte Antwort")
        assert response.status_code == 500, response.text
        assert response.headers.get("X-Turn-Error-Code") == main_module.ERROR_CODE_JSON_REPAIR, response.headers

        # Case 2: validate-Fehler / SCHEMA_VALIDATION_ERROR
        def fake_turn_validate_error(**kwargs: Any) -> Dict[str, Any]:
            raise main_module.TurnFlowError(
                error_code=main_module.ERROR_CODE_SCHEMA_VALIDATION,
                phase="schema_validation",
                trace_id=str((kwargs.get("trace_ctx") or {}).get("trace_id") or "trace_fake"),
                user_message=main_module.user_message_for_error_code(main_module.ERROR_CODE_SCHEMA_VALIDATION),
                cause_class="ValueError",
                cause_message="unknown field in patch",
            )

        main_module.create_turn_record = fake_turn_validate_error
        response = post_turn(client, info, "Ungültiges Patch")
        assert response.status_code == 500, response.text
        assert response.headers.get("X-Turn-Error-Code") == main_module.ERROR_CODE_SCHEMA_VALIDATION, response.headers

        # Case 3: Persistenzfehler / PERSISTENCE_ERROR
        def fake_turn_ok(**kwargs: Any) -> Dict[str, Any]:
            return {
                "turn_id": "turn_ok",
            }

        def fake_save_json(path: str, payload: Dict[str, Any]) -> None:
            raise OSError("disk full")

        main_module.create_turn_record = fake_turn_ok
        main_module.save_json = fake_save_json
        response = post_turn(client, info, "Persistenzfehler")
        assert response.status_code == 500, response.text
        assert response.headers.get("X-Turn-Error-Code") == main_module.ERROR_CODE_PERSISTENCE, response.headers

        # Case 4: Apply-Fehler / PATCH_APPLY_ERROR
        def fake_turn_apply_error(**kwargs: Any) -> Dict[str, Any]:
            raise main_module.TurnFlowError(
                error_code=main_module.ERROR_CODE_PATCH_APPLY,
                phase="patch_apply",
                trace_id=str((kwargs.get("trace_ctx") or {}).get("trace_id") or "trace_fake"),
                user_message=main_module.user_message_for_error_code(main_module.ERROR_CODE_PATCH_APPLY),
                cause_class="ValueError",
                cause_message="cannot apply patch to unknown scene",
            )

        main_module.create_turn_record = fake_turn_apply_error
        main_module.save_json = original_save_json
        response = post_turn(client, info, "Applyfehler")
        assert response.status_code == 500, response.text
        assert response.headers.get("X-Turn-Error-Code") == main_module.ERROR_CODE_PATCH_APPLY, response.headers

        # Case 5: Erfolgsfall mit trace_id
        main_module.create_turn_record = fake_turn_ok
        response = post_turn(client, info, "Erfolg")
        assert response.status_code == 200, response.text
        body = response.json()
        assert isinstance(body.get("trace_id"), str) and body["trace_id"].startswith("trace_"), body

        print("OK: Fehlerklassifikation + Erfolgsfall mit trace_id sind valide.")
    finally:
        main_module.create_turn_record = original_create_turn_record
        main_module.save_json = original_save_json


if __name__ == "__main__":
    main()
