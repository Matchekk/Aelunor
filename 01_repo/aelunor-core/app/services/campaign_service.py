import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class CampaignServiceDependencies:
    ensure_campaign_storage: Callable[[], None]
    create_campaign_record: Callable[[str, str], Dict[str, Any]]
    find_campaign_by_join_code: Callable[[str], Optional[CampaignState]]
    new_player: Callable[[str], Dict[str, str]]
    utc_now: Callable[[], str]
    hash_secret: Callable[[str], str]
    save_campaign: Callable[..., None]
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    require_host: Callable[[CampaignState, Optional[str]], None]
    deep_copy: Callable[[Any], Any]
    intro_state: Callable[[CampaignState], Dict[str, Any]]
    active_turns: Callable[[CampaignState], Any]
    can_start_adventure: Callable[[CampaignState], bool]
    clear_live_activity: Callable[[str, Optional[str]], None]
    start_blocking_action: Callable[..., None]
    clear_blocking_action: Callable[[str], None]
    try_generate_adventure_intro: Callable[[CampaignState], Optional[Dict[str, Any]]]
    apply_world_time_advance: Callable[[Dict[str, Any], int, Optional[str]], None]
    rebuild_all_character_derived: Callable[[CampaignState], None]
    append_character_change_events: Callable[[Dict[str, Any], Dict[str, Any]], None]
    normalize_class_current: Callable[[Any], Any]
    rebuild_character_derived: Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any]], None]
    normalize_world_time: Callable[[Dict[str, Any]], Dict[str, Any]]
    campaign_path: Callable[[str], str]
    clear_live_campaign_state: Callable[[str], None]


def create_campaign(*, title: str, display_name: str, deps: CampaignServiceDependencies) -> Dict[str, Any]:
    deps.ensure_campaign_storage()
    return deps.create_campaign_record(title, display_name)


def join_campaign(*, join_code: str, display_name: str, deps: CampaignServiceDependencies) -> Dict[str, Any]:
    deps.ensure_campaign_storage()
    campaign = deps.find_campaign_by_join_code(join_code)
    if not campaign:
        raise HTTPException(status_code=404, detail="Join-Code nicht gefunden.")
    identity = deps.new_player(display_name)
    now = deps.utc_now()
    campaign["players"][identity["player_id"]] = {
        "display_name": identity["display_name"],
        "player_token_hash": deps.hash_secret(identity["player_token"]),
        "joined_at": now,
        "last_seen_at": now,
    }
    deps.save_campaign(campaign)
    return {
        "campaign": campaign,
        "campaign_id": campaign["campaign_meta"]["campaign_id"],
        "join_code": join_code.strip().upper(),
        "player_id": identity["player_id"],
        "player_token": identity["player_token"],
        "campaign_summary": {
            "title": campaign["campaign_meta"]["title"],
            "status": campaign["campaign_meta"]["status"],
        },
    }


