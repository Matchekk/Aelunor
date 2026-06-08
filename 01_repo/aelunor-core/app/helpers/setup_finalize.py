import re
from typing import Any, Dict, Optional


CampaignState = Dict[str, Any]


def _coerce_player_count(value: Any, *, default: int = 1) -> int:
    """Best-effort parser for setup player count to avoid finalize-time 500s."""
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            # OverflowError: int(float('inf')); ValueError: int(float('nan'))
            return default
    text = str(value or "").strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        match = re.search(r"\d+", text)
        if not match:
            return default
        try:
            return int(match.group(0))
        except (TypeError, ValueError):
            return default


def build_world_summary(campaign: CampaignState, *, deps: Any) -> Dict[str, Any]:
    answers = campaign["setup"]["world"]["answers"]
    theme = deps.extract_text_answer(answers.get("theme"))
    tone = deps.extract_text_answer(answers.get("tone"))
    difficulty = deps.extract_text_answer(answers.get("difficulty"))
    death_possible = bool(answers.get("death_possible", True))
    death_policy = "Charaktertod mÃ¶glich" if death_possible else "Kein permanenter Charaktertod"
    world_structure = deps.extract_text_answer(answers.get("world_structure"))
    world_laws = []
    laws_answer = answers.get("world_laws")
    if isinstance(laws_answer, dict):
        world_laws.extend(laws_answer.get("selected", []))
        world_laws.extend(laws_answer.get("other_values", []))
    central_conflict = deps.extract_text_answer(answers.get("central_conflict"))
    factions = deps.parse_factions(deps.extract_text_answer(answers.get("factions")))
    player_count = _coerce_player_count(deps.extract_text_answer(answers.get("player_count")), default=1)
    attribute_range = deps.parse_attribute_range(answers.get("attribute_range"))
    summary = deps.normalize_answer_summary_defaults()
    resource_name = deps.normalize_resource_name(
        deps.extract_text_answer(answers.get("resource_name")) or summary.get("resource_name", "Aether"),
        "Aether",
    )
    campaign_length = deps.normalize_campaign_length_choice(
        deps.extract_text_answer(answers.get("campaign_length")) or summary.get("campaign_length", "medium")
    )
    summary.update(
        {
            "theme": theme,
            "premise": central_conflict or theme,
            "tone": tone,
            "difficulty": difficulty,
            "death_policy": death_policy,
            "death_possible": death_possible,
            "ruleset": deps.normalize_ruleset_choice(answers.get("ruleset")),
            "outcome_model": deps.extract_text_answer(answers.get("outcome_model")),
            "world_structure": world_structure,
            "world_laws": world_laws,
            "central_conflict": central_conflict,
            "factions": factions,
            "taboos": deps.extract_text_answer(answers.get("taboos")),
            "player_count": max(1, min(deps.max_players, player_count)),
            "resource_scarcity": deps.extract_text_answer(answers.get("resource_scarcity")),
            "healing_frequency": deps.extract_text_answer(answers.get("healing_frequency")),
            "monsters_density": deps.extract_text_answer(answers.get("monsters_density")),
            "attribute_range_label": attribute_range["label"],
            "attribute_range_min": attribute_range["min"],
            "attribute_range_max": attribute_range["max"],
            "resource_name": resource_name,
            "consequence_severity": "hoch" if deps.normalized_eval_text(difficulty) in {"brutal", "hardcore"} else "mittel",
            "progression_speed": "normal",
            "evolution_cost_policy": "leicht",
            "offclass_xp_multiplier": 0.7,
            "onclass_xp_multiplier": 1.0,
            "campaign_length": campaign_length,
            "target_turns": deps.deep_copy(deps.target_turns_defaults),
            "pacing_profile": deps.deep_copy(deps.pacing_profile_defaults),
        }
    )
    return summary


