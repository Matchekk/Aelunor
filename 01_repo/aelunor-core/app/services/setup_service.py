from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class SetupServiceDependencies:
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    require_host: Callable[[CampaignState, Optional[str]], None]
    is_host: Callable[[CampaignState, Optional[str]], bool]
    current_question_id: Callable[[Dict[str, Any]], Optional[str]]
    clear_live_activity: Callable[[str, Optional[str]], None]
    start_blocking_action: Callable[..., None]
    clear_blocking_action: Callable[[str], None]
    ensure_question_ai_copy: Callable[..., None]
    save_campaign: Callable[..., None]
    build_world_question_state: Callable[[CampaignState, Optional[str]], Optional[Dict[str, Any]]]
    build_character_question_state: Callable[[CampaignState, str], Optional[Dict[str, Any]]]
    progress_payload: Callable[[Dict[str, Any]], Dict[str, Any]]
    validate_answer_payload: Callable[[Dict[str, Any], Dict[str, Any]], Any]
    store_setup_answer: Callable[..., None]
    build_random_setup_preview: Callable[..., List[Dict[str, Any]]]
    apply_random_setup_preview: Callable[..., int]
    finalize_world_setup: Callable[[CampaignState, Optional[str]], None]
    finalize_character_setup: Callable[[CampaignState, str], Optional[Dict[str, Any]]]
    deep_copy: Callable[[Any], Any]
    build_world_summary: Callable[[CampaignState], Dict[str, Any]]
    build_character_summary: Callable[[CampaignState, str], Dict[str, Any]]
    normalize_world_settings: Callable[[Any], Dict[str, Any]]
    apply_world_summary_to_boards: Callable[[CampaignState, Optional[str]], None]
    apply_character_summary_to_state: Callable[[CampaignState, str], None]
    campaign_slots: Callable[[CampaignState], Any]
    target_turns_defaults: Dict[str, Any]
    pacing_profile_defaults: Dict[str, Any]
    world_question_map: Dict[str, Dict[str, Any]]
    character_question_map: Dict[str, Dict[str, Any]]


def _require_character_setup_access(
    *,
    campaign: CampaignState,
    slot_name: str,
    player_id: Optional[str],
    is_host: Callable[[CampaignState, Optional[str]], bool],
) -> None:
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    claimed_owner = campaign["claims"].get(slot_name)
    if claimed_owner != player_id and not is_host(campaign, player_id):
        raise HTTPException(status_code=403, detail="Nur der claimgende Spieler oder Host darf dieses Profil bauen.")


