from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Tuple

from app.config.runtime import (
    EXTRACTION_REASON_AMBIGUOUS_CLASS,
    EXTRACTION_REASON_CONFLICT_WITH_LLM,
    EXTRACTION_REASON_DUPLICATE,
    EXTRACTION_REASON_ENV_OBJECT,
    EXTRACTION_REASON_GENERIC_LOCATION,
    EXTRACTION_REASON_LOW_CONFIDENCE,
    EXTRACTION_REASON_MISSING_ACQUIRE,
    EXTRACTION_REASON_VERB_STYLE_SKILL,
)
from app.core.ids import deep_copy, make_id, utc_now
from app.services.campaigns.party import active_party, campaign_slots, display_name_for_slot
from app.services.campaigns.views import active_turns
from app.services.characters.resource_maxima import list_inventory_items
from app.services.characters.resources import resource_name_for_character
from app.services.extraction.abilities import clean_auto_ability_name, extract_auto_learned_abilities
from app.services.extraction.classes import extract_auto_class_change
from app.services.extraction.items import (
    actor_relevant_story_sentences,
    build_auto_item_stub,
    clean_auto_item_name,
    extract_auto_story_item_events,
    item_id_from_name,
    sentence_mentions_actor_name,
)
from app.services.extraction.quarantine import append_extraction_quarantine
from app.services.items.inventory import ensure_item_shape, normalize_equipment_update_payload
from app.services.patch_payloads import blank_patch, normalize_patch_semantics
from app.services.state_basics import is_slot_id
from app.services.world.math_utils import clamp
from app.services.world.npc import normalize_npc_alias
from app.services.world.progression import normalize_class_current
from app.services.world.scene import canonical_scene_id, extract_scene_candidates, is_generic_scene_identifier
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import AUTO_ITEM_ACQUIRE_PATTERNS, AUTO_ITEM_EQUIP_PATTERNS, AUTO_ITEM_GENERIC_NAMES, STORY_LEARN_CUES, UNIVERSAL_SKILL_LIKE_NAMES


def clamp_float(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def _missing_dependency(name: str) -> Callable[..., Any]:
    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"Heuristic extraction dependency is not configured: {name}")
    return _missing


@dataclass(frozen=True)
class HeuristicExtractionDependencies:
    skill_id_from_name: Callable[..., str] = _missing_dependency("skill_id_from_name")
    skill_rank_sort_value: Callable[..., int] = _missing_dependency("skill_rank_sort_value")
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]] = _missing_dependency("normalize_dynamic_skill_state")


_DEPS = HeuristicExtractionDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def skill_id_from_name(*args: Any, **kwargs: Any) -> str:
    return _DEPS.skill_id_from_name(*args, **kwargs)


def skill_rank_sort_value(*args: Any, **kwargs: Any) -> int:
    return _DEPS.skill_rank_sort_value(*args, **kwargs)