def build_character_summary(campaign: CampaignState, slot_name: str, *, deps: Any) -> Dict[str, Any]:
    answers = campaign["setup"]["characters"][slot_name]["answers"]
    tags = []
    tags_answer = answers.get("personality_tags")
    if isinstance(tags_answer, dict):
        tags.extend(tags_answer.get("selected", []))
        tags.extend(tags_answer.get("other_values", []))
    return {
        "display_name": deps.extract_text_answer(answers.get("char_name")),
        "gender": deps.extract_text_answer(answers.get("char_gender")),
        "age_bucket": deps.extract_text_answer(answers.get("char_age")),
        "earth_life": deps.extract_text_answer(answers.get("earth_life")),
        "personality_tags": tags,
        "background_tags": deps.parse_lines(deps.extract_text_answer(answers.get("earth_life")))[:3],
        "strength": deps.extract_text_answer(answers.get("strength")),
        "weakness": deps.extract_text_answer(answers.get("weakness")),
        "class_start_mode": deps.extract_text_answer(answers.get("class_start_mode")),
        "class_seed": deps.extract_text_answer(answers.get("class_seed")),
        "class_custom_name": deps.extract_text_answer(answers.get("class_custom_name")),
        "class_custom_description": deps.extract_text_answer(answers.get("class_custom_description")),
        "class_custom_tags": deps.parse_lines(deps.extract_text_answer(answers.get("class_custom_tags"))),
        "current_focus": deps.extract_text_answer(answers.get("current_focus")),
        "first_goal": deps.extract_text_answer(answers.get("first_goal")),
        "isekai_price": deps.extract_text_answer(answers.get("isekai_price")),
        "earth_items": deps.parse_earth_items(deps.extract_text_answer(answers.get("earth_items"))),
        "signature_item": deps.extract_text_answer(answers.get("signature_item")),
    }


def finalize_world_setup(campaign: CampaignState, player_id: Optional[str], *, deps: Any) -> None:
    setup_node = campaign["setup"]["world"]
    setup_node["completed"] = True
    setup_node["summary"] = build_world_summary(campaign, deps=deps)
    campaign.setdefault("state", {}).setdefault("world", {}).setdefault("settings", {})
    campaign["state"]["world"]["settings"].update(
        {
            "resource_name": setup_node["summary"].get("resource_name", "Aether"),
            "consequence_severity": setup_node["summary"].get("consequence_severity", "mittel"),
            "progression_speed": setup_node["summary"].get("progression_speed", "normal"),
            "evolution_cost_policy": setup_node["summary"].get("evolution_cost_policy", "leicht"),
            "offclass_xp_multiplier": setup_node["summary"].get("offclass_xp_multiplier", 0.7),
            "onclass_xp_multiplier": setup_node["summary"].get("onclass_xp_multiplier", 1.0),
            "campaign_length": setup_node["summary"].get("campaign_length", "medium"),
            "target_turns": deps.deep_copy(setup_node["summary"].get("target_turns") or deps.target_turns_defaults),
            "pacing_profile": deps.deep_copy(setup_node["summary"].get("pacing_profile") or deps.pacing_profile_defaults),
        }
    )
    campaign["state"]["world"]["settings"] = deps.normalize_world_settings(campaign["state"]["world"].get("settings") or {})
    deps.ensure_world_codex_from_setup(campaign["state"], setup_node.get("summary") or {})
    deps.initialize_dynamic_slots(campaign, setup_node["summary"]["player_count"])
    deps.apply_world_summary_to_boards(campaign, player_id)
    campaign["state"]["world"]["notes"] = setup_node["summary"].get("premise", "")
    campaign["state"]["meta"]["phase"] = "character_setup_open"


def finalize_character_setup(campaign: CampaignState, slot_name: str, *, deps: Any) -> Optional[Dict[str, Any]]:
    setup_node = campaign["setup"]["characters"][slot_name]
    setup_node["completed"] = True
    setup_node["summary"] = build_character_summary(campaign, slot_name, deps=deps)
    deps.apply_character_summary_to_state(campaign, slot_name)
    if campaign["state"]["meta"].get("phase") != "active":
        campaign["state"]["meta"]["phase"] = "character_setup_open"
    return deps.maybe_start_adventure(campaign)
