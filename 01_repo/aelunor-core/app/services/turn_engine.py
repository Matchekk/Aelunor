import json
import re
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

_CONFIGURED = False

def configure(main_globals: Dict[str, Any]) -> None:
    """Inject main-module globals needed by extracted turn engine functions."""
    global _CONFIGURED
    globals().update(main_globals)
    _CONFIGURED = True

class TurnFlowError(Exception):
    def __init__(
        self,
        *,
        error_code: str,
        phase: str,
        trace_id: str,
        user_message: str,
        cause_class: str = "",
        cause_message: str = "",
    ) -> None:
        super().__init__(user_message)
        self.error_code = str(error_code or ERROR_CODE_TURN_INTERNAL)
        self.phase = str(phase or "")
        self.trace_id = str(trace_id or "")
        self.user_message = str(user_message or TURN_ERROR_USER_MESSAGES[ERROR_CODE_TURN_INTERNAL])
        self.cause_class = str(cause_class or "")
        self.cause_message = str(cause_message or "")

    def to_client_detail(self) -> str:
        return f"{self.user_message} [E:{self.error_code}]"

def user_message_for_error_code(error_code: str) -> str:
    return TURN_ERROR_USER_MESSAGES.get(error_code, TURN_ERROR_USER_MESSAGES[ERROR_CODE_TURN_INTERNAL])

def new_turn_trace_context(campaign_id: str, slot_id: str, player_id: Optional[str]) -> Dict[str, Any]:
    return {
        "trace_id": make_id("trace"),
        "campaign_id": str(campaign_id or ""),
        "slot_id": str(slot_id or ""),
        "player_id": str(player_id or ""),
        "turn_id": "",
        "last_phase": "",
    }

def emit_turn_phase_event(
    ctx: Optional[Dict[str, Any]],
    phase: str,
    success: bool,
    error_code: str = "OK",
    error_class: str = "",
    message: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if not isinstance(ctx, dict):
        return
    try:
        ctx["last_phase"] = str(phase or "")
        payload: Dict[str, Any] = {
            "event": "turn_phase",
            "ts": utc_now(),
            "trace_id": str(ctx.get("trace_id") or ""),
            "campaign_id": str(ctx.get("campaign_id") or ""),
            "slot_id": str(ctx.get("slot_id") or ""),
            "player_id": str(ctx.get("player_id") or ""),
            "turn_id": str(ctx.get("turn_id") or ""),
            "phase": str(phase or ""),
            "success": bool(success),
            "error_code": str(error_code or "OK"),
            "error_class": str(error_class or ""),
            "message": str(message or ""),
        }
        if isinstance(extra, dict) and extra:
            payload["extra"] = deep_copy(extra)
        LOGGER.info(json.dumps(payload, ensure_ascii=False))
    except Exception:
        return

def turn_flow_error(
    *,
    error_code: str,
    phase: str,
    trace_ctx: Optional[Dict[str, Any]],
    exc: Optional[BaseException] = None,
    user_message: Optional[str] = None,
) -> TurnFlowError:
    trace_id = str((trace_ctx or {}).get("trace_id") or "")
    return TurnFlowError(
        error_code=error_code,
        phase=phase,
        trace_id=trace_id,
        user_message=user_message or user_message_for_error_code(error_code),
        cause_class=exc.__class__.__name__ if exc else "",
        cause_message=str(exc) if exc else "",
    )

def looks_like_ollama_transport_error(message: str) -> bool:
    lowered = str(message or "").strip().lower()
    return (
        "ollama error" in lowered
        or "failed to parse grammar" in lowered
        or "grammar_init" in lowered
        or "llm predict error" in lowered
        or "read timed out" in lowered
        or "connection aborted" in lowered
    )

def classify_turn_exception(
    exc: Exception,
    *,
    phase: str,
    trace_ctx: Optional[Dict[str, Any]],
) -> TurnFlowError:
    if isinstance(exc, TurnFlowError):
        return exc
    if isinstance(exc, (requests.Timeout, requests.ConnectionError, requests.HTTPError)):
        return turn_flow_error(
            error_code=ERROR_CODE_NARRATOR_RESPONSE,
            phase=phase,
            trace_ctx=trace_ctx,
            exc=exc,
        )
    if isinstance(exc, requests.RequestException):
        return turn_flow_error(
            error_code=ERROR_CODE_NARRATOR_RESPONSE,
            phase=phase,
            trace_ctx=trace_ctx,
            exc=exc,
        )
    if isinstance(exc, RuntimeError):
        msg = str(exc)
        if "Model returned non-JSON content" in msg:
            return turn_flow_error(
                error_code=ERROR_CODE_JSON_REPAIR,
                phase=phase,
                trace_ctx=trace_ctx,
                exc=exc,
            )
        if looks_like_ollama_transport_error(msg):
            return turn_flow_error(
                error_code=ERROR_CODE_NARRATOR_RESPONSE,
                phase=phase,
                trace_ctx=trace_ctx,
                exc=exc,
            )
    return turn_flow_error(
        error_code=ERROR_CODE_TURN_INTERNAL,
        phase=phase,
        trace_ctx=trace_ctx,
        exc=exc,
    )

def text_tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-ZäöüÄÖÜß]{2,}", str(text or "").lower())

def looks_non_german_text(text: str, *, allow_short: bool = False) -> bool:
    tokens = text_tokens(text)
    if not tokens:
        return False
    minimum_length = 4 if allow_short else 6
    if len(tokens) < minimum_length:
        return False
    english_hits = sum(1 for token in tokens if token in ENGLISH_LANGUAGE_MARKERS)
    german_hits = sum(1 for token in tokens if token in GERMAN_LANGUAGE_MARKERS)
    if allow_short and english_hits >= 2 and german_hits == 0:
        return True
    if english_hits >= 4 and english_hits >= german_hits + 2:
        return True
    if english_hits >= 3 and german_hits == 0 and english_hits / max(len(tokens), 1) >= 0.2:
        return True
    return False