def normalize_dynamic_skill_state(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.normalize_dynamic_skill_state(*args, **kwargs)

def resolve_extractor_conflicts(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    patch: Dict[str, Any],
    *,
    source: str,
) -> Dict[str, Any]:
    resolved = normalize_patch_semantics(patch)
    allow_retcon = action_type == "canon" or str(source_text or "").strip().lower().startswith("retcon:")
    if source == "player" and not allow_retcon:
        actor_patch = (resolved.get("characters") or {}).get(actor) or {}
        next_scene = str(actor_patch.get("scene_id") or "").strip()
        current_scene = str(((state.get("characters", {}) or {}).get(actor) or {}).get("scene_id") or "").strip()
        if next_scene and current_scene and next_scene != current_scene:
            resolved["characters"][actor].pop("scene_id", None)
            if not resolved["characters"][actor]:
                resolved["characters"].pop(actor, None)
            resolved.setdefault("events_add", []).append(
                f"Widerspruch erkannt: {display_name_for_slot(campaign, actor)} kann den Ort nicht still über STORY/DO/SAY überschreiben."
            )
            resolved["map_add_nodes"] = [node for node in (resolved.get("map_add_nodes") or []) if node.get("id") != next_scene]
    for slot_name, upd in list((resolved.get("characters") or {}).items()):
        cleaned_abilities = []
        converted_skills = upd.setdefault("skills_set", {})
        character_resource = resource_name_for_character(((state.get("characters", {}) or {}).get(slot_name) or {}), ((state.get("world") or {}).get("settings") or {}))
        for ability in upd.get("abilities_add", []) or []:
            ability_name = clean_auto_ability_name(ability.get("name", ""))
            normalized_name = normalized_eval_text(ability_name)
            if normalized_name in UNIVERSAL_SKILL_LIKE_NAMES:
                skill_id = skill_id_from_name(ability_name)
                converted_skills[skill_id] = normalize_dynamic_skill_state(
                    {
                        "id": skill_id,
                        "name": ability_name,
                        "rank": "F",
                        "level": 1,
                        "level_max": 10,
                        "tags": list(dict.fromkeys([*(ability.get("tags") or []), "allgemein"])),
                        "description": str(ability.get("description", "") or f"{ability_name} wurde kanonisch gelernt."),
                        "cost": None,
                        "price": None,
                        "cooldown_turns": None,
                        "unlocked_from": "Canon Extractor",
                        "synergy_notes": None,
                    },
                    resource_name=character_resource,
                )
                continue
            cleaned_abilities.append(ability)
        if "abilities_add" in upd:
            upd["abilities_add"] = cleaned_abilities
    return resolved

def is_suspicious_story_text(text: str) -> bool:
    if not text:
        return True
    stripped = text.strip()
    if len(stripped) < 40:
        return True
    if stripped.endswith("\\"):
        return True
    if stripped.endswith(("„", '"', "'", "(", "[", "{", ":", ",", ";")):
        return True
    if stripped.count('"') % 2 == 1:
        return True
    if stripped.count("„") != stripped.count("“"):
        return True
    return False

def extract_story_target_evidence(campaign: Dict[str, Any], target: str, *, max_hits: int = 6) -> Dict[str, Any]:
    normalized_target = normalize_npc_alias(target)
    if not normalized_target:
        return {"facts": [], "sources": []}
    token_set = {token for token in normalized_target.split() if len(token) >= 3}
    facts: List[str] = []
    sources: List[Dict[str, str]] = []
    seen_sentences: set[str] = set()
    turns = list(active_turns(campaign))[-24:]
    for turn in reversed(turns):
        turn_id = str(turn.get("turn_id") or "")
        turn_number = int(turn.get("turn_number") or 0)
        for field_name, label in (("gm_text_display", "GM"), ("input_text_display", "Spieler")):
            text_block = str(turn.get(field_name) or "")
            if not text_block:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text_block):
                clean_sentence = str(sentence or "").strip()
                if len(clean_sentence) < 12:
                    continue
                normalized_sentence = normalize_npc_alias(clean_sentence)
                if not normalized_sentence:
                    continue
                direct_hit = normalized_target in normalized_sentence
                token_hit = bool(token_set) and sum(1 for token in token_set if token in normalized_sentence) >= max(1, min(2, len(token_set)))
                if not direct_hit and not token_hit:
                    continue
                signature = normalized_sentence[:220]
                if signature in seen_sentences:
                    continue
                seen_sentences.add(signature)
                facts.append(clean_sentence)
                sources.append(
                    {
                        "type": "turn",
                        "id": turn_id or f"turn_{turn_number}",
                        "label": f"Turn {turn_number} ({label})",
                    }
                )
                if len(facts) >= max_hits:
                    return {"facts": facts, "sources": sources}
    return {"facts": facts, "sources": sources}

