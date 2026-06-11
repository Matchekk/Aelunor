from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from app.config.runtime import MAX_PLAYERS


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class WorldSummaryBoardPorts:
    make_id: Callable[[str], str]
    utc_now: Callable[[], str]


@dataclass(frozen=True)
class DynamicSlotPorts:
    slot_id: Callable[[int], str]
    blank_character_state: Callable[[str], CampaignState]
    default_character_setup_node: Callable[[], CampaignState]


def default_character_setup_node(*, build_character_question_queue: Callable[[], Any]) -> CampaignState:
    return {
        "completed": False,
        "question_queue": build_character_question_queue(),
        "answers": {},
        "summary": {},
        "raw_transcript": [],
        "question_runtime": {},
    }


def apply_world_summary_to_boards(
    campaign: CampaignState,
    updated_by: Optional[str],
    *,
    ports: WorldSummaryBoardPorts,
) -> None:
    summary = campaign["setup"]["world"]["summary"]
    boards = campaign.setdefault("boards", {})
    if not isinstance(boards, dict):
        boards = {}
        campaign["boards"] = boards

    boards["plot_essentials"] = {
        "premise": summary.get("premise", ""),
        "current_goal": "",
        "current_threat": summary.get("central_conflict", ""),
        "active_scene": "",
        "open_loops": [],
        "tone": summary.get("tone", ""),
        "updated_at": ports.utc_now(),
        "updated_by": updated_by,
    }
    authors_lines = [
        f"Theme: {summary.get('theme', '')}",
        f"Ton: {summary.get('tone', '')}",
        f"Schwierigkeit: {summary.get('difficulty', '')}",
        f"Wertebereich: {summary.get('attribute_range_label', '')}",
        f"Kraftquelle: {summary.get('resource_name', '')}",
        f"Tod: {summary.get('death_policy', '')}",
        f"Ressourcen: {summary.get('resource_scarcity', '')}",
        f"Heilung: {summary.get('healing_frequency', '')}",
        f"Monsterdichte: {summary.get('monsters_density', '')}",
        f"Erzählrahmen: {summary.get('ruleset', '')}",
        f"Outcome-Modell: {summary.get('outcome_model', '')}",
        f"Weltstruktur: {summary.get('world_structure', '')}",
        f"Weltgesetze: {', '.join(summary.get('world_laws', []))}",
        f"Zentraler Konflikt: {summary.get('central_conflict', '')}",
        f"Tabus/Notizen: {summary.get('taboos', '')}",
    ]
    boards["authors_note"] = {
        "content": "\n".join(line for line in authors_lines if line.split(": ", 1)[1]),
        "updated_at": ports.utc_now(),
        "updated_by": updated_by,
    }
    boards["world_info"] = _world_info_entries(summary, updated_by, ports=ports)


def _world_info_entries(
    summary: CampaignState,
    updated_by: Optional[str],
    *,
    ports: WorldSummaryBoardPorts,
) -> list[CampaignState]:
    entries = [
        _world_info_entry("Weltstruktur", "world", summary.get("world_structure", ""), ["setup"], updated_by, ports=ports),
        _world_info_entry("Wertebereich", "rule", summary.get("attribute_range_label", ""), ["setup", "rule"], updated_by, ports=ports),
        _world_info_entry("Kraftquelle", "rule", summary.get("resource_name", ""), ["setup", "rule"], updated_by, ports=ports),
        _world_info_entry("Weltgesetze", "rule", ", ".join(summary.get("world_laws", [])), ["setup"], updated_by, ports=ports),
        _world_info_entry("Zentraler Konflikt", "conflict", summary.get("central_conflict", ""), ["setup"], updated_by, ports=ports),
    ]
    factions = summary.get("factions", [])
    if not isinstance(factions, list):
        factions = []
    for faction in factions:
        if not isinstance(faction, dict):
            continue
        entries.append(
            _world_info_entry(
                faction.get("name", "Fraktion"),
                "faction",
                f"Ziel: {faction.get('goal', '')} Methoden: {faction.get('methods', '')}".strip(),
                ["setup", "faction"],
                updated_by,
                ports=ports,
            )
        )
    return entries


def _world_info_entry(
    title: str,
    category: str,
    content: str,
    tags: list[str],
    updated_by: Optional[str],
    *,
    ports: WorldSummaryBoardPorts,
) -> CampaignState:
    return {
        "entry_id": ports.make_id("world"),
        "title": title,
        "category": category,
        "content": content,
        "tags": tags,
        "updated_at": ports.utc_now(),
        "updated_by": updated_by,
    }


def initialize_dynamic_slots(campaign: CampaignState, player_count: int, *, ports: DynamicSlotPorts) -> None:
    player_count = max(1, min(MAX_PLAYERS, int(player_count)))
    campaign["claims"] = {}
    campaign["state"]["characters"] = {}
    for index in range(1, player_count + 1):
        current_slot = ports.slot_id(index)
        campaign["claims"][current_slot] = None
        campaign["state"]["characters"][current_slot] = ports.blank_character_state(current_slot)
        campaign["setup"]["characters"].setdefault(current_slot, ports.default_character_setup_node())