def non_german_request_fields(requests_payload: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    for index, request in enumerate(normalize_requests_payload(requests_payload), start=1):
        for field in ("question",):
            value = request.get(field, "")
            if value and looks_non_german_text(value, allow_short=True):
                issues.append(f"Request {index} Feld '{field}' ist nicht auf Deutsch.")
        for option in request.get("options", []) or []:
            if option and looks_non_german_text(option, allow_short=True):
                issues.append(f"Request {index} Option ist nicht auf Deutsch.")
    return issues

def is_first_person_action(text: str) -> bool:
    return bool(
        re.search(
            r"\b(ich|mich|mir|mein|meine|meinen|meinem|meiner|meins)\b",
            str(text or "").lower(),
        )
    )

def first_sentences(text: str, count: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    return " ".join(part for part in parts[:count] if part)

def text_similarity(left: str, right: str) -> float:
    left_norm = normalized_eval_text(left)
    right_norm = normalized_eval_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(a=left_norm, b=right_norm).ratio()

def novelty_ratio(candidate: str, reference: str) -> float:
    candidate_tokens = {
        token
        for token in text_tokens(candidate)
        if len(token) >= 4 and token not in ACTION_STOPWORDS
    }
    if not candidate_tokens:
        return 0.0
    reference_tokens = {
        token
        for token in text_tokens(reference)
        if len(token) >= 4 and token not in ACTION_STOPWORDS
    }
    new_tokens = candidate_tokens - reference_tokens
    return len(new_tokens) / max(len(candidate_tokens), 1)

def salient_action_tokens(text: str) -> List[str]:
    tokens = []
    for token in re.findall(r"[a-zA-ZäöüÄÖÜß]{4,}", str(text or "").lower()):
        if token in ACTION_STOPWORDS:
            continue
        tokens.append(token)
    return tokens[:8]

def repetition_issue_messages() -> set[str]:
    return {
        "Die GM-Antwort wiederholt den letzten Beat fast unverändert.",
        "Die GM-Antwort ist zu nah an einer der letzten Antworten.",
        "Die Antwort paraphrasiert den Story-Impuls zu direkt, statt danach weiterzuerzählen.",
        "Der Weiter-Zug führt die Szene nicht wirklich fort.",
    }

def anti_repetition_examples(campaign: Dict[str, Any]) -> Dict[str, List[str]]:
    turns = active_turns(campaign)
    openings: List[str] = []
    closings: List[str] = []
    seen_openings = set()
    seen_closings = set()
    for turn in reversed(turns[-5:]):
        gm_text = str(turn.get("gm_text_display", "") or "").strip()
        if not gm_text:
            continue
        opening = first_sentences(gm_text, 2).strip()
        if opening and opening not in seen_openings:
            seen_openings.add(opening)
            openings.append(opening[:220])
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", gm_text) if part.strip()]
        closing = " ".join(parts[-2:]).strip() if parts else ""
        if closing and closing not in seen_closings:
            seen_closings.add(closing)
            closings.append(closing[:220])
        if len(openings) >= 3 and len(closings) >= 2:
            break
    return {"openings": openings, "closings": closings}

def response_quality_issues(
    campaign: Dict[str, Any],
    actor: str,
    action_type: str,
    content: str,
    out: Dict[str, Any],
    patch: Dict[str, Any],
) -> List[str]:
    issues = []
    story = str(out.get("story", "") or "")
    is_story_guidance = action_type == "story" and not is_continue_story_content(content)
    is_direct_action = action_type == "do"
    if looks_non_german_text(story):
        issues.append("Die GM-Antwort ist nicht konsequent auf Deutsch.")
    issues.extend(non_german_request_fields(out.get("requests", [])))
    turns = active_turns(campaign)
    patch_summary = build_patch_summary(patch or blank_patch())
    no_progress = (
        patch_summary["characters_changed"] == 0
        and patch_summary["items_added"] == 0
        and patch_summary["plot_updates"] == 0
        and patch_summary["map_updates"] == 0
        and patch_summary["events_added"] == 0
    )
    last_gm = turns[-1]["gm_text_display"] if turns else ""
    last_requests = turns[-1].get("requests") if turns else []
    last_similarity = text_similarity(last_gm, story) if last_gm else 0.0
    last_novelty = novelty_ratio(story, last_gm) if last_gm else 1.0
    input_similarity = text_similarity(content, story) if content else 0.0
    input_novelty = novelty_ratio(story, content) if content else 1.0
    if last_gm and not is_story_guidance and last_similarity >= 0.84 and last_novelty <= 0.18:
        issues.append("Die GM-Antwort wiederholt den letzten Beat fast unverändert.")
    if is_story_guidance and last_gm and last_similarity >= 0.9 and last_novelty <= 0.12 and no_progress:
        issues.append("Die STORY-Antwort dreht sich inhaltlich im Kreis und führt die Szene nicht sichtbar weiter.")
    if is_direct_action and input_similarity >= 0.72 and input_novelty <= 0.28 and no_progress:
        issues.append("Die GM-Antwort paraphrasiert nur die TUN-Eingabe, statt ein Ergebnis mit Konsequenz zu erzählen.")
    recent_gm = [turn.get("gm_text_display", "") for turn in turns[-3:]]
    if not is_story_guidance and any(
        previous
        and text_similarity(previous, story) >= 0.9
        and novelty_ratio(story, previous) <= 0.14
        for previous in recent_gm
    ):
        issues.append("Die GM-Antwort ist zu nah an einer der letzten Antworten.")
    action_tokens = salient_action_tokens(content)
    story_norm = normalized_eval_text(story)
    if action_type in ("do", "say") and action_tokens:
        opening_norm = normalized_eval_text(first_sentences(story, 4))
        if not any(token[:4] in opening_norm for token in action_tokens):
            issues.append("Die GM-Antwort löst die konkrete Spieleraktion nicht zuerst und sichtbar auf.")
    if is_story_guidance:
        opening = first_sentences(story, 3)
        if content and opening and text_similarity(content, opening) >= 0.76 and novelty_ratio(opening, content) <= 0.16:
            issues.append("Die Antwort paraphrasiert den Story-Impuls zu direkt, statt danach weiterzuerzählen.")
    if content.strip().lower().startswith("weiter") and last_gm and text_similarity(last_gm, story) >= 0.68 and last_novelty <= 0.15:
        issues.append("Der Weiter-Zug führt die Szene nicht wirklich fort.")
    current_request_sig = " || ".join(
        sorted(
            f"{str(req.get('type') or '').strip().lower()}|{normalized_eval_text(req.get('question') or '')}|"
            f"{'|'.join(normalized_eval_text(opt) for opt in ((req.get('options') or []) if isinstance(req.get('options') or [], list) else []))}"
            for req in (out.get("requests") or [])
            if isinstance(req, dict)
        )
    )
    last_request_sig = " || ".join(
        sorted(
            f"{str(req.get('type') or '').strip().lower()}|{normalized_eval_text(req.get('question') or '')}|"
            f"{'|'.join(normalized_eval_text(opt) for opt in ((req.get('options') or []) if isinstance(req.get('options') or [], list) else []))}"
            for req in (last_requests or [])
            if isinstance(req, dict)
        )
    )
    if (
        current_request_sig
        and current_request_sig == last_request_sig
        and last_similarity >= 0.72
        and last_novelty <= 0.3
    ):
        issues.append("Die Antwort hängt in derselben Choice-Szene fest und bietet keinen echten neuen Zustand.")
    if actor and is_slot_id(actor):
        actor_display = normalized_eval_text(display_name_for_slot(campaign, actor))
        if actor_display and actor_display not in story_norm and no_progress and not is_story_guidance:
            issues.append("Die Antwort verliert den aktiven Charakter aus dem Fokus.")
        if is_first_person_action(content):
            opening_norm = normalized_eval_text(first_sentences(story, 2))
            other_party = [
                normalized_eval_text(display_name_for_slot(campaign, slot_name))
                for slot_name in active_party(campaign)
                if slot_name != actor
            ]
            if actor_display and actor_display not in opening_norm:
                issues.append("Die Antwort löst eine Ich-Aktion nicht klar auf den aktiven Charakter auf.")
            elif any(name and name in opening_norm for name in other_party):
                issues.append("Die Antwort zieht in den ersten Sätzen den falschen Charakter in den Fokus.")

    content_norm = normalized_eval_text(content)
    opening_norm = normalized_eval_text(first_sentences(story, 4))

    if content_norm:
        asks_for_info = any(token in content_norm for token in ("frage", "informationen", "informier", "boss", "auftrag"))
        escalates_to_direct_conflict = any(
            token in opening_norm
            for token in ("kampf", "angriff", "konfrontation", "duell", "hinterhalt", "boss", "ritual", "observatorium")
        )
        if asks_for_info and escalates_to_direct_conflict:
            issues.append("Die Antwort überspringt Missionsschritte zu schnell und eskaliert zu früh in direkte Konfrontation.")

        system_query = any(token in content_norm for token in ("systemfenster", "systemwindow", "status", "element", "info", "kontext"))
        if system_query and escalates_to_direct_conflict:
            issues.append("Eine System-/Info-Aktion wurde fälschlich als harte Story-Eskalation behandelt.")

        undercover_context = any(token in content_norm for token in ("tarn", "undercover", "händler", "verkleid"))
        cover_break = any(token in opening_norm for token in ("offenbart", "enttarnt", "enthüllt seine identität", "gibt sich zu erkennen"))
        if undercover_context and cover_break:
            issues.append("Die aktive Tarnung/Cover-Identität wird ohne ausdrückliche Spielerentscheidung gebrochen.")

    question_marks = story.count("?")
    if question_marks > 1:
        issues.append("Zu viele rhetorische Abschlussfragen; ende mit einer klaren spielbaren Lage.")
    return issues

def build_repetition_retry_instruction(campaign: Dict[str, Any], content: str) -> str:
    examples = anti_repetition_examples(campaign)
    lines = [
        "WIEDERHOLUNGS-SPERRE:",
        "- Schreibe keine Einleitung, die mit denselben Bildern, Satzstämmen oder Fakten beginnt wie die letzten Antworten.",
        "- Wiederhole den letzten Zustand nicht als Zusammenfassung. Gehe sofort in neue Konsequenz, neue Wahrnehmung oder neue Handlung über.",
        "- Der erste Absatz muss mindestens ein neues konkretes Element enthalten: Folge, Reaktion, Ortsdetail, Verletzung, Fund, Eskalation oder Entscheidungspunkt.",
    ]
    if content.strip():
        lines.append(f"- Die Spieleraktion ist bereits bekannt und gesetzt: {content[:220]}")
    if examples["openings"]:
        lines.append("- Diese jüngsten Einleitungen darfst du nicht wörtlich oder fast wörtlich wiederverwenden:")
        lines.extend(f"  * {entry}" for entry in examples["openings"])
    if examples["closings"]:
        lines.append("- Auch diese jüngsten Schlussbilder dürfen nicht einfach erneut paraphrasiert werden:")
        lines.extend(f"  * {entry}" for entry in examples["closings"])
    lines.append("- Beginne stattdessen direkt mit der unmittelbar nächsten Entwicklung.")
    return "\n".join(lines)

def inactive_character_refs(campaign: Dict[str, Any], story: str, patch: Dict[str, Any]) -> List[str]:
    inactive_slots = [slot_name for slot_name in campaign_slots(campaign) if slot_name not in active_party(campaign)]
    refs = []
    patch_chars = patch.get("characters") or {}
    for slot_name in inactive_slots:
        display = display_name_for_slot(campaign, slot_name)
        if slot_name in patch_chars or (display and display != f"Slot {slot_index(slot_name)}" and display in story):
            refs.append(display or slot_name)
    return refs

def validate_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> None:
    patch = normalize_patch_semantics(patch)
    known_scene_ids = set((state.get("scenes") or {}).keys()) | set(((state.get("map") or {}).get("nodes") or {}).keys()) | {
        str(node.get("id") or "").strip() for node in (patch.get("map_add_nodes") or []) if isinstance(node, dict)
    }
    for slot_name, upd in (patch.get("characters") or {}).items():
        if slot_name not in state["characters"]:
            raise ValueError(f"Unbekannter Slot im Patch: {slot_name}")
        if "derived" in upd:
            raise ValueError(f"Derived stats duerfen nicht direkt gepatcht werden: {slot_name}")
        if upd.get("scene_id") and upd.get("scene_id") not in known_scene_ids:
            raise ValueError(f"Unknown scene id for {slot_name}: {upd.get('scene_id')}")
        resource_name = resource_name_for_character(state["characters"][slot_name], ((state.get("world") or {}).get("settings") or {}))
        world_model = state.get("world") if isinstance(state.get("world"), dict) else {}
        for skill_id, skill_value in (upd.get("skills_set") or {}).items():
            normalized_skill = normalize_dynamic_skill_state(
                skill_value,
                skill_id=str(skill_id),
                skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else str(skill_id),
                resource_name=resource_name,
            )
            normalized_skill = normalize_skill_elements_for_world(normalized_skill, world_model)
            if normalized_skill.get("elements") and not all(
                element_id in ((world_model.get("elements") or {}).keys())
                for element_id in (normalized_skill.get("elements") or [])
            ):
                raise ValueError(f"Skill mit unbekanntem Element auf {slot_name}: {normalized_skill.get('name')}")
            cost = normalized_skill.get("cost")
            if cost and str(cost.get("resource") or "") != resource_name:
                raise ValueError(f"Skill-Kosten nutzen fuer {slot_name} die falsche Ressource: {normalized_skill.get('name')}")
            combat_relevant = bool(
                {
                    normalized_eval_text(tag)
                    for tag in (normalized_skill.get("tags") or [])
                    if normalized_eval_text(tag)
                }
                & {"kampf", "magie", "zauber", "waffe", "technik", "rune", "shadow", "holy"}
            )
            if combat_relevant and not cost:
                raise ValueError(f"Kampf-Skill ohne Kostenvertrag auf {slot_name}: {normalized_skill.get('name')}")
        for skill_id, delta in (upd.get("skills_delta") or {}).items():
            if isinstance(delta, dict):
                cost = (delta.get("cost") or {})
                if cost and str(cost.get("resource") or "") != resource_name:
                    raise ValueError(f"Skill-Delta nutzt fuer {slot_name} die falsche Ressource: {skill_id}")
        for ability in upd.get("abilities_add", []) or []:
            if ability.get("owner") != slot_name:
                raise ValueError(f"Ability owner mismatch: {ability.get('id')} owner={ability.get('owner')} expected={slot_name}")
            if normalized_eval_text(ability.get("name", "")) in UNIVERSAL_SKILL_LIKE_NAMES:
                raise ValueError(f"Ability wirkt wie universelle Fertigkeit auf {slot_name}: {ability.get('name')}")
        for faction in upd.get("factions_add", []) or []:
            if not faction.get("faction_id"):
                raise ValueError(f"Faction membership without faction_id on {slot_name}")
        class_set = normalize_class_current(upd.get("class_set"))
        class_update = upd.get("class_update") or {}
        if upd.get("class_set") and not class_set:
            raise ValueError(f"class_set ohne gueltige Klasse auf {slot_name}")
        if class_set and not (class_set.get("affinity_tags") or []):
            raise ValueError(f"class_set ohne affinity_tags auf {slot_name}")
        if class_set:
            resolved_class_element = resolve_class_element_id(class_set, world_model)
            if class_set.get("element_id") and not resolved_class_element:
                raise ValueError(f"class_set mit unbekanntem Element auf {slot_name}: {class_set.get('element_id')}")
        if class_update and not state["characters"][slot_name].get("class_current"):
            raise ValueError(f"class_update ohne bestehende Klasse auf {slot_name}")
        if class_update.get("rank") and normalize_skill_rank(class_update.get("rank")) != str(class_update.get("rank")).upper():
            raise ValueError(f"class_update mit ungueltigem Rank auf {slot_name}")
        if "progression_events" in upd:
            normalized_events = normalize_progression_event_list(
                upd.get("progression_events"),
                actor=slot_name,
                source_turn=int((state.get("meta") or {}).get("turn", 0) or 0) + 1,
            )
            if len(normalized_events) != len(upd.get("progression_events") or []):
                raise ValueError(f"ungueltige progression_events auf {slot_name}")
            for event in normalized_events:
                if str(event.get("actor") or "").strip() != slot_name:
                    raise ValueError(f"progression_event actor mismatch auf {slot_name}")
                if str(event.get("type") or "").strip().lower() == "skill_manifestation":
                    skill_payload = event.get("skill") if isinstance(event.get("skill"), dict) else {}
                    if not skill_payload and not str(event.get("target_skill_id") or "").strip():
                        raise ValueError(f"skill_manifestation ohne Skill-Definition auf {slot_name}")
                    skill_name = str((skill_payload or {}).get("name") or "").strip()
                    actor_name = str((((state.get("characters") or {}).get(slot_name) or {}).get("bio") or {}).get("name") or slot_name)
                    if skill_name and not is_skill_manifestation_name_plausible(skill_name, actor_name):
                        raise ValueError(f"skill_manifestation mit unplausiblem Skillnamen auf {slot_name}: {skill_name}")
                    if skill_payload:
                        normalized_manifest = normalize_dynamic_skill_state(
                            skill_payload,
                            skill_id=str((skill_payload or {}).get("id") or ""),
                            skill_name=str((skill_payload or {}).get("name") or ""),
                            resource_name=resource_name,
                        )
                        normalized_manifest = normalize_skill_elements_for_world(
                            normalized_manifest,
                            world_model,
                        )
                        if normalized_manifest.get("elements") and not all(
                            element_id in ((world_model.get("elements") or {}).keys())
                            for element_id in (normalized_manifest.get("elements") or [])
                        ):
                            raise ValueError(f"skill_manifestation mit unbekanntem Element auf {slot_name}")
        for injury in upd.get("injuries_add", []) or []:
            if not normalize_injury_state(injury):
                raise ValueError(f"ungueltige Injury auf {slot_name}")
        for injury in upd.get("injuries_update", []) or []:
            if not isinstance(injury, dict) or not str(injury.get("id") or "").strip():
                raise ValueError(f"injuries_update ohne id auf {slot_name}")
            if injury.get("severity") and str(injury.get("severity")).strip().lower() not in INJURY_SEVERITIES:
                raise ValueError(f"injuries_update mit ungueltiger severity auf {slot_name}")
            if injury.get("healing_stage") and str(injury.get("healing_stage")).strip().lower() not in INJURY_HEALING_STAGES:
                raise ValueError(f"injuries_update mit ungueltiger healing_stage auf {slot_name}")
        for scar in upd.get("scars_add", []) or []:
            if not normalize_scar_state(scar):
                raise ValueError(f"ungueltige Scar auf {slot_name}")
        resources_set = upd.get("resources_set") or {}
        for key in ("hp_current", "hp_max", "sta_current", "sta_max", "res_current", "res_max", "carry_current", "carry_max"):
            if key in resources_set and int(resources_set.get(key, 0) or 0) < 0:
                raise ValueError(f"negative Ressource in resources_set fuer {slot_name}: {key}")

    items_new = patch.get("items_new") or {}
    for item_id, item in (items_new or {}).items():
        if not isinstance(item, dict):
            raise ValueError(f"Ungültiges Item für {item_id}")
        weapon_profile = item.get("weapon_profile") if isinstance(item.get("weapon_profile"), dict) else {}
        if weapon_profile:
            for numeric_key in ("attack_bonus", "damage_min", "damage_max"):
                if numeric_key in weapon_profile and not isinstance(weapon_profile.get(numeric_key), int):
                    raise ValueError(f"weapon_profile.{numeric_key} muss integer sein ({item_id})")
    known_items = set(state.get("items", {}).keys()) | set(items_new.keys())
    for slot_name, upd in (patch.get("characters") or {}).items():
        for item_id in upd.get("inventory_add", []) or []:
            if item_id not in known_items:
                raise ValueError(f"Unknown item id in inventory_add for {slot_name}: {item_id}")
        eq = normalize_equipment_update_payload(upd.get("equip_set") or upd.get("equipment_set") or {})
        for equip_slot, value in eq.items():
            if value and value not in known_items:
                raise ValueError(f"Unknown item id in equipment_set.{equip_slot} for {slot_name}: {value}")
            if value:
                item_ref = (state.get("items", {}) or {}).get(value) or (items_new.get(value) or {})
                if not item_matches_equipment_slot(item_ref, equip_slot):
                    raise ValueError(f"Item {value} passt nicht in equipment_set.{equip_slot} fuer {slot_name}")

def sanitize_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    patch = normalize_patch_semantics(patch)
    sanitized = deep_copy(patch)
    cleaned_items_new: Dict[str, Any] = {}
    for item_id, raw_item in ((sanitized.get("items_new") or {}).items()):
        if not isinstance(raw_item, dict):
            continue
        candidate_name = clean_auto_item_name(str(raw_item.get("name") or ""))
        if not candidate_name:
            candidate_name = clean_creator_item_name(str(raw_item.get("name") or ""))
        if not candidate_name:
            continue
        normalized_item = ensure_item_shape(item_id, raw_item)
        normalized_item["name"] = candidate_name[0].upper() + candidate_name[1:] if candidate_name else candidate_name
        inferred_slot = infer_item_slot_from_definition(normalized_item)
        if inferred_slot and not normalize_equipment_slot_key(normalized_item.get("slot")):
            normalized_item["slot"] = inferred_slot
        cleaned_items_new[item_id] = normalized_item
    sanitized["items_new"] = cleaned_items_new
    known_items = set((state.get("items") or {}).keys()) | set(cleaned_items_new.keys())
    characters = sanitized.get("characters") or {}
    for slot_name in list(characters.keys()):
        if slot_name not in state["characters"]:
            characters.pop(slot_name, None)
            continue
        upd = characters[slot_name]
        upd["inventory_add"] = [item_id for item_id in (upd.get("inventory_add") or []) if item_id in known_items]
        eq = normalize_equipment_update_payload(upd.get("equip_set") or upd.get("equipment_set") or {})
        for equip_slot in list(eq.keys()):
            item_id = eq.get(equip_slot, "")
            if not item_id or item_id not in known_items:
                eq.pop(equip_slot, None)
                continue
            item_ref = (state.get("items", {}) or {}).get(item_id) or cleaned_items_new.get(item_id) or {}
            if not item_matches_equipment_slot(item_ref, equip_slot):
                eq.pop(equip_slot, None)
        if eq:
            upd["equipment_set"] = eq
            upd.pop("equip_set", None)
        else:
            upd.pop("equipment_set", None)
            upd.pop("equip_set", None)
        upd.pop("derived", None)
        if "class_set" in upd:
            normalized_class = normalize_class_current(upd.get("class_set"))
            if normalized_class:
                upd["class_set"] = normalized_class
            else:
                upd.pop("class_set", None)
        if upd.get("class_update"):
            upd["class_update"] = deep_copy(upd["class_update"])
        if upd.get("skills_set"):
            normalized_skill_updates = {}
            for raw_key, raw_value in (upd.get("skills_set") or {}).items():
                skill_name = (raw_value or {}).get("name", raw_key) if isinstance(raw_value, dict) else raw_key
                skill_key = skill_id_from_name(str(skill_name or raw_key))
                normalized_skill_updates[skill_key] = normalize_dynamic_skill_state(
                    raw_value,
                    skill_id=skill_key,
                    skill_name=str(skill_name or raw_key),
                    resource_name=resource_name_for_character(state["characters"][slot_name], ((state.get("world") or {}).get("settings") or {})),
                )
                normalized_skill_updates[skill_key] = normalize_skill_elements_for_world(
                    normalized_skill_updates[skill_key],
                    state.get("world") if isinstance(state.get("world"), dict) else {},
                )
            upd["skills_set"] = normalized_skill_updates
        if upd.get("skills_delta"):
            normalized_skill_deltas = {}
            for raw_key, raw_value in (upd.get("skills_delta") or {}).items():
                skill_name = (raw_value or {}).get("name", raw_key) if isinstance(raw_value, dict) else raw_key
                skill_key = skill_id_from_name(str(skill_name or raw_key))
                existing_delta = normalized_skill_deltas.get(skill_key)
                if isinstance(existing_delta, dict) and isinstance(raw_value, dict):
                    merged_delta = deep_copy(existing_delta)
                    merged_delta.update(deep_copy(raw_value))
                    normalized_skill_deltas[skill_key] = merged_delta
                elif isinstance(existing_delta, int) and isinstance(raw_value, int):
                    normalized_skill_deltas[skill_key] = existing_delta + raw_value
                else:
                    normalized_skill_deltas[skill_key] = deep_copy(raw_value)
            upd["skills_delta"] = normalized_skill_deltas
        if "progression_events" in upd:
            source_turn = int((state.get("meta") or {}).get("turn", 0) or 0) + 1
            upd["progression_events"] = normalize_progression_event_list(
                upd.get("progression_events"),
                actor=slot_name,
                source_turn=source_turn,
            )
        if upd.get("injuries_add"):
            upd["injuries_add"] = [entry for entry in (normalize_injury_state(raw) for raw in (upd.get("injuries_add") or [])) if entry]
        if upd.get("injuries_update"):
            cleaned_updates = []
            for raw in (upd.get("injuries_update") or []):
                if isinstance(raw, dict) and str(raw.get("id") or "").strip():
                    cleaned_updates.append(deep_copy(raw))
            upd["injuries_update"] = cleaned_updates
        if upd.get("injuries_heal"):
            upd["injuries_heal"] = [str(entry).strip() for entry in (upd.get("injuries_heal") or []) if str(entry).strip()]
        if upd.get("scars_add"):
            upd["scars_add"] = [entry for entry in (normalize_scar_state(raw) for raw in (upd.get("scars_add") or [])) if entry]
    sanitized["characters"] = characters
    sanitized["plotpoints_add"] = [
        entry
        for entry in (normalize_plotpoint_entry(raw) for raw in (sanitized.get("plotpoints_add") or []))
        if entry
    ]
    sanitized["plotpoints_update"] = [
        entry
        for entry in (normalize_plotpoint_update_entry(raw) for raw in (sanitized.get("plotpoints_update") or []))
        if entry
    ]
    sanitized_map_nodes: List[Dict[str, Any]] = []
    for node in (sanitized.get("map_add_nodes") or []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            continue
        node_name = clean_scene_name(str(node.get("name") or node.get("id") or ""))
        if not node_name:
            continue
        if not is_plausible_scene_name(node_name):
            continue
        if is_generic_scene_identifier(node_id, node_name):
            continue
        sanitized_map_nodes.append(
            {
                "id": node_id,
                "name": node_name,
                "type": str(node.get("type") or "location").strip() or "location",
                "danger": clamp(int(node.get("danger", 1) or 1), 0, 10),
                "discovered": bool(node.get("discovered", True)),
            }
        )
    sanitized["map_add_nodes"] = sanitized_map_nodes
    sanitized["map_add_edges"] = [
        {
            "from": str(edge.get("from") or "").strip(),
            "to": str(edge.get("to") or "").strip(),
            "kind": str(edge.get("kind") or "path").strip() or "path",
        }
        for edge in (sanitized.get("map_add_edges") or [])
        if isinstance(edge, dict) and str(edge.get("from") or "").strip() and str(edge.get("to") or "").strip()
    ]
    sanitized["events_add"] = [
        entry
        for entry in (normalize_event_entry(raw) for raw in (sanitized.get("events_add") or []))
        if entry
    ]
    return sanitized

def apply_patch(state: Dict[str, Any], patch: Dict[str, Any], *, attribute_cap: int = 10) -> Dict[str, Any]:
    patch = normalize_patch_semantics(patch)
    state.setdefault("items", {})
    attribute_cap = max(1, int(attribute_cap or 10))
    for item_id, item in (patch.get("items_new") or {}).items():
        state["items"][item_id] = ensure_item_shape(item_id, item)

    state["plotpoints"] = [
        entry
        for entry in (normalize_plotpoint_entry(raw) for raw in (state.get("plotpoints") or []))
        if entry
    ]
    for raw_pp in (patch.get("plotpoints_add") or []):
        pp = normalize_plotpoint_entry(raw_pp)
        if not pp:
            continue
        if not any(isinstance(existing, dict) and existing.get("id") == pp.get("id") for existing in state["plotpoints"]):
            state["plotpoints"].append(pp)

    for raw_upd in (patch.get("plotpoints_update") or []):
        upd = normalize_plotpoint_update_entry(raw_upd)
        if not upd:
            continue
        pid = upd.get("id")
        for pp in state["plotpoints"]:
            if isinstance(pp, dict) and pp.get("id") == pid:
                if "status" in upd:
                    pp["status"] = upd["status"]
                if "notes" in upd and upd["notes"]:
                    pp["notes"] = upd["notes"]

    state.setdefault("map", {"nodes": {}, "edges": []})
    state["map"].setdefault("nodes", {})
    for node in (patch.get("map_add_nodes") or []):
        node_id = node["id"]
        state["map"]["nodes"][node_id] = {
            "name": node["name"],
            "type": node["type"],
            "danger": node["danger"],
            "discovered": node["discovered"],
        }
        state.setdefault("scenes", {})
        state["scenes"].setdefault(node_id, {"name": node["name"], "danger": node["danger"], "notes": ""})

    for edge in (patch.get("map_add_edges") or []):
        if edge not in state["map"]["edges"]:
            state["map"]["edges"].append(edge)

    time_advance = ((patch.get("meta") or {}).get("time_advance") or {})
    if time_advance:
        apply_world_time_advance(state, int(time_advance.get("days", 0) or 0), time_advance.get("time_of_day"))
        if time_advance.get("reason"):
            state.setdefault("events", [])
            state["events"].append(f"Zeit vergeht: +{int(time_advance.get('days', 0) or 0)} Tage ({time_advance.get('reason')}).")

    effective_world_time = normalize_world_time(state.get("meta", {}))
    for slot_name, upd in (patch.get("characters") or {}).items():
        if slot_name not in state["characters"]:
            continue
        character = state["characters"][slot_name]
        ensure_progression_shape(character)
        ensure_character_progression_core(character)
        character["scene_id"] = upd.get("scene_id", character["scene_id"])
        if upd.get("bio_set"):
            character["bio"] = {**character.get("bio", {}), **upd["bio_set"]}
            character["bio"].pop("party_role", None)
        if upd.get("resources_set"):
            canonical_set = canonical_resources_set_from_payload(
                upd.get("resources_set"),
                character,
                ((state.get("world") or {}).get("settings") or {}),
            )
            for key, value in canonical_set.items():
                character[key] = max(0, int(value or 0))
            misc_resource_set = legacy_misc_resources_set_from_payload(upd.get("resources_set"))
            if misc_resource_set:
                resources_store = character.setdefault("resources", {})
                if not isinstance(resources_store, dict):
                    resources_store = {}
                    character["resources"] = resources_store
                for misc_key, misc_payload in misc_resource_set.items():
                    max_value = max(0, int(misc_payload.get("max", 0) or 0))
                    current_value = max(0, int(misc_payload.get("current", 0) or 0))
                    resources_store[misc_key] = {
                        "current": clamp(current_value, 0, max_value) if max_value > 0 else current_value,
                        "base_max": max_value,
                        "bonus_max": 0,
                        "max": max_value,
                    }
        canonical_resource_deltas = canonical_resource_deltas_from_update(upd)
        if canonical_resource_deltas["hp_current"]:
            character["hp_current"] = int(character.get("hp_current", 0) or 0) + canonical_resource_deltas["hp_current"]
        if canonical_resource_deltas["sta_current"]:
            character["sta_current"] = int(character.get("sta_current", 0) or 0) + canonical_resource_deltas["sta_current"]
        if canonical_resource_deltas["res_current"]:
            character["res_current"] = int(character.get("res_current", 0) or 0) + canonical_resource_deltas["res_current"]
        if canonical_resource_deltas["carry_current"]:
            character["carry_current"] = int(character.get("carry_current", 0) or 0) + canonical_resource_deltas["carry_current"]
        misc_resource_deltas = legacy_misc_resource_deltas_from_update(upd)
        if any(int(misc_resource_deltas.get(key, 0) or 0) != 0 for key in ("stress", "corruption", "wounds")):
            resources_store = character.setdefault("resources", {})
            if not isinstance(resources_store, dict):
                resources_store = {}
                character["resources"] = resources_store
            for misc_key in ("stress", "corruption", "wounds"):
                delta = int(misc_resource_deltas.get(misc_key, 0) or 0)
                if not delta:
                    continue
                current_entry = resources_store.get(misc_key) if isinstance(resources_store.get(misc_key), dict) else {}
                max_value = max(0, int(current_entry.get("max", 10 if misc_key != "wounds" else 3) or (10 if misc_key != "wounds" else 3)))
                current_value = int(current_entry.get("current", 0) or 0) + delta
                resources_store[misc_key] = {
                    "current": clamp(current_value, 0, max_value),
                    "base_max": max(0, int(current_entry.get("base_max", max_value) or max_value)),
                    "bonus_max": int(current_entry.get("bonus_max", 0) or 0),
                    "max": max_value,
                }

        if upd.get("attributes_set"):
            character.setdefault("attributes", {}).update(
                {
                    key: clamp(int(value or 0), 0, attribute_cap)
                    for key, value in upd["attributes_set"].items()
                    if key in ATTRIBUTE_KEYS
                }
            )
        for key, value in (upd.get("attributes_delta") or {}).items():
            if key in ATTRIBUTE_KEYS:
                character.setdefault("attributes", {})[key] = clamp(
                    int(character["attributes"].get(key, 0) or 0) + int(value or 0),
                    0,
                    attribute_cap,
                )

        skill_store = character.setdefault("skills", {})
        resource_name = resource_name_for_character(character, ((state.get("world") or {}).get("settings") or {}))
        if upd.get("skills_set"):
            for key, value in (upd.get("skills_set") or {}).items():
                skill_key = str(key or "").strip()
                if not skill_key:
                    continue
                normalized_skill = normalize_dynamic_skill_state(
                    value,
                    skill_id=skill_key,
                    skill_name=(value or {}).get("name", skill_key) if isinstance(value, dict) else skill_key,
                    resource_name=resource_name,
                    unlocked_from="Patch",
                )
                normalized_skill = normalize_skill_elements_for_world(
                    normalized_skill,
                    state.get("world") if isinstance(state.get("world"), dict) else {},
                )
                existing_skill = skill_store.get(normalized_skill["id"])
                if not existing_skill:
                    existing_skill = next(
                        (
                            skill_value
                            for skill_value in skill_store.values()
                            if isinstance(skill_value, dict)
                            and normalized_eval_text(skill_value.get("name", "")) == normalized_eval_text(normalized_skill.get("name", ""))
                        ),
                        None,
                    )
                skill_store[normalized_skill["id"]] = merge_dynamic_skill(existing_skill, normalized_skill, resource_name=resource_name) if existing_skill else normalized_skill
                if existing_skill:
                    duplicate_ids = [
                        existing_id
                        for existing_id, skill_value in list(skill_store.items())
                        if existing_id != normalized_skill["id"]
                        and isinstance(skill_value, dict)
                        and normalized_eval_text(skill_value.get("name", "")) == normalized_eval_text(normalized_skill.get("name", ""))
                    ]
                    for duplicate_id in duplicate_ids:
                        skill_store.pop(duplicate_id, None)
        world_settings = ((state.get("world") or {}).get("settings") or {})
        for key, value in (upd.get("skills_delta") or {}).items():
            skill_key = str(key or "").strip()
            if not skill_key:
                continue
            existing_skill = skill_store.get(skill_key)
            if not existing_skill:
                existing_skill = normalize_dynamic_skill_state(
                    {"id": skill_key, "name": skill_key, "level": 1, "rank": "F", "level_max": 10, "tags": [], "description": f"{skill_key} wurde im Abenteuer aktiviert.", "unlocked_from": "Patch"},
                    resource_name=resource_name,
                )
            skill = normalize_dynamic_skill_state(existing_skill, skill_id=skill_key, skill_name=(existing_skill or {}).get("name", skill_key), resource_name=resource_name)
            skill = normalize_skill_elements_for_world(
                skill,
                state.get("world") if isinstance(state.get("world"), dict) else {},
            )
            if isinstance(value, dict):
                if "xp" in value:
                    multiplier = effective_skill_progress_multiplier(character, skill, world_settings)
                    skill["xp"] = max(0, int(skill.get("xp", 0) or 0) + int(round(float(value.get("xp", 0) or 0) * multiplier)))
                if "level" in value:
                    level_max = max(1, int(skill.get("level_max", DEFAULT_DYNAMIC_SKILL_LEVEL_MAX) or DEFAULT_DYNAMIC_SKILL_LEVEL_MAX))
                    skill["level"] = clamp(int(skill.get("level", 1) or 1) + int(value.get("level", 0) or 0), 1, level_max)
                if "description" in value and str(value.get("description") or "").strip():
                    skill["description"] = str(value.get("description")).strip()
                if "elements" in value:
                    skill["elements"] = list(dict.fromkeys([str(entry).strip() for entry in (value.get("elements") or []) if str(entry).strip()]))
                if "element_primary" in value:
                    skill["element_primary"] = str(value.get("element_primary") or "").strip() or None
                if "element_synergies" in value:
                    skill["element_synergies"] = list(dict.fromkeys([str(entry).strip() for entry in (value.get("element_synergies") or []) if str(entry).strip()])) or None
            else:
                multiplier = effective_skill_progress_multiplier(character, skill, world_settings)
                raw_delta = int(value or 0)
                xp_gain = int(round(raw_delta * DEFAULT_NUMERIC_SKILL_DELTA_XP * multiplier))
                skill["xp"] = max(0, int(skill.get("xp", 0) or 0) + xp_gain)
            while skill["xp"] >= int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"])) and skill["level"] < int(skill.get("level_max", DEFAULT_DYNAMIC_SKILL_LEVEL_MAX) or DEFAULT_DYNAMIC_SKILL_LEVEL_MAX):
                next_xp = int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"]))
                skill["xp"] = max(0, skill["xp"] - next_xp)
                skill["level"] += 1
            skill["next_xp"] = next_skill_xp_for_level(skill["level"])
            skill["xp"] = clamp(int(skill.get("xp", 0) or 0), 0, skill["next_xp"])
            skill_store[skill["id"]] = normalize_skill_elements_for_world(
                normalize_dynamic_skill_state(skill, resource_name=resource_name),
                state.get("world") if isinstance(state.get("world"), dict) else {},
            )

        for condition in upd.get("conditions_add", []) or []:
            if condition and condition not in character["conditions"]:
                character["conditions"].append(condition)
        for condition in upd.get("conditions_remove", []) or []:
            if condition in character["conditions"]:
                character["conditions"].remove(condition)

        for effect in upd.get("effects_add", []) or []:
            if effect.get("id") and not any(existing.get("id") == effect.get("id") for existing in character.get("effects", [])):
                character.setdefault("effects", []).append(effect)
        remove_effect_ids = set(upd.get("effects_remove", []) or [])
        if remove_effect_ids:
            character["effects"] = [effect for effect in character.get("effects", []) if effect.get("id") not in remove_effect_ids]

        for item_id in upd.get("inventory_add", []) or []:
            if item_id and not any(entry.get("item_id") == item_id for entry in character.get("inventory", {}).get("items", [])):
                character.setdefault("inventory", {}).setdefault("items", []).append({"item_id": item_id, "stack": 1})
        for item_id in upd.get("inventory_remove", []) or []:
            character.setdefault("inventory", {}).setdefault("items", [])
            character["inventory"]["items"] = [entry for entry in character["inventory"]["items"] if entry.get("item_id") != item_id]

        inventory_set = upd.get("inventory_set") or {}
        if inventory_set.get("items") is not None:
            character.setdefault("inventory", {})["items"] = inventory_set.get("items", [])
        if inventory_set.get("quick_slots") is not None:
            character.setdefault("inventory", {})["quick_slots"] = inventory_set.get("quick_slots", {})

        equipment_set = upd.get("equipment_set") or upd.get("equip_set")
        if equipment_set:
            normalized_equipment = character.get("equipment", {})
            normalized_update = normalize_equipment_update_payload(equipment_set)
            for key, value in normalized_update.items():
                normalized_equipment[key] = value
                if value and not any(entry.get("item_id") == value for entry in character.get("inventory", {}).get("items", [])):
                    character.setdefault("inventory", {}).setdefault("items", []).append({"item_id": value, "stack": 1})
            character["equipment"] = normalized_equipment

        for ability in upd.get("abilities_add", []) or []:
            normalized_ability = normalize_ability_state(ability, slot_name)
            normalized_skill = normalize_dynamic_skill_state(
                {
                    "id": skill_id_from_name(normalized_ability.get("name", normalized_ability.get("id", ""))),
                    "name": normalized_ability.get("name"),
                    "rank": normalize_skill_rank(normalized_ability.get("rank")),
                    "level": max(1, int(normalized_ability.get("level", 1) or 1)),
                    "level_max": 10,
                    "tags": list(dict.fromkeys([*(normalized_ability.get("tags") or []), normalized_ability.get("type", "")])),
                    "description": normalized_ability.get("description") or f"{normalized_ability.get('name', 'Technik')} wurde gelernt.",
                    "cost": None if not normalized_ability.get("cost") else {"resource": resource_name, "amount": sum(int(v or 0) for v in (normalized_ability.get("cost") or {}).values())},
                    "price": None,
                    "cooldown_turns": normalized_ability.get("cooldown_turns"),
                    "unlocked_from": normalized_ability.get("source") or "Patch",
                    "synergy_notes": None,
                    "xp": int(normalized_ability.get("xp", 0) or 0),
                    "next_xp": int(normalized_ability.get("next_xp", next_skill_xp_for_level(max(1, int(normalized_ability.get('level', 1) or 1)))) or next_skill_xp_for_level(max(1, int(normalized_ability.get('level', 1) or 1)))),
                    "mastery": int(normalized_ability.get("mastery", 0) or 0),
                },
                resource_name=resource_name,
            )
            existing_skill = skill_store.get(normalized_skill["id"])
            skill_store[normalized_skill["id"]] = merge_dynamic_skill(existing_skill, normalized_skill, resource_name=resource_name) if existing_skill else normalized_skill
        for ability_update in upd.get("abilities_update", []) or []:
            ability_id = skill_id_from_name(str(ability_update.get("id") or ""))
            existing_skill = skill_store.get(ability_id)
            if not existing_skill:
                continue
            skill = normalize_dynamic_skill_state(existing_skill, resource_name=resource_name)
            if "level" in ability_update:
                skill["level"] = max(1, int(ability_update.get("level", 1) or 1))
            if "xp" in ability_update:
                skill["xp"] = max(0, int(ability_update.get("xp", 0) or 0))
            if "cooldown_turns" in ability_update:
                skill["cooldown_turns"] = max(0, int(ability_update.get("cooldown_turns", 0) or 0))
            skill_store[ability_id] = normalize_dynamic_skill_state(skill, resource_name=resource_name)
        if ENABLE_LEGACY_SHADOW_WRITEBACK:
            character["abilities"] = []
        else:
            character.pop("abilities", None)

        for potential in upd.get("potential_add", []) or []:
            if isinstance(potential, dict):
                existing_ids = {entry.get("id") for entry in character.get("progression", {}).get("potential_cards", [])}
                if potential.get("id") and potential.get("id") not in existing_ids:
                    character.setdefault("progression", {}).setdefault("potential_cards", []).append(potential)
            elif potential:
                card = {"id": make_id("potential"), "name": str(potential), "description": "", "tags": [], "requirements": [], "status": "locked"}
                character.setdefault("progression", {}).setdefault("potential_cards", []).append(card)

        if upd.get("progression_set"):
            progression_set = deep_copy(upd["progression_set"] or {})
            character.setdefault("progression", {}).update(progression_set)
            if "level" in progression_set:
                character["level"] = max(1, int(progression_set.get("level", character.get("level", 1)) or character.get("level", 1)))
            if "xp_total" in progression_set:
                character["xp_total"] = max(0, int(progression_set.get("xp_total", character.get("xp_total", 0)) or character.get("xp_total", 0)))
            if "xp_current" in progression_set:
                character["xp_current"] = max(0, int(progression_set.get("xp_current", character.get("xp_current", 0)) or character.get("xp_current", 0)))
            if "xp_to_next" in progression_set:
                character["xp_to_next"] = max(1, int(progression_set.get("xp_to_next", character.get("xp_to_next", 1)) or character.get("xp_to_next", 1)))
            if "class_xp" in progression_set or "class_level" in progression_set:
                current_class = normalize_class_current(character.get("class_current")) or default_class_current()
                if "class_xp" in progression_set:
                    current_class["xp"] = max(0, int(progression_set.get("class_xp", current_class.get("xp", 0)) or current_class.get("xp", 0)))
                if "class_xp_to_next" in progression_set:
                    current_class["xp_next"] = max(1, int(progression_set.get("class_xp_to_next", current_class.get("xp_next", 1)) or current_class.get("xp_next", 1)))
                if "class_level" in progression_set:
                    current_class["level"] = max(1, int(progression_set.get("class_level", current_class.get("level", 1)) or current_class.get("level", 1)))
                character["class_current"] = normalize_class_current(current_class)
        if upd.get("journal_add"):
            journal = character.setdefault("journal", {})
            for key, value in upd["journal_add"].items():
                journal.setdefault(key, [])
                if isinstance(value, list):
                    journal[key].extend(value)

        if upd.get("class_set"):
            character["class_current"] = normalize_class_current(upd["class_set"])
        if upd.get("class_update"):
            current_class = normalize_class_current(character.get("class_current")) or default_class_current()
            merged_class = deep_copy(current_class)
            merged_class.update(deep_copy(upd["class_update"]))
            character["class_current"] = normalize_class_current(merged_class)
        character["class_current"] = normalize_class_current(character.get("class_current"))
        if character.get("class_current"):
            resolved_element = resolve_class_element_id(
                character.get("class_current"),
                state.get("world") if isinstance(state.get("world"), dict) else {},
            )
            class_current = normalize_class_current(character.get("class_current")) or default_class_current()
            if resolved_element:
                class_current["element_id"] = resolved_element
                class_current["element_tags"] = list(
                    dict.fromkeys([*(class_current.get("element_tags") or []), resolved_element])
                )
            character["class_current"] = normalize_class_current(class_current)
        core_skill_messages = ensure_class_rank_core_skills(
            character,
            state.get("world") if isinstance(state.get("world"), dict) else {},
            ((state.get("world") or {}).get("settings") or {}),
            unlock_extra=False,
        )
        if core_skill_messages:
            state.setdefault("events", [])
            state["events"].extend(core_skill_messages)
        for faction in upd.get("factions_add", []) or []:
            faction_id = faction.get("faction_id", "")
            if not faction_id:
                continue
            memberships = character.setdefault("faction_memberships", [])
            existing = next((entry for entry in memberships if entry.get("faction_id") == faction_id), None)
            if existing:
                existing.update(deep_copy(faction))
            else:
                memberships.append(deep_copy(faction))
        for faction_update in upd.get("factions_update", []) or []:
            faction_id = faction_update.get("faction_id", "")
            for membership in character.setdefault("faction_memberships", []):
                if membership.get("faction_id") == faction_id:
                    membership.update(deep_copy(faction_update))
                    break
        injuries = character.setdefault("injuries", [])
        if upd.get("injuries_add"):
            existing_injury_ids = {entry.get("id") for entry in injuries if isinstance(entry, dict)}
            for injury in upd.get("injuries_add", []) or []:
                if injury.get("id") not in existing_injury_ids:
                    injuries.append(injury)
                    existing_injury_ids.add(injury.get("id"))
        if upd.get("injuries_update"):
            injury_index = {entry.get("id"): entry for entry in injuries if isinstance(entry, dict)}
            for injury_update in upd.get("injuries_update", []) or []:
                target = injury_index.get(injury_update.get("id"))
                if target:
                    target.update(deep_copy(injury_update))
        if upd.get("injuries_heal"):
            heal_ids = {str(entry) for entry in (upd.get("injuries_heal") or [])}
            for injury in injuries:
                if isinstance(injury, dict) and injury.get("id") in heal_ids:
                    injury["healing_stage"] = "geheilt"
        scars_store = character.setdefault("scars", [])
        if upd.get("scars_add"):
            existing_scar_ids = {entry.get("id") for entry in scars_store if isinstance(entry, dict)}
            for scar in upd.get("scars_add", []) or []:
                if scar.get("id") not in existing_scar_ids:
                    scars_store.append(scar)
                    existing_scar_ids.add(scar.get("id"))
        for flag in upd.get("appearance_flags_add", []) or []:
            if not flag:
                continue
            character.setdefault("appearance", {}).setdefault("visual_modifiers", []).append(
                {
                    "source_type": "story",
                    "source_id": "story_flag",
                    "kind": "skin_mark",
                    "value": str(flag),
                    "active": True,
                }
            )

        ensure_progression_shape(character)
        ensure_character_progression_core(character)
        character["skills"] = normalize_skill_store(character.get("skills") or {}, resource_name=resource_name)
        new_scars = resolve_injury_healing(character, int(state.get("meta", {}).get("turn", 0) or 0))
        if new_scars:
            state.setdefault("events", [])
            char_name = str(((character.get("bio") or {}).get("name")) or slot_name).strip() or slot_name
            for scar in new_scars:
                state["events"].append(f"{char_name} trägt nun {scar.get('title')}.")
        rebuild_character_derived(character, state.get("items", {}), effective_world_time)
        reconcile_canonical_resources(character, ((state.get("world") or {}).get("settings") or {}))
        strip_legacy_shadow_fields(character, ((state.get("world") or {}).get("settings") or {}))
        if ENABLE_LEGACY_SHADOW_WRITEBACK:
            write_legacy_shadow_fields(character, ((state.get("world") or {}).get("settings") or {}))
        sync_scars_into_appearance(character)

    meta = patch.get("meta")
    if meta and "phase" in meta:
        state["meta"]["phase"] = meta["phase"]

    state.setdefault("events", [])
    for entry in (normalize_event_entry(raw) for raw in (patch.get("events_add") or [])):
        if entry:
            state["events"].append(entry)
    return state

def enforce_non_milestone_patch_limits(state: Dict[str, Any], patch: Dict[str, Any], *, is_milestone: bool, action_type: str) -> Dict[str, Any]:
    if is_milestone or action_type == "canon":
        return patch
    limited = deep_copy(patch)
    removed_notes: List[str] = []
    plotpoints_add = limited.get("plotpoints_add") or []
    filtered_plotpoints = []
    for entry in plotpoints_add:
        if isinstance(entry, dict) and str(entry.get("type") or "").strip().lower() == "class_ascension":
            removed_notes.append("Klassenaufstiegs-Quest auf Milestone verschoben.")
            continue
        filtered_plotpoints.append(entry)
    limited["plotpoints_add"] = filtered_plotpoints

    for slot_name, upd in (limited.get("characters") or {}).items():
        if slot_name not in (state.get("characters") or {}):
            continue
        existing_class = normalize_class_current(((state.get("characters", {}).get(slot_name) or {}).get("class_current")))
        existing_rank_value = class_rank_sort_value((existing_class or {}).get("rank", "F"))

        if upd.get("class_set"):
            proposed_class = normalize_class_current(upd.get("class_set"))
            if proposed_class and class_rank_sort_value(proposed_class.get("rank")) > existing_rank_value:
                proposed_class["rank"] = (existing_class or {}).get("rank", "F")
                upd["class_set"] = proposed_class
                removed_notes.append(f"Rank-Sprung für {slot_name} auf Milestone verschoben.")
        if upd.get("class_update"):
            class_update = deep_copy(upd.get("class_update") or {})
            rank_value = class_rank_sort_value(class_update.get("rank", "F"))
            if class_update.get("rank") and rank_value > existing_rank_value:
                class_update.pop("rank", None)
                removed_notes.append(f"Klassen-Rank-Update für {slot_name} auf Milestone verschoben.")
            upd["class_update"] = class_update

        existing_skills = set((((state.get("characters", {}).get(slot_name) or {}).get("skills") or {}).keys()))
        skill_updates = upd.get("skills_set") or {}
        filtered_skills = {}
        for skill_id, skill_value in skill_updates.items():
            if skill_id in existing_skills:
                filtered_skills[skill_id] = skill_value
                continue
            normalized_skill = normalize_dynamic_skill_state(
                skill_value,
                skill_id=str(skill_id),
                skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else str(skill_id),
                resource_name=resource_name_for_character((state.get("characters", {}).get(slot_name) or {}), ((state.get("world") or {}).get("settings") or {})),
            )
            if normalize_skill_rank(normalized_skill.get("rank")) in {"A", "S"}:
                removed_notes.append(f"Neuer {normalized_skill.get('rank')}-Skill für {slot_name} auf Milestone verschoben.")
                continue
            filtered_skills[skill_id] = skill_value
        if skill_updates:
            upd["skills_set"] = filtered_skills

    if removed_notes:
        limited.setdefault("events_add", [])
        limited["events_add"].extend(sorted(set(removed_notes)))
    return limited

def enforce_progression_set_mode_limits(patch: Dict[str, Any], *, action_type: str) -> Dict[str, Any]:
    if action_type == "canon":
        return patch
    limited = deep_copy(patch or blank_patch())
    blocked_changes: List[str] = []
    for slot_name, upd in (limited.get("characters") or {}).items():
        if not isinstance(upd, dict):
            continue
        progression_set = upd.get("progression_set") if isinstance(upd.get("progression_set"), dict) else {}
        if not progression_set:
            continue
        stripped = False
        for key in PROGRESSION_SET_DIRECT_KEYS:
            if key in progression_set:
                progression_set.pop(key, None)
                stripped = True
        if stripped:
            blocked_changes.append(slot_name)
        if progression_set:
            upd["progression_set"] = progression_set
        else:
            upd.pop("progression_set", None)
    if blocked_changes:
        limited.setdefault("events_add", [])
        limited["events_add"].append(
            "System: Direkte XP/Level-Setzung ist nur im Modus CANON bindend."
        )
    return limited

def rewrite_story_length_guard(
    *,
    system_prompt: str,
    user_prompt: str,
    story_text: str,
    patch: Dict[str, Any],
    requests_payload: List[Dict[str, Any]],
    min_story_chars: int,
    max_story_chars: int,
) -> str:
    story = str(story_text or "").strip()
    if not story:
        return story
    rewrite_instruction = (
        "REWRITE-AUFTRAG:\n"
        f"- Schreibe dieselbe Szene neu.\n"
        f"- story muss mindestens {min_story_chars} Zeichen enthalten.\n"
        "- Mehr Plotbewegung, weniger Fülltext.\n"
        "- Keine Wiederholung alter Absätze.\n"
        "- Bewahre exakt dieselben kanonischen Fakten bei.\n"
        "- Ändere keine Struktur außerhalb von story.\n"
    )
    for _ in range(MIN_STORY_REWRITE_ATTEMPTS):
        if len(story) >= min_story_chars:
            break
        rewrite_user = (
            user_prompt
            + "\n\n"
            + rewrite_instruction
            + "\nAktuelle zu kurze story:\n"
            + story
            + "\n\nPATCH (unverändert lassen):\n"
            + json.dumps(patch or {}, ensure_ascii=False)
            + "\nREQUESTS (unverändert lassen):\n"
            + json.dumps(requests_payload or [], ensure_ascii=False)
        )
        rewritten = call_ollama_schema(
            system_prompt,
            rewrite_user,
            STORY_REWRITE_SCHEMA,
            timeout=120,
            temperature=max(0.4, OLLAMA_TEMPERATURE - 0.05),
        )
        story = str((rewritten or {}).get("story", "") or "").strip()
    if len(story) < min_story_chars:
        raise HTTPException(status_code=500, detail=f"Modell konnte Mindestlänge ({min_story_chars}) nach Retry nicht erfüllen. Bitte erneut versuchen.")

    for _ in range(MAX_STORY_COMPRESS_ATTEMPTS):
        if len(story) <= max_story_chars:
            break
        compress_user = (
            user_prompt
            + "\n\nKOMPRIMIERUNGSAUFTRAG:\n"
            + f"- Kürze dieselbe Szene auf maximal {max_story_chars} Zeichen.\n"
            + "- Keine Fakten verlieren, keine Wiederholung, gleiche Konsequenzen.\n"
            + "\nAktuelle lange story:\n"
            + story
        )
        compressed = call_ollama_schema(
            system_prompt,
            compress_user,
            STORY_REWRITE_SCHEMA,
            timeout=90,
            temperature=max(0.35, OLLAMA_TEMPERATURE - 0.1),
        )
        story = str((compressed or {}).get("story", "") or "").strip()
    return story

def create_turn_record(
    *,
    campaign: Dict[str, Any],
    actor: str,
    player_id: Optional[str],
    action_type: str,
    content: str,
    request_received_ts: Optional[float] = None,
    retry_of_turn_id: Optional[str] = None,
    trace_ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state_before = deep_copy(campaign["state"])
    working_state = deep_copy(campaign["state"])
    working_state["meta"]["turn"] += 1
    working_state.setdefault("world", {}).setdefault("settings", {})
    working_state["world"]["settings"] = normalize_world_settings(working_state["world"].get("settings") or {})
    compute_turn_budget_estimates(working_state)
    pacing_block = build_pacing_instruction_block(working_state)
    pacing_profile = pacing_block["profile"]
    milestone_info = pacing_block["milestone"]
    min_story_chars = int(pacing_profile.get("min_story_chars", 800) or 800)
    max_story_chars = int(pacing_profile.get("max_story_chars", 2200) or 2200)
    combat_context = infer_combat_context(working_state, actor, action_type, content)
    combat_scaling_context = build_combat_scaling_context(working_state, actor)
    actor_character = (working_state.get("characters", {}) or {}).get(actor, {})
    attribute_profile = derive_attribute_relevance(working_state, actor, action_type, content, combat_context)
    attribute_bias = compute_attribute_bias(attribute_profile, actor_character, ((working_state.get("world") or {}).get("settings") or {}))
    if action_type == "canon":
        attribute_profile = {
            "primary_attributes": [],
            "influence_tier": "none",
            "narrative_bias": [],
            "combat_active": bool(combat_context.get("active")),
        }
        attribute_bias = {
            "damage_taken_mult": 1.0,
            "cost_mult": 1.0,
            "complication_mult": 1.0,
            "outgoing_effect_mult": 1.0,
        }
    attribute_prompt_hints = compose_attribute_prompt_hints(attribute_profile, attribute_bias)

    context = build_context_packet(campaign, working_state, actor, action_type)
    actor_display = display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor
    actor_resolution_hint = [
        f"Aktiver Actor-Slot: {actor}.",
        f"Aktive Figur dieses Turns: {actor_display}.",
        f"Diese {action_type}-Aktion gehört ausschließlich zu {actor_display}.",
    ]
    if is_first_person_action(content):
        actor_resolution_hint.append(
            f"Erste-Person-Pronomen im Spieltext wie 'ich', 'mich', 'mir' oder 'mein' meinen in diesem Turn immer {actor_display} und niemals eine andere Figur."
        )
    action_packet = {
        "actor": actor,
        "actor_display": actor_display,
        "action_type": action_type,
        "action_type_note": TURN_MODE_GUIDE[action_type],
        "content": content,
        "actor_resolution_hint": " ".join(actor_resolution_hint),
    }
    user_prompt = (
        "CONTEXT_PACKET(JSON):\n"
        + context
        + "\n\nOUTPUT-KONTRAKT:\n"
        + TURN_RESPONSE_JSON_CONTRACT
        + "\n\nPLAYER_ACTION(JSON):\n"
        + json.dumps(action_packet, ensure_ascii=False)
        + "\n\nACTOR_AUFLÖSUNG:\n"
        + "\n".join(f"- {line}" for line in actor_resolution_hint)
        + "\n\nAntworte ausschließlich im JSON-Format gemäß OUTPUT-KONTRAKT."
    )
    system_prompt = (
        SYSTEM_PROMPT
        + "\n\nACTION_TYPE-HINWEIS:\n"
        + "\n".join(f"- {mode}: {description}" for mode, description in TURN_MODE_GUIDE.items())
        + "\n\n"
        + pacing_block["text"]
        + "\n\n"
        + attribute_prompt_hints
        + "\nAuthor's Note ist immer bindender Zusatzkontext und liegt im Context Packet unter boards.authors_note.content."
        + "\nJeder sichtbare Text in story und requests muss vollständig auf Deutsch sein. Englische Sätze oder englische UI-Texte sind verboten."
        + "\nDu musst immer direkt auf die letzte Spieleraktion reagieren."
        + "\nGreife in den ersten 1-2 Sätzen die konkrete Aktion oder Aussage des Actors sichtbar auf."
        + "\nINTENT-FIRST ist bindend: Löse die explizite Spielerhandlung zuerst auf, bevor du neue Komplikationen einführst."
        + "\nMISSION-PACING ist bindend: Überspringe keine Zwischenstufen (Infiltration/Ermittlung/Verifikation), außer der Spieler eskaliert explizit."
        + "\nNO-RESET: Ziehe eine laufende Szene fort und starte sie nicht mit denselben Stakes oder derselben Einleitung neu."
        + "\nSystem-/Status-/Info-Aktionen führen primär zu Informationen und nur zu minimaler Umweltdynamik; keine harte Eskalation ohne Anlass."
        + "\nAktive Tarnungen/Coverstories bleiben bestehen, bis der Spieler sie ausdrücklich aufgibt oder die Szene sie glaubwürdig bricht."
        + "\nWenn der Spieltext in der ersten Person formuliert ist, löse 'ich/mich/mir/mein' immer auf den aktuellen Actor-Slot auf."
        + "\nNeue oder veränderte Kräfte, Magien, Waffenkünste und Körperentwicklungen werden im Patch über skills_set oder skills_delta abgebildet."
        + "\nELEMENTSYSTEM ist bindend: Nutze nur Elemente aus world.elements. Wenn keine Relation definiert ist, gilt neutral."
        + "\nElementare Klassen müssen element_id oder element_tags tragen. Skills können elements und element_primary setzen."
        + "\nKlassenpfade sind in world.element_class_paths hinterlegt. Klassenfortschritt soll zu passenden Kernskills führen."
        + "\nWenn du beim aktuellen Actor sichtbar einen neuen getragenen oder gehaltenen Gegenstand einführst, musst du ihn auch im Patch über items_new plus inventory_add oder equipment_set kanonisch festhalten."
        + "\nBei action_type=story ist der Spielertext ein bereits gesetzter Story-Impuls oder kanonischer Beat. Wiederhole oder paraphrasiere ihn nicht fast wörtlich. Nimm ihn als gesetzt und schreibe direkt die unmittelbaren Konsequenzen und die nächste Entwicklung weiter."
        + "\nBei 'Weiter' setzt du exakt am letzten erzählten Beat an und springst nicht zu einer früheren Standardidee zurück."
        + "\nWiederhole niemals frühere GM-Sätze oder fast identische Paraphrasen."
        + "\nEröffne neue Antworten nie mit einer bloßen Wiederholung des zuletzt etablierten Zustands. Starte mit Veränderung, Konsequenz, Reaktion oder neuem Detail."
        + "\nJede Antwort braucht mindestens ein neues konkretes Element, das in den letzten zwei GM-Antworten so noch nicht gesagt wurde."
        + "\nPro Turn maximal eine große neue Hauptkomplikation; vertiefe primär bestehende Konflikte."
        + "\nBeende Antworten mit klarer spielbarer Lage statt mit mehreren rhetorischen Fragen (maximal eine Abschlussfrage)."
        + "\nWenn eine Figur Schaden nimmt, erschöpft wird oder ihre Ressource sichtbar einsetzt, muss der Patch das sofort über hp_delta, stamina_delta oder resources_delta(res) abbilden."
        + "\nWenn eine Figur im Text klar getroffen, verwundet, erschöpft oder magisch ausgelaugt wird und der Patch keine passende Ressourcenänderung enthält, ist die Antwort unvollständig."
        + "\nIn Kampfszenen musst du aktiv vorhandene Ausrüstung, Klasse, Attribute und Skills der beteiligten Figuren berücksichtigen und im Fließtext konkret benennen, statt generische Treffertexte zu schreiben."
        + "\nNutze progression_events im Character-Patch für Fortschritt: type, actor, severity, reason, optional target_skill_id, optional target_class_id, optional skill (für skill_manifestation)."
        + "\nNeue Skills dürfen nur über skills_set oder progression_events(type=skill_manifestation) entstehen. Eine reine Floskel reicht nicht."
        + "\nErzähle Skill-/Klassenfortschritt möglichst nur dann als vollendete Tatsache, wenn im selben Output die passende strukturierte Änderung im Patch enthalten ist."
        + "\nWenn der aktuelle Actor noch keinen Skill besitzt und sich in einer klaren Kampf-/Konfliktszene befindet, soll in hoher Priorität (Richtwert ~80%) eine plausible Skill-Erstmanifestation im Patch landen."
        + f"\nCOMBAT-SKALIERUNG: actor_score={combat_scaling_context.get('actor_score')} threat_score={combat_scaling_context.get('threat_score')} pressure={combat_scaling_context.get('pressure')} ratio={combat_scaling_context.get('ratio')} weighted_ratio={combat_scaling_context.get('weighted_ratio')} element_factor={combat_scaling_context.get('element_factor')}."
        + "\nEs gibt keine Würfel, keine DCs und keine Roll-Requests. requests darf nur clarify, choice oder none enthalten."
        + f"\nDie story muss mindestens {min_story_chars} Zeichen enthalten."
    )
    prompt_payload: Dict[str, Any] = {
        "system": system_prompt,
        "user": user_prompt,
        "context": json.loads(context),
        "pacing": {
            "campaign_length": pacing_profile.get("campaign_length"),
            "min_story_chars": min_story_chars,
            "max_story_chars": max_story_chars,
            "milestone": milestone_info,
        },
        "attribute_profile": attribute_profile,
        "attribute_bias": attribute_bias,
        "combat_context": combat_context,
        "combat_scaling": combat_scaling_context,
    }

    narrator_patch = blank_patch()
    extractor_patch = blank_patch()
    requests_payload: List[Dict[str, Any]] = []
    gm_text_display = ""
    canon_applied = action_type == "canon"
    resource_deltas_applied: Dict[str, Any] = {}
    combat_resolution: Dict[str, Any] = {}

    def narrator_turn_error(message: str) -> TurnFlowError:
        emit_turn_phase_event(
            trace_ctx,
            phase="narrator_call_finished",
            success=False,
            error_code=ERROR_CODE_NARRATOR_RESPONSE,
            error_class="NarratorGuardError",
            message=str(message)[:240],
        )
        return turn_flow_error(
            error_code=ERROR_CODE_NARRATOR_RESPONSE,
            phase="narrator_call_finished",
            trace_ctx=trace_ctx,
            user_message=message,
        )

    if action_type == "canon":
        prompt_payload = {
            "system": CANON_EXTRACTOR_SYSTEM_PROMPT,
            "user": build_extractor_context_packet(campaign, working_state, actor, action_type, content, source="player"),
        }
        emit_turn_phase_event(trace_ctx, phase="extractor_patch_generation", success=True, extra={"stage": "canon"})
        try:
            extractor_piece = call_canon_extractor(campaign, working_state, actor, action_type, content, source="player")
            emit_turn_phase_event(trace_ctx, phase="extractor_patch_generation", success=True, extra={"stage": "canon", "result": "ok"})
        except Exception as exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="extractor_patch_generation",
                success=False,
                error_code=ERROR_CODE_EXTRACTOR,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": "canon"},
            )
            raise turn_flow_error(
                error_code=ERROR_CODE_EXTRACTOR,
                phase="extractor_patch_generation",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        extractor_piece.setdefault("events_add", [])
        extractor_piece["events_add"].append(f"KANON: {content}")
        emit_turn_phase_event(trace_ctx, phase="extractor_patch_apply", success=True, extra={"stage": "canon"})
        try:
            emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "canon"})
            extractor_piece = sanitize_patch(working_state, extractor_piece)
            emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "canon", "result": "ok"})
        except Exception as exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="patch_sanitize",
                success=False,
                error_code=ERROR_CODE_PATCH_SANITIZE,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": "canon"},
            )
            raise turn_flow_error(
                error_code=ERROR_CODE_PATCH_SANITIZE,
                phase="patch_sanitize",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        extractor_piece = enforce_progression_set_mode_limits(extractor_piece, action_type=action_type)
        try:
            emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "canon"})
            validate_patch(working_state, extractor_piece)
            emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "canon", "result": "ok"})
        except Exception as exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="schema_validation",
                success=False,
                error_code=ERROR_CODE_SCHEMA_VALIDATION,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": "canon"},
            )
            raise turn_flow_error(
                error_code=ERROR_CODE_SCHEMA_VALIDATION,
                phase="schema_validation",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        try:
            emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "canon"})
            working_state = apply_patch(working_state, extractor_piece, attribute_cap=attribute_cap_for_campaign(campaign))
            emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "canon", "result": "ok"})
            emit_turn_phase_event(trace_ctx, phase="extractor_patch_apply", success=True, extra={"stage": "canon", "result": "ok"})
        except Exception as exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="patch_apply",
                success=False,
                error_code=ERROR_CODE_PATCH_APPLY,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": "canon"},
            )
            emit_turn_phase_event(
                trace_ctx,
                phase="extractor_patch_apply",
                success=False,
                error_code=ERROR_CODE_PATCH_APPLY,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": "canon"},
            )
            raise turn_flow_error(
                error_code=ERROR_CODE_PATCH_APPLY,
                phase="patch_apply",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        extractor_patch = merge_patch_payloads(extractor_patch, extractor_piece)
        gm_text_display = "Kanon übernommen."
    else:
        out = None
        prompt_attempt_user = user_prompt
        for attempt in range(1, MAX_TURN_MODEL_ATTEMPTS + 1):
            attempt_temperature = OLLAMA_TEMPERATURE if attempt == 1 else min(0.9, OLLAMA_TEMPERATURE + 0.12 * (attempt - 1))
            attempt_repeat_penalty = OLLAMA_REPEAT_PENALTY if attempt == 1 else min(1.35, OLLAMA_REPEAT_PENALTY + 0.06 * (attempt - 1))
            emit_turn_phase_event(trace_ctx, phase="narrator_call_started", success=True, extra={"attempt": attempt})
            try:
                out = normalize_model_output_payload(
                    call_ollama_json(
                        system_prompt,
                        prompt_attempt_user,
                        temperature=attempt_temperature,
                        repeat_penalty=attempt_repeat_penalty,
                        trace_ctx=trace_ctx,
                    ),
                    default_actor=actor,
                )
                emit_turn_phase_event(trace_ctx, phase="narrator_call_finished", success=True, extra={"attempt": attempt})
            except Exception as exc:
                classified = classify_turn_exception(exc, phase="narrator_call_finished", trace_ctx=trace_ctx)
                emit_turn_phase_event(
                    trace_ctx,
                    phase="narrator_call_finished",
                    success=False,
                    error_code=classified.error_code,
                    error_class=classified.cause_class or exc.__class__.__name__,
                    message=(classified.cause_message or str(exc))[:240],
                    extra={"attempt": attempt},
                )
                raise classified
            if not isinstance(out, dict) or "story" not in out or "patch" not in out or "requests" not in out:
                if attempt < MAX_TURN_MODEL_ATTEMPTS:
                    prompt_attempt_user = (
                        user_prompt
                        + "\n\nDEINE LETZTE ANTWORT HATTE EIN UNGÜLTIGES FORMAT. "
                        + "Antworte NUR als valides JSON mit genau den Feldern story (string), patch (object), requests (array). "
                        + "Kein Markdown, kein Freitext außerhalb des JSON."
                    )
                    continue
                actor_name = display_name_for_slot(campaign, actor) if actor else "Die Figur"
                fallback_story = (
                    f"{actor_name} setzt die Handlung fort und reagiert direkt auf die letzte Aktion. "
                    "Die Szene bleibt in Bewegung, ohne den bisherigen Kanon zu brechen."
                )
                out = {
                    "story": fallback_story,
                    "patch": blank_patch(),
                    "requests": [{"type": "none", "actor": actor}],
                }
                break
            inactive_refs = inactive_character_refs(campaign, out.get("story", ""), out.get("patch") or {})
            if inactive_refs:
                if attempt == MAX_TURN_MODEL_ATTEMPTS:
                    raise narrator_turn_error(f"Die KI hat wiederholt ungültige Figuren eingeführt: {', '.join(inactive_refs)}.")
                prompt_attempt_user = (
                    user_prompt
                    + "\n\nDEINE LETZTE ANTWORT HAT INAKTIVE ODER UNFERTIGE FIGUREN EINGEFÜHRT ("
                    + ", ".join(inactive_refs)
                    + "). Nutze ausschließlich die Figuren aus active_party."
                )
                continue
            quality_issues = response_quality_issues(campaign, actor, action_type, content, out, out.get("patch") or {})
            if quality_issues:
                only_repetition = set(quality_issues).issubset(repetition_issue_messages())
                if attempt == MAX_TURN_MODEL_ATTEMPTS and only_repetition:
                    break
                if attempt == MAX_TURN_MODEL_ATTEMPTS:
                    # Hard fail here blocks gameplay loops. After max retries, accept the best effort
                    # response and continue the turn pipeline instead of returning 500.
                    break
                prompt_attempt_user = (
                    user_prompt
                    + "\n\nDEINE LETZTE ANTWORT WAR QUALITATIV NICHT AKZEPTABEL:\n- "
                    + "\n- ".join(quality_issues)
                    + "\n"
                    + build_repetition_retry_instruction(campaign, content)
                    + "\nSchreibe die Szene neu. Reagiere direkt auf die letzte Aktion, entwickle die Lage sichtbar weiter und liefere nur konkrete, nicht-generische Requests."
                )
                continue
            if not is_suspicious_story_text(out.get("story", "")):
                break
            if attempt == MAX_TURN_MODEL_ATTEMPTS:
                raise narrator_turn_error("Die KI-Antwort wirkt abgeschnitten.")
            prompt_attempt_user = (
                user_prompt
                + "\n\nDEINE LETZTE ANTWORT WAR OFFENSICHTLICH ABGESCHNITTEN. "
                + "Schreibe dieselbe Szene erneut, aber diesmal als vollstaendige, abgeschlossene Prosa ohne abgebrochene Zeichen, ohne endenden Backslash und ohne offenen Satz."
            )

        if not isinstance(out, dict):
            out = {
                "story": "Die Szene wird fortgesetzt. Die Lage entwickelt sich konsistent weiter.",
                "patch": blank_patch(),
                "requests": [{"type": "none", "actor": actor}],
            }
        requests_payload = normalize_requests_payload(out.get("requests", []), default_actor=actor)
        try:
            out["story"] = rewrite_story_length_guard(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                story_text=out.get("story", ""),
                patch=out.get("patch") or blank_patch(),
                requests_payload=requests_payload,
                min_story_chars=min_story_chars,
                max_story_chars=max_story_chars,
            )
        except Exception as exc:
            raise classify_turn_exception(exc, phase="narrator_call_finished", trace_ctx=trace_ctx)

        try:
            emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "narrator"})
            narrator_patch = sanitize_patch(working_state, out["patch"])
            emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "narrator", "result": "ok"})
        except Exception as exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="patch_sanitize",
                success=False,
                error_code=ERROR_CODE_PATCH_SANITIZE,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": "narrator"},
            )
            raise turn_flow_error(
                error_code=ERROR_CODE_PATCH_SANITIZE,
                phase="patch_sanitize",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        narrator_patch, attribute_delta_adjustments = apply_attribute_bias_to_patch(narrator_patch, actor, attribute_bias)
        if attribute_delta_adjustments:
            resource_deltas_applied["attribute_bias"] = attribute_delta_adjustments
        skill_cost_payload = infer_skill_cost_deltas_from_text(
            working_state,
            actor,
            action_type,
            f"{content}\n{out.get('story', '')}",
            combat_context=combat_context,
        )
        if skill_cost_payload.get("deltas"):
            narrator_patch = apply_skill_cost_deltas_to_patch(narrator_patch, actor, skill_cost_payload)
            resource_deltas_applied["skill_cost"] = deep_copy(skill_cost_payload.get("deltas") or {})
            resource_deltas_applied["skill_cost_skills"] = deep_copy(skill_cost_payload.get("skills") or [])
        narrator_patch, combat_scaling_meta = apply_combat_scaling_to_patch(
            narrator_patch,
            actor=actor,
            combat_context=combat_context,
            scaling_context=combat_scaling_context,
            action_type=action_type,
        )
        if combat_scaling_meta.get("applied"):
            resource_deltas_applied["combat_scaling"] = deep_copy(combat_scaling_meta)
        narrator_patch = enforce_non_milestone_patch_limits(
            working_state,
            narrator_patch,
            is_milestone=bool(milestone_info.get("is_milestone")),
            action_type=action_type,
        )
        narrator_patch = enforce_progression_set_mode_limits(narrator_patch, action_type=action_type)
        try:
            emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "narrator"})
            validate_patch(working_state, narrator_patch)
            emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "narrator", "result": "ok"})
        except Exception as exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="schema_validation",
                success=False,
                error_code=ERROR_CODE_SCHEMA_VALIDATION,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": "narrator"},
            )
            raise turn_flow_error(
                error_code=ERROR_CODE_SCHEMA_VALIDATION,
                phase="schema_validation",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        try:
            emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "narrator"})
            working_state = apply_patch(working_state, narrator_patch, attribute_cap=attribute_cap_for_campaign(campaign))
            emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "narrator", "result": "ok"})
        except Exception as exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="patch_apply",
                success=False,
                error_code=ERROR_CODE_PATCH_APPLY,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": "narrator"},
            )
            raise turn_flow_error(
                error_code=ERROR_CODE_PATCH_APPLY,
                phase="patch_apply",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        for source_text, source_kind in ((content, "player"), (out.get("story", ""), "narrator")):
            emit_turn_phase_event(trace_ctx, phase="extractor_patch_generation", success=True, extra={"stage": source_kind})
            try:
                extractor_piece = call_canon_extractor(campaign, working_state, actor, action_type, source_text, source=source_kind)
                emit_turn_phase_event(
                    trace_ctx,
                    phase="extractor_patch_generation",
                    success=True,
                    extra={"stage": source_kind, "result": "ok"},
                )
            except Exception as exc:
                emit_turn_phase_event(
                    trace_ctx,
                    phase="extractor_patch_generation",
                    success=False,
                    error_code=ERROR_CODE_EXTRACTOR,
                    error_class=exc.__class__.__name__,
                    message=str(exc)[:240],
                    extra={"stage": source_kind},
                )
                raise turn_flow_error(
                    error_code=ERROR_CODE_EXTRACTOR,
                    phase="extractor_patch_generation",
                    trace_ctx=trace_ctx,
                    exc=exc,
                )
            emit_turn_phase_event(trace_ctx, phase="extractor_patch_apply", success=True, extra={"stage": source_kind})
            try:
                emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": f"extractor_{source_kind}"})
                extractor_piece = sanitize_patch(working_state, extractor_piece)
                emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": f"extractor_{source_kind}", "result": "ok"})
            except Exception as exc:
                emit_turn_phase_event(
                    trace_ctx,
                    phase="patch_sanitize",
                    success=False,
                    error_code=ERROR_CODE_PATCH_SANITIZE,
                    error_class=exc.__class__.__name__,
                    message=str(exc)[:240],
                    extra={"stage": f"extractor_{source_kind}"},
                )
                emit_turn_phase_event(
                    trace_ctx,
                    phase="extractor_patch_apply",
                    success=False,
                    error_code=ERROR_CODE_PATCH_SANITIZE,
                    error_class=exc.__class__.__name__,
                    message=str(exc)[:240],
                    extra={"stage": source_kind},
                )
                raise turn_flow_error(
                    error_code=ERROR_CODE_PATCH_SANITIZE,
                    phase="patch_sanitize",
                    trace_ctx=trace_ctx,
                    exc=exc,
                )
            extractor_piece = enforce_non_milestone_patch_limits(
                working_state,
                extractor_piece,
                is_milestone=bool(milestone_info.get("is_milestone")),
                action_type=action_type,
            )
            extractor_piece = enforce_progression_set_mode_limits(extractor_piece, action_type=action_type)
            try:
                emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": f"extractor_{source_kind}"})
                validate_patch(working_state, extractor_piece)
                emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": f"extractor_{source_kind}", "result": "ok"})
            except Exception as exc:
                emit_turn_phase_event(
                    trace_ctx,
                    phase="schema_validation",
                    success=False,
                    error_code=ERROR_CODE_SCHEMA_VALIDATION,
                    error_class=exc.__class__.__name__,
                    message=str(exc)[:240],
                    extra={"stage": f"extractor_{source_kind}"},
                )
                emit_turn_phase_event(
                    trace_ctx,
                    phase="extractor_patch_apply",
                    success=False,
                    error_code=ERROR_CODE_SCHEMA_VALIDATION,
                    error_class=exc.__class__.__name__,
                    message=str(exc)[:240],
                    extra={"stage": source_kind},
                )
                raise turn_flow_error(
                    error_code=ERROR_CODE_SCHEMA_VALIDATION,
                    phase="schema_validation",
                    trace_ctx=trace_ctx,
                    exc=exc,
                )
            try:
                emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": f"extractor_{source_kind}"})
                working_state = apply_patch(working_state, extractor_piece, attribute_cap=attribute_cap_for_campaign(campaign))
                emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": f"extractor_{source_kind}", "result": "ok"})
                emit_turn_phase_event(trace_ctx, phase="extractor_patch_apply", success=True, extra={"stage": source_kind, "result": "ok"})
            except Exception as exc:
                emit_turn_phase_event(
                    trace_ctx,
                    phase="patch_apply",
                    success=False,
                    error_code=ERROR_CODE_PATCH_APPLY,
                    error_class=exc.__class__.__name__,
                    message=str(exc)[:240],
                    extra={"stage": f"extractor_{source_kind}"},
                )
                emit_turn_phase_event(
                    trace_ctx,
                    phase="extractor_patch_apply",
                    success=False,
                    error_code=ERROR_CODE_PATCH_APPLY,
                    error_class=exc.__class__.__name__,
                    message=str(exc)[:240],
                    extra={"stage": source_kind},
                )
                raise turn_flow_error(
                    error_code=ERROR_CODE_PATCH_APPLY,
                    phase="patch_apply",
                    trace_ctx=trace_ctx,
                    exc=exc,
                )
            extractor_patch = merge_patch_payloads(extractor_patch, extractor_piece)
        gm_text_display = out["story"]

    response_ready_ts = time.time()
    if request_received_ts is not None:
        update_turn_timing_ema(working_state, float(request_received_ts), response_ready_ts)
    compute_turn_budget_estimates(working_state)
    milestone_after = milestone_state_for_turn(int((working_state.get("meta") or {}).get("turn", 0) or 0), active_pacing_profile(working_state))
    working_state.setdefault("meta", {})
    working_state["meta"]["last_milestone_turn"] = int(milestone_after["last"])
    working_state["meta"]["next_milestone_turn"] = int(milestone_after["next"])

    patch = merge_patch_payloads(narrator_patch, extractor_patch)
    canon_gate_result = run_canon_gate(
        campaign,
        state_before=state_before,
        state_after=working_state,
        patch=patch,
        actor=actor,
        action_type=action_type,
        player_text=content,
        story_text=gm_text_display,
        trace_ctx=trace_ctx,
    )
    patch = normalize_patch_semantics(canon_gate_result.get("patch") or patch)
    working_state = canon_gate_result.get("state") if isinstance(canon_gate_result.get("state"), dict) else working_state
    canon_gate_meta = deep_copy(canon_gate_result.get("meta") or {})
    combat_resolution = apply_attribute_bias_to_resolution(
        {
            "damage_taken": abs(int((resource_deltas_applied.get("attribute_bias") or {}).get("hp_delta", 0) or 0)),
            "cost": abs(int((resource_deltas_applied.get("attribute_bias") or {}).get("stamina_delta", 0) or 0))
            + abs(int((resource_deltas_applied.get("attribute_bias") or {}).get("res_delta", 0) or 0)),
        },
        attribute_bias,
    )
    updated_combat = update_combat_meta_after_turn(
        working_state,
        actor=actor,
        action_type=action_type,
        input_text=content,
        story_text=gm_text_display,
        patch=patch,
        combat_context=combat_context,
        resolution_summary=combat_resolution,
    )
    attribute_meta = normalize_attribute_influence_meta(working_state.setdefault("meta", {}))
    attribute_meta["last_turn"] = int((working_state.get("meta") or {}).get("turn", 0) or 0)
    attribute_meta["last_actor"] = actor
    attribute_meta["last_profile"] = {
        "primary_attributes": deep_copy(attribute_profile.get("primary_attributes") or []),
        "influence_tier": str(attribute_profile.get("influence_tier") or "none"),
        "narrative_bias": deep_copy(attribute_profile.get("narrative_bias") or []),
        "mechanical_bias": {
            "damage_taken_mult": float(attribute_bias.get("damage_taken_mult", 1.0)),
            "cost_mult": float(attribute_bias.get("cost_mult", 1.0)),
            "complication_mult": float(attribute_bias.get("complication_mult", 1.0)),
            "outgoing_effect_mult": float(attribute_bias.get("outgoing_effect_mult", 1.0)),
        },
    }
    state_after = working_state
    append_character_change_events(state_before, state_after, turn_number=int(state_after.get("meta", {}).get("turn", 0) or 0))
    progression_result = apply_progression_events(
        campaign,
        state_before,
        state_after,
        patch,
        actor=actor,
        action_type=action_type,
        player_text=content,
        story_text=gm_text_display,
    )
    skill_messages = apply_skill_events(campaign, state_after, patch.get("events_add") or [])
    if skill_messages:
        state_after.setdefault("events", [])
        state_after["events"].extend(skill_messages)
    npc_source_story = gm_text_display if action_type != "canon" else ""
    emit_turn_phase_event(trace_ctx, phase="npc_extractor", success=True, extra={"stage": "start"})
    try:
        npc_upserts = call_npc_extractor(
            campaign,
            state_after,
            actor,
            action_type,
            content,
            npc_source_story,
        )
        npc_updates = apply_npc_upserts(
            campaign,
            state_after,
            npc_upserts,
            source_text=f"{content}\n{npc_source_story}".strip(),
            turn_number=int(state_after.get("meta", {}).get("turn", 0) or 0),
        )
        emit_turn_phase_event(trace_ctx, phase="npc_extractor", success=True, extra={"stage": "ok", "upserts": len(npc_upserts or [])})
    except Exception as exc:
        emit_turn_phase_event(
            trace_ctx,
            phase="npc_extractor",
            success=False,
            error_code=ERROR_CODE_EXTRACTOR,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
        )
        raise turn_flow_error(
            error_code=ERROR_CODE_EXTRACTOR,
            phase="npc_extractor",
            trace_ctx=trace_ctx,
            exc=exc,
        )
    codex_trigger_bundle = collect_codex_triggers(
        campaign,
        state_after,
        actor=actor,
        action_type=action_type,
        player_text=content,
        gm_text=npc_source_story or gm_text_display,
        patch=patch,
        npc_updates=npc_updates,
        turn_number=int(state_after.get("meta", {}).get("turn", 0) or 0),
    )
    codex_updates = apply_codex_triggers(
        state_after,
        codex_trigger_bundle,
        turn_number=int(state_after.get("meta", {}).get("turn", 0) or 0),
    )
    skill_requests = build_skill_system_requests(campaign, state_before, state_after)
    now = utc_now()
    combined_requests = normalize_requests_payload(requests_payload + skill_requests, default_actor=actor)
    input_text_display = "" if is_continue_story_content(content) else content
    turn_record = {
        "turn_id": make_id("turn"),
        "turn_number": len(campaign.get("turns", [])) + 1,
        "status": "active",
        "actor": actor,
        "player_id": player_id,
        "action_type": action_type,
        "input_text_raw": content,
        "input_text_display": input_text_display,
        "gm_text_raw": gm_text_display,
        "gm_text_display": gm_text_display,
        "requests": combined_requests,
        "patch": patch,
        "narrator_patch": narrator_patch,
        "extractor_patch": extractor_patch,
        "source_mode": action_type,
        "canon_applied": canon_applied,
        "attribute_profile": deep_copy(attribute_profile),
        "combat_resolution": deep_copy(combat_resolution),
        "resource_deltas_applied": deep_copy(resource_deltas_applied),
        "progression_events": deep_copy(progression_result.get("events") or []),
        "canon_gate": deep_copy(canon_gate_meta),
        "npc_updates": deep_copy(npc_updates),
        "codex_updates": deep_copy(codex_updates),
        "combat_meta": deep_copy(updated_combat),
        "state_before": state_before,
        "state_after": deep_copy(state_after),
        "retry_of_turn_id": retry_of_turn_id,
        "edited_at": None,
        "created_at": now,
        "updated_at": now,
        "edit_history": [],
        "prompt_payload": prompt_payload,
    }
    if isinstance(trace_ctx, dict):
        trace_ctx["turn_id"] = turn_record["turn_id"]
    campaign["state"] = state_after
    normalize_npc_codex_state(campaign)
    campaign.setdefault("turns", []).append(turn_record)
    remember_recent_story(campaign)
    rebuild_memory_summary(campaign)
    return turn_record

def find_turn(campaign: Dict[str, Any], turn_id: str) -> Dict[str, Any]:
    for turn in campaign.get("turns", []):
        if turn["turn_id"] == turn_id:
            return turn
    raise HTTPException(status_code=404, detail="Turn nicht gefunden.")

def reset_turn_branch(campaign: Dict[str, Any], turn: Dict[str, Any], new_status: str) -> None:
    if turn["status"] != "active":
        raise HTTPException(status_code=409, detail="Nur aktive Turns können rückgängig gemacht oder neu aufgebaut werden.")
    campaign["state"] = deep_copy(turn["state_before"])
    for current_turn in campaign.get("turns", []):
        if current_turn["status"] == "active" and current_turn["turn_number"] >= turn["turn_number"]:
            current_turn["status"] = new_status
            current_turn["updated_at"] = utc_now()
    remember_recent_story(campaign)
    rebuild_memory_summary(campaign)

