import os
import secrets
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException

from app.core.ids import hash_secret, make_id, utc_now
from app.serializers.campaign_view import is_host
from app.services.campaigns.party import expected_setup_slots
from app.services.world.state_defaults import default_intro_state


CampaignState = Dict[str, Any]


def intro_state(campaign: CampaignState) -> CampaignState:
    return campaign.setdefault("state", {}).setdefault("meta", {}).setdefault("intro_state", default_intro_state())


def can_start_adventure(campaign: CampaignState) -> bool:
    if not campaign["setup"]["world"].get("completed"):
        return False
    required_slots = expected_setup_slots(campaign)
    setup_chars = (campaign.get("setup", {}).get("characters") or {})
    claims = campaign.get("claims", {}) or {}
    if not required_slots:
        return False
    for slot_name in required_slots:
        if not claims.get(slot_name):
            return False
        if not (setup_chars.get(slot_name) or {}).get("completed"):
            return False
    return True


def default_boards(player_id: Optional[str] = None) -> CampaignState:
    now = utc_now()
    return {
        "plot_essentials": {
            "premise": "",
            "current_goal": "",
            "current_threat": "",
            "active_scene": "",
            "open_loops": [],
            "tone": "",
            "updated_at": now,
            "updated_by": player_id,
        },
        "authors_note": {
            "content": "",
            "updated_at": now,
            "updated_by": player_id,
        },
        "story_cards": [],
        "world_info": [],
        "memory_summary": {
            "content": "Noch keine Zusammenfassung vorhanden.",
            "updated_through_turn": 0,
            "updated_at": now,
        },
        "player_diaries": {},
    }


def new_player(display_name: str) -> Dict[str, str]:
    return {
        "player_id": make_id("player"),
        "player_token": secrets.token_urlsafe(24),
        "display_name": display_name.strip(),
    }


@dataclass(frozen=True)
class CampaignCreatePorts:
    make_join_code: Callable[[], str]
    deep_copy: Callable[[Any], Any]
    initial_state: CampaignState
    default_boards: Callable[..., CampaignState]
    default_setup: Callable[[], CampaignState]
    normalize_campaign: Callable[[CampaignState], CampaignState]
    current_question_id: Callable[[CampaignState], Optional[str]]
    ensure_question_ai_copy: Callable[..., Any]
    remember_recent_story: Callable[[CampaignState], None]
    rebuild_memory_summary: Callable[[CampaignState], None]
    save_campaign: Callable[..., None]


def create_campaign_record(
    title: str,
    display_name: str,
    *,
    legacy_state: Optional[CampaignState] = None,
    imported_turns: Optional[List[CampaignState]] = None,
    legacy_flag: Optional[CampaignState] = None,
    ports: CampaignCreatePorts,
) -> CampaignState:
    identity = new_player(display_name or "Host")
    join_code = ports.make_join_code()
    now = utc_now()
    state = ports.deep_copy(legacy_state if legacy_state is not None else ports.initial_state)
    state.setdefault("characters", {})
    campaign_id = make_id("camp")
    campaign = {
        "campaign_meta": {
            "campaign_id": campaign_id,
            "title": title.strip() or "Neue Aelunor-Kampagne",
            "join_code_hash": hash_secret(join_code),
            "host_player_id": identity["player_id"],
            "created_at": now,
            "updated_at": now,
            "status": "active",
        },
        "players": {
            identity["player_id"]: {
                "display_name": identity["display_name"],
                "player_token_hash": hash_secret(identity["player_token"]),
                "joined_at": now,
                "last_seen_at": now,
            }
        },
        "claims": {},
        "state": state,
        "turns": imported_turns or [],
        "boards": ports.default_boards(identity["player_id"]),
        "setup": ports.default_setup(),
        "board_revisions": [],
        "legacy_migration": legacy_flag,
    }
    campaign.setdefault("state", {}).setdefault("meta", {})["phase"] = "lobby"
    ports.normalize_campaign(campaign)
    first_world_qid = ports.current_question_id(campaign["setup"]["world"])
    if first_world_qid:
        ports.ensure_question_ai_copy(campaign, setup_type="world", question_id=first_world_qid)
    ports.remember_recent_story(campaign)
    ports.rebuild_memory_summary(campaign)
    ports.save_campaign(campaign)
    return {
        "campaign": campaign,
        "join_code": join_code,
        "player_id": identity["player_id"],
        "player_token": identity["player_token"],
    }


