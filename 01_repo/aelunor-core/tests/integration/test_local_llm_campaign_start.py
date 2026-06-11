from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import local_llm_campaign_helpers as llm


pytestmark = [pytest.mark.integration, pytest.mark.local_llm]


def test_local_ollama_campaign_start_and_three_playable_turns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if os.getenv(llm.LOCAL_LLM_ENV) != "1":
        pytest.skip(f"Setze {llm.LOCAL_LLM_ENV}=1, um den lokalen Ollama/Gemma-Live-Test auszuführen.")

    data_dir = tmp_path / "aelunor-local-llm-data"
    assert data_dir.resolve().is_relative_to(tmp_path.resolve())

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_URL", llm.OLLAMA_URL)
    monkeypatch.setenv("OLLAMA_MODEL", llm.OLLAMA_MODEL)
    # Player turns carry the full history context; on consumer hardware gemma
    # needs more than 420s per call once retries/rewrites kick in.
    monkeypatch.setenv("OLLAMA_TIMEOUT_SEC", os.getenv("OLLAMA_TIMEOUT_SEC", "600"))
    monkeypatch.setenv("OLLAMA_NUM_CTX", os.getenv("AELUNOR_LOCAL_LLM_NUM_CTX", "32768"))
    monkeypatch.setenv("ENABLE_SETUP_AI_COPY", "0")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost,::1")

    llm.install_no_external_requests_guard(monkeypatch)
    llm.require_local_ollama_model()
    llm.reload_app_modules_for_local_env()

    from app import main
    from app.services import live_state_service, presence_service, state_engine

    live_state_service.LIVE_STATE_REGISTRY.clear()
    presence_service.clear_stream_tickets()
    state_engine.ensure_campaign_storage()

    with TestClient(main.app) as client:
        created = llm.create_campaign(client)
        campaign_id = created["campaign_id"]
        player_id = created["player_id"]
        headers = {"X-Player-Id": player_id, "X-Player-Token": created["player_token"]}

        saved_path = data_dir / "campaigns" / f"{campaign_id}.json"
        assert saved_path.is_file()
        assert str(saved_path.resolve()).startswith(str(data_dir.resolve()))

        world_preview = llm.post_ok(
            client,
            f"/api/campaigns/{campaign_id}/setup/world/random",
            headers=headers,
            json={"mode": "all"},
        )
        world_answers = llm.preview_answers(world_preview)
        llm.replace_answer(world_answers, "player_count", selected="1")
        world_apply = llm.post_ok(
            client,
            f"/api/campaigns/{campaign_id}/setup/world/random/apply",
            headers=headers,
            json={"preview_answers": world_answers},
        )
        assert world_apply["completed"] is True

        claim_payload = llm.post_ok(client, f"/api/campaigns/{campaign_id}/slots/{llm.SLOT_ID}/claim", headers=headers)
        assert claim_payload["campaign"]["claims"][llm.SLOT_ID] == player_id

        character_preview = llm.post_ok(
            client,
            f"/api/campaigns/{campaign_id}/slots/{llm.SLOT_ID}/setup/random",
            headers=headers,
            json={"mode": "all"},
        )
        character_apply = llm.post_ok(
            client,
            f"/api/campaigns/{campaign_id}/slots/{llm.SLOT_ID}/setup/random/apply",
            headers=headers,
            json={"preview_answers": llm.preview_answers(character_preview)},
        )
        assert character_apply["completed"] is True
        assert character_apply["started_adventure"] is True

        campaign = character_apply["campaign"]
        llm.assert_campaign_state_valid(campaign, player_id=player_id, expected_turn=1)
        intro_text = llm.latest_narration(campaign)
        llm.assert_playable_narration(intro_text, label="initiale KI-Narration")
        print(f"\n[local_llm] intro: {llm.compact(intro_text)}")

        raw_after_intro = state_engine.load_campaign(campaign_id)
        assert len(raw_after_intro.get("turns", [])) == 1
        assert raw_after_intro["turns"][0]["turn_number"] == 1
        assert raw_after_intro["turns"][0]["state_after"]["meta"]["turn"] == 1

        turn_narrations = []
        previous_turn_count = len(raw_after_intro.get("turns", []))
        for index, action in enumerate(llm.PLAYER_ACTIONS, start=1):
            turn_payload = llm.post_ok(
                client,
                f"/api/campaigns/{campaign_id}/turns",
                headers=headers,
                json={"actor": llm.SLOT_ID, "mode": "do", "text": action},
            )
            campaign = turn_payload["campaign"]
            expected_turn = index + 1
            llm.assert_campaign_state_valid(campaign, player_id=player_id, expected_turn=expected_turn)

            narration = llm.latest_narration(campaign)
            llm.assert_playable_narration(narration, label=f"Turn {index}")
            llm.assert_response_reacts_to_action(narration, index=index)
            turn_narrations.append(narration)
            print(f"[local_llm] turn {index}: {llm.compact(narration)}")

            raw_campaign = state_engine.load_campaign(campaign_id)
            turns = raw_campaign.get("turns", [])
            assert len(turns) == previous_turn_count + 1
            last_turn = turns[-1]
            assert last_turn["turn_id"] == turn_payload["turn_id"]
            assert last_turn["turn_number"] == expected_turn
            assert last_turn["actor"] == llm.SLOT_ID
            assert last_turn["player_id"] == player_id
            assert last_turn["input_text_raw"] == action
            assert last_turn["gm_text_display"].strip() == narration.strip()
            assert last_turn["state_before"]["meta"]["turn"] == expected_turn - 1
            assert last_turn["state_after"]["meta"]["turn"] == expected_turn
            assert raw_campaign["state"]["meta"]["turn"] == expected_turn
            previous_turn_count = len(turns)

        llm.assert_distinct_turn_narrations(turn_narrations)

        reloaded = llm.get_ok(client, f"/api/campaigns/{campaign_id}", headers=headers)
        llm.assert_campaign_state_valid(reloaded, player_id=player_id, expected_turn=4)
        assert len(state_engine.load_campaign(campaign_id).get("turns", [])) == 4