def make_extraction_candidate(
    *,
    state: Dict[str, Any],
    actor: str,
    source: str,
    entity_type: str,
    operation: str,
    label: str,
    normalized_key: str,
    evidence_text: str,
    payload: Dict[str, Any],
    confidence: float,
) -> Dict[str, Any]:
    return {
        "candidate_id": make_id("xc"),
        "source": str(source or "unknown"),
        "actor": str(actor or ""),
        "turn": max(0, int(((state.get("meta") or {}).get("turn", 0) or 0))),
        "entity_type": str(entity_type or "unknown"),
        "operation": str(operation or ""),
        "label": str(label or "").strip(),
        "normalized_key": str(normalized_key or "").strip(),
        "evidence_text": str(evidence_text or "").strip(),
        "payload": deep_copy(payload or {}),
        "confidence": float(clamp_float(float(confidence or 0.0), 0.0, 1.0)),
        "status": "review",
        "reason_code": EXTRACTION_REASON_LOW_CONFIDENCE,
        "created_at": utc_now(),
    }

def candidate_status_rank(status: str) -> int:
    lowered = str(status or "").strip().lower()
    if lowered == "safe":
        return 3
    if lowered == "review":
        return 2
    return 1

def item_name_in_character_inventory(state: Dict[str, Any], slot_name: str, item_name: str) -> bool:
    normalized_name = normalized_eval_text(item_name)
    if not normalized_name:
        return False
    character = ((state.get("characters") or {}).get(slot_name) or {})
    items_db = state.get("items") or {}
    for entry in list_inventory_items(character):
        item_id = str(entry.get("item_id") or "").strip()
        if not item_id:
            continue
        item = items_db.get(item_id) or {}
        if normalized_eval_text(str(item.get("name") or "")) == normalized_name:
            return True
    return False

def extract_environment_item_mentions(story_text: str, actor_display: str) -> List[Dict[str, str]]:
    mentions: List[Dict[str, str]] = []
    seen = set()
    pattern = re.compile(
        r"\b(?:liegt|liegen|stand|steht|stehen|haengt|hängt|hingen)\s+(?:ein|eine|einen|der|die|das)\s+([^,.!?;\n]{3,80})",
        flags=re.IGNORECASE,
    )
    actor_relevant = actor_relevant_story_sentences(story_text, actor_display)
    actor_relevant_set = set(actor_relevant)
    sentence_pool = list(actor_relevant)
    if not sentence_pool:
        sentence_pool = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(story_text or ""))
            if sentence.strip()
        ]
    for sentence in sentence_pool:
        lowered = normalized_eval_text(sentence)
        if sentence not in actor_relevant_set and not re.search(r"\b(ihm|ihr|ihnen)\b", lowered):
            continue
        if any(pattern_acq.search(sentence) for pattern_acq in AUTO_ITEM_ACQUIRE_PATTERNS):
            continue
        if any(pattern_eq.search(sentence) for pattern_eq in AUTO_ITEM_EQUIP_PATTERNS):
            continue
        for match in pattern.findall(sentence):
            item_name = clean_auto_item_name(match)
            normalized_name = normalized_eval_text(item_name)
            if not item_name or not normalized_name or normalized_name in seen:
                continue
            seen.add(normalized_name)
            mentions.append({"name": item_name, "sentence": sentence})
    return mentions

