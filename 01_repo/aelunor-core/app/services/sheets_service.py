from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class SheetsServiceDependencies:
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    build_party_overview: Callable[[CampaignState], Any]
    build_character_sheet_view: Callable[[CampaignState, str], Dict[str, Any]]
    build_npc_sheet_view: Callable[[CampaignState, str], Dict[str, Any]]


def get_party_overview(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SheetsServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    return {"party_overview": deps.build_party_overview(campaign)}


def get_character_sheet(
    *,
    campaign_id: str,
    slot_name: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SheetsServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    if slot_name not in campaign.get("state", {}).get("characters", {}):
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden.")
    return deps.build_character_sheet_view(campaign, slot_name)


def get_npc_sheet(
    *,
    campaign_id: str,
    npc_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: SheetsServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    return deps.build_npc_sheet_view(campaign, npc_id)

