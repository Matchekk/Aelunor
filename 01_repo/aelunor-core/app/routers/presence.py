from typing import Any, Callable, Dict, Optional, Type

from fastapi import APIRouter, Header, Query
from fastapi.responses import StreamingResponse

from app.services import presence_service


def build_presence_router(
    *,
    presence_activity_model: Type[Any],
    presence_service_dependencies: Callable[[], presence_service.PresenceServiceDependencies],
    campaign_event_stream: Callable[[str], Any],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/campaigns/{campaign_id}/events")
    def stream_campaign_events(
        campaign_id: str,
        stream_token: Optional[str] = Query(default=None),
        player_id: Optional[str] = Query(default=None),
        player_token: Optional[str] = Query(default=None),
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> StreamingResponse:
        deps = presence_service_dependencies()
        if stream_token:
            presence_service.authenticate_event_stream_ticket(
                campaign_id=campaign_id,
                stream_token=stream_token,
                deps=deps,
            )
        else:
            # Deprecated compatibility path for legacy/debug clients only.
            # The v1 frontend must use /events/ticket and never place player_token in the EventSource URL.
            auth_player_id = player_id or x_player_id
            auth_player_token = player_token or x_player_token
            presence_service.authenticate_event_stream(
                campaign_id=campaign_id,
                player_id=auth_player_id,
                player_token=auth_player_token,
                deps=deps,
            )
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(campaign_event_stream(campaign_id), media_type="text/event-stream", headers=headers)

    @router.post("/api/campaigns/{campaign_id}/events/ticket")
    def create_stream_ticket(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return presence_service.issue_event_stream_ticket(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=presence_service_dependencies(),
        )

    @router.post("/api/campaigns/{campaign_id}/presence/activity")
    def set_presence_activity(
        campaign_id: str,
        inp: presence_activity_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return presence_service.set_presence_activity(
            campaign_id=campaign_id,
            kind=inp.kind,
            slot_id=inp.slot_id,
            target_turn_id=inp.target_turn_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=presence_service_dependencies(),
        )

    @router.post("/api/campaigns/{campaign_id}/presence/clear")
    def clear_presence_activity(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return presence_service.clear_presence_activity(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=presence_service_dependencies(),
        )

    return router
