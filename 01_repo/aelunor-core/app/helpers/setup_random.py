import json
import random
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.helpers import setup_helpers


CampaignState = Dict[str, Any]


def fallback_random_text(
    question_id: str,
    *,
    setup_type: str,
    campaign: CampaignState,
    deps: Any,
    slot_name: Optional[str] = None,
) -> str:
    world_theme = deps.extract_text_answer((campaign.get("setup", {}).get("world", {}).get("answers", {}) or {}).get("theme"))
    gender = ""
    if slot_name:
        gender = deps.extract_text_answer((((campaign.get("setup", {}) or {}).get("characters", {}) or {}).get(slot_name, {}).get("answers", {}) or {}).get("char_gender"))
    fallbacks = {
        "central_conflict": "Ein sterbendes Grenzland wird von einem alten Schattenkult und hungrigen Bestien zugleich zerfressen.",
        "factions": "Die Schwarze Abtei - will verbotene Reliquien sammeln und herrscht durch Angst.\nDie Roten ZÃ¶llner - pressen die letzten Siedlungen mit Gewalt aus.\nDer Aschencirkel - jagt jede fremde Macht und opfert Wissen fÃ¼r StÃ¤rke.",
        "taboos": "Keine zusÃ¤tzlichen Tabus. Konsequenzen sollen hart, aber fair bleiben.",
        "resource_name": "Mana",
        "earth_life": "Auf der Erde fÃ¼hrte die Figur ein unscheinbares Leben, war aber zÃ¤h, aufmerksam und unter Druck belastbar.",
        "first_goal": "Schnell einen sicheren Ort finden und verstehen, welche Macht diese Welt im Hintergrund lenkt.",
        "earth_items": "Taschenlampe, Feuerzeug, kleines Notizbuch",
        "signature_item": "Ein abgenutztes Messer mit Erinnerungsspur",
    }
    if question_id == "char_name":
        male_names = ["Riven", "Kael", "Marek", "Taron", "Levin"]
        female_names = ["Mira", "Elara", "Sera", "Nyra", "Talia"]
        neutral_names = ["Ash", "Rin", "Nox", "Vale", "Kian"]
        if "mÃ¤nn" in gender.lower():
            return random.choice(male_names)
        if "weib" in gender.lower():
            return random.choice(female_names)
        return random.choice(neutral_names)
    if question_id == "central_conflict" and world_theme:
        return f"In einer Welt mit dem Thema {world_theme} kÃ¤mpfen die letzten freien Enklaven gegen eine Macht, die langsam alles Lebendige verdirbt."
    return fallbacks.get(question_id, "Etwas DÃ¼steres, Eigenes und Folgenschweres.")


def fallback_random_answer_payload(
    campaign: CampaignState,
    question: Dict[str, Any],
    *,
    setup_type: str,
    deps: Any,
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
    deps: Any,
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
        "Gib eine passende zufÃ¤llige Antwort fÃ¼r genau diese eine Frage zurÃ¼ck."
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
        setup_helpers.validate_answer_payload(question, normalized)
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
        setup_helpers.validate_answer_payload(question, normalized_fallback)
        return normalized_fallback


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
    deps: Any,
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
        stored = setup_helpers.validate_answer_payload(question, _entry_model_dump(entry))
        setup_helpers.store_setup_answer(preview_setup_node, question, stored, player_id=player_id, source="ai_preview_locked", deps=deps)
    previews: List[Dict[str, Any]] = []
    generated_count = 0
    while True:
        qid = deps.current_question_id(preview_setup_node)
        if not qid:
            break
        if question_id and generated_count == 0 and qid != question_id:
            raise HTTPException(status_code=409, detail="Die aktive Setup-Frage hat sich geÃ¤ndert. Bitte neu Ã¶ffnen.")
        question = question_map.get(qid)
        if not question:
            raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
        if mode == "all":
            raw_answer = fallback_random_answer_payload(preview_campaign, question, setup_type=setup_type, slot_name=slot_name, deps=deps)
        else:
            raw_answer = generate_random_setup_answer(
                preview_campaign,
                question,
                setup_type=setup_type,
                slot_name=slot_name,
                setup_node=preview_setup_node,
                deps=deps,
            )
        stored = setup_helpers.validate_answer_payload(question, raw_answer)
        setup_helpers.store_setup_answer(preview_setup_node, question, stored, player_id=player_id, source="ai_preview", deps=deps)
        previews.append(
            {
                "question_id": qid,
                "label": question["label"],
                "type": question["type"],
                "preview_text": setup_helpers.setup_answer_preview_text(question, stored),
                "answer": setup_helpers.setup_answer_to_input_payload(question, stored),
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
    deps: Any,
) -> int:
    _ = campaign
    applied_count = 0
    for entry in preview_answers:
        qid = deps.current_question_id(setup_node)
        if not qid:
            break
        if _entry_question_id(entry) != qid:
            raise HTTPException(status_code=409, detail="Die Setup-Reihenfolge hat sich geÃ¤ndert. Bitte neu erzeugen.")
        question = question_map.get(qid)
        if not question:
            raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
        stored = setup_helpers.validate_answer_payload(question, _entry_model_dump(entry))
        setup_helpers.store_setup_answer(setup_node, question, stored, player_id=player_id, source="ai_random", deps=deps)
        applied_count += 1
    return applied_count