def get_campaign(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: CampaignServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    return campaign


def retry_campaign_intro(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: CampaignServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    intro = deps.intro_state(campaign)
    if deps.active_turns(campaign):
        intro["status"] = "generated"
        if not intro.get("generated_turn_id"):
            intro["generated_turn_id"] = deps.active_turns(campaign)[0]["turn_id"]
        deps.save_campaign(campaign)
        return {
            "turn": None,
            "intro_state": deps.deep_copy(intro),
            "campaign": campaign,
        }
    if not deps.can_start_adventure(campaign):
        raise HTTPException(
            status_code=409,
            detail="Der Kampagnenauftakt ist noch nicht bereit. Schließe zuerst Welt-Setup und alle benoetigten Charaktere ab.",
        )
    if intro.get("status") not in ("pending", "failed", "idle"):
        raise HTTPException(status_code=409, detail="Der Kampagnenauftakt wurde bereits erzeugt.")
    deps.clear_live_activity(campaign_id, player_id)
    deps.start_blocking_action(campaign, player_id=player_id, kind="generate_intro")
    try:
        turn = deps.try_generate_adventure_intro(campaign)
        deps.save_campaign(campaign, reason="intro_retry")
    finally:
        deps.clear_blocking_action(campaign_id)
    return {
        "turn": turn,
        "intro_state": deps.deep_copy(deps.intro_state(campaign)),
        "campaign": campaign,
    }


def advance_campaign_time(
    *,
    campaign_id: str,
    days: int,
    time_of_day: Optional[str],
    reason: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: CampaignServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    state_before = deps.deep_copy(campaign["state"])
    deps.apply_world_time_advance(campaign["state"], days, time_of_day)
    deps.rebuild_all_character_derived(campaign)
    deps.append_character_change_events(state_before, campaign["state"], turn_number=int(campaign["state"]["meta"].get("turn", 0) or 0))
    if reason.strip():
        campaign["state"].setdefault("events", []).append(f"Zeit vergeht: +{days} Tage ({reason.strip()}).")
    deps.save_campaign(campaign)
    return campaign


def unlock_character_class(
    *,
    campaign_id: str,
    slot_name: str,
    class_id: str,
    class_name: Optional[str],
    visual_modifiers: Any,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: CampaignServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    if slot_name not in campaign.get("state", {}).get("characters", {}):
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden.")
    state_before = deps.deep_copy(campaign["state"])
    character = campaign["state"]["characters"][slot_name]
    character["class_current"] = deps.normalize_class_current(
        {
            "id": class_id,
            "name": class_name or class_id,
            "rank": "F",
            "level": 1,
            "level_max": 10,
            "xp": 0,
            "xp_next": 100,
            "affinity_tags": [],
            "description": "",
            "visual_modifiers": deps.deep_copy(visual_modifiers),
            "ascension": {"status": "none", "quest_id": None, "requirements": [], "result_hint": None},
        }
    )
    deps.rebuild_character_derived(character, campaign["state"].get("items", {}), deps.normalize_world_time(campaign["state"]["meta"]))
    deps.append_character_change_events(state_before, campaign["state"], turn_number=int(campaign["state"]["meta"].get("turn", 0) or 0))
    deps.save_campaign(campaign)
    return campaign


def join_character_faction(
    *,
    campaign_id: str,
    slot_name: str,
    faction_id: str,
    name: str,
    rank: str,
    visual_modifiers: Any,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: CampaignServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    if slot_name not in campaign.get("state", {}).get("characters", {}):
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden.")
    state_before = deps.deep_copy(campaign["state"])
    character = campaign["state"]["characters"][slot_name]
    memberships = character.setdefault("faction_memberships", [])
    existing = next((entry for entry in memberships if entry.get("faction_id") == faction_id), None)
    faction_payload = {
        "faction_id": faction_id,
        "name": name,
        "rank": rank,
        "joined_at_turn": int(campaign["state"]["meta"].get("turn", 0) or 0),
        "active": True,
        "visual_modifiers": deps.deep_copy(visual_modifiers),
    }
    if existing:
        existing.update(faction_payload)
    else:
        memberships.append(faction_payload)
    deps.rebuild_character_derived(character, campaign["state"].get("items", {}), deps.normalize_world_time(campaign["state"]["meta"]))
    deps.append_character_change_events(state_before, campaign["state"], turn_number=int(campaign["state"]["meta"].get("turn", 0) or 0))
    deps.save_campaign(campaign)
    return campaign


def patch_campaign_meta(
    *,
    campaign_id: str,
    title: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: CampaignServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    campaign["campaign_meta"]["title"] = title.strip() or "Unbenannte Session"
    deps.save_campaign(campaign)
    return campaign


def export_campaign(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: CampaignServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    return campaign


def delete_campaign(
    *,
    campaign_id: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: CampaignServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    path = deps.campaign_path(campaign_id)
    if os.path.exists(path):
        os.remove(path)
    deps.clear_live_campaign_state(campaign_id)
    return {"ok": True, "campaign_id": campaign_id}

