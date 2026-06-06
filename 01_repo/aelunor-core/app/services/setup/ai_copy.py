import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException

from app.catalogs.runtime_catalogs import CHARACTER_QUESTION_MAP, WORLD_QUESTION_MAP
from app.prompts.system_prompts import SETUP_QUESTION_SYSTEM_PROMPT


@dataclass(frozen=True)
class SetupAiCopyDependencies:
    call_ollama_text: Callable[[str, str], str]
    display_name_for_slot: Callable[[Dict[str, Any], str], str]
    looks_non_german_text: Callable[..., bool]
    utc_now: Callable[[], str]


def clean_setup_ai_copy(text: str) -> str:
    return str(text or "").strip().strip('"').strip("'").strip()


def is_bad_setup_ai_copy(text: str) -> bool:
    lowered = clean_setup_ai_copy(text).lower()
    if not lowered:
        return True
    meta_markers = (
        "frage-id:",
        "typ:",
        "setup-stufe:",
        "aktuelles weltprofil:",
        "es geht um den slot",
        '"premise":',
        '"tone":',
        '"difficulty":',
        '"player_count":',
        "{",
        "}",
    )
    if any(marker in lowered for marker in meta_markers):
        return True
    if len(lowered) > 260:
        return True
    return False


def generate_setup_ai_copy(
    campaign: Dict[str, Any],
    question: Dict[str, Any],
    *,
    setup_type: str,
    deps: SetupAiCopyDependencies,
    slot_name: Optional[str] = None,
) -> str:
    prompt = question.get("prompt_template") or question["label"]
    summary = campaign.get("setup", {}).get("world", {}).get("summary", {})
    role_text = (
        f"Es geht um den Slot {slot_name} ({deps.display_name_for_slot(campaign, slot_name)})"
        if slot_name
        else "Es geht um das Welt-Setup"
    )
    user = (
        f"Frage-ID: {question['id']}\n"
        f"Typ: {question['type']}\n"
        f"Setup-Stufe: {setup_type}\n"
        f"{role_text}\n"
        f"Aktuelles Weltprofil: {json.dumps(summary, ensure_ascii=False)}\n"
        f"Basistext: {prompt}"
    )
    try:
        text = deps.call_ollama_text(SETUP_QUESTION_SYSTEM_PROMPT, user)
        text = clean_setup_ai_copy(text)
        return prompt if is_bad_setup_ai_copy(text) or deps.looks_non_german_text(text, allow_short=True) else text
    except Exception:
        return prompt


def get_persisted_question_ai_copy(setup_node: Dict[str, Any], question_id: str) -> str:
    runtime = (setup_node.get("question_runtime") or {}).get(question_id) or {}
    return clean_setup_ai_copy(runtime.get("ai_copy", ""))


def store_question_ai_copy(setup_node: Dict[str, Any], question_id: str, ai_copy: str, source: str, *, deps: SetupAiCopyDependencies) -> str:
    runtime = setup_node.setdefault("question_runtime", {})
    cleaned = clean_setup_ai_copy(ai_copy)
    runtime[question_id] = {
        "ai_copy": cleaned,
        "generated_at": deps.utc_now(),
        "source": source,
    }
    return cleaned


def ensure_question_ai_copy(
    campaign: Dict[str, Any],
    *,
    setup_type: str,
    question_id: str,
    deps: SetupAiCopyDependencies,
    slot_name: Optional[str] = None,
) -> str:
    question_map = WORLD_QUESTION_MAP if setup_type == "world" else CHARACTER_QUESTION_MAP
    question = question_map.get(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
    if setup_type == "world":
        setup_node = campaign["setup"]["world"]
    else:
        setup_node = campaign["setup"]["characters"].get(slot_name or "")
        if not setup_node:
            raise HTTPException(status_code=404, detail="Unbekannter Setup-Slot.")
    existing = get_persisted_question_ai_copy(setup_node, question_id)
    if existing:
        return existing
    generated = generate_setup_ai_copy(campaign, question, setup_type=setup_type, slot_name=slot_name, deps=deps)
    source = "fallback" if clean_setup_ai_copy(generated) == clean_setup_ai_copy(question.get("prompt_template") or question["label"]) else "ai"
    return store_question_ai_copy(setup_node, question_id, generated or question["label"], source, deps=deps)