def _character_setup_payload(*, campaign: CampaignState, slot_name: str, state: Optional[Dict[str, Any]], progress_payload: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    setup_node = campaign["setup"]["characters"][slot_name]
    return {
        "completed": setup_node.get("completed", False),
        "question": state["question"] if state else None,
        "progress": state["progress"] if state else progress_payload(setup_node),
    }


def _world_setup_payload(
    *,
    campaign: CampaignState,
    state: Optional[Dict[str, Any]],
    progress_payload: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    setup_node = campaign["setup"]["world"]
    return {
        "completed": setup_node.get("completed", False),
        "question": state["question"] if state else None,
        "progress": state["progress"] if state else progress_payload(setup_node),
    }


def next_world_setup_question(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    campaign["state"]["meta"]["phase"] = "world_setup"
    qid = deps.current_question_id(campaign["setup"]["world"])
    if qid:
        deps.clear_live_activity(campaign_id, player_id)
        deps.start_blocking_action(campaign, player_id=player_id, kind="building_world")
        try:
            deps.ensure_question_ai_copy(campaign, setup_type="world", question_id=qid)
            deps.save_campaign(campaign, reason="world_setup_next")
        finally:
            deps.clear_blocking_action(campaign_id)
    setup_state = deps.build_world_question_state(campaign, player_id)
    payload = _world_setup_payload(campaign=campaign, state=setup_state, progress_payload=deps.progress_payload)
    payload["campaign"] = campaign
    return payload


def answer_world_setup_question(
    *,
    campaign_id: str,
    question_id: str,
    answer_payload: Dict[str, Any],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    campaign["state"]["meta"]["phase"] = "world_setup"
    question = deps.world_question_map.get(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Unbekannte Weltfrage.")
    setup_node = campaign["setup"]["world"]
    stored = deps.validate_answer_payload(question, answer_payload)
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="building_world")
    try:
        deps.store_setup_answer(setup_node, question, stored, player_id=player_id, source="manual")
        next_qid = deps.current_question_id(setup_node)
        if not next_qid:
            deps.finalize_world_setup(campaign, player_id)
        else:
            deps.ensure_question_ai_copy(campaign, setup_type="world", question_id=next_qid)
        deps.save_campaign(campaign, reason="world_setup_answer")
    finally:
        deps.clear_blocking_action(campaign_id)
    updated = deps.load_campaign(campaign_id)
    next_state = deps.build_world_question_state(updated, player_id)
    payload = _world_setup_payload(campaign=updated, state=next_state, progress_payload=deps.progress_payload)
    payload["campaign"] = updated
    return payload


def randomize_world_setup_question(
    *,
    campaign_id: str,
    mode: str,
    question_id: Optional[str],
    preview_answers: Optional[List[Any]],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    campaign["state"]["meta"]["phase"] = "world_setup"
    setup_node = campaign["setup"]["world"]
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="world_randomize")
    try:
        generated_preview_answers = deps.build_random_setup_preview(
            campaign,
            setup_node,
            deps.world_question_map,
            setup_type="world",
            player_id=player_id,
            mode=mode,
            question_id=question_id,
            preview_answers=preview_answers,
        )
    finally:
        deps.clear_blocking_action(campaign_id)
    return {
        "mode": mode,
        "question_id": question_id,
        "preview_answers": generated_preview_answers,
        "randomized_count": len(generated_preview_answers),
    }


def apply_world_setup_random_preview(
    *,
    campaign_id: str,
    preview_answers: List[Any],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    campaign["state"]["meta"]["phase"] = "world_setup"
    setup_node = campaign["setup"]["world"]
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="world_randomize")
    try:
        applied_count = deps.apply_random_setup_preview(
            campaign,
            setup_node,
            deps.world_question_map,
            preview_answers,
            player_id=player_id,
        )
        next_qid = deps.current_question_id(setup_node)
        if not next_qid:
            deps.finalize_world_setup(campaign, player_id)
        else:
            deps.ensure_question_ai_copy(campaign, setup_type="world", question_id=next_qid)
        deps.save_campaign(campaign, reason="world_setup_random_apply")
    finally:
        deps.clear_blocking_action(campaign_id)
    updated = deps.load_campaign(campaign_id)
    next_state = deps.build_world_question_state(updated, player_id)
    payload = _world_setup_payload(campaign=updated, state=next_state, progress_payload=deps.progress_payload)
    payload["campaign"] = updated
    payload["randomized_count"] = applied_count
    return payload


def next_character_setup_question(
    *,
    campaign_id: str,
    slot_name: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    _require_character_setup_access(campaign=campaign, slot_name=slot_name, player_id=player_id, is_host=deps.is_host)
    qid = deps.current_question_id(campaign["setup"]["characters"][slot_name])
    if qid:
        deps.clear_live_activity(campaign_id, player_id)
        deps.start_blocking_action(campaign, player_id=player_id, kind="building_character", slot_id=slot_name)
        try:
            deps.ensure_question_ai_copy(campaign, setup_type="character", question_id=qid, slot_name=slot_name)
            deps.save_campaign(campaign, reason="character_setup_next")
        finally:
            deps.clear_blocking_action(campaign_id)
    state = deps.build_character_question_state(campaign, slot_name)
    payload = _character_setup_payload(campaign=campaign, slot_name=slot_name, state=state, progress_payload=deps.progress_payload)
    payload["campaign"] = campaign
    return payload


def answer_character_setup_question(
    *,
    campaign_id: str,
    slot_name: str,
    question_id: str,
    answer_payload: Dict[str, Any],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    _require_character_setup_access(campaign=campaign, slot_name=slot_name, player_id=player_id, is_host=deps.is_host)
    if campaign["state"]["meta"].get("phase") == "world_setup":
        raise HTTPException(status_code=409, detail="Das Welt-Setup muss zuerst abgeschlossen werden.")
    question = deps.character_question_map.get(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Unbekannte Charakterfrage.")
    setup_node = campaign["setup"]["characters"][slot_name]
    stored = deps.validate_answer_payload(question, answer_payload)
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="building_character", slot_id=slot_name)
    try:
        deps.store_setup_answer(setup_node, question, stored, player_id=player_id, source="manual")
        next_qid = deps.current_question_id(setup_node)
        started_turn = None
        if not next_qid:
            started_turn = deps.finalize_character_setup(campaign, slot_name)
        else:
            deps.ensure_question_ai_copy(campaign, setup_type="character", question_id=next_qid, slot_name=slot_name)
        deps.save_campaign(campaign, reason="character_setup_answer")
    finally:
        deps.clear_blocking_action(campaign_id)
    updated = deps.load_campaign(campaign_id)
    state = deps.build_character_question_state(updated, slot_name)
    payload = _character_setup_payload(campaign=updated, slot_name=slot_name, state=state, progress_payload=deps.progress_payload)
    payload["started_adventure"] = bool(started_turn)
    payload["turn_id"] = started_turn["turn_id"] if started_turn else None
    payload["campaign"] = updated
    return payload


def randomize_character_setup_question(
    *,
    campaign_id: str,
    slot_name: str,
    mode: str,
    question_id: Optional[str],
    preview_answers: Optional[List[Any]],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    _require_character_setup_access(campaign=campaign, slot_name=slot_name, player_id=player_id, is_host=deps.is_host)
    if campaign["state"]["meta"].get("phase") == "world_setup":
        raise HTTPException(status_code=409, detail="Das Welt-Setup muss zuerst abgeschlossen werden.")
    setup_node = campaign["setup"]["characters"][slot_name]
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="character_randomize", slot_id=slot_name)
    try:
        generated_preview_answers = deps.build_random_setup_preview(
            campaign,
            setup_node,
            deps.character_question_map,
            setup_type="character",
            player_id=player_id,
            slot_name=slot_name,
            mode=mode,
            question_id=question_id,
            preview_answers=preview_answers,
        )
    finally:
        deps.clear_blocking_action(campaign_id)
    return {
        "mode": mode,
        "question_id": question_id,
        "preview_answers": generated_preview_answers,
        "randomized_count": len(generated_preview_answers),
    }


def apply_character_setup_random_preview(
    *,
    campaign_id: str,
    slot_name: str,
    preview_answers: List[Any],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    _require_character_setup_access(campaign=campaign, slot_name=slot_name, player_id=player_id, is_host=deps.is_host)
    if campaign["state"]["meta"].get("phase") == "world_setup":
        raise HTTPException(status_code=409, detail="Das Welt-Setup muss zuerst abgeschlossen werden.")
    setup_node = campaign["setup"]["characters"][slot_name]
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="character_randomize", slot_id=slot_name)
    try:
        applied_count = deps.apply_random_setup_preview(
            campaign,
            setup_node,
            deps.character_question_map,
            preview_answers,
            player_id=player_id,
        )
        next_qid = deps.current_question_id(setup_node)
        started_turn = None
        if not next_qid:
            started_turn = deps.finalize_character_setup(campaign, slot_name)
        else:
            deps.ensure_question_ai_copy(campaign, setup_type="character", question_id=next_qid, slot_name=slot_name)
        deps.save_campaign(campaign, reason="character_setup_random_apply")
    finally:
        deps.clear_blocking_action(campaign_id)
    updated = deps.load_campaign(campaign_id)
    state = deps.build_character_question_state(updated, slot_name)
    payload = _character_setup_payload(campaign=updated, slot_name=slot_name, state=state, progress_payload=deps.progress_payload)
    payload["started_adventure"] = bool(started_turn)
    payload["turn_id"] = started_turn["turn_id"] if started_turn else None
    payload["campaign"] = updated
    payload["randomized_count"] = applied_count
    return payload


def finalize_setup(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SetupServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    if campaign["setup"]["world"]["answers"]:
        campaign["setup"]["world"]["summary"] = deps.build_world_summary(campaign)
        campaign.setdefault("state", {}).setdefault("world", {}).setdefault("settings", {})
        campaign["state"]["world"]["settings"].update(
            {
                "resource_name": campaign["setup"]["world"]["summary"].get("resource_name", "Aether"),
                "consequence_severity": campaign["setup"]["world"]["summary"].get("consequence_severity", "mittel"),
                "progression_speed": campaign["setup"]["world"]["summary"].get("progression_speed", "normal"),
                "evolution_cost_policy": campaign["setup"]["world"]["summary"].get("evolution_cost_policy", "leicht"),
                "offclass_xp_multiplier": campaign["setup"]["world"]["summary"].get("offclass_xp_multiplier", 0.7),
                "onclass_xp_multiplier": campaign["setup"]["world"]["summary"].get("onclass_xp_multiplier", 1.0),
                "campaign_length": campaign["setup"]["world"]["summary"].get("campaign_length", "medium"),
                "target_turns": deps.deep_copy(campaign["setup"]["world"]["summary"].get("target_turns") or deps.target_turns_defaults),
                "pacing_profile": deps.deep_copy(campaign["setup"]["world"]["summary"].get("pacing_profile") or deps.pacing_profile_defaults),
            }
        )
        campaign["state"]["world"]["settings"] = deps.normalize_world_settings(campaign["state"]["world"].get("settings") or {})
        deps.apply_world_summary_to_boards(campaign, player_id)
    for slot_name in deps.campaign_slots(campaign):
        if campaign["setup"]["characters"].get(slot_name, {}).get("answers"):
            campaign["setup"]["characters"][slot_name]["summary"] = deps.build_character_summary(campaign, slot_name)
            deps.apply_character_summary_to_state(campaign, slot_name)
    deps.save_campaign(campaign)
    return campaign
