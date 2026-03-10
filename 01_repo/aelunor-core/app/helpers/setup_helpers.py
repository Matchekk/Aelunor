import json
import random
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


def _coerce_player_count(value: Any, *, default: int = 1) -> int:
    """Best-effort parser for setup player count to avoid finalize-time 500s."""
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError):
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


@dataclass(frozen=True)
class SetupHelperDependencies:
    setup_random_system_prompt: str
    setup_random_schema: Dict[str, Any]
    target_turns_defaults: Dict[str, Any]
    pacing_profile_defaults: Dict[str, Any]
    max_players: int
    call_ollama_schema: Callable[..., Any]
    extract_text_answer: Callable[[Any], str]
    normalized_eval_text: Callable[[Any], str]
    utc_now: Callable[[], str]
    deep_copy: Callable[[Any], Any]
    current_question_id: Callable[[Dict[str, Any]], Optional[str]]
    normalize_answer_summary_defaults: Callable[[], Dict[str, Any]]
    normalize_resource_name: Callable[[Any, str], str]
    normalize_campaign_length_choice: Callable[[Any], str]
    normalize_ruleset_choice: Callable[[Any], str]
    parse_attribute_range: Callable[[Any], Dict[str, Any]]
    parse_factions: Callable[[str], List[Dict[str, str]]]
    parse_lines: Callable[[str], List[str]]
    parse_earth_items: Callable[[str], List[str]]
    normalize_world_settings: Callable[[Any], Dict[str, Any]]
    ensure_world_codex_from_setup: Callable[[Dict[str, Any], Dict[str, Any]], None]
    initialize_dynamic_slots: Callable[[CampaignState, int], None]
    apply_world_summary_to_boards: Callable[[CampaignState, Optional[str]], None]
    apply_character_summary_to_state: Callable[[CampaignState, str], None]
    maybe_start_adventure: Callable[[CampaignState], Optional[Dict[str, Any]]]


def validate_answer_payload(question: Dict[str, Any], answer: Dict[str, Any]) -> Any:
    qtype = question["type"]
    required = question.get("required", False)
    allow_other = question.get("allow_other", False)
    options = question.get("options", [])

    if qtype in ("text", "textarea"):
        value = str(answer.get("value") or "").strip()
        if required and not value:
            raise HTTPException(status_code=400, detail=f"Antwort für {question['label']} fehlt.")
        return value

    if qtype == "boolean":
        value = answer.get("value")
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in ("ja", "true", "1"):
            return True
        if text in ("nein", "false", "0"):
            return False
        raise HTTPException(status_code=400, detail=f"Antwort für {question['label']} muss Ja oder Nein sein.")

    if qtype == "select":
        selected = str(answer.get("value") or answer.get("selected") or "").strip()
        other_text = str(answer.get("other_text") or "").strip()
        if required and not selected and not other_text:
            raise HTTPException(status_code=400, detail=f"Antwort für {question['label']} fehlt.")
        if not required and not selected and not other_text:
            return {"selected": "", "other_text": ""}
        if selected in options:
            return {"selected": selected, "other_text": other_text}
        if allow_other and other_text:
            return {"selected": "Sonstiges", "other_text": other_text}
        raise HTTPException(status_code=400, detail=f"Ungültige Auswahl für {question['label']}.")

    if qtype == "multiselect":
        raw = answer.get("selected")
        if raw is None:
            raw = answer.get("value")
        if raw is None:
            raw_list: List[str] = []
        elif isinstance(raw, list):
            raw_list = [str(entry).strip() for entry in raw if str(entry).strip()]
        else:
            raw_list = [str(raw).strip()] if str(raw).strip() else []
        selected = [entry for entry in raw_list if entry in options]
        other_values = [str(entry).strip() for entry in answer.get("other_values", []) if str(entry).strip()]
        if allow_other and answer.get("other_text"):
            other_values.append(str(answer["other_text"]).strip())
        count = len(selected) + len(other_values)
        if required and count == 0:
            raise HTTPException(status_code=400, detail=f"Antwort für {question['label']} fehlt.")
        if not required and count == 0:
            return {"selected": [], "other_values": []}
        if question.get("min_selected") and count < question["min_selected"]:
            raise HTTPException(status_code=400, detail=f"Bitte wähle mehr Einträge für {question['label']}.")
        if question.get("max_selected") and count > question["max_selected"]:
            raise HTTPException(status_code=400, detail=f"Zu viele Einträge für {question['label']}.")
        return {"selected": selected, "other_values": other_values}

    raise HTTPException(status_code=400, detail=f"Unbekannter Frage-Typ: {qtype}")


