from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class BoardsServiceDependencies:
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    require_host: Callable[[CampaignState, Optional[str]], None]
    save_campaign: Callable[..., None]
    utc_now: Callable[[], str]
    deep_copy: Callable[[Any], Any]
    log_board_revision: Callable[..., None]
    default_player_diary_entry: Callable[[str, str], Dict[str, Any]]
    make_id: Callable[[str], str]


def patch_plot_essentials(
    *,
    campaign_id: str,
    payload: Dict[str, Any],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: BoardsServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    board = campaign["boards"]["plot_essentials"]
    previous = deps.deep_copy(board)
    for key, value in payload.items():
        board[key] = value
    board["updated_at"] = deps.utc_now()
    board["updated_by"] = player_id
    deps.log_board_revision(campaign, board="plot_essentials", op="patch", updated_by=player_id, previous=previous, current=deps.deep_copy(board))
    deps.save_campaign(campaign)
    return campaign


def patch_authors_note(
    *,
    campaign_id: str,
    content: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: BoardsServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    board = campaign["boards"]["authors_note"]
    previous = deps.deep_copy(board)
    board["content"] = content
    board["updated_at"] = deps.utc_now()
    board["updated_by"] = player_id
    deps.log_board_revision(campaign, board="authors_note", op="patch", updated_by=player_id, previous=previous, current=deps.deep_copy(board))
    deps.save_campaign(campaign)
    return campaign


def patch_player_diary(
    *,
    campaign_id: str,
    diary_player_id: str,
    content: str,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: BoardsServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    if diary_player_id != player_id:
        raise HTTPException(status_code=403, detail="Du darfst nur dein eigenes Tagebuch bearbeiten.")
    diaries = campaign["boards"].setdefault("player_diaries", {})
    diary = diaries.setdefault(
        diary_player_id,
        deps.default_player_diary_entry(diary_player_id, campaign.get("players", {}).get(diary_player_id, {}).get("display_name", "")),
    )
    previous = deps.deep_copy(diary)
    diary["display_name"] = campaign.get("players", {}).get(diary_player_id, {}).get("display_name", diary.get("display_name", ""))
    diary["content"] = content
    diary["updated_at"] = deps.utc_now()
    diary["updated_by"] = player_id
    deps.log_board_revision(campaign, board="player_diaries", op="patch", updated_by=player_id, previous=previous, current=deps.deep_copy(diary), item_id=diary_player_id)
    deps.save_campaign(campaign, reason="player_diary_updated")
    return campaign


def create_story_card(
    *,
    campaign_id: str,
    title: str,
    kind: str,
    content: str,
    tags: Any,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: BoardsServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    card = {
        "card_id": deps.make_id("card"),
        "title": title.strip(),
        "kind": kind,
        "content": content.strip(),
        "tags": tags,
        "archived": False,
        "updated_at": deps.utc_now(),
        "updated_by": player_id,
    }
    campaign["boards"]["story_cards"].append(card)
    deps.log_board_revision(campaign, board="story_cards", op="create", updated_by=player_id, previous=None, current=deps.deep_copy(card), item_id=card["card_id"])
    deps.save_campaign(campaign)
    return campaign


def patch_story_card(
    *,
    campaign_id: str,
    card_id: str,
    payload: Dict[str, Any],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: BoardsServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    for card in campaign["boards"]["story_cards"]:
        if card["card_id"] == card_id:
            previous = deps.deep_copy(card)
            for key, value in payload.items():
                card[key] = value
            card["updated_at"] = deps.utc_now()
            card["updated_by"] = player_id
            deps.log_board_revision(campaign, board="story_cards", op="patch", updated_by=player_id, previous=previous, current=deps.deep_copy(card), item_id=card_id)
            deps.save_campaign(campaign)
            return campaign
    raise HTTPException(status_code=404, detail="Story Card nicht gefunden.")


def create_world_info(
    *,
    campaign_id: str,
    title: str,
    category: str,
    content: str,
    tags: Any,
    player_id: Optional[str],
    player_token: Optional[str],
    deps: BoardsServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    entry = {
        "entry_id": deps.make_id("world"),
        "title": title.strip(),
        "category": category.strip(),
        "content": content.strip(),
        "tags": tags,
        "updated_at": deps.utc_now(),
        "updated_by": player_id,
    }
    campaign["boards"]["world_info"].append(entry)
    deps.log_board_revision(campaign, board="world_info", op="create", updated_by=player_id, previous=None, current=deps.deep_copy(entry), item_id=entry["entry_id"])
    deps.save_campaign(campaign)
    return campaign


def patch_world_info(
    *,
    campaign_id: str,
    entry_id: str,
    payload: Dict[str, Any],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: BoardsServiceDependencies,
) -> CampaignState:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    deps.require_host(campaign, player_id)
    for entry in campaign["boards"]["world_info"]:
        if entry["entry_id"] == entry_id:
            previous = deps.deep_copy(entry)
            for key, value in payload.items():
                entry[key] = value
            entry["updated_at"] = deps.utc_now()
            entry["updated_by"] = player_id
            deps.log_board_revision(campaign, board="world_info", op="patch", updated_by=player_id, previous=previous, current=deps.deep_copy(entry), item_id=entry_id)
            deps.save_campaign(campaign)
            return campaign
    raise HTTPException(status_code=404, detail="World-Info-Eintrag nicht gefunden.")

