import json
import re
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.services.turn.patch_sanitizer import (
    PatchSanitizerDependencies,
    configure as configure_patch_sanitizer,
    sanitize_patch,
)
from app.services.turn.patch_apply_abilities import apply_patch_character_ability_potential_updates
from app.services.turn.patch_apply_bio import apply_patch_character_bio_updates
from app.services.turn.patch_apply_conditions import apply_patch_character_condition_effect_updates
from app.services.turn.patch_apply_events import apply_patch_event_updates
from app.services.turn.patch_apply_injuries import apply_patch_character_injury_appearance_updates
from app.services.turn.patch_apply_inventory import apply_patch_character_inventory_equipment_updates
from app.services.turn.patch_apply_progression import apply_patch_character_progression_updates
from app.services.turn.patch_apply_skills import apply_patch_character_skill_updates
from app.services.turn.patch_apply_class import apply_patch_character_class_updates
from app.services.turn.patch_apply_items import apply_patch_item_updates
from app.services.turn.patch_apply_journal_factions import apply_patch_character_journal_faction_updates
from app.services.turn.patch_apply_map import apply_patch_map_updates
from app.services.turn.patch_apply_meta import apply_patch_meta_updates
from app.services.turn.patch_apply_normalization import apply_patch_character_late_normalization
from app.services.turn.patch_apply_plotpoints import apply_patch_plotpoint_updates
from app.services.turn.patch_apply_resources import apply_patch_character_resource_attribute_updates
from app.services.turn.patch_apply_time import apply_patch_time_advance
from app.services.turn.patch_limits import (
    enforce_non_milestone_patch_limits as _enforce_non_milestone_patch_limits,
    enforce_progression_set_mode_limits as _enforce_progression_set_mode_limits,
)
from app.services.turn.patch_validator import (
    PatchValidatorDependencies,
    configure as configure_patch_validator,
    validate_patch,
)
from app.services.turn.prompt_payloads import build_turn_system_prompt, build_turn_user_prompt
from app.services.turn.records import build_turn_record_payload
from app.services.turn.story_length_guard import (
    rewrite_story_length_guard as _rewrite_story_length_guard,
)

_CONFIGURED = False
_PATCH_SANITIZER_DEP_NAMES = (
    "normalize_patch_semantics",
    "deep_copy",
    "clean_auto_item_name",
    "clean_creator_item_name",
    "ensure_item_shape",
    "infer_item_slot_from_definition",
    "normalize_equipment_slot_key",
    "normalize_equipment_update_payload",
    "item_matches_equipment_slot",
    "normalize_class_current",
    "skill_id_from_name",
    "normalize_dynamic_skill_state",
    "resource_name_for_character",
    "normalize_skill_elements_for_world",
    "normalize_progression_event_list",
    "normalize_injury_state",
    "normalize_scar_state",
    "normalize_plotpoint_entry",
    "normalize_plotpoint_update_entry",
    "clean_scene_name",
    "is_plausible_scene_name",
    "is_generic_scene_identifier",
    "clamp",
    "normalize_event_entry",
)
_PATCH_VALIDATOR_DEP_NAMES = (
    "normalize_patch_semantics",
    "resource_name_for_character",
    "normalize_dynamic_skill_state",
    "normalize_skill_elements_for_world",
    "normalized_eval_text",
    "normalize_class_current",
    "resolve_class_element_id",
    "normalize_skill_rank",
    "normalize_progression_event_list",
    "is_skill_manifestation_name_plausible",
    "normalize_injury_state",
    "normalize_scar_state",
    "normalize_equipment_update_payload",
    "item_matches_equipment_slot",
    "UNIVERSAL_SKILL_LIKE_NAMES",
    "INJURY_SEVERITIES",
    "INJURY_HEALING_STAGES",
)


