from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.catalogs.runtime_catalogs import CHARACTER_QUESTION_MAP, WORLD_QUESTION_MAP
from app.services.setup.ai_copy import clean_setup_ai_copy, get_persisted_question_ai_copy
from app.services.setup.option_descriptions import append_context_hint, dynamic_option_description


@dataclass(frozen=True)
class SetupPayloadDependencies:
    deep_copy: Callable[[Any], Any]
    display_name_for_slot: Callable[[Dict[str, Any], str], str]
    extract_text_answer: Callable[[Any], str]
    is_host: Callable[[Dict[str, Any], Optional[str]], bool]
    current_question_id: Callable[[Dict[str, Any]], Optional[str]]
    progress_payload: Callable[[Dict[str, Any]], Dict[str, Any]]
    normalize_campaign_length_choice: Callable[[Any], str]
    normalize_ruleset_choice: Callable[[Any], str]


def build_setup_option_context(
    campaign: Dict[str, Any],
    *,
    setup_type: str,
    deps: SetupPayloadDependencies,
    slot_name: Optional[str] = None,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    world_answers = (((campaign.get("setup") or {}).get("world") or {}).get("answers") or {})
    world_summary = (((campaign.get("setup") or {}).get("world") or {}).get("summary") or {})
    character_node = (((campaign.get("setup") or {}).get("characters") or {}).get(slot_name or "")) or {}
    character_answers = (setup_node or character_node).get("answers", {}) or {}
    character_summary = (character_node.get("summary") or {})
    return {
        "setup_type": setup_type,
        "slot_name": slot_name or "",
        "slot_display_name": deps.display_name_for_slot(campaign, slot_name) if slot_name else "",
        "theme": deps.extract_text_answer(world_answers.get("theme")) or str(world_summary.get("theme", "") or ""),
        "campaign_length": deps.normalize_campaign_length_choice(
            deps.extract_text_answer(world_answers.get("campaign_length")) or str(world_summary.get("campaign_length", "") or "")
        ),
        "tone": deps.extract_text_answer(world_answers.get("tone")) or str(world_summary.get("tone", "") or ""),
        "difficulty": deps.extract_text_answer(world_answers.get("difficulty")) or str(world_summary.get("difficulty", "") or ""),
        "world_structure": deps.extract_text_answer(world_answers.get("world_structure")) or str(world_summary.get("world_structure", "") or ""),
        "resource_scarcity": deps.extract_text_answer(world_answers.get("resource_scarcity")) or str(world_summary.get("resource_scarcity", "") or ""),
        "resource_name": deps.extract_text_answer(world_answers.get("resource_name")) or str(world_summary.get("resource_name", "") or ""),
        "monsters_density": deps.extract_text_answer(world_answers.get("monsters_density")) or str(world_summary.get("monsters_density", "") or ""),
        "healing_frequency": deps.extract_text_answer(world_answers.get("healing_frequency")) or str(world_summary.get("healing_frequency", "") or ""),
        "ruleset": deps.normalize_ruleset_choice(deps.extract_text_answer(world_answers.get("ruleset")) or str(world_summary.get("ruleset", "") or "")),
        "attribute_range": str(world_summary.get("attribute_range_label", "") or deps.extract_text_answer(world_answers.get("attribute_range"))),
        "char_gender": deps.extract_text_answer(character_answers.get("char_gender")) or str(character_summary.get("gender", "") or ""),
        "char_age": deps.extract_text_answer(character_answers.get("char_age")) or str(character_summary.get("age_stage", "") or ""),
        "strength": deps.extract_text_answer(character_answers.get("strength")) or str(character_summary.get("strength", "") or ""),
        "weakness": deps.extract_text_answer(character_answers.get("weakness")) or str(character_summary.get("weakness", "") or ""),
        "class_start_mode": deps.extract_text_answer(character_answers.get("class_start_mode")) or str(character_summary.get("class_start_mode", "") or ""),
        "current_focus": deps.extract_text_answer(character_answers.get("current_focus")) or str(character_summary.get("current_focus", "") or character_summary.get("focus", "") or ""),
        "personality_tags": deps.extract_text_answer(character_answers.get("personality_tags")) or ", ".join(character_summary.get("personality_tags", []) or character_summary.get("personality", []) or []),
    }


def dynamic_other_hint(question: Dict[str, Any], context: Dict[str, str]) -> str:
    theme = context.get("theme", "")
    tone = context.get("tone", "")
    if question["type"] == "select":
        if context.get("setup_type") == "world":
            return f"Wenn nichts passt, gib eine eigene Welt-Richtung an, die trotzdem mit {theme or 'dem Run'} und {tone or 'dem aktuellen Ton'} zusammenarbeitet."
        return f"Wenn nichts passt, beschreibe eine eigene Antwort, die zur Figur und zur Welt {theme or 'des Runs'} passt."
    if question["type"] == "multiselect":
        if context.get("setup_type") == "world":
            return "Eigene zusÃ¤tzliche Gesetze oder Marker kannst du hier als kommagetrennte Liste ergÃ¤nzen."
        return "Eigene zusÃ¤tzliche Merkmale kannst du hier als kommagetrennte Liste ergÃ¤nzen."
    return ""


def build_dynamic_option_entries(
    question: Dict[str, Any],
    *,
    context: Dict[str, str],
) -> List[Dict[str, str]]:
    entries = []
    for option in question.get("options", []) or []:
        text = str(option).strip()
        if not text:
            continue
        entries.append(
            {
                "value": text,
                "label": text,
                "description": dynamic_option_description(question["id"], text, context),
            }
        )
    return entries


def build_question_payload(
    question: Dict[str, Any],
    *,
    campaign: Dict[str, Any],
    setup_type: str,
    ai_copy: str,
    deps: SetupPayloadDependencies,
    slot_name: Optional[str] = None,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = build_setup_option_context(
        campaign,
        setup_type=setup_type,
        slot_name=slot_name,
        setup_node=setup_node,
        deps=deps,
    )
    payload = {
        "question_id": question["id"],
        "label": question["label"],
        "type": question["type"],
        "required": question.get("required", False),
        "options": question.get("options", []),
        "option_entries": build_dynamic_option_entries(question, context=context),
        "min_selected": question.get("min_selected"),
        "max_selected": question.get("max_selected"),
        "allow_other": question.get("allow_other", False),
        "other_hint": dynamic_other_hint(question, context),
        "ai_copy": clean_setup_ai_copy(ai_copy) or question["label"],
        "existing_answer": None,
    }
    if setup_node:
        payload["existing_answer"] = deps.deep_copy(setup_node.get("answers", {}).get(question["id"]))
    return payload


def build_world_question_state(campaign: Dict[str, Any], viewer_id: Optional[str], *, deps: SetupPayloadDependencies) -> Optional[Dict[str, Any]]:
    if not deps.is_host(campaign, viewer_id):
        return None
    setup_node = campaign["setup"]["world"]
    qid = deps.current_question_id(setup_node)
    if not qid:
        return None
    base_question = WORLD_QUESTION_MAP[qid]
    question = build_question_payload(
        base_question,
        campaign=campaign,
        setup_type="world",
        ai_copy=get_persisted_question_ai_copy(setup_node, qid) or base_question["label"],
        setup_node=setup_node,
        deps=deps,
    )
    return {
        "question": question,
        "progress": deps.progress_payload(setup_node),
    }


def build_character_question_state(campaign: Dict[str, Any], slot_name: str, *, deps: SetupPayloadDependencies) -> Optional[Dict[str, Any]]:
    setup_node = campaign["setup"]["characters"].get(slot_name)
    if not setup_node:
        return None
    qid = deps.current_question_id(setup_node)
    if not qid:
        return None
    base_question = CHARACTER_QUESTION_MAP[qid]
    question = build_question_payload(
        base_question,
        campaign=campaign,
        setup_type="character",
        ai_copy=get_persisted_question_ai_copy(setup_node, qid) or base_question["label"],
        slot_name=slot_name,
        setup_node=setup_node,
        deps=deps,
    )
    return {
        "question": question,
        "progress": deps.progress_payload(setup_node),
    }
