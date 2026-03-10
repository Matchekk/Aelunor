from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class PresenceServiceDependencies:
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    set_live_activity: Callable[..., Dict[str, Any]]
    clear_live_activity: Callable[[str, Optional[str]], None]
    live_snapshot: Callable[[str], Dict[str, Any]]


def set_presence_activity(
    *,
    campaign_id: str,
    kind: str,
    slot_id: Optional[str],
    target_turn_id: Optional[str],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: PresenceServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    activity = deps.set_live_activity(
        campaign,
        player_id,
        kind,
        slot_id=slot_id,
        target_turn_id=target_turn_id,
    )
    return {"ok": True, "activity": activity, "live": deps.live_snapshot(campaign_id)}


def clear_presence_activity(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: PresenceServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.clear_live_activity(campaign_id, player_id)
    return {"ok": True, "live": deps.live_snapshot(campaign_id)}


def authenticate_event_stream(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: PresenceServiceDependencies,
) -> None:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)