def build_heuristic_candidates(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    source: str,
) -> List[Dict[str, Any]]:
    if not str(source_text or "").strip():
        return []
    candidates: List[Dict[str, Any]] = []
    seen_keys: set = set()
    actor_display = display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor
    normalized_content = normalized_eval_text(source_text)

    def push(candidate: Dict[str, Any]) -> None:
        key = str(candidate.get("normalized_key") or "").strip()
        if not key or key in seen_keys:
            return
        seen_keys.add(key)
        candidates.append(candidate)

    if actor in (state.get("characters") or {}):
        class_payload = extract_auto_class_change(source_text, actor_display)
        if class_payload:
            normalized_class = normalize_class_current(class_payload)
            if normalized_class:
                class_label = str(normalized_class.get("name") or normalized_class.get("id") or "").strip()
                push(
                    make_extraction_candidate(
                        state=state,
                        actor=actor,
                        source=source,
                        entity_type="class",
                        operation="set_class",
                        label=class_label,
                        normalized_key=f"class:{normalized_eval_text(str(normalized_class.get('id') or class_label))}",
                        evidence_text=source_text,
                        payload={"class_set": normalized_class},
                        confidence=0.86,
                    )
                )
        elif "klasse" in normalized_content and actor_display and normalized_eval_text(actor_display) in normalized_content:
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="class",
                    operation="set_class",
                    label="Klassenhinweis",
                    normalized_key=f"class:ambiguous:{actor}",
                    evidence_text=source_text,
                    payload={"ambiguous": True},
                    confidence=0.25,
                )
            )

        for learned in extract_auto_learned_abilities(source_text, actor_display):
            skill_name = str(learned.get("name") or "").strip()
            if not skill_name:
                continue
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="skill",
                    operation="add_skill",
                    label=skill_name,
                    normalized_key=f"skill:{normalized_eval_text(skill_name)}",
                    evidence_text=str(learned.get("description") or source_text),
                    payload={
                        "name": skill_name,
                        "description": str(learned.get("description") or "").strip(),
                        "tags": deep_copy(learned.get("tags") or []),
                        "type": str(learned.get("type") or "active"),
                        "explicit_learn": True,
                    },
                    confidence=0.78,
                )
            )

        verb_style_match = re.search(
            r"\b(?:ich|er|sie)\s+(?:kaempft|kämpft|rennt|springt|weicht|bewegt\s+sich)\b",
            normalized_content,
        )
        if verb_style_match and not any(cue in normalized_content for cue in STORY_LEARN_CUES):
            label = str(verb_style_match.group(0) or "stilaktion").strip()
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="skill",
                    operation="add_skill",
                    label=label,
                    normalized_key=f"skill:verbstyle:{normalized_eval_text(label)}",
                    evidence_text=source_text,
                    payload={"mode": "style_verb"},
                    confidence=0.2,
                )
            )

        for event in extract_auto_story_item_events(source_text, actor_display):
            item_name = str(event.get("name") or "").strip()
            if not item_name:
                continue
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="item",
                    operation="add_item",
                    label=item_name,
                    normalized_key=f"item:{normalized_eval_text(item_name)}",
                    evidence_text=str(event.get("sentence") or source_text),
                    payload={
                        "name": item_name,
                        "mode": str(event.get("mode") or "acquire"),
                        "sentence": str(event.get("sentence") or source_text),
                    },
                    confidence=0.8 if str(event.get("mode") or "") in {"acquire", "equip"} else 0.55,
                )
            )

        for mention in extract_environment_item_mentions(source_text, actor_display):
            item_name = str(mention.get("name") or "").strip()
            if not item_name:
                continue
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="item",
                    operation="add_item",
                    label=item_name,
                    normalized_key=f"item:env:{normalized_eval_text(item_name)}",
                    evidence_text=str(mention.get("sentence") or source_text),
                    payload={"name": item_name, "mode": "environment_only"},
                    confidence=0.2,
                )
            )

    for scene in extract_scene_candidates(source_text, actor_display):
        scene_name = str(scene.get("name") or "").strip()
        if not scene_name:
            continue
        scope = str(scene.get("scope") or "").strip().lower()
        scene_id = canonical_scene_id(scene_name)
        targets = active_party(campaign) if scope == "group" and active_party(campaign) else [actor]
        push(
            make_extraction_candidate(
                state=state,
                actor=actor,
                source=source,
                entity_type="map",
                operation="add_scene",
                label=scene_name,
                normalized_key=f"scene:{scene_id}",
                evidence_text=source_text,
                payload={
                    "scene_id": scene_id,
                    "scene_name": scene_name,
                    "scope": scope,
                    "targets": targets,
                },
                confidence=0.82 if scope in {"actor", "group"} else 0.4,
            )
        )
    return candidates