def _configure_patch_sanitizer_if_ready() -> None:
    if any(name not in globals() for name in _PATCH_SANITIZER_DEP_NAMES):
        return
    configure_patch_sanitizer(
        PatchSanitizerDependencies(
            normalize_patch_semantics=normalize_patch_semantics,
            deep_copy=deep_copy,
            clean_auto_item_name=clean_auto_item_name,
            clean_creator_item_name=clean_creator_item_name,
            ensure_item_shape=ensure_item_shape,
            infer_item_slot_from_definition=infer_item_slot_from_definition,
            normalize_equipment_slot_key=normalize_equipment_slot_key,
            normalize_equipment_update_payload=normalize_equipment_update_payload,
            item_matches_equipment_slot=item_matches_equipment_slot,
            normalize_class_current=normalize_class_current,
            skill_id_from_name=skill_id_from_name,
            normalize_dynamic_skill_state=normalize_dynamic_skill_state,
            resource_name_for_character=resource_name_for_character,
            normalize_skill_elements_for_world=normalize_skill_elements_for_world,
            normalize_progression_event_list=normalize_progression_event_list,
            normalize_injury_state=normalize_injury_state,
            normalize_scar_state=normalize_scar_state,
            normalize_plotpoint_entry=normalize_plotpoint_entry,
            normalize_plotpoint_update_entry=normalize_plotpoint_update_entry,
            clean_scene_name=clean_scene_name,
            is_plausible_scene_name=is_plausible_scene_name,
            is_generic_scene_identifier=is_generic_scene_identifier,
            clamp=clamp,
            normalize_event_entry=normalize_event_entry,
        )
    )


def _configure_patch_validator_if_ready() -> None:
    if any(name not in globals() for name in _PATCH_VALIDATOR_DEP_NAMES):
        return
    configure_patch_validator(
        PatchValidatorDependencies(
            normalize_patch_semantics=normalize_patch_semantics,
            resource_name_for_character=resource_name_for_character,
            normalize_dynamic_skill_state=normalize_dynamic_skill_state,
            normalize_skill_elements_for_world=normalize_skill_elements_for_world,
            normalized_eval_text=normalized_eval_text,
            normalize_class_current=normalize_class_current,
            resolve_class_element_id=resolve_class_element_id,
            normalize_skill_rank=normalize_skill_rank,
            normalize_progression_event_list=normalize_progression_event_list,
            is_skill_manifestation_name_plausible=is_skill_manifestation_name_plausible,
            normalize_injury_state=normalize_injury_state,
            normalize_scar_state=normalize_scar_state,
            normalize_equipment_update_payload=normalize_equipment_update_payload,
            item_matches_equipment_slot=item_matches_equipment_slot,
            universal_skill_like_names=set(UNIVERSAL_SKILL_LIKE_NAMES),
            injury_severities=set(INJURY_SEVERITIES),
            injury_healing_stages=set(INJURY_HEALING_STAGES),
        )
    )

def configure(main_globals: Dict[str, Any]) -> None:
    """Inject main-module globals needed by extracted turn engine functions."""
    global _CONFIGURED
    globals().update(main_globals)
    _configure_patch_sanitizer_if_ready()
    _configure_patch_validator_if_ready()
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

