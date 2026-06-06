from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.serializers import campaign_view as campaign_view_serializer
from app.services.boards.public import build_public_boards as _build_public_boards
from app.services.setup.answers import extract_text_answer
from app.services.state_basics import is_slot_id
from app.services.campaigns.party import (
    active_party,
    available_slots,
    build_party_overview,
    campaign_slots,
    compact_conditions,
    display_name_for_slot,
    expected_setup_slots,
    player_claim,
    public_player,
    setup_slot_statuses,
)


CampaignState = Dict[str, Any]


def active_turns(campaign: CampaignState) -> List[CampaignState]:
    return campaign_view_serializer.active_turns(campaign)


def is_host(campaign: CampaignState, player_id: Optional[str]) -> bool:
    return campaign_view_serializer.is_host(campaign, player_id)


def is_campaign_player(campaign: CampaignState, player_id: Optional[str]) -> bool:
    return campaign_view_serializer.is_campaign_player(campaign, player_id)


@dataclass(frozen=True)
class CampaignViewPorts:
    normalize_campaign: Callable[[CampaignState], CampaignState]
    deep_copy: Callable[[Any], Any]
    derive_scene_name: Callable[[CampaignState, str], str]
    normalize_character_state: Callable[..., CampaignState]
    blank_character_state: Callable[[str], CampaignState]
    normalize_class_current: Callable[[Any], Any]
    next_character_xp_for_level: Callable[[int], int]
    resource_name_for_character: Callable[[CampaignState, CampaignState], str]
    clamp: Callable[[int, int, int], int]
    normalize_world_time: Callable[[CampaignState], CampaignState]
    build_world_question_state: Callable[[CampaignState, Optional[str]], Optional[CampaignState]]
    build_character_question_state: Callable[[CampaignState, str], Optional[CampaignState]]
    progress_payload: Callable[[CampaignState], CampaignState]
    setup_global_progress: Callable[[CampaignState], CampaignState]
    setup_chapter_config: Callable[[str], Dict[str, Any]]
    setup_question_chapter_key: Callable[[str, str], str]
    setup_chapter_progress: Callable[[CampaignState, str, str], CampaignState]
    setup_phase_display: Callable[[str], str]
    setup_summary_preview: Callable[..., Any]
    normalize_requests_payload: Callable[[Any], Any]
    blank_patch: Callable[[], CampaignState]
    public_turn: Callable[[CampaignState, CampaignState, Optional[str]], CampaignState]
    live_snapshot: Callable[[str], CampaignState]


def public_turn(turn: CampaignState, campaign: CampaignState, viewer_id: Optional[str], *, ports: CampaignViewPorts) -> CampaignState:
    return campaign_view_serializer.public_turn(
        turn,
        campaign,
        viewer_id,
        display_name_for_slot=display_name_for_slot,
        is_slot_id=is_slot_id,
        normalize_requests_payload=ports.normalize_requests_payload,
        blank_patch=ports.blank_patch,
        is_campaign_player_fn=is_campaign_player,
    )


def build_viewer_context(campaign: CampaignState, player_id: Optional[str], *, ports: CampaignViewPorts) -> CampaignState:
    player = campaign.get("players", {}).get(player_id or "")
    claimed_slot = player_claim(campaign, player_id)
    pending_setup_question = None
    current_phase = str(campaign["state"]["meta"].get("phase") or "")
    if not campaign["setup"]["world"].get("completed", False) and current_phase in {"lobby", "world_setup"}:
        pending_setup_question = ports.build_world_question_state(campaign, player_id)
    elif claimed_slot and current_phase in {"character_setup_open", "ready_to_start"}:
        pending_setup_question = ports.build_character_question_state(campaign, claimed_slot)
    return {
        "player_id": player_id,
        "display_name": player.get("display_name") if player else None,
        "is_host": is_host(campaign, player_id),
        "claimed_slot_id": claimed_slot,
        "claimed_character": claimed_slot,
        "phase": current_phase,
        "needs_world_setup": not campaign["setup"]["world"].get("completed", False),
        "needs_character_setup": (
            current_phase in {"character_setup_open", "ready_to_start"}
            and bool(claimed_slot)
            and not campaign["setup"]["characters"].get(claimed_slot, {}).get("completed", False)
        ),
        "pending_setup_question": pending_setup_question,
    }