def classify_heuristic_candidate(
    candidate: Dict[str, Any],
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    source_text: str,
) -> Dict[str, Any]:
    classified = deep_copy(candidate)
    entity_type = str(classified.get("entity_type") or "").strip().lower()
    label = str(classified.get("label") or "").strip()
    payload = classified.get("payload") if isinstance(classified.get("payload"), dict) else {}
    status = "review"
    reason_code = EXTRACTION_REASON_LOW_CONFIDENCE
    confidence = float(classified.get("confidence", 0.0) or 0.0)

    if entity_type == "map":
        scene_id = str(payload.get("scene_id") or canonical_scene_id(label)).strip()
        generic_names = {
            "dorf",
            "wald",
            "strasse",
            "straße",
            "raum",
            "gebaude",
            "gebäude",
            "tuer",
            "tür",
            "haus",
            "gegend",
        }
        normalized_label = normalized_eval_text(label)
        scope = str(payload.get("scope") or "").strip().lower()
        if normalized_label in generic_names or is_generic_scene_identifier(scene_id, label):
            status = "reject"
            reason_code = EXTRACTION_REASON_GENERIC_LOCATION
            confidence = min(confidence, 0.25)
        elif scope in {"actor", "group"}:
            status = "safe"
            reason_code = "SAFE_CONFIRMED"
            confidence = max(confidence, 0.75)
        else:
            status = "review"
            reason_code = EXTRACTION_REASON_LOW_CONFIDENCE
    elif entity_type == "item":
        mode = str(payload.get("mode") or "").strip().lower()
        normalized_label = normalized_eval_text(label)
        if mode == "environment_only":
            status = "reject"
            reason_code = EXTRACTION_REASON_ENV_OBJECT
            confidence = min(confidence, 0.25)
        elif normalized_label in {normalized_eval_text(entry) for entry in AUTO_ITEM_GENERIC_NAMES}:
            status = "reject"
            reason_code = EXTRACTION_REASON_ENV_OBJECT
            confidence = min(confidence, 0.2)
        elif mode in {"acquire", "equip"}:
            status = "safe"
            reason_code = "SAFE_CONFIRMED"
            confidence = max(confidence, 0.72)
        else:
            status = "review"
            reason_code = EXTRACTION_REASON_MISSING_ACQUIRE
            confidence = min(confidence, 0.45)
        if status == "safe" and item_name_in_character_inventory(state, actor, label):
            status = "review"
            reason_code = EXTRACTION_REASON_DUPLICATE
            confidence = min(confidence, 0.5)
    elif entity_type == "skill":
        if str(payload.get("mode") or "").strip().lower() == "style_verb":
            status = "reject"
            reason_code = EXTRACTION_REASON_VERB_STYLE_SKILL
            confidence = min(confidence, 0.25)
        elif payload.get("explicit_learn"):
            status = "safe"
            reason_code = "SAFE_CONFIRMED"
            confidence = max(confidence, 0.72)
        else:
            status = "review"
            reason_code = EXTRACTION_REASON_LOW_CONFIDENCE
        if status == "safe":
            existing_skill_names = {
                normalized_eval_text((entry or {}).get("name", ""))
                for entry in (((state.get("characters") or {}).get(actor) or {}).get("skills") or {}).values()
                if isinstance(entry, dict)
            }
            if normalized_eval_text(label) in existing_skill_names:
                status = "review"
                reason_code = EXTRACTION_REASON_DUPLICATE
                confidence = min(confidence, 0.5)
    elif entity_type == "class":
        class_set = normalize_class_current(payload.get("class_set"))
        if payload.get("ambiguous") or not class_set:
            status = "review"
            reason_code = EXTRACTION_REASON_AMBIGUOUS_CLASS
            confidence = min(confidence, 0.35)
        else:
            existing_class = normalize_class_current((((state.get("characters") or {}).get(actor) or {}).get("class_current")))
            if existing_class and (
                normalized_eval_text(existing_class.get("id", "")) == normalized_eval_text(class_set.get("id", ""))
                or normalized_eval_text(existing_class.get("name", "")) == normalized_eval_text(class_set.get("name", ""))
            ):
                status = "review"
                reason_code = EXTRACTION_REASON_DUPLICATE
                confidence = min(confidence, 0.45)
            else:
                status = "safe"
                reason_code = "SAFE_CONFIRMED"
                confidence = max(confidence, 0.78)
            payload["class_set"] = class_set
    else:
        status = "reject"
        reason_code = EXTRACTION_REASON_LOW_CONFIDENCE
        confidence = min(confidence, 0.2)

    classified["payload"] = payload
    classified["status"] = status
    classified["reason_code"] = reason_code
    classified["confidence"] = clamp_float(confidence, 0.0, 1.0)
    return classified

