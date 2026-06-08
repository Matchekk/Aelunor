from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.catalogs.runtime_catalogs import PROGRESSION_EXTRACTOR_SCHEMA
from app.config.progression import (
    DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
    PROGRESSION_CLAIM_TYPES,
    PROGRESSION_DENSITY_CAP_MILESTONE,
    PROGRESSION_DENSITY_CAP_NON_MILESTONE,
    PROGRESSION_EVENT_PRIORITY,
    PROGRESSION_EVENT_SEVERITIES,
    PROGRESSION_EVENT_TYPES,
    PROGRESSION_EXTRACTOR_CONFIDENCE_ORDER,
    PROGRESSION_EXTRACTOR_CONFIDENCE_SCORE,
    PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS,
)
from app.config.runtime import CAMPAIGN_LENGTHS, PACING_PROFILE_DEFAULTS
from app.core.ids import deep_copy
from app.prompts.system_prompts import PROGRESSION_EXTRACTOR_JSON_CONTRACT, PROGRESSION_EXTRACTOR_SYSTEM_PROMPT
from app.services.campaigns.party import display_name_for_slot
from app.services.characters.resources import resource_name_for_character
from app.services.extraction.abilities import clean_extracted_skill_name, story_sentences_for_actor
from app.services.patch_payloads import normalize_patch_semantics
from app.services.world.math_utils import clamp
from app.services.world.progression import normalize_class_current
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import (
    ABILITY_UNLOCK_GENERIC_NAMES,
    PROGRESSION_CLAIM_CUES,
    SKILL_MANIFESTATION_NAME_STOPWORDS,
    SKILL_MANIFESTATION_NAME_TOKEN_BLACKLIST,
    SKILL_MANIFESTATION_VERB_BLACKLIST,
    UNIVERSAL_SKILL_LIKE_NAMES,
)


def _missing_dependency(name: str) -> Callable[..., Any]:
    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"Progression gate dependency is not configured: {name}")
    return _missing


def _default_active_pacing_profile(state: Dict[str, Any]) -> Dict[str, Any]:
    settings = ((state.get("world") or {}).get("settings") or {})
    selected = str(settings.get("campaign_length") or "medium").lower()
    if selected not in CAMPAIGN_LENGTHS:
        selected = "medium"
    profile = deep_copy((settings.get("pacing_profile") or {}).get(selected) or PACING_PROFILE_DEFAULTS[selected])
    profile["campaign_length"] = selected
    profile["target_turn"] = (settings.get("target_turns") or {}).get(selected)
    return profile


def _default_milestone_state_for_turn(turn_number: int, profile: Dict[str, Any]) -> Dict[str, int | bool]:
    every = max(1, int(profile.get("milestone_every_n_turns", 18) or 18))
    current_turn = max(0, int(turn_number or 0))
    if current_turn <= 0:
        return {"is_milestone": False, "last": 0, "next": every}
    is_milestone = current_turn % every == 0
    last = current_turn if is_milestone else (current_turn // every) * every
    next_turn = current_turn + every if is_milestone else last + every
    return {"is_milestone": is_milestone, "last": last, "next": max(next_turn, every)}


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


@dataclass(frozen=True)
class ProgressionGateDependencies:
    active_pacing_profile: Callable[..., Dict[str, Any]] = _default_active_pacing_profile
    build_extractor_context_packet: Callable[..., str] = _missing_dependency("build_extractor_context_packet")
    call_ollama_schema: Callable[..., Dict[str, Any]] = _missing_dependency("call_ollama_schema")
    milestone_state_for_turn: Callable[..., Dict[str, int | bool]] = _default_milestone_state_for_turn
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]] = _missing_dependency("normalize_dynamic_skill_state")