def apply_patch(state: Dict[str, Any], patch: Dict[str, Any], *, attribute_cap: int = 10) -> Dict[str, Any]:
    patch = normalize_patch_semantics(patch)
    attribute_cap = max(1, int(attribute_cap or 10))
    apply_patch_item_updates(state, patch, ensure_item_shape=ensure_item_shape)

    apply_patch_plotpoint_updates(
        state,
        patch,
        normalize_plotpoint_entry=normalize_plotpoint_entry,
        normalize_plotpoint_update_entry=normalize_plotpoint_update_entry,
    )

    apply_patch_map_updates(state, patch)

    apply_patch_time_advance(state, patch, apply_world_time_advance=apply_world_time_advance)

    effective_world_time = normalize_world_time(state.get("meta", {}))
    for slot_name, upd in (patch.get("characters") or {}).items():
        if slot_name not in state["characters"]:
            continue
        character = state["characters"][slot_name]
        ensure_progression_shape(character)
        ensure_character_progression_core(character)
        apply_patch_character_bio_updates(character, upd)
        apply_patch_character_resource_attribute_updates(
            character,
            upd,
            world_settings=((state.get("world") or {}).get("settings") or {}),
            clamp=clamp,
            attribute_cap=attribute_cap,
            attribute_keys=ATTRIBUTE_KEYS,
            canonical_resources_set_from_payload=canonical_resources_set_from_payload,
            legacy_misc_resources_set_from_payload=legacy_misc_resources_set_from_payload,
            canonical_resource_deltas_from_update=canonical_resource_deltas_from_update,
            legacy_misc_resource_deltas_from_update=legacy_misc_resource_deltas_from_update,
        )

        apply_patch_character_skill_updates(
            character,
            upd,
            state,
            resource_name_for_character=resource_name_for_character,
            normalize_dynamic_skill_state=normalize_dynamic_skill_state,
            normalize_skill_elements_for_world=normalize_skill_elements_for_world,
            normalized_eval_text=normalized_eval_text,
            merge_dynamic_skill=merge_dynamic_skill,
            effective_skill_progress_multiplier=effective_skill_progress_multiplier,
            clamp=clamp,
            next_skill_xp_for_level=next_skill_xp_for_level,
            DEFAULT_DYNAMIC_SKILL_LEVEL_MAX=DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
            DEFAULT_NUMERIC_SKILL_DELTA_XP=DEFAULT_NUMERIC_SKILL_DELTA_XP,
        )

        apply_patch_character_condition_effect_updates(character, upd)

        apply_patch_character_inventory_equipment_updates(
            character,
            upd,
            normalize_equipment_update_payload=normalize_equipment_update_payload,
        )

        skill_store = character.setdefault("skills", {})
        resource_name = resource_name_for_character(character, ((state.get("world") or {}).get("settings") or {}))
        apply_patch_character_ability_potential_updates(
            character,
            upd,
            slot_name=slot_name,
            skill_store=skill_store,
            resource_name=resource_name,
            enable_legacy_shadow_writeback=ENABLE_LEGACY_SHADOW_WRITEBACK,
            make_id=make_id,
            normalize_ability_state=normalize_ability_state,
            normalize_dynamic_skill_state=normalize_dynamic_skill_state,
            skill_id_from_name=skill_id_from_name,
            normalize_skill_rank=normalize_skill_rank,
            next_skill_xp_for_level=next_skill_xp_for_level,
            merge_dynamic_skill=merge_dynamic_skill,
        )

        apply_patch_character_progression_updates(
            character,
            upd,
            deep_copy=deep_copy,
            normalize_class_current=normalize_class_current,
            default_class_current=default_class_current,
        )
        apply_patch_character_journal_faction_updates(
            character,
            upd,
            deep_copy=deep_copy,
            include_factions=False,
        )

        apply_patch_character_class_updates(
            character,
            upd,
            state,
            deep_copy=deep_copy,
            normalize_class_current=normalize_class_current,
            default_class_current=default_class_current,
            resolve_class_element_id=resolve_class_element_id,
            ensure_class_rank_core_skills=ensure_class_rank_core_skills,
        )
        apply_patch_character_journal_faction_updates(
            character,
            upd,
            deep_copy=deep_copy,
            include_journal=False,
        )
        apply_patch_character_injury_appearance_updates(
            character,
            upd,
            deep_copy=deep_copy,
        )

        apply_patch_character_late_normalization(
            character,
            state,
            slot_name,
            resource_name=resource_name,
            effective_world_time=effective_world_time,
            ENABLE_LEGACY_SHADOW_WRITEBACK=ENABLE_LEGACY_SHADOW_WRITEBACK,
            ensure_progression_shape=ensure_progression_shape,
            ensure_character_progression_core=ensure_character_progression_core,
            normalize_skill_store=normalize_skill_store,
            resolve_injury_healing=resolve_injury_healing,
            rebuild_character_derived=rebuild_character_derived,
            reconcile_canonical_resources=reconcile_canonical_resources,
            strip_legacy_shadow_fields=strip_legacy_shadow_fields,
            write_legacy_shadow_fields=write_legacy_shadow_fields,
            sync_scars_into_appearance=sync_scars_into_appearance,
        )

    apply_patch_meta_updates(state, patch)

    apply_patch_event_updates(state, patch, normalize_event_entry=normalize_event_entry)
    return state