@dataclass(frozen=True)
class CampaignStoragePorts:
    data_dir: str
    campaigns_dir: str
    legacy_state_path: str
    ensure_storage_dirs: Callable[..., None]
    list_campaign_ids: Callable[[], List[str]]
    load_json: Callable[[str], CampaignState]
    deep_copy: Callable[[Any], Any]
    make_turn_id: Callable[[], str]
    blank_patch: Callable[[], CampaignState]
    create_campaign_record: Callable[..., CampaignState]


def ensure_campaign_storage(*, ports: CampaignStoragePorts) -> None:
    ports.ensure_storage_dirs(data_dir=ports.data_dir, campaigns_dir=ports.campaigns_dir)
    if ports.list_campaign_ids():
        return
    if not os.path.exists(ports.legacy_state_path):
        return
    legacy_state = ports.load_json(ports.legacy_state_path)
    now = utc_now()
    imported_turns = []
    for index, story in enumerate(legacy_state.get("recent_story", []), start=1):
        snapshot = ports.deep_copy(legacy_state)
        imported_turns.append(
            {
                "turn_id": ports.make_turn_id(),
                "turn_number": index,
                "status": "active",
                "actor": "SYSTEM",
                "player_id": None,
                "action_type": "story",
                "input_text_raw": "Importierte Story",
                "input_text_display": "Importierte Story",
                "gm_text_raw": story,
                "gm_text_display": story,
                "requests": [],
                "patch": ports.blank_patch(),
                "state_before": snapshot,
                "state_after": snapshot,
                "retry_of_turn_id": None,
                "edited_at": None,
                "created_at": now,
                "updated_at": now,
                "edit_history": [],
                "prompt_payload": {"imported": True},
            }
        )
    ports.create_campaign_record(
        "Legacy Campaign",
        "Legacy Host",
        legacy_state=legacy_state,
        imported_turns=imported_turns,
        legacy_flag={"source": "state.json", "migrated_at": now},
    )


@dataclass(frozen=True)
class JoinCodeLookupPorts:
    list_campaign_ids: Callable[[], List[str]]
    campaign_path: Callable[[str], str]
    load_campaign: Callable[[str], CampaignState]


def find_campaign_by_join_code(join_code: str, *, ports: JoinCodeLookupPorts) -> Optional[CampaignState]:
    join_hash = hash_secret(join_code.strip().upper())
    for campaign_id in ports.list_campaign_ids():
        path = ports.campaign_path(campaign_id)
        try:
            with open(path, "r", encoding="utf-8") as f:
                if join_hash not in f.read():
                    continue
        except OSError:
            continue

        campaign = ports.load_campaign(campaign_id)
        if campaign.get("campaign_meta", {}).get("join_code_hash") == join_hash:
            return campaign
    return None


def touch_player(campaign: CampaignState, player_id: str) -> None:
    player = campaign["players"].get(player_id)
    if player:
        player["last_seen_at"] = utc_now()


def authenticate_player(
    campaign: CampaignState,
    player_id: Optional[str],
    player_token: Optional[str],
    *,
    required: bool = True,
) -> Optional[CampaignState]:
    if not player_id or not player_token:
        if required:
            raise HTTPException(status_code=401, detail="Session fehlt oder ist unvollständig.")
        return None
    player = campaign.get("players", {}).get(player_id)
    if not player:
        raise HTTPException(status_code=401, detail="Unbekannter Spieler.")
    if hash_secret(player_token) != player.get("player_token_hash"):
        raise HTTPException(status_code=401, detail="Ungültiger Spieler-Token.")
    touch_player(campaign, player_id)
    return player


def require_host(campaign: CampaignState, player_id: Optional[str]) -> None:
    if not is_host(campaign, player_id):
        raise HTTPException(status_code=403, detail="Nur der Host darf diese Aktion ausführen.")


def require_claim(campaign: CampaignState, player_id: str, actor: str) -> None:
    claimed_player_id = campaign["claims"].get(actor)
    if not claimed_player_id:
        raise HTTPException(status_code=403, detail="Dieser Slot ist nicht geclaimt.")
    if claimed_player_id != player_id:
        raise HTTPException(status_code=403, detail="Du darfst nur deinen geclaimten Slot spielen.")