def fallback_random_text(
    question_id: str,
    *,
    setup_type: str,
    campaign: CampaignState,
    deps: SetupHelperDependencies,
    slot_name: Optional[str] = None,
) -> str:
    world_theme = deps.extract_text_answer((campaign.get("setup", {}).get("world", {}).get("answers", {}) or {}).get("theme"))
    gender = ""
    if slot_name:
        gender = deps.extract_text_answer((((campaign.get("setup", {}) or {}).get("characters", {}) or {}).get(slot_name, {}).get("answers", {}) or {}).get("char_gender"))
    fallbacks = {
        "central_conflict": "Ein sterbendes Grenzland wird von einem alten Schattenkult und hungrigen Bestien zugleich zerfressen.",
        "factions": "Die Schwarze Abtei - will verbotene Reliquien sammeln und herrscht durch Angst.\nDie Roten Zöllner - pressen die letzten Siedlungen mit Gewalt aus.\nDer Aschencirkel - jagt jede fremde Macht und opfert Wissen für Stärke.",
        "taboos": "Keine zusätzlichen Tabus. Konsequenzen sollen hart, aber fair bleiben.",
        "resource_name": "Mana",
        "earth_life": "Auf der Erde führte die Figur ein unscheinbares Leben, war aber zäh, aufmerksam und unter Druck belastbar.",
        "first_goal": "Schnell einen sicheren Ort finden und verstehen, welche Macht diese Welt im Hintergrund lenkt.",
        "earth_items": "Taschenlampe, Feuerzeug, kleines Notizbuch",
        "signature_item": "Ein abgenutztes Messer mit Erinnerungsspur",
    }
    if question_id == "char_name":
        male_names = ["Riven", "Kael", "Marek", "Taron", "Levin"]
        female_names = ["Mira", "Elara", "Sera", "Nyra", "Talia"]
        neutral_names = ["Ash", "Rin", "Nox", "Vale", "Kian"]
        if "männ" in gender.lower():
            return random.choice(male_names)
        if "weib" in gender.lower():
            return random.choice(female_names)
        return random.choice(neutral_names)
    if question_id == "central_conflict" and world_theme:
        return f"In einer Welt mit dem Thema {world_theme} kämpfen die letzten freien Enklaven gegen eine Macht, die langsam alles Lebendige verdirbt."
    return fallbacks.get(question_id, "Etwas Düsteres, Eigenes und Folgenschweres.")


def fallback_random_answer_payload(
    campaign: CampaignState,
    question: Dict[str, Any],
    *,
    setup_type: str,
    deps: SetupHelperDependencies,
    slot_name: Optional[str] = None,
) -> Dict[str, Any]:
    qtype = question["type"]
    options = question.get("options", [])
    min_selected = int(question.get("min_selected") or 1)
    max_selected = int(question.get("max_selected") or max(min_selected, len(options) or 1))
    if qtype in ("text", "textarea"):
        return {"value": fallback_random_text(question["id"], setup_type=setup_type, campaign=campaign, slot_name=slot_name, deps=deps)}
    if qtype == "boolean":
        return {"value": random.choice([True, False])}
    if qtype == "select":
        if options:
            return {"selected": random.choice(options), "other_text": ""}
        return {"selected": "", "other_text": fallback_random_text(question["id"], setup_type=setup_type, campaign=campaign, slot_name=slot_name, deps=deps)}
    if qtype == "multiselect":
        if not options:
            return {"selected": [], "other_values": []}
        count = random.randint(min_selected, min(max_selected, len(options)))
        return {"selected": random.sample(options, count), "other_values": []}
    return {"value": ""}


