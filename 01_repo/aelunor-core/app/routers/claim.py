from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Header

from app.services import claim_service


def build_claim_router(
    *,
    claim_service_dependencies: Callable[[], claim_service.ClaimServiceDependencies],
    build_campaign_view: Callable[[Dict[str, Any], Optional[str]], Dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/campaigns/{campaign_id}/slots/{slot_name}/claim")
    def claim_slot(
        campaign_id: str,
        slot_name: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = claim_service.claim_slot(
            campaign_id=campaign_id,
            slot_name=slot_name,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=claim_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/slots/{slot_name}/takeover")
    def takeover_slot(
        campaign_id: str,
        slot_name: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = claim_service.takeover_slot(
            campaign_id=campaign_id,
            slot_name=slot_name,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=claim_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/slots/{slot_name}/unclaim")
    def unclaim_slot(
        campaign_id: str,
        slot_name: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = claim_service.unclaim_slot(
            campaign_id=campaign_id,
            slot_name=slot_name,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=claim_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    return router

