from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class ClaimServiceDependencies:
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    player_claim: Callable[[CampaignState, Optional[str]], Optional[str]]
    current_question_id: Callable[[Dict[str, Any]], str]
    ensure_question_ai_copy: Callable[..., None]
    save_campaign: Callable[..., None]
    is_host: Callable[[CampaignState, Optional[str]], bool]


def claim_slot(
    *,
    campaign_id: str,
    slot_name: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: ClaimServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    if not campaign["setup"]["world"].get("completed", False):
        raise HTTPException(status_code=409, detail="Slots können erst nach dem Welt-Setup geclaimt werden.")
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    current_owner = campaign["claims"].get(slot_name)
    if current_owner and current_owner != player_id:
        raise HTTPException(status_code=409, detail="Dieser Slot ist bereits geclaimt.")
    existing_claim = deps.player_claim(campaign, player_id)
    if existing_claim and existing_claim != slot_name:
        raise HTTPException(status_code=409, detail="Du hast bereits einen anderen Slot geclaimt.")
    campaign["claims"][slot_name] = player_id
    qid = deps.current_question_id(campaign["setup"]["characters"].get(slot_name, {}))
    if qid:
        deps.ensure_question_ai_copy(campaign, setup_type="character", question_id=qid, slot_name=slot_name)
    deps.save_campaign(campaign)
    return campaign


def takeover_slot(
    *,
    campaign_id: str,
    slot_name: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: ClaimServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    if not campaign["setup"]["world"].get("completed", False):
        raise HTTPException(status_code=409, detail="Slots können erst nach dem Welt-Setup übernommen werden.")
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    existing_claim = deps.player_claim(campaign, player_id)
    if existing_claim == slot_name:
        return campaign
    if existing_claim:
        campaign["claims"][existing_claim] = None
    campaign["claims"][slot_name] = player_id
    qid = deps.current_question_id(campaign["setup"]["characters"].get(slot_name, {}))
    if qid:
        deps.ensure_question_ai_copy(campaign, setup_type="character", question_id=qid, slot_name=slot_name)
    deps.save_campaign(campaign)
    return campaign


def unclaim_slot(
    *,
    campaign_id: str,
    slot_name: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: ClaimServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    current_owner = campaign["claims"].get(slot_name)
    if current_owner != player_id and not deps.is_host(campaign, player_id):
        raise HTTPException(status_code=403, detail="Du darfst diesen Claim nicht lösen.")
    campaign["claims"][slot_name] = None
    deps.save_campaign(campaign)
    return campaign