def enforce_non_milestone_patch_limits(state: Dict[str, Any], patch: Dict[str, Any], *, is_milestone: bool, action_type: str) -> Dict[str, Any]:
    return _enforce_non_milestone_patch_limits(
        state,
        patch,
        is_milestone=is_milestone,
        action_type=action_type,
        deep_copy=deep_copy,
        normalize_class_current=normalize_class_current,
        class_rank_sort_value=class_rank_sort_value,
        normalize_dynamic_skill_state=normalize_dynamic_skill_state,
        resource_name_for_character=resource_name_for_character,
        normalize_skill_rank=normalize_skill_rank,
    )

def enforce_progression_set_mode_limits(patch: Dict[str, Any], *, action_type: str) -> Dict[str, Any]:
    return _enforce_progression_set_mode_limits(
        patch,
        action_type=action_type,
        deep_copy=deep_copy,
        blank_patch=blank_patch,
        progression_set_direct_keys=PROGRESSION_SET_DIRECT_KEYS,
    )

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
    return _rewrite_story_length_guard(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        story_text=story_text,
        patch=patch,
        requests_payload=requests_payload,
        min_story_chars=min_story_chars,
        max_story_chars=max_story_chars,
        min_story_rewrite_attempts=MIN_STORY_REWRITE_ATTEMPTS,
        max_story_compress_attempts=MAX_STORY_COMPRESS_ATTEMPTS,
        story_rewrite_schema=STORY_REWRITE_SCHEMA,
        ollama_temperature=OLLAMA_TEMPERATURE,
        call_ollama_schema=call_ollama_schema,
        http_exception_type=HTTPException,
    )

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
    user_prompt, actor_display, actor_resolution_hint = build_turn_user_prompt(
        campaign=campaign,
        actor=actor,
        action_type=action_type,
        content=content,
        context=context,
        turn_mode_guide=TURN_MODE_GUIDE,
        turn_response_json_contract=TURN_RESPONSE_JSON_CONTRACT,
        display_name_for_slot=display_name_for_slot,
        is_slot_id=is_slot_id,
        is_first_person_action=is_first_person_action,
    )
    system_prompt = build_turn_system_prompt(
        system_prompt_base=SYSTEM_PROMPT,
        turn_mode_guide=TURN_MODE_GUIDE,
        pacing_text=pacing_block["text"],
        attribute_prompt_hints=attribute_prompt_hints,
        combat_scaling_context=combat_scaling_context,
        min_story_chars=min_story_chars,
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
    turn_record = build_turn_record_payload(
        campaign=campaign,
        actor=actor,
        player_id=player_id,
        action_type=action_type,
        content=content,
        gm_text_display=gm_text_display,
        requests_payload=requests_payload,
        skill_requests=skill_requests,
        patch=patch,
        narrator_patch=narrator_patch,
        extractor_patch=extractor_patch,
        canon_applied=canon_applied,
        attribute_profile=attribute_profile,
        combat_resolution=combat_resolution,
        resource_deltas_applied=resource_deltas_applied,
        progression_result=progression_result,
        canon_gate_meta=canon_gate_meta,
        npc_updates=npc_updates,
        codex_updates=codex_updates,
        updated_combat=updated_combat,
        state_before=state_before,
        state_after=state_after,
        retry_of_turn_id=retry_of_turn_id,
        prompt_payload=prompt_payload,
        make_id=make_id,
        utc_now=utc_now,
        deep_copy=deep_copy,
        normalize_requests_payload=normalize_requests_payload,
        is_continue_story_content=is_continue_story_content,
    )
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