_DEPS = ProgressionGateDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def active_pacing_profile(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.active_pacing_profile(*args, **kwargs)


def build_extractor_context_packet(*args: Any, **kwargs: Any) -> str:
    return _DEPS.build_extractor_context_packet(*args, **kwargs)


def call_ollama_schema(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.call_ollama_schema(*args, **kwargs)


def milestone_state_for_turn(*args: Any, **kwargs: Any) -> Dict[str, int | bool]:
    return _DEPS.milestone_state_for_turn(*args, **kwargs)


def normalize_dynamic_skill_state(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.normalize_dynamic_skill_state(*args, **kwargs)


def normalize_progression_event_severity(value: Any) -> str:
    severity = str(value or "medium").strip().lower()
    return severity if severity in PROGRESSION_EVENT_SEVERITIES else "medium"

def _safe_int(value: Any, default: int) -> int:
    """Coerce arbitrary (LLM-supplied) values to int, falling back to default.

    Prevents a non-numeric ``source_turn`` in an extractor patch from raising
    ValueError inside merge_progression_patch_additive, which runs outside the
    gate's try/except and would otherwise abort the entire turn."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_progression_event(
    raw_event: Any,
    *,
    actor: str,
    source_turn: int,
    default_type: str = "milestone_progress",
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_event, dict):
        return None
    event_type = str(raw_event.get("type") or default_type).strip().lower()
    if event_type not in PROGRESSION_EVENT_TYPES:
        return None
    normalized_actor = str(raw_event.get("actor") or actor or "").strip()
    if not normalized_actor:
        return None
    target_skill_id = str(raw_event.get("target_skill_id") or "").strip() or None
    target_class_id = str(raw_event.get("target_class_id") or "").strip() or None
    target_element_id = str(raw_event.get("target_element_id") or "").strip() or None
    reason = str(raw_event.get("reason") or "").strip()
    metadata = deep_copy(raw_event.get("metadata") or {})
    skill_payload = deep_copy(raw_event.get("skill") or {})
    tags = [str(tag).strip() for tag in (raw_event.get("tags") or []) if str(tag).strip()]
    if event_type == "skill_manifestation":
        tags = list(dict.fromkeys(tags + ["manifestation"]))
    return {
        "type": event_type,
        "actor": normalized_actor,
        "target_skill_id": target_skill_id,
        "target_class_id": target_class_id,
        "target_element_id": target_element_id,
        "severity": normalize_progression_event_severity(raw_event.get("severity")),
        "tags": list(dict.fromkeys(tags)),
        "source_turn": max(0, _safe_int(raw_event.get("source_turn"), source_turn)),
        "reason": reason,
        "metadata": metadata if isinstance(metadata, dict) else {},
        "skill": skill_payload if isinstance(skill_payload, dict) else {},
    }

def is_skill_manifestation_name_plausible(skill_name: str, actor_name: str) -> bool:
    clean = clean_extracted_skill_name(skill_name)
    normalized = normalized_eval_text(clean)
    actor_norm = normalized_eval_text(actor_name)
    if not clean or len(normalized) < 3:
        return False
    if len(clean) > 42:
        return False
    words = [word for word in re.split(r"\s+", clean.strip()) if word]
    if len(words) > 4:
        return False
    if normalized in UNIVERSAL_SKILL_LIKE_NAMES:
        return False
    if normalized in ABILITY_UNLOCK_GENERIC_NAMES:
        return False
    if normalized in SKILL_MANIFESTATION_VERB_BLACKLIST:
        return False
    normalized_words = [normalized_eval_text(word) for word in words]
    if any(word in SKILL_MANIFESTATION_VERB_BLACKLIST for word in normalized_words):
        return False
    if len(words) >= 3 and any(word in SKILL_MANIFESTATION_NAME_STOPWORDS for word in normalized_words):
        return False
    if any(fragment in normalized for fragment in SKILL_MANIFESTATION_NAME_TOKEN_BLACKLIST):
        return False
    if any(char.isdigit() for char in clean):
        return False
    if actor_norm and normalized == actor_norm:
        return False
    return True

def normalize_progression_event_list(
    events: Any,
    *,
    actor: str,
    source_turn: int,
) -> List[Dict[str, Any]]:
    if not isinstance(events, list):
        return []
    normalized_events: List[Dict[str, Any]] = []
    for raw_event in events:
        normalized_event = normalize_progression_event(raw_event, actor=actor, source_turn=source_turn)
        if normalized_event:
            normalized_events.append(normalized_event)
    return normalized_events

def progression_event_priority(event_type: str) -> int:
    return int(PROGRESSION_EVENT_PRIORITY.get(str(event_type or "").strip().lower(), 10))

def _event_origin(raw_event: Dict[str, Any]) -> str:
    metadata = raw_event.get("metadata") if isinstance(raw_event.get("metadata"), dict) else {}
    origin = str(metadata.get("origin") or "").strip().lower()
    return origin if origin in {"explicit_patch", "inferred_patch"} else "inferred_patch"

def reduce_progression_event_density(
    events: List[Dict[str, Any]],
    *,
    state_after: Dict[str, Any],
    action_type: str,
) -> List[Dict[str, Any]]:
    if action_type == "canon":
        return [deep_copy(entry) for entry in events if isinstance(entry, dict)]
    milestone = milestone_state_for_turn(
        int((state_after.get("meta") or {}).get("turn", 0) or 0),
        active_pacing_profile(state_after),
    )
    caps = PROGRESSION_DENSITY_CAP_MILESTONE if bool(milestone.get("is_milestone")) else PROGRESSION_DENSITY_CAP_NON_MILESTONE
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    actor_order: List[str] = []
    for idx, raw_event in enumerate(events):
        if not isinstance(raw_event, dict):
            continue
        actor = str(raw_event.get("actor") or "").strip()
        if not actor:
            continue
        if actor not in grouped:
            grouped[actor] = []
            actor_order.append(actor)
        entry = deep_copy(raw_event)
        entry["_index"] = idx
        grouped[actor].append(entry)

    reduced: List[Dict[str, Any]] = []
    for actor in actor_order:
        actor_events = grouped.get(actor, [])
        explicit_events: List[Dict[str, Any]] = []
        inferred_events: List[Dict[str, Any]] = []
        seen_keys: set[Tuple[str, str, str, str, str, str]] = set()
        for event in actor_events:
            dedupe_key = progression_event_dedupe_key(event) + (_event_origin(event),)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            if _event_origin(event) == "explicit_patch":
                explicit_events.append(event)
            else:
                inferred_events.append(event)

        inferred_events = sorted(
            inferred_events,
            key=lambda item: (
                -progression_event_priority(str(item.get("type") or "")),
                -{"low": 1, "medium": 2, "high": 3}.get(str(item.get("severity") or "medium").strip().lower(), 2),
                int(item.get("_index", 0) or 0),
            ),
        )
        selected = explicit_events + inferred_events[: max(0, int(caps["inferred"]))]
        selected = sorted(selected, key=lambda item: int(item.get("_index", 0) or 0))
        if not explicit_events:
            selected = selected[: max(1, int(caps["total"]))]
        for event in selected:
            event.pop("_index", None)
            reduced.append(event)
    return reduced

def patch_has_explicit_skill_progression_for_actor(patch: Dict[str, Any], actor: str) -> bool:
    actor_patch = ((patch.get("characters") or {}).get(actor) or {}) if isinstance((patch.get("characters") or {}), dict) else {}
    if not isinstance(actor_patch, dict):
        return False
    if (
        actor_patch.get("skills_set")
        or actor_patch.get("skills_delta")
        or actor_patch.get("abilities_add")
        or actor_patch.get("class_set")
        or actor_patch.get("class_update")
        or actor_patch.get("progression_set")
    ):
        return True
    explicit_events = normalize_progression_event_list(
        actor_patch.get("progression_events"),
        actor=actor,
        source_turn=0,
    )
    return bool(explicit_events)

def normalize_progression_claim_type(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in PROGRESSION_CLAIM_TYPES:
        return normalized
    return ""

def progression_claim_text_for_actor(story_text: str, actor_display: str) -> str:
    relevant = story_sentences_for_actor(story_text, actor_display)
    if relevant:
        return "\n".join(relevant)
    return str(story_text or "")

def detect_progression_claim_types(story_text: str, actor_display: str) -> List[str]:
    normalized_story = normalized_eval_text(progression_claim_text_for_actor(story_text, actor_display))
    if not normalized_story:
        return []
    detected: List[str] = []
    for claim_type, cues in PROGRESSION_CLAIM_CUES.items():
        if any(cue in normalized_story for cue in cues):
            detected.append(claim_type)
    return list(dict.fromkeys(detected))

def progression_claim_coverage_for_actor_patch(patch: Dict[str, Any], actor: str) -> Set[str]:
    coverage: Set[str] = set()
    actor_patch = ((patch.get("characters") or {}).get(actor) or {}) if isinstance((patch.get("characters") or {}), dict) else {}
    if not isinstance(actor_patch, dict):
        return coverage

    skills_set = actor_patch.get("skills_set") if isinstance(actor_patch.get("skills_set"), dict) else {}
    if skills_set:
        coverage.add("skill_claim")
        for raw_skill in skills_set.values():
            if isinstance(raw_skill, dict):
                if int(raw_skill.get("level", 1) or 1) > 1 or int(raw_skill.get("xp", 0) or 0) > 0:
                    coverage.add("skill_level_claim")
                break

    skills_delta = actor_patch.get("skills_delta") if isinstance(actor_patch.get("skills_delta"), dict) else {}
    if skills_delta:
        coverage.add("skill_level_claim")

    class_set = normalize_class_current(actor_patch.get("class_set"))
    if class_set:
        coverage.add("class_claim")
        if int(class_set.get("level", 1) or 1) > 1:
            coverage.add("class_level_claim")

    class_update = actor_patch.get("class_update") if isinstance(actor_patch.get("class_update"), dict) else {}
    if class_update:
        coverage.add("class_claim")
        if any(key in class_update for key in ("level", "xp", "xp_next", "rank")):
            coverage.add("class_level_claim")

    progression_set = actor_patch.get("progression_set") if isinstance(actor_patch.get("progression_set"), dict) else {}
    if progression_set:
        if any(key in progression_set for key in ("class_level", "class_xp", "class_xp_to_next")):
            coverage.add("class_level_claim")
        if any(key in progression_set for key in ("level", "xp_total", "xp_current", "xp_to_next")):
            coverage.add("skill_level_claim")

    explicit_events = normalize_progression_event_list(
        actor_patch.get("progression_events"),
        actor=actor,
        source_turn=0,
    )
    for event in explicit_events:
        event_type = str(event.get("type") or "").strip().lower()
        if event_type == "skill_manifestation":
            coverage.add("manifestation_claim")
            coverage.add("skill_claim")
        elif event_type in {"skill_mastery_use", "training_success"}:
            coverage.add("skill_level_claim")
        elif event_type == "class_breakthrough":
            coverage.add("class_claim")
            coverage.add("class_level_claim")
    return coverage

def normalized_progression_claims(claim_types: List[str]) -> List[str]:
    normalized = [normalize_progression_claim_type(entry) for entry in (claim_types or [])]
    return [entry for entry in list(dict.fromkeys(normalized)) if entry]

def progression_missing_claim_types(claim_types: List[str], coverage: Set[str]) -> List[str]:
    claims = normalized_progression_claims(claim_types)
    missing = [claim_type for claim_type in claims if claim_type not in (coverage or set())]
    return list(dict.fromkeys(missing))

def normalize_progression_extractor_character_patch(raw_patch: Any) -> Dict[str, Any]:
    patch = raw_patch if isinstance(raw_patch, dict) else {}
    normalized: Dict[str, Any] = {}
    if isinstance(patch.get("skills_set"), dict):
        normalized["skills_set"] = deep_copy(patch.get("skills_set") or {})
    if isinstance(patch.get("skills_delta"), dict):
        normalized["skills_delta"] = deep_copy(patch.get("skills_delta") or {})
    if isinstance(patch.get("progression_events"), list):
        normalized["progression_events"] = deep_copy(patch.get("progression_events") or [])
    class_set = normalize_class_current(patch.get("class_set"))
    if class_set:
        normalized["class_set"] = class_set
    if isinstance(patch.get("class_update"), dict) and patch.get("class_update"):
        normalized["class_update"] = deep_copy(patch.get("class_update") or {})
    if isinstance(patch.get("progression_set"), dict) and patch.get("progression_set"):
        normalized["progression_set"] = deep_copy(patch.get("progression_set") or {})
    return normalized

def progression_event_dedupe_key(event: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    event_type = str(event.get("type") or "").strip().lower()
    target_skill = str(event.get("target_skill_id") or "").strip().lower()
    target_class = str(event.get("target_class_id") or "").strip().lower()
    reason = normalized_eval_text(str(event.get("reason") or ""))
    skill_name = normalized_eval_text(str(((event.get("skill") or {}) if isinstance(event.get("skill"), dict) else {}).get("name") or ""))
    return (event_type, target_skill, target_class, reason, skill_name)

def merge_progression_patch_additive(
    *,
    base_patch: Dict[str, Any],
    actor: str,
    supplement_character_patch: Dict[str, Any],
    state_after: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    merged = normalize_patch_semantics(base_patch)
    actor_update = merged.setdefault("characters", {}).setdefault(actor, {})
    incoming = normalize_progression_extractor_character_patch(supplement_character_patch)
    merge_meta = {
        "applied_keys": [],
        "conflicts": [],
        "added_events": 0,
    }

    state_character = ((state_after.get("characters") or {}).get(actor) or {})
    state_skill_names = {
        normalized_eval_text((entry or {}).get("name", ""))
        for entry in ((state_character.get("skills") or {}).values())
        if isinstance(entry, dict)
    }

    incoming_skills_set = incoming.get("skills_set") if isinstance(incoming.get("skills_set"), dict) else {}
    if incoming_skills_set:
        target_skills = actor_update.setdefault("skills_set", {})
        target_skill_names = {
            normalized_eval_text((entry or {}).get("name", ""))
            for entry in (target_skills.values())
            if isinstance(entry, dict)
        }
        for skill_id, raw_skill in incoming_skills_set.items():
            normalized_skill = normalize_dynamic_skill_state(
                raw_skill,
                skill_id=str(skill_id),
                skill_name=(raw_skill or {}).get("name", skill_id) if isinstance(raw_skill, dict) else str(skill_id),
                resource_name=resource_name_for_character(state_character, ((state_after.get("world") or {}).get("settings") or {})),
            )
            skill_name_norm = normalized_eval_text(normalized_skill.get("name", ""))
            if str(skill_id) in target_skills or (skill_name_norm and (skill_name_norm in target_skill_names or skill_name_norm in state_skill_names)):
                merge_meta["conflicts"].append({"key": "skills_set", "id": str(skill_id), "name": normalized_skill.get("name", "")})
                continue
            target_skills[str(skill_id)] = normalized_skill
            if skill_name_norm:
                target_skill_names.add(skill_name_norm)
            if "skills_set" not in merge_meta["applied_keys"]:
                merge_meta["applied_keys"].append("skills_set")

    incoming_skills_delta = incoming.get("skills_delta") if isinstance(incoming.get("skills_delta"), dict) else {}
    if incoming_skills_delta:
        target_delta = actor_update.setdefault("skills_delta", {})
        for skill_id, delta_payload in incoming_skills_delta.items():
            sid = str(skill_id or "").strip()
            if not sid:
                continue
            if sid in target_delta:
                merge_meta["conflicts"].append({"key": "skills_delta", "id": sid})
                continue
            target_delta[sid] = deep_copy(delta_payload)
            if "skills_delta" not in merge_meta["applied_keys"]:
                merge_meta["applied_keys"].append("skills_delta")

    incoming_events = normalize_progression_event_list(incoming.get("progression_events"), actor=actor, source_turn=0)
    if incoming_events:
        target_events = actor_update.setdefault("progression_events", [])
        existing_keys = {
            progression_event_dedupe_key(event)
            for event in normalize_progression_event_list(target_events, actor=actor, source_turn=0)
        }
        for event in incoming_events:
            key = progression_event_dedupe_key(event)
            if key in existing_keys:
                merge_meta["conflicts"].append({"key": "progression_events", "type": event.get("type", "")})
                continue
            existing_keys.add(key)
            target_events.append(deep_copy(event))
            merge_meta["added_events"] = int(merge_meta.get("added_events", 0) or 0) + 1
            if "progression_events" not in merge_meta["applied_keys"]:
                merge_meta["applied_keys"].append("progression_events")

    for scalar_key in ("class_set", "class_update", "progression_set"):
        value = incoming.get(scalar_key)
        if not value:
            continue
        if actor_update.get(scalar_key):
            merge_meta["conflicts"].append({"key": scalar_key})
            continue
        actor_update[scalar_key] = deep_copy(value)
        if scalar_key not in merge_meta["applied_keys"]:
            merge_meta["applied_keys"].append(scalar_key)

    return merged, merge_meta

def evaluate_progression_extractor_confidence(
    *,
    actor: str,
    actor_display: str,
    claim_types: List[str],
    model_confidence: str,
    character_patch: Dict[str, Any],
) -> Dict[str, Any]:
    normalized_model_confidence = str(model_confidence or "").strip().lower()
    if normalized_model_confidence not in PROGRESSION_EXTRACTOR_CONFIDENCE_ORDER:
        normalized_model_confidence = "medium"
    model_score = PROGRESSION_EXTRACTOR_CONFIDENCE_SCORE.get(normalized_model_confidence, 0.6)

    heuristic_score = 0.0
    if character_patch.get("skills_set"):
        heuristic_score += 0.35
    if character_patch.get("skills_delta"):
        heuristic_score += 0.2
    if character_patch.get("progression_events"):
        heuristic_score += 0.3
    if character_patch.get("class_set") or character_patch.get("class_update") or character_patch.get("progression_set"):
        heuristic_score += 0.25

    coverage = progression_claim_coverage_for_actor_patch({"characters": {actor: character_patch}}, actor)
    normalized_claims = normalized_progression_claims(claim_types)
    if normalized_claims:
        covered_count = len([claim for claim in normalized_claims if claim in coverage])
        heuristic_score += 0.25 * (covered_count / max(1, len(normalized_claims)))

    for raw_skill in (character_patch.get("skills_set") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        skill_name = str(raw_skill.get("name") or "").strip()
        if skill_name and not is_skill_manifestation_name_plausible(skill_name, actor_display):
            heuristic_score -= 0.3
            break

    heuristic_score = clamp_float(heuristic_score, 0.0, 1.0)
    combined_score = clamp_float((heuristic_score * 0.65) + (model_score * 0.35), 0.0, 1.0)
    if combined_score >= PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS["high"]:
        final_confidence = "high"
    elif combined_score >= PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS["medium"]:
        final_confidence = "medium"
    else:
        final_confidence = "low"
    return {
        "confidence": final_confidence,
        "score": combined_score,
        "model_confidence": normalized_model_confidence,
        "heuristic_score": heuristic_score,
        "coverage": sorted(coverage),
    }

def call_progression_canon_extractor(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    claim_types: List[str],
    claim_text: str,
    player_text: str,
    story_text: str,
) -> Dict[str, Any]:
    context_packet = build_extractor_context_packet(
        campaign,
        state,
        actor,
        action_type,
        story_text,
        source="progression_gate",
    )
    user_prompt = (
        "STATE_PACKET(JSON):\n"
        + context_packet
        + "\n\nCLAIM_TYPES(JSON):\n"
        + json.dumps(normalized_progression_claims(claim_types), ensure_ascii=False)
        + "\n\nCLAIM_TEXT:\n"
        + str(claim_text or "")[:2200]
        + "\n\nPLAYER_TEXT:\n"
        + str(player_text or "")[:1200]
        + "\n\nOUTPUT-KONTRAKT:\n"
        + PROGRESSION_EXTRACTOR_JSON_CONTRACT
    )
    payload = call_ollama_schema(
        PROGRESSION_EXTRACTOR_SYSTEM_PROMPT,
        user_prompt,
        PROGRESSION_EXTRACTOR_SCHEMA,
        timeout=90,
        temperature=0.15,
    )
    character_patch = normalize_progression_extractor_character_patch((payload or {}).get("character_patch"))
    confidence_meta = evaluate_progression_extractor_confidence(
        actor=actor,
        actor_display=display_name_for_slot(campaign, actor),
        claim_types=claim_types,
        model_confidence=str((payload or {}).get("confidence") or "medium"),
        character_patch=character_patch,
    )
    return {
        "character_patch": character_patch,
        "confidence": confidence_meta["confidence"],
        "confidence_score": confidence_meta["score"],
        "model_confidence": confidence_meta["model_confidence"],
        "heuristic_score": confidence_meta["heuristic_score"],
        "coverage": confidence_meta["coverage"],
        "reason": str((payload or {}).get("reason") or "").strip(),
    }
