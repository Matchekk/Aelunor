from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Header

from app.services import sheets_service


def build_sheets_router(
    *,
    sheets_service_dependencies: Callable[[], sheets_service.SheetsServiceDependencies],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/campaigns/{campaign_id}/party-overview")
    def get_party_overview(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return sheets_service.get_party_overview(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=sheets_service_dependencies(),
        )

    @router.get("/api/campaigns/{campaign_id}/characters/{slot_name}")
    def get_character_sheet(
        campaign_id: str,
        slot_name: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return sheets_service.get_character_sheet(
            campaign_id=campaign_id,
            slot_name=slot_name,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=sheets_service_dependencies(),
        )

    @router.get("/api/campaigns/{campaign_id}/npcs/{npc_id}")
    def get_npc_sheet(
        campaign_id: str,
        npc_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return sheets_service.get_npc_sheet(
            campaign_id=campaign_id,
            npc_id=npc_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=sheets_service_dependencies(),
        )

    return router

