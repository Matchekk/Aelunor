from dataclasses import dataclass
from typing import Any, Callable, Dict

from app.catalogs.runtime_catalogs import CHARACTER_QUESTION_MAP, INITIAL_STATE, WORLD_QUESTION_MAP
from app.config.runtime import LEGACY_CHARACTERS
from app.core.ids import utc_now
from app.services.state_basics import is_slot_id


CampaignState = Dict[str, Any]


def is_legacy_campaign(campaign: CampaignState) -> bool:
    chars = list((campaign.get("state", {}).get("characters") or {}).keys())
    claims = list((campaign.get("claims") or {}).keys())
    if any(name in LEGACY_CHARACTERS for name in chars):
        return True
    if any(name in LEGACY_CHARACTERS for name in claims):
        return True
    setup = campaign.get("setup", {})
    if setup and setup.get("version") == 2:
        return False
    return bool(chars or claims) and not all(is_slot_id(name) for name in chars + claims if name)


def remap_turn_context_slot_names(turn: CampaignState, mapping: Dict[str, str]) -> None:
    if turn.get("actor") in mapping:
        turn["actor"] = mapping[turn["actor"]]
    patch_chars = (turn.get("patch") or {}).get("characters")
    if isinstance(patch_chars, dict):
        turn["patch"]["characters"] = {mapping.get(key, key): value for key, value in patch_chars.items()}
    for state_key in ("state_before", "state_after"):
        state_snapshot = turn.get(state_key) or {}
        chars = state_snapshot.get("characters")
        if isinstance(chars, dict):
            state_snapshot["characters"] = {mapping.get(key, key): value for key, value in chars.items()}
    prompt_context = ((turn.get("prompt_payload") or {}).get("context") or {})
    if prompt_context:
        chars = prompt_context.get("characters")
        if isinstance(chars, dict):
            prompt_context["characters"] = {mapping.get(key, key): value for key, value in chars.items()}
        claims = prompt_context.get("claims")
        if isinstance(claims, dict):
            prompt_context["claims"] = {mapping.get(key, key): value for key, value in claims.items()}
        active = prompt_context.get("active_party")
        if isinstance(active, list):
            prompt_context["active_party"] = [mapping.get(entry, entry) for entry in active]
        display = prompt_context.get("display_party")
        if isinstance(display, list):
            for entry in display:
                if isinstance(entry, dict) and entry.get("slot_id") in mapping:
                    entry["slot_id"] = mapping[entry["slot_id"]]
    for request in turn.get("requests", []):
        if isinstance(request, dict) and request.get("actor") in mapping:
            request["actor"] = mapping[request["actor"]]


@dataclass(frozen=True)
class CampaignSlotMigrationPorts:
    slot_id: Callable[[int], str]
    deep_copy: Callable[[Any], Any]
    blank_character_state: Callable[[str], CampaignState]
    default_setup: Callable[[], CampaignState]
    normalize_campaign_length_choice: Callable[[Any], str]
    legacy_select_answer_payload: Callable[[CampaignState, Any], CampaignState]
    normalize_resource_name: Callable[[Any], str]
    build_world_summary: Callable[[CampaignState], CampaignState]
    extract_text_answer: Callable[[Any], str]
    parse_earth_items: Callable[[str], Any]
    normalize_class_current: Callable[[Any], Any]
    default_character_setup_node: Callable[[], CampaignState]
    build_character_summary: Callable[[CampaignState, str], CampaignState]


