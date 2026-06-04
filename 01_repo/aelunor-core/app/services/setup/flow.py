from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.catalogs.runtime_catalogs import CATALOG_VERSION, CHARACTER_FORM_CATALOG, CHARACTER_QUESTION_MAP, WORLD_FORM_CATALOG
from app.config.setup import CHAR_SETUP_CHAPTERS, WORLD_SETUP_CHAPTERS
from app.services.setup.answers import extract_text_answer
from app.services.world.text_normalization import normalized_eval_text


def setup_question_is_applicable(setup_node: Dict[str, Any], question_id: str) -> bool:
    if question_id not in CHARACTER_QUESTION_MAP:
        return True
    answers = setup_node.get("answers", {}) or {}
    class_start_mode = normalized_eval_text(extract_text_answer(answers.get("class_start_mode")))
    if not class_start_mode:
        return True
    if question_id == "class_seed":
        return "ki" in class_start_mode
    if question_id in {"class_custom_name", "class_custom_description", "class_custom_tags"}:
        return "selbst" in class_start_mode
    return True


def build_world_question_queue() -> List[str]:
    required = [entry["id"] for entry in WORLD_FORM_CATALOG if entry.get("required")]
    optional = [entry["id"] for entry in WORLD_FORM_CATALOG if not entry.get("required")]
    return required + optional


def build_character_question_queue() -> List[str]:
    required = [entry["id"] for entry in CHARACTER_FORM_CATALOG if entry.get("required")]
    optional = [entry["id"] for entry in CHARACTER_FORM_CATALOG if not entry.get("required")]
    return required + optional


def default_setup() -> Dict[str, Any]:
    return {
        "version": 4,
        "engine": {
            "world_catalog_version": CATALOG_VERSION,
            "character_catalog_version": CATALOG_VERSION,
        },
        "world": {
            "completed": False,
            "question_queue": build_world_question_queue(),
            "answers": {},
            "summary": {},
            "raw_transcript": [],
            "question_runtime": {},
        },
        "characters": {},
    }


def current_question_id(setup_node: Dict[str, Any]) -> Optional[str]:
    answers = setup_node.get("answers", {})
    for qid in setup_node.get("question_queue", []):
        if not setup_question_is_applicable(setup_node, qid):
            continue
        if qid not in answers:
            return qid
    return None


def answered_count(setup_node: Dict[str, Any]) -> int:
    answers = setup_node.get("answers", {})
    return sum(
        1
        for qid in setup_node.get("question_queue", [])
        if setup_question_is_applicable(setup_node, qid) and qid in answers
    )


def progress_payload(setup_node: Dict[str, Any]) -> Dict[str, int]:
    total = sum(1 for qid in setup_node.get("question_queue", []) if setup_question_is_applicable(setup_node, qid))
    return {
        "answered": answered_count(setup_node),
        "total": total,
        "step": min(answered_count(setup_node) + 1, total) if total else 0,
    }


def setup_chapter_config(setup_type: str) -> Dict[str, Dict[str, Any]]:
    return WORLD_SETUP_CHAPTERS if setup_type == "world" else CHAR_SETUP_CHAPTERS


def setup_question_chapter_key(setup_type: str, question_id: str) -> str:
    for chapter_key, config in setup_chapter_config(setup_type).items():
        if question_id in (config.get("questions") or set()):
            return chapter_key
    return "general"


def setup_chapter_progress(setup_node: Dict[str, Any], setup_type: str, chapter_key: str) -> Dict[str, int]:
    config = setup_chapter_config(setup_type).get(chapter_key) or {}
    questions = [qid for qid in setup_node.get("question_queue", []) if qid in (config.get("questions") or set())]
    total = 0
    answered = 0
    for qid in questions:
        if not setup_question_is_applicable(setup_node, qid):
            continue
        total += 1
        if qid in (setup_node.get("answers") or {}):
            answered += 1
    return {"answered": answered, "total": total}


def setup_global_progress(setup_node: Dict[str, Any]) -> Dict[str, int]:
    payload = progress_payload(setup_node)
    return {"answered": int(payload.get("answered", 0) or 0), "total": int(payload.get("total", 0) or 0)}


def setup_phase_display(phase: str) -> str:
    phase = str(phase or "").strip().lower()
    if phase == "world_setup":
        return "Weltaufbau"
    if phase == "character_setup_open":
        return "Charakterwerdung"
    if phase == "ready_to_start":
        return "Bereit zum Start"
    if phase == "active":
        return "Aktive Spielphase"
    return "Kampagne"