def build_setup_runtime(campaign: CampaignState, viewer_id: Optional[str], *, ports: CampaignViewPorts) -> CampaignState:
    current_phase = str(campaign["state"]["meta"].get("phase") or "")
    claimed_slot = player_claim(campaign, viewer_id)
    world_node = campaign["setup"]["world"]
    world_question_state = ports.build_world_question_state(campaign, viewer_id)
    world_chapter_key = ports.setup_question_chapter_key("world", (world_question_state or {}).get("question", {}).get("question_id", ""))
    world_chapter_cfg = ports.setup_chapter_config("world").get(world_chapter_key, {})
    world_slots = setup_slot_statuses(campaign)
    world_ready_count = sum(1 for entry in world_slots if entry.get("status") == "ready")
    world_total_count = len(world_slots)
    character_state = ports.build_character_question_state(campaign, claimed_slot) if claimed_slot else None
    character_node = (((campaign.get("setup") or {}).get("characters") or {}).get(claimed_slot or "")) or {}
    char_chapter_key = ports.setup_question_chapter_key("character", (character_state or {}).get("question", {}).get("question_id", ""))
    char_chapter_cfg = ports.setup_chapter_config("character").get(char_chapter_key, {})
    world_chapters = ports.setup_chapter_config("world")
    character_chapters = ports.setup_chapter_config("character")
    return {
        "phase": current_phase,
        "phase_display": ports.setup_phase_display(current_phase),
        "world": {
            "completed": world_node.get("completed", False),
            "progress": ports.progress_payload(world_node),
            "global_progress": ports.setup_global_progress(world_node),
            "next_question": world_question_state,
            "chapter_key": world_chapter_key,
            "chapter_label": world_chapter_cfg.get("label", "Welt"),
            "chapter_index": list(world_chapters.keys()).index(world_chapter_key) + 1 if world_chapter_key in world_chapters else 1,
            "chapter_total": len(world_chapters),
            "chapter_progress": ports.setup_chapter_progress(world_node, "world", world_chapter_key),
            "is_review_step": bool(world_node.get("completed")) or (
                bool((world_question_state or {}).get("progress", {}).get("total"))
                and int((world_question_state or {}).get("progress", {}).get("step", 0) or 0)
                >= int((world_question_state or {}).get("progress", {}).get("total", 0) or 0)
            ),
            "summary_preview": ports.setup_summary_preview(campaign, "world"),
            "slot_statuses": world_slots,
            "ready_counter": {"ready": world_ready_count, "total": world_total_count},
        },
        "claimed_slot_id": claimed_slot,
        "character": (
            {
                **(character_state or {}),
                "global_progress": ports.setup_global_progress(character_node),
                "chapter_key": char_chapter_key,
                "chapter_label": char_chapter_cfg.get("label", "Figur"),
                "chapter_index": list(character_chapters.keys()).index(char_chapter_key) + 1 if char_chapter_key in character_chapters else 1,
                "chapter_total": len(character_chapters),
                "chapter_progress": ports.setup_chapter_progress(character_node, "character", char_chapter_key),
                "is_review_step": bool((character_node.get("completed"))) or (
                    bool((character_state or {}).get("progress", {}).get("total"))
                    and int((character_state or {}).get("progress", {}).get("step", 0) or 0)
                    >= int((character_state or {}).get("progress", {}).get("total", 0) or 0)
                ),
                "summary_preview": ports.setup_summary_preview(campaign, "character", claimed_slot),
            }
            if claimed_slot
            else None
        ),
        "slot_statuses": world_slots,
        "ready_counter": {"ready": world_ready_count, "total": world_total_count},
        "is_ready_to_start": current_phase == "ready_to_start",
    }


def setup_summary_preview(campaign: CampaignState, setup_type: str, slot_name: Optional[str] = None) -> CampaignState:
    if setup_type == "world":
        summary = ((campaign.get("setup") or {}).get("world") or {}).get("summary") or {}
        if not summary:
            answers = (((campaign.get("setup") or {}).get("world") or {}).get("answers") or {})
            summary = {
                "theme": extract_text_answer(answers.get("theme")),
                "tone": extract_text_answer(answers.get("tone")),
                "resource_name": extract_text_answer(answers.get("resource_name")),
                "central_conflict": extract_text_answer(answers.get("central_conflict")),
            }
        return {
            "theme": summary.get("theme", ""),
            "tone": summary.get("tone", ""),
            "resource_name": summary.get("resource_name", ""),
            "campaign_length": summary.get("campaign_length", ""),
            "central_conflict": summary.get("central_conflict", ""),
            "world_structure": summary.get("world_structure", ""),
        }
    setup_node = (((campaign.get("setup") or {}).get("characters") or {}).get(slot_name or "")) or {}
    summary = setup_node.get("summary") or {}
    answers = setup_node.get("answers") or {}
    return {
        "display_name": summary.get("display_name") or extract_text_answer(answers.get("char_name")),
        "focus": summary.get("current_focus") or extract_text_answer(answers.get("current_focus")),
        "class_start_mode": summary.get("class_start_mode") or extract_text_answer(answers.get("class_start_mode")),
        "first_goal": summary.get("first_goal") or extract_text_answer(answers.get("first_goal")),
        "strength": summary.get("strength") or extract_text_answer(answers.get("strength")),
        "weakness": summary.get("weakness") or extract_text_answer(answers.get("weakness")),
    }


def build_public_boards(campaign: CampaignState, viewer_id: Optional[str], *, ports: CampaignViewPorts) -> CampaignState:
    return _build_public_boards(campaign, viewer_id, copy_value=ports.deep_copy)


def build_campaign_view(campaign: CampaignState, viewer_id: Optional[str], *, ports: CampaignViewPorts) -> CampaignState:
    dependencies = campaign_view_serializer.CampaignViewDependencies(
        normalize_campaign=ports.normalize_campaign,
        deep_copy=ports.deep_copy,
        build_setup_runtime=lambda value, viewer: build_setup_runtime(value, viewer, ports=ports),
        available_slots=lambda value: available_slots(value, ports=ports),
        active_party=active_party,
        display_name_for_slot=display_name_for_slot,
        normalize_world_time=ports.normalize_world_time,
        build_public_boards=lambda value, viewer: build_public_boards(value, viewer, ports=ports),
        active_turns=active_turns,
        public_turn=ports.public_turn,
        build_party_overview=lambda value: build_party_overview(value, ports=ports),
        campaign_slots=campaign_slots,
        public_player=public_player,
        build_viewer_context=lambda value, viewer: build_viewer_context(value, viewer, ports=ports),
        live_snapshot=ports.live_snapshot,
    )
    return campaign_view_serializer.build_campaign_view(campaign, viewer_id, deps=dependencies)
