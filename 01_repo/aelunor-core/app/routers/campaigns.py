from typing import Any, Callable, Dict, Optional, Type

from fastapi import APIRouter, Header

from app.services import campaign_service


def build_campaigns_router(
    *,
    campaign_create_model: Type[Any],
    join_campaign_model: Type[Any],
    campaign_meta_patch_model: Type[Any],
    time_advance_model: Type[Any],
    class_unlock_model: Type[Any],
    faction_join_model: Type[Any],
    campaign_service_dependencies: Callable[[], campaign_service.CampaignServiceDependencies],
    build_campaign_view: Callable[[Dict[str, Any], Optional[str]], Dict[str, Any]],
    public_turn: Callable[[Dict[str, Any], Dict[str, Any], Optional[str]], Dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/campaigns")
    def create_campaign(inp: campaign_create_model) -> Dict[str, Any]:
        result = campaign_service.create_campaign(
            title=inp.title,
            display_name=inp.display_name,
            deps=campaign_service_dependencies(),
        )
        campaign = result["campaign"]
        return {
            "campaign_id": campaign["campaign_meta"]["campaign_id"],
            "join_code": result["join_code"],
            "player_id": result["player_id"],
            "player_token": result["player_token"],
            "campaign": build_campaign_view(campaign, result["player_id"]),
        }

    @router.post("/api/campaigns/join")
    def join_campaign(inp: join_campaign_model) -> Dict[str, Any]:
        result = campaign_service.join_campaign(
            join_code=inp.join_code,
            display_name=inp.display_name,
            deps=campaign_service_dependencies(),
        )
        return {
            "campaign_id": result["campaign_id"],
            "join_code": result["join_code"],
            "player_id": result["player_id"],
            "player_token": result["player_token"],
            "campaign_summary": result["campaign_summary"],
            "campaign": build_campaign_view(result["campaign"], result["player_id"]),
        }

    @router.get("/api/campaigns/{campaign_id}")
    def get_campaign(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = campaign_service.get_campaign(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=campaign_service_dependencies(),
        )
        return build_campaign_view(campaign, x_player_id)

    @router.post("/api/campaigns/{campaign_id}/intro/retry")
    def retry_campaign_intro(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = campaign_service.retry_campaign_intro(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=campaign_service_dependencies(),
        )
        return {
            "turn": public_turn(result["turn"], result["campaign"], x_player_id) if result["turn"] else None,
            "intro_state": result["intro_state"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
        }

    @router.post("/api/campaigns/{campaign_id}/time/advance")
    def advance_campaign_time(
        campaign_id: str,
        inp: time_advance_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = campaign_service.advance_campaign_time(
            campaign_id=campaign_id,
            days=inp.days,
            time_of_day=inp.time_of_day,
            reason=inp.reason,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=campaign_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/characters/{slot_name}/class/unlock")
    def unlock_character_class(
        campaign_id: str,
        slot_name: str,
        inp: class_unlock_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = campaign_service.unlock_character_class(
            campaign_id=campaign_id,
            slot_name=slot_name,
            class_id=inp.class_id,
            class_name=inp.class_name,
            visual_modifiers=inp.visual_modifiers,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=campaign_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/characters/{slot_name}/factions/join")
    def join_character_faction(
        campaign_id: str,
        slot_name: str,
        inp: faction_join_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = campaign_service.join_character_faction(
            campaign_id=campaign_id,
            slot_name=slot_name,
            faction_id=inp.faction_id,
            name=inp.name,
            rank=inp.rank,
            visual_modifiers=inp.visual_modifiers,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=campaign_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.patch("/api/campaigns/{campaign_id}/meta")
    def patch_campaign_meta(
        campaign_id: str,
        inp: campaign_meta_patch_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = campaign_service.patch_campaign_meta(
            campaign_id=campaign_id,
            title=inp.title,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=campaign_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.get("/api/campaigns/{campaign_id}/export")
    def export_campaign(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return campaign_service.export_campaign(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=campaign_service_dependencies(),
        )

    @router.delete("/api/campaigns/{campaign_id}")
    def delete_campaign(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return campaign_service.delete_campaign(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=campaign_service_dependencies(),
        )

    return router

