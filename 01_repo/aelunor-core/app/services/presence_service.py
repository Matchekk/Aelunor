from dataclasses import dataclass
import secrets
import threading
import time
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]
STREAM_TICKET_TTL_SEC = 120

_STREAM_TICKET_LOCK = threading.Lock()
_STREAM_TICKETS: Dict[str, Dict[str, Any]] = {}


@dataclass(frozen=True)
class PresenceServiceDependencies:
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    set_live_activity: Callable[..., Dict[str, Any]]
    clear_live_activity: Callable[[str, Optional[str]], None]
    live_snapshot: Callable[[str], Dict[str, Any]]


def _cleanup_stream_tickets_locked(now: Optional[float] = None) -> None:
    current_time = time.time() if now is None else now
    expired = [
        token
        for token, ticket in _STREAM_TICKETS.items()
        if float(ticket.get("expires_at_ts") or 0) <= current_time
    ]
    for token in expired:
        _STREAM_TICKETS.pop(token, None)


def clear_stream_tickets() -> None:
    with _STREAM_TICKET_LOCK:
        _STREAM_TICKETS.clear()


def create_stream_ticket(*, campaign_id: str, player_id: str) -> Dict[str, Any]:
    token = secrets.token_urlsafe(32)
    expires_at_ts = time.time() + STREAM_TICKET_TTL_SEC
    with _STREAM_TICKET_LOCK:
        _cleanup_stream_tickets_locked()
        _STREAM_TICKETS[token] = {
            "campaign_id": campaign_id,
            "player_id": player_id,
            "expires_at_ts": expires_at_ts,
        }
    return {"stream_token": token, "expires_in_sec": STREAM_TICKET_TTL_SEC}


def validate_stream_ticket(*, campaign_id: str, stream_token: Optional[str]) -> str:
    if not stream_token:
        raise HTTPException(status_code=401, detail="Stream-Ticket fehlt.")
    with _STREAM_TICKET_LOCK:
        _cleanup_stream_tickets_locked()
        ticket = _STREAM_TICKETS.get(stream_token)
        if not ticket:
            raise HTTPException(status_code=401, detail="Stream-Ticket ist ungültig oder abgelaufen.")
        if ticket.get("campaign_id") != campaign_id:
            raise HTTPException(status_code=401, detail="Stream-Ticket gehört nicht zu dieser Kampagne.")
        return str(ticket.get("player_id") or "")


def _player_is_host(campaign: CampaignState, player_id: Optional[str]) -> bool:
    return bool(player_id) and campaign.get("campaign_meta", {}).get("host_player_id") == player_id


def _validate_presence_slot(campaign: CampaignState, player_id: Optional[str], slot_id: Optional[str]) -> None:
    if not slot_id:
        return
    claims = campaign.get("claims") or {}
    if slot_id not in claims:
        raise HTTPException(status_code=403, detail="Presence-Slot ist nicht Teil dieser Kampagne.")
    if _player_is_host(campaign, player_id):
        return
    if claims.get(slot_id) != player_id:
        raise HTTPException(status_code=403, detail="Presence-Slot gehört nicht zu diesem Spieler.")


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
    _validate_presence_slot(campaign, player_id, slot_id)
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


def issue_event_stream_ticket(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: PresenceServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    return create_stream_ticket(campaign_id=campaign_id, player_id=str(player_id or ""))


def authenticate_event_stream_ticket(
    *,
    campaign_id: str,
    stream_token: Optional[str],
    deps: PresenceServiceDependencies,
) -> str:
    player_id = validate_stream_ticket(campaign_id=campaign_id, stream_token=stream_token)
    campaign = deps.load_campaign(campaign_id)
    if player_id not in (campaign.get("players") or {}):
        raise HTTPException(status_code=401, detail="Stream-Ticket-Spieler ist nicht mehr Teil der Kampagne.")
    return player_id
