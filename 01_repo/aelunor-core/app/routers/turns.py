from typing import Any, Callable, Dict, Optional, Type

from fastapi import APIRouter, Header, HTTPException

from app.services import turn_service


def build_turns_router(
    *,
    turn_create_model: Type[Any],
    turn_edit_model: Type[Any],
    turn_service_dependencies: Callable[[], turn_service.TurnServiceDependencies],
    build_campaign_view: Callable[[Dict[str, Any], Optional[str]], Dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/campaigns/{campaign_id}/turns")
    def create_turn(
        campaign_id: str,
        inp: turn_create_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        actor = inp.actor.strip()
        try:
            action_type = inp.normalized_action_type()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        content = inp.normalized_content().strip()
        result = turn_service.create_turn(
            campaign_id=campaign_id,
            actor=actor,
            action_type=action_type,
            content=content,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=turn_service_dependencies(),
        )
        return {
            "turn_id": result["turn_id"],
            "trace_id": result["trace_id"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
        }

    @router.patch("/api/campaigns/{campaign_id}/turns/{turn_id}")
    def edit_turn(
        campaign_id: str,
        turn_id: str,
        inp: turn_edit_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = turn_service.edit_turn(
            campaign_id=campaign_id,
            turn_id=turn_id,
            input_text_display=inp.input_text_display,
            gm_text_display=inp.gm_text_display,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=turn_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/turns/{turn_id}/undo")
    def undo_turn(
        campaign_id: str,
        turn_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = turn_service.undo_turn(
            campaign_id=campaign_id,
            turn_id=turn_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=turn_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/turns/{turn_id}/retry")
    def retry_turn(
        campaign_id: str,
        turn_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = turn_service.retry_turn(
            campaign_id=campaign_id,
            turn_id=turn_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=turn_service_dependencies(),
        )
        return {
            "turn_id": result["turn_id"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
        }

    return router