def split_candidates(candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for candidate in candidates:
        key = str(candidate.get("normalized_key") or "").strip() or str(candidate.get("candidate_id") or make_id("xc"))
        current = deduped.get(key)
        if current is None:
            deduped[key] = candidate
            continue
        current_rank = candidate_status_rank(current.get("status", "reject"))
        incoming_rank = candidate_status_rank(candidate.get("status", "reject"))
        if incoming_rank > current_rank:
            deduped[key] = candidate
            continue
        if incoming_rank == current_rank and float(candidate.get("confidence", 0.0) or 0.0) > float(current.get("confidence", 0.0) or 0.0):
            deduped[key] = candidate
    safe: List[Dict[str, Any]] = []
    review: List[Dict[str, Any]] = []
    reject: List[Dict[str, Any]] = []
    for candidate in deduped.values():
        status = str(candidate.get("status") or "").strip().lower()
        if status == "safe":
            safe.append(candidate)
        elif status == "review":
            review.append(candidate)
        else:
            reject.append(candidate)
    return safe, review, reject

def safe_candidates_to_patch(
    candidates_safe: List[Dict[str, Any]],
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
) -> Dict[str, Any]:
    patch = blank_patch()
    state_items = state.get("items") or {}
    for candidate in candidates_safe:
        entity_type = str(candidate.get("entity_type") or "").strip().lower()
        payload = candidate.get("payload") if isinstance(candidate.get("payload"), dict) else {}
        if entity_type == "map":
            scene_id = str(payload.get("scene_id") or "").strip()
            scene_name = str(payload.get("scene_name") or candidate.get("label") or "").strip()
            targets = [slot for slot in (payload.get("targets") or [actor]) if slot in (state.get("characters") or {})]
            if not scene_id or not scene_name or not targets:
                continue
            known_scene_ids = set((state.get("scenes") or {}).keys()) | set(((state.get("map") or {}).get("nodes") or {}).keys())
            if scene_id not in known_scene_ids and not any(str(node.get("id") or "").strip() == scene_id for node in (patch.get("map_add_nodes") or [])):
                patch["map_add_nodes"].append(
                    {
                        "id": scene_id,
                        "name": scene_name,
                        "type": "location",
                        "danger": 1,
                        "discovered": True,
                    }
                )
            for slot_name in targets:
                patch["characters"].setdefault(slot_name, {})["scene_id"] = scene_id
        elif entity_type == "item":
            item_name = str(payload.get("name") or candidate.get("label") or "").strip()
            mode = str(payload.get("mode") or "acquire").strip().lower()
            sentence = str(payload.get("sentence") or candidate.get("evidence_text") or "")
            if not item_name or actor not in (state.get("characters") or {}):
                continue
            target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
            target_patch.setdefault("inventory_add", [])
            target_patch.setdefault("equipment_set", {})
            candidate_item_id = item_id_from_name(item_name)
            item_id = candidate_item_id
            suffix = 2
            while item_id in state_items or item_id in (patch.get("items_new") or {}):
                known = state_items.get(item_id) or (patch.get("items_new") or {}).get(item_id) or {}
                if normalized_eval_text(str((known or {}).get("name") or "")) == normalized_eval_text(item_name):
                    break
                item_id = f"{candidate_item_id}-{suffix}"
                suffix += 1
            item_stub = build_auto_item_stub(item_name, sentence)
            patch.setdefault("items_new", {})[item_id] = ensure_item_shape(
                item_id,
                {
                    "name": item_name[0].upper() + item_name[1:] if item_name else item_name,
                    "rarity": "common",
                    "slot": item_stub.get("slot", ""),
                    "weight": 1,
                    "stackable": False,
                    "max_stack": 1,
                    "weapon_profile": item_stub.get("weapon_profile", {}),
                    "modifiers": [],
                    "effects": [],
                    "durability": {"current": 100, "max": 100},
                    "cursed": False,
                    "curse_text": "",
                    "tags": item_stub.get("tags", ["story_auto", "auto_item"]),
                },
            )
            if item_id not in (target_patch.get("inventory_add") or []):
                target_patch["inventory_add"].append(item_id)
            if mode == "equip":
                equip_slot = item_stub.get("slot") or "weapon"
                target_patch["equipment_set"].setdefault(equip_slot, item_id)
            if not target_patch.get("equipment_set"):
                target_patch.pop("equipment_set", None)
        elif entity_type == "skill":
            if actor not in (state.get("characters") or {}):
                continue
            skill_name = str(payload.get("name") or candidate.get("label") or "").strip()
            if not skill_name:
                continue
            resource_name = resource_name_for_character(
                ((state.get("characters") or {}).get(actor) or {}),
                ((state.get("world") or {}).get("settings") or {}),
            )
            skill_id = skill_id_from_name(skill_name)
            target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
            target_patch.setdefault("skills_set", {})
            target_patch["skills_set"][skill_id] = normalize_dynamic_skill_state(
                {
                    "id": skill_id,
                    "name": skill_name,
                    "rank": "F",
                    "level": 1,
                    "level_max": 10,
                    "tags": deep_copy(payload.get("tags") or ["allgemein"]),
                    "description": str(payload.get("description") or f"{skill_name} wurde im Abenteuer gelernt."),
                    "cost": {"resource": resource_name, "amount": 1} if "magie" in (payload.get("tags") or []) else None,
                    "price": None,
                    "cooldown_turns": None,
                    "unlocked_from": "Story",
                    "synergy_notes": None,
                },
                resource_name=resource_name,
            )
        elif entity_type == "class":
            class_set = normalize_class_current(payload.get("class_set"))
            if not class_set or actor not in (state.get("characters") or {}):
                continue
            patch.setdefault("characters", {}).setdefault(actor, {})["class_set"] = class_set
    return patch

def merge_safe_patch_additive(
    llm_patch: Dict[str, Any],
    safe_patch: Dict[str, Any],
    state: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    merged = normalize_patch_semantics(llm_patch)
    safe = normalize_patch_semantics(safe_patch)
    conflicts: List[Dict[str, Any]] = []

    merged_items = merged.setdefault("items_new", {})
    for item_id, item_payload in (safe.get("items_new") or {}).items():
        if item_id in merged_items:
            conflicts.append({"entity_type": "item", "label": str((item_payload or {}).get("name") or item_id), "payload": {"item_id": item_id}})
            continue
        merged_items[item_id] = deep_copy(item_payload)

    existing_node_ids = {str(node.get("id") or "").strip() for node in (merged.get("map_add_nodes") or []) if isinstance(node, dict)}
    for node in (safe.get("map_add_nodes") or []):
        node_id = str((node or {}).get("id") or "").strip()
        if not node_id or node_id in existing_node_ids:
            continue
        existing_node_ids.add(node_id)
        merged.setdefault("map_add_nodes", []).append(deep_copy(node))

    existing_edges = {
        (str(edge.get("from") or "").strip(), str(edge.get("to") or "").strip(), str(edge.get("kind") or "path").strip())
        for edge in (merged.get("map_add_edges") or [])
        if isinstance(edge, dict)
    }
    for edge in (safe.get("map_add_edges") or []):
        if not isinstance(edge, dict):
            continue
        key = (str(edge.get("from") or "").strip(), str(edge.get("to") or "").strip(), str(edge.get("kind") or "path").strip())
        if not key[0] or not key[1] or key in existing_edges:
            continue
        existing_edges.add(key)
        merged.setdefault("map_add_edges", []).append(deep_copy(edge))

    existing_events = {str(event) for event in (merged.get("events_add") or [])}
    for event in (safe.get("events_add") or []):
        text = str(event or "").strip()
        if not text or text in existing_events:
            continue
        existing_events.add(text)
        merged.setdefault("events_add", []).append(text)

    merged_characters = merged.setdefault("characters", {})
    for slot_name, safe_update in (safe.get("characters") or {}).items():
        if slot_name not in (state.get("characters") or {}):
            continue
        target = merged_characters.setdefault(slot_name, {})
        if safe_update.get("scene_id"):
            if target.get("scene_id"):
                conflicts.append(
                    {
                        "entity_type": "map",
                        "label": str(safe_update.get("scene_id") or ""),
                        "payload": {"slot": slot_name, "scene_id": safe_update.get("scene_id")},
                    }
                )
            else:
                target["scene_id"] = str(safe_update.get("scene_id") or "").strip()

        if safe_update.get("class_set"):
            if target.get("class_set") or target.get("class_update"):
                conflicts.append(
                    {
                        "entity_type": "class",
                        "label": str((safe_update.get("class_set") or {}).get("name") or ""),
                        "payload": {"slot": slot_name},
                    }
                )
            else:
                target["class_set"] = deep_copy(safe_update.get("class_set"))

        safe_skills = safe_update.get("skills_set") or {}
        if safe_skills:
            target_skills = target.setdefault("skills_set", {})
            existing_state_skill_names = {
                normalized_eval_text((entry or {}).get("name", ""))
                for entry in (((state.get("characters") or {}).get(slot_name) or {}).get("skills") or {}).values()
                if isinstance(entry, dict)
            }
            existing_target_skill_names = {
                normalized_eval_text((entry or {}).get("name", ""))
                for entry in (target_skills or {}).values()
                if isinstance(entry, dict)
            }
            for skill_id, skill_payload in safe_skills.items():
                skill_name_norm = normalized_eval_text((skill_payload or {}).get("name", ""))
                if skill_id in target_skills or (skill_name_norm and (skill_name_norm in existing_state_skill_names or skill_name_norm in existing_target_skill_names)):
                    conflicts.append(
                        {
                            "entity_type": "skill",
                            "label": str((skill_payload or {}).get("name") or skill_id),
                            "payload": {"slot": slot_name, "skill_id": skill_id},
                        }
                    )
                    continue
                target_skills[skill_id] = deep_copy(skill_payload)
                if skill_name_norm:
                    existing_target_skill_names.add(skill_name_norm)

        safe_inventory_add = safe_update.get("inventory_add") or []
        if safe_inventory_add:
            target_inventory_add = target.setdefault("inventory_add", [])
            existing_inventory_ids = {
                str(entry.get("item_id") or "").strip()
                for entry in list_inventory_items(((state.get("characters") or {}).get(slot_name) or {}))
                if str(entry.get("item_id") or "").strip()
            }
            for item_id in safe_inventory_add:
                item_key = str(item_id or "").strip()
                if not item_key:
                    continue
                if item_key in existing_inventory_ids or item_key in target_inventory_add:
                    conflicts.append({"entity_type": "item", "label": item_key, "payload": {"slot": slot_name, "item_id": item_key}})
                    continue
                target_inventory_add.append(item_key)

        safe_equipment = normalize_equipment_update_payload(safe_update.get("equipment_set") or safe_update.get("equip_set") or {})
        if safe_equipment:
            target_equipment = normalize_equipment_update_payload(target.get("equipment_set") or target.get("equip_set") or {})
            for equip_slot, equip_item_id in safe_equipment.items():
                if not equip_item_id:
                    continue
                if target_equipment.get(equip_slot):
                    conflicts.append(
                        {
                            "entity_type": "item",
                            "label": equip_item_id,
                            "payload": {"slot": slot_name, "equip_slot": equip_slot, "item_id": equip_item_id},
                        }
                    )
                    continue
                target_equipment[equip_slot] = equip_item_id
            if target_equipment:
                target["equipment_set"] = target_equipment
                target.pop("equip_set", None)
    return merged, conflicts
