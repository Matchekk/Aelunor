from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


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

from app.helpers.setup_finalize import (
    build_character_summary,
    build_world_summary,
    finalize_character_setup,
    finalize_world_setup,
)
from app.helpers.setup_random import (
    apply_random_setup_preview,
    build_random_setup_preview,
    fallback_random_answer_payload,
    fallback_random_text,
    generate_random_setup_answer,
)