def migrate_campaign_to_dynamic_slots(campaign: CampaignState, *, ports: CampaignSlotMigrationPorts) -> None:
    mapping = {name: ports.slot_id(index + 1) for index, name in enumerate(LEGACY_CHARACTERS)}
    world_question = WORLD_QUESTION_MAP
    char_question = CHARACTER_QUESTION_MAP
    state = campaign.setdefault("state", ports.deep_copy(INITIAL_STATE))
    old_characters = state.get("characters") or {}
    new_characters: CampaignState = {}
    old_claims = campaign.get("claims") or {}
    new_claims: CampaignState = {}
    for index, legacy_name in enumerate(LEGACY_CHARACTERS, start=1):
        new_slot = ports.slot_id(index)
        old_char = ports.deep_copy(old_characters.get(legacy_name) or ports.blank_character_state(new_slot))
        old_char["slot_id"] = new_slot
        new_characters[new_slot] = old_char
        new_claims[new_slot] = old_claims.get(legacy_name)
    state["characters"] = new_characters
    campaign["claims"] = new_claims

    old_setup = campaign.get("setup") or {}
    new_setup = ports.default_setup()
    world_setup = (old_setup.get("world") or {})
    legacy_campaign_length = ports.normalize_campaign_length_choice((((state.get("world") or {}).get("settings") or {}).get("campaign_length")))
    if legacy_campaign_length == "short":
        legacy_campaign_length_label = "Kurz"
    elif legacy_campaign_length == "open":
        legacy_campaign_length_label = "Unbestimmt"
    else:
        legacy_campaign_length_label = "Mittel"
    world_answers = {
        "theme": ports.legacy_select_answer_payload(world_question["theme"], world_setup.get("theme", "")),
        "player_count": {"selected": str(max(1, len([owner for owner in new_claims.values() if owner]) or 1)), "other_text": ""},
        "campaign_length": ports.legacy_select_answer_payload(world_question["campaign_length"], legacy_campaign_length_label),
        "tone": ports.legacy_select_answer_payload(world_question["tone"], world_setup.get("tone", "")),
        "difficulty": ports.legacy_select_answer_payload(world_question["difficulty"], "Brutal"),
        "death_possible": True,
        "monsters_density": ports.legacy_select_answer_payload(world_question["monsters_density"], "Regelmäßig"),
        "resource_scarcity": ports.legacy_select_answer_payload(world_question["resource_scarcity"], "Mittel"),
        "resource_name": ports.legacy_select_answer_payload(
            world_question["resource_name"],
            ports.normalize_resource_name((((state.get("world") or {}).get("settings") or {}).get("resource_name") or "Aether")),
        ),
        "healing_frequency": ports.legacy_select_answer_payload(world_question["healing_frequency"], "Normal"),
        "ruleset": ports.legacy_select_answer_payload(world_question["ruleset"], "Konsequent"),
        "attribute_range": ports.legacy_select_answer_payload(world_question["attribute_range"], "1-10"),
        "outcome_model": ports.legacy_select_answer_payload(world_question["outcome_model"], "Erfolg / Teilerfolg / Misserfolg-mit-Preis"),
        "world_structure": ports.legacy_select_answer_payload(world_question["world_structure"], world_setup.get("world_structure", "")),
        "world_laws": {"selected": [], "other_values": []},
        "central_conflict": str(world_setup.get("conflict", "") or campaign.get("boards", {}).get("plot_essentials", {}).get("current_threat", "")).strip(),
        "factions": "\n".join(
            entry.get("title", "")
            for entry in campaign.get("boards", {}).get("world_info", [])
            if entry.get("category") == "faction"
        ),
        "taboos": str(world_setup.get("special_notes", "")).strip(),
    }
    new_setup["world"]["answers"] = world_answers
    new_setup["world"]["summary"] = ports.build_world_summary({"setup": {"world": {"answers": world_answers}}})
    new_setup["world"]["completed"] = state.get("meta", {}).get("phase") in ("character_setup", "character_setup_open", "adventure", "active", "ready_to_start")

    old_setup_chars = old_setup.get("characters") or {}
    for legacy_name, new_slot in mapping.items():
        old_answers = ((old_setup_chars.get(legacy_name) or {}).get("answers") or {})
        bio = (new_characters[new_slot].get("bio") or {})
        legacy_gender = bio.get("gender") or ports.extract_text_answer(old_answers.get("char_gender"))
        legacy_age = bio.get("age") or ports.extract_text_answer(old_answers.get("char_age"))
        legacy_strength = bio.get("strength") or ports.extract_text_answer(old_answers.get("strength"))
        legacy_weakness = bio.get("weakness") or ports.extract_text_answer(old_answers.get("weakness"))
        legacy_focus = bio.get("focus") or ports.extract_text_answer(old_answers.get("current_focus"))
        legacy_price = bio.get("isekai_price") or ports.extract_text_answer(old_answers.get("isekai_price"))
        legacy_items = bio.get("earth_items") or ports.parse_earth_items(ports.extract_text_answer(old_answers.get("earth_items")))
        current_class = ports.normalize_class_current(new_characters[new_slot].get("class_current"))
        node = ports.default_character_setup_node()
        node["answers"] = {
            "char_name": bio.get("name", ""),
            "char_gender": ports.legacy_select_answer_payload(char_question["char_gender"], legacy_gender),
            "char_age": ports.legacy_select_answer_payload(char_question["char_age"], legacy_age),
            "earth_life": bio.get("earth_life", old_answers.get("earth_life", "")),
            "personality_tags": {"selected": bio.get("personality", []), "other_values": []},
            "strength": ports.legacy_select_answer_payload(char_question["strength"], legacy_strength),
            "weakness": ports.legacy_select_answer_payload(char_question["weakness"], legacy_weakness),
            "class_start_mode": ports.legacy_select_answer_payload(char_question["class_start_mode"], "Erst in der Story"),
            "class_seed": "",
            "class_custom_name": (current_class or {}).get("name", ""),
            "class_custom_description": (current_class or {}).get("description", ""),
            "class_custom_tags": ", ".join((current_class or {}).get("affinity_tags", [])),
            "current_focus": ports.legacy_select_answer_payload(char_question["current_focus"], legacy_focus),
            "first_goal": bio.get("goal", ""),
            "isekai_price": ports.legacy_select_answer_payload(char_question["isekai_price"], legacy_price),
            "earth_items": ", ".join(legacy_items),
            "signature_item": bio.get("signature_item", ""),
        }
        node["summary"] = ports.build_character_summary({"setup": {"characters": {new_slot: node}}}, new_slot)
        node["completed"] = bool(node["summary"].get("display_name")) or state.get("meta", {}).get("phase") in {"adventure", "active"}
        new_setup["characters"][new_slot] = node

    campaign["setup"] = new_setup
    for turn in campaign.get("turns", []):
        remap_turn_context_slot_names(turn, mapping)

    campaign["legacy_migration"] = {
        "original_schema": "fixed_3_slots_v1",
        "migrated_at": utc_now(),
    }