def generate_random_setup_answer(
    campaign: CampaignState,
    question: Dict[str, Any],
    *,
    setup_type: str,
    deps: SetupHelperDependencies,
    slot_name: Optional[str] = None,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary = campaign.get("setup", {}).get("world", {}).get("summary", {})
    current_answers = (setup_node or {}).get("answers", {})
    user = (
        f"Setup-Typ: {setup_type}\n"
        f"Slot: {slot_name or '-'}\n"
        f"Aktuelle Welt-Zusammenfassung: {json.dumps(summary, ensure_ascii=False)}\n"
        f"Bisherige Antworten dieses Flows: {json.dumps(current_answers, ensure_ascii=False)}\n"
        f"Frage: {json.dumps(question, ensure_ascii=False)}\n"
        "Gib eine passende zufällige Antwort für genau diese eine Frage zurück."
    )
    try:
        raw = deps.call_ollama_schema(deps.setup_random_system_prompt, user, deps.setup_random_schema, timeout=120, temperature=0.7)
    except Exception:
        raw = fallback_random_answer_payload(campaign, question, setup_type=setup_type, slot_name=slot_name, deps=deps)
    if not isinstance(raw, dict):
        raw = fallback_random_answer_payload(campaign, question, setup_type=setup_type, slot_name=slot_name, deps=deps)
    normalized = {
        "question_id": question["id"],
        "value": raw.get("value"),
        "selected": raw.get("selected"),
        "other_text": str(raw.get("other_text") or ""),
        "other_values": [str(entry).strip() for entry in (raw.get("other_values") or []) if str(entry).strip()],
    }
    try:
        validate_answer_payload(question, normalized)
        return normalized
    except HTTPException:
        fallback = fallback_random_answer_payload(campaign, question, setup_type=setup_type, slot_name=slot_name, deps=deps)
        normalized_fallback = {
            "question_id": question["id"],
            "value": fallback.get("value"),
            "selected": fallback.get("selected"),
            "other_text": str(fallback.get("other_text") or ""),
            "other_values": [str(entry).strip() for entry in (fallback.get("other_values") or []) if str(entry).strip()],
        }
        validate_answer_payload(question, normalized_fallback)
        return normalized_fallback


def store_setup_answer(
    setup_node: Dict[str, Any],
    question: Dict[str, Any],
    stored: Any,
    *,
    player_id: Optional[str],
    deps: SetupHelperDependencies,
    source: str = "manual",
) -> None:
    setup_node["answers"][question["id"]] = stored
    if question["id"] == "class_start_mode":
        mode_text = deps.normalized_eval_text(deps.extract_text_answer(stored))
        if "ki" in mode_text:
            for key in ("class_custom_name", "class_custom_description", "class_custom_tags"):
                setup_node["answers"].pop(key, None)
        elif "selbst" in mode_text:
            setup_node["answers"].pop("class_seed", None)
        else:
            for key in ("class_seed", "class_custom_name", "class_custom_description", "class_custom_tags"):
                setup_node["answers"].pop(key, None)
    setup_node["raw_transcript"].append(
        {
            "question_id": question["id"],
            "label": question["label"],
            "answer": stored,
            "answered_at": deps.utc_now(),
            "answered_by": player_id,
            "source": source,
        }
    )


def setup_answer_to_input_payload(question: Dict[str, Any], stored: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "question_id": question["id"],
        "value": None,
        "selected": None,
        "other_text": "",
        "other_values": [],
    }
    qtype = question["type"]
    if qtype in ("text", "textarea", "boolean"):
        payload["value"] = stored
        return payload
    if qtype == "select":
        if isinstance(stored, dict):
            payload["selected"] = stored.get("selected")
            payload["other_text"] = str(stored.get("other_text") or "")
        return payload
    if qtype == "multiselect":
        if isinstance(stored, dict):
            payload["selected"] = stored.get("selected", [])
            payload["other_values"] = list(stored.get("other_values", []))
        return payload
    return payload


def setup_answer_preview_text(question: Dict[str, Any], stored: Any) -> str:
    qtype = question["type"]
    if qtype == "boolean":
        return "Ja" if bool(stored) else "Nein"
    if qtype in ("text", "textarea"):
        return str(stored or "").strip() or "Leer"
    if qtype == "select":
        if isinstance(stored, dict):
            selected = str(stored.get("selected") or "").strip()
            other_text = str(stored.get("other_text") or "").strip()
            if selected == "Sonstiges" and other_text:
                return other_text
            return selected or other_text or "Leer"
        return str(stored or "").strip() or "Leer"
    if qtype == "multiselect":
        if isinstance(stored, dict):
            values = list(stored.get("selected", [])) + list(stored.get("other_values", []))
            return ", ".join(value for value in values if value) or "Leer"
        if isinstance(stored, list):
            return ", ".join(str(value) for value in stored if value) or "Leer"
    return str(stored or "").strip() or "Leer"


def _entry_question_id(entry: Any) -> str:
    if isinstance(entry, dict):
        return str(entry.get("question_id") or "")
    return str(getattr(entry, "question_id", "") or "")


def _entry_model_dump(entry: Any) -> Dict[str, Any]:
    if isinstance(entry, dict):
        return entry
    model_dump = getattr(entry, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return {
        "question_id": _entry_question_id(entry),
        "value": getattr(entry, "value", None),
        "selected": getattr(entry, "selected", None),
        "other_text": getattr(entry, "other_text", ""),
        "other_values": list(getattr(entry, "other_values", []) or []),
    }


def build_random_setup_preview(
    campaign: CampaignState,
    setup_node: Dict[str, Any],
    question_map: Dict[str, Dict[str, Any]],
    *,
    setup_type: str,
    player_id: Optional[str],
    deps: SetupHelperDependencies,
    slot_name: Optional[str] = None,
    mode: str,
    question_id: Optional[str] = None,
    preview_answers: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    preview_campaign = deps.deep_copy(campaign)
    preview_setup_node = preview_campaign["setup"]["world"] if setup_type == "world" else preview_campaign["setup"]["characters"][slot_name]
    for entry in preview_answers or []:
        qid = deps.current_question_id(preview_setup_node)
        if not qid:
            break
        if _entry_question_id(entry) != qid:
            raise HTTPException(status_code=409, detail="Die Vorschau passt nicht mehr zur aktuellen Setup-Reihenfolge.")
        question = question_map.get(qid)
        if not question:
            raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
        stored = validate_answer_payload(question, _entry_model_dump(entry))
        store_setup_answer(preview_setup_node, question, stored, player_id=player_id, source="ai_preview_locked", deps=deps)
    previews: List[Dict[str, Any]] = []
    generated_count = 0
    while True:
        qid = deps.current_question_id(preview_setup_node)
        if not qid:
            break
        if question_id and generated_count == 0 and qid != question_id:
            raise HTTPException(status_code=409, detail="Die aktive Setup-Frage hat sich geändert. Bitte neu öffnen.")
        question = question_map.get(qid)
        if not question:
            raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
        if mode == "all":
            raw_answer = fallback_random_answer_payload(
                preview_campaign,
                question,
                setup_type=setup_type,
                slot_name=slot_name,
                deps=deps,
            )
        else:
            raw_answer = generate_random_setup_answer(
                preview_campaign,
                question,
                setup_type=setup_type,
                slot_name=slot_name,
                setup_node=preview_setup_node,
                deps=deps,
            )
        stored = validate_answer_payload(question, raw_answer)
        store_setup_answer(preview_setup_node, question, stored, player_id=player_id, source="ai_preview", deps=deps)
        previews.append(
            {
                "question_id": qid,
                "label": question["label"],
                "type": question["type"],
                "preview_text": setup_answer_preview_text(question, stored),
                "answer": setup_answer_to_input_payload(question, stored),
            }
        )
        generated_count += 1
        if mode == "single":
            break
    return previews


def apply_random_setup_preview(
    campaign: CampaignState,
    setup_node: Dict[str, Any],
    question_map: Dict[str, Dict[str, Any]],
    preview_answers: List[Any],
    *,
    player_id: Optional[str],
    deps: SetupHelperDependencies,
) -> int:
    _ = campaign
    applied_count = 0
    for entry in preview_answers:
        qid = deps.current_question_id(setup_node)
        if not qid:
            break
        if _entry_question_id(entry) != qid:
            raise HTTPException(status_code=409, detail="Die Setup-Reihenfolge hat sich geändert. Bitte neu erzeugen.")
        question = question_map.get(qid)
        if not question:
            raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
        stored = validate_answer_payload(question, _entry_model_dump(entry))
        store_setup_answer(setup_node, question, stored, player_id=player_id, source="ai_random", deps=deps)
        applied_count += 1
    return applied_count


def build_world_summary(campaign: CampaignState, *, deps: SetupHelperDependencies) -> Dict[str, Any]:
    answers = campaign["setup"]["world"]["answers"]
    theme = deps.extract_text_answer(answers.get("theme"))
    tone = deps.extract_text_answer(answers.get("tone"))
    difficulty = deps.extract_text_answer(answers.get("difficulty"))
    death_possible = bool(answers.get("death_possible", True))
    death_policy = "Charaktertod möglich" if death_possible else "Kein permanenter Charaktertod"
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


def build_character_summary(campaign: CampaignState, slot_name: str, *, deps: SetupHelperDependencies) -> Dict[str, Any]:
    answers = campaign["setup"]["characters"][slot_name]["answers"]
    tags = []
    tags_answer = answers.get("personality_tags")
    if isinstance(tags_answer, dict):
        tags.extend(tags_answer.get("selected", []))
        tags.extend(tags_answer.get("other_values", []))
    summary = {
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
    return summary


def finalize_world_setup(campaign: CampaignState, player_id: Optional[str], *, deps: SetupHelperDependencies) -> None:
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


def finalize_character_setup(campaign: CampaignState, slot_name: str, *, deps: SetupHelperDependencies) -> Optional[Dict[str, Any]]:
    setup_node = campaign["setup"]["characters"][slot_name]
    setup_node["completed"] = True
    setup_node["summary"] = build_character_summary(campaign, slot_name, deps=deps)
    deps.apply_character_summary_to_state(campaign, slot_name)
    if campaign["state"]["meta"].get("phase") != "active":
        campaign["state"]["meta"]["phase"] = "character_setup_open"
    return deps.maybe_start_adventure(campaign)
