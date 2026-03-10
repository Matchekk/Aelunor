import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class TurnServiceDependencies:
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    active_turns: Callable[[CampaignState], Any]
    intro_state: Callable[[CampaignState], Dict[str, Any]]
    require_claim: Callable[[CampaignState, str, str], None]
    new_turn_trace_context: Callable[[str, str, Optional[str]], Dict[str, Any]]
    emit_turn_phase_event: Callable[..., None]
    clear_live_activity: Callable[[str, Optional[str]], None]
    start_blocking_action: Callable[..., None]
    clear_blocking_action: Callable[[str], None]
    create_turn_record: Callable[..., Dict[str, Any]]
    save_campaign: Callable[..., None]
    classify_turn_exception: Callable[..., Any]
    turn_flow_error_cls: type
    remember_recent_story: Callable[[CampaignState], None]
    rebuild_memory_summary: Callable[[CampaignState], None]
    find_turn: Callable[[CampaignState, str], Dict[str, Any]]
    reset_turn_branch: Callable[[CampaignState, Dict[str, Any], str], None]
    utc_now: Callable[[], str]


def create_turn(
    *,
    campaign_id: str,
    actor: str,
    action_type: str,
    content: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: TurnServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    if actor not in campaign["state"]["characters"]:
        raise HTTPException(status_code=400, detail="Unbekannter Slot.")
    if not content.strip():
        raise HTTPException(status_code=400, detail="Leerer Turn ist nicht erlaubt.")
    if campaign["state"]["meta"].get("phase") != "active":
        raise HTTPException(status_code=409, detail="Story-Turns sind erst nach Welt- und Charakter-Setup möglich.")
    if not deps.active_turns(campaign):
        intro = deps.intro_state(campaign)
        if intro.get("status") == "failed":
            raise HTTPException(status_code=409, detail="Der Kampagnenauftakt fehlt noch. Bitte zuerst den Auftakt erneut versuchen.")
        raise HTTPException(status_code=409, detail="Die Geschichte hat noch keinen Auftakt. Bitte warte auf den ersten GM-Text.")

    deps.require_claim(campaign, player_id, actor)
    trace_ctx = deps.new_turn_trace_context(campaign_id, actor, player_id)
    deps.emit_turn_phase_event(trace_ctx, phase="input_accepted", success=True, extra={"action_type": action_type})
    deps.clear_live_activity(campaign_id, player_id)
    blocking_kind = "continue_turn" if content.startswith("Weiter.") else "submit_turn"
    deps.start_blocking_action(campaign, player_id=player_id, kind=blocking_kind, slot_id=actor)
    request_received_ts = time.time()
    try:
        turn = deps.create_turn_record(
            campaign=campaign,
            actor=actor,
            player_id=player_id,
            action_type=action_type,
            content=content,
            request_received_ts=request_received_ts,
            trace_ctx=trace_ctx,
        )
        deps.save_campaign(campaign, reason="turn_created", trace_ctx=trace_ctx)
    except deps.turn_flow_error_cls as exc:
        deps.emit_turn_phase_event(
            trace_ctx,
            phase=exc.phase or str((trace_ctx or {}).get("last_phase") or "turn_internal"),
            success=False,
            error_code=exc.error_code,
            error_class=exc.cause_class,
            message=exc.cause_message[:240],
        )
        raise HTTPException(
            status_code=500,
            detail=exc.to_client_detail(),
            headers={
                "X-Turn-Trace-Id": exc.trace_id,
                "X-Turn-Error-Code": exc.error_code,
            },
        )
    except HTTPException as exc:
        if int(exc.status_code or 500) < 500:
            raise
        classified = deps.classify_turn_exception(
            exc,
            phase=str((trace_ctx or {}).get("last_phase") or "turn_internal"),
            trace_ctx=trace_ctx,
        )
        deps.emit_turn_phase_event(
            trace_ctx,
            phase=classified.phase,
            success=False,
            error_code=classified.error_code,
            error_class=classified.cause_class or exc.__class__.__name__,
            message=(classified.cause_message or str(exc.detail))[:240],
        )
        raise HTTPException(
            status_code=500,
            detail=classified.to_client_detail(),
            headers={
                "X-Turn-Trace-Id": classified.trace_id,
                "X-Turn-Error-Code": classified.error_code,
            },
        )
    except Exception as exc:
        classified = deps.classify_turn_exception(
            exc,
            phase=str((trace_ctx or {}).get("last_phase") or "turn_internal"),
            trace_ctx=trace_ctx,
        )
        deps.emit_turn_phase_event(
            trace_ctx,
            phase=classified.phase,
            success=False,
            error_code=classified.error_code,
            error_class=classified.cause_class or exc.__class__.__name__,
            message=(classified.cause_message or str(exc))[:240],
        )
        raise HTTPException(
            status_code=500,
            detail=classified.to_client_detail(),
            headers={
                "X-Turn-Trace-Id": classified.trace_id,
                "X-Turn-Error-Code": classified.error_code,
            },
        )
    finally:
        deps.clear_blocking_action(campaign_id)
    return {
        "turn_id": turn["turn_id"],
        "trace_id": str((trace_ctx or {}).get("trace_id") or ""),
        "campaign": campaign,
    }


def edit_turn(
    *,
    campaign_id: str,
    turn_id: str,
    input_text_display: str,
    gm_text_display: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: TurnServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    turn = deps.find_turn(campaign, turn_id)
    previous = {
        "input_text_display": turn["input_text_display"],
        "gm_text_display": turn["gm_text_display"],
    }
    turn.setdefault("edit_history", []).append(
        {
            "edited_at": deps.utc_now(),
            "edited_by": player_id,
            "previous": previous,
        }
    )
    turn["input_text_display"] = input_text_display.strip()
    turn["gm_text_display"] = gm_text_display.strip()
    turn["edited_at"] = deps.utc_now()
    turn["updated_at"] = turn["edited_at"]
    deps.remember_recent_story(campaign)
    deps.rebuild_memory_summary(campaign)
    deps.save_campaign(campaign)
    return campaign


def undo_turn(
    *,
    campaign_id: str,
    turn_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: TurnServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    turn = deps.find_turn(campaign, turn_id)
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="undo_turn", slot_id=turn.get("actor"))
    try:
        deps.reset_turn_branch(campaign, turn, "undone")
        deps.save_campaign(campaign, reason="turn_undone")
    finally:
        deps.clear_blocking_action(campaign_id)
    return campaign


def retry_turn(
    *,
    campaign_id: str,
    turn_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: TurnServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    turn = deps.find_turn(campaign, turn_id)
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="retry_turn", slot_id=turn.get("actor"))
    try:
        deps.reset_turn_branch(campaign, turn, "superseded")
        new_turn = deps.create_turn_record(
            campaign=campaign,
            actor=turn["actor"],
            player_id=turn.get("player_id"),
            action_type=turn["action_type"],
            content=turn["input_text_raw"],
            retry_of_turn_id=turn["turn_id"],
        )
        new_turn["input_text_display"] = turn.get("input_text_display", new_turn["input_text_display"])
        deps.save_campaign(campaign, reason="turn_retried")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        deps.clear_blocking_action(campaign_id)
    return {
        "turn_id": new_turn["turn_id"],
        "campaign": campaign,
    }

