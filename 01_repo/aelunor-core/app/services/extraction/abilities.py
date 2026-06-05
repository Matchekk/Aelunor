from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List

from app.services.campaigns.party import display_name_for_slot
from app.services.campaigns.views import active_turns
from app.services.characters.resources import resource_name_for_character
from app.services.extraction.items import sentence_mentions_actor_name
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import (
    ABILITY_UNLOCK_GENERIC_NAMES,
    ABILITY_UNLOCK_TRIGGER_PATTERNS,
    STORY_ACTION_CUES,
    STORY_EXPLORE_CUES,
    STORY_LEARN_CUES,
    UNIVERSAL_SKILL_LIKE_NAMES,
)
from app.core.ids import deep_copy, make_id


def _missing_dependency(name: str) -> Callable[..., Any]:
    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"Ability extraction dependency is not configured: {name}")
    return _missing


@dataclass(frozen=True)
class AbilityExtractionDependencies:
    skill_id_from_name: Callable[..., str] = _missing_dependency("skill_id_from_name")
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]] = _missing_dependency("normalize_dynamic_skill_state")


_DEPS = AbilityExtractionDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def skill_id_from_name(*args: Any, **kwargs: Any) -> str:
    return _DEPS.skill_id_from_name(*args, **kwargs)


def normalize_dynamic_skill_state(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.normalize_dynamic_skill_state(*args, **kwargs)

def clean_auto_ability_name(raw_name: str) -> str:
    name = str(raw_name or "").strip().strip(".,:;!?\"“”„' ")
    name = re.sub(r"^(?:die|der|das|ein|eine|einen)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(?:sein(?:e|en|em|er)?|ihr(?:e|en|em|er)?|mein(?:e|en|em|er)?|dein(?:e|en|em|er)?)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(?:alte|alter|altes|alten|neue|neuer|neues|neuen|frühere|fruehere|früheren|frueheren)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:und|aber|doch|wobei|wodurch|als|während)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:wieder|erneut|zurück|zurueck)$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(" -")
    normalized = normalized_eval_text(name)
    if not name or normalized in ABILITY_UNLOCK_GENERIC_NAMES:
        return ""
    if normalized in UNIVERSAL_SKILL_LIKE_NAMES:
        return ""
    word_count = len(name.split())
    if word_count > 6 or len(name) < 3:
        return ""
    if not re.search(r"[A-Za-zÄÖÜäöüß]", name):
        return ""
    return name

def clean_extracted_skill_name(raw_name: str) -> str:
    name = clean_auto_ability_name(raw_name)
    if not name:
        return ""
    name = re.sub(
        r"\s+(?:sowie|und)\s+(?:die\s+technik|den\s+zauber|das\s+ritual|die\s+kunst|die\s+faehigkeit|die\s+fähigkeit)\b.*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    name = re.sub(r"\s+(?:sowie|und)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(" -")
    return clean_auto_ability_name(name)

def split_extracted_skill_names(raw_name: str) -> List[str]:
    text = str(raw_name or "").strip()
    if not text:
        return []
    parts = re.split(
        r"\s+(?:sowie|und)\s+(?:die\s+technik\s+|den\s+zauber\s+|das\s+ritual\s+|die\s+kunst\s+|die\s+faehigkeit\s+|die\s+fähigkeit\s+)?",
        text,
        flags=re.IGNORECASE,
    )
    names: List[str] = []
    seen = set()
    for part in parts:
        cleaned = clean_extracted_skill_name(part)
        normalized = normalized_eval_text(cleaned)
        if not cleaned or normalized in seen:
            continue
        seen.add(normalized)
        names.append(cleaned)
    return names

def infer_auto_skill_tags(text: str) -> List[str]:
    lowered = normalized_eval_text(text)
    tags: List[str] = []
    if any(marker in lowered for marker in ("magie", "zauber", "rune", "fluch", "aether", "mana")):
        tags.append("magie")
    if any(marker in lowered for marker in ("schatten", "dunkel")):
        tags.append("schatten")
    if any(marker in lowered for marker in ("feuer", "brand")):
        tags.append("feuer")
    if any(marker in lowered for marker in ("körper", "hauter", "ausdauer", "regeneration")):
        tags.append("körper")
    if any(marker in lowered for marker in ("sinn", "instinkt", "blick", "wahrnehm")):
        tags.append("sinn")
    if any(marker in lowered for marker in ("waffe", "klinge", "schwert", "kampf")):
        tags.append("kampf")
    return tags or ["allgemein"]

def extract_auto_learned_abilities(story_text: str, actor_display: str) -> List[Dict[str, Any]]:
    actor_name = normalized_eval_text(actor_display)
    candidates: List[Dict[str, Any]] = []
    seen = set()

    def add_candidate(name: str, sentence: str) -> bool:
        normalized_name = normalized_eval_text(name)
        if not name or normalized_name in seen:
            return False
        seen.add(normalized_name)
        candidates.append(
            {
                "name": name,
                "description": sentence[:220].strip(),
                "type": "passive" if normalized_name in UNIVERSAL_SKILL_LIKE_NAMES else "active",
                "tags": list(dict.fromkeys(["story_auto", "auto_unlock", *infer_auto_skill_tags(sentence)])),
            }
        )
        return len(candidates) >= 2

    sentence_parts = re.split(r"(?<=[.!?])\s+|\n+", str(story_text or ""))
    for sentence in sentence_parts:
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized_sentence = normalized_eval_text(sentence)
        if actor_name and not sentence_mentions_actor_name(sentence, actor_display) and not normalized_sentence.startswith(("er ", "sie ", "es ")):
            continue
        if not any(
            cue in normalized_sentence
            for cue in (
                "erlernt",
                "erlent",
                "wiedererlernt",
                "lernt",
                "meistert",
                "beherrscht",
                "schaltet",
                "erhält",
                "entwickelt",
                "entfesselt",
                "erweckt",
                "erwacht",
                "reaktiviert",
                "kann wieder",
                "wieder in sich",
                "manifestiert",
                "entsteht",
                "hervorgeht",
                "formt sich",
            )
        ):
            continue
        direct_magic_match = re.search(r"\b([A-ZÄÖÜa-zäöüß][A-Za-zÄÖÜäöüß\-]{2,40}magie)\b", sentence, flags=re.IGNORECASE)
        if direct_magic_match:
            for magic_name in split_extracted_skill_names(direct_magic_match.group(1)):
                if add_candidate(magic_name, sentence):
                    return candidates
        for explicit_match in re.findall(
            r"(?:technik|zauber|ritual|kunst|fähigkeit|faehigkeit)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,60})",
            sentence,
            flags=re.IGNORECASE,
        ):
            for name in split_extracted_skill_names(explicit_match):
                if add_candidate(name, sentence):
                    return candidates
        for emergent_match in re.findall(
            r"(?:technik|rittertechnik|kerntechnik|kunst|haltung|form)\s*(?:[–—:-]\s*|entsteht\s*(?:als|zu|wie)?\s*|wird\s*(?:zu|als)\s*)[„\"']?([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,60})[\"”']?",
            sentence,
            flags=re.IGNORECASE,
        ):
            for name in split_extracted_skill_names(emergent_match):
                if add_candidate(name, sentence):
                    return candidates
        for quoted_match in re.findall(r"[„\"']([^\"“”']{3,60})[\"”']", sentence):
            if not any(keyword in normalized_sentence for keyword in ("technik", "rittertechnik", "kerntechnik", "kunst", "haltung")):
                continue
            for name in split_extracted_skill_names(quoted_match):
                if add_candidate(name, sentence):
                    return candidates
        for pattern in ABILITY_UNLOCK_TRIGGER_PATTERNS:
            for match in pattern.findall(sentence):
                for name in split_extracted_skill_names(match):
                    if add_candidate(name, sentence):
                        return candidates
    filtered: List[Dict[str, Any]] = []
    for candidate in candidates:
        candidate_norm = normalized_eval_text(candidate.get("name", ""))
        if any(
            candidate_norm
            and candidate_norm != normalized_eval_text(other.get("name", ""))
            and normalized_eval_text(other.get("name", "")).startswith(candidate_norm)
            for other in candidates
        ):
            continue
        filtered.append(candidate)
    return filtered

def story_sentences_for_actor(story_text: str, actor_display: str) -> List[str]:
    actor_name = normalized_eval_text(actor_display)
    relevant: List[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(story_text or "")):
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized_sentence = normalized_eval_text(sentence)
        if sentence_mentions_actor_name(sentence, actor_display):
            relevant.append(sentence)
            continue
        if normalized_sentence.startswith(("er ", "sie ", "es ")):
            relevant.append(sentence)
    return relevant

def build_turn_journal_notes(
    campaign: Dict[str, Any],
    actor: str,
    story_text: str,
    *,
    seed_text: str = "",
) -> List[Dict[str, Any]]:
    actor_display = display_name_for_slot(campaign, actor)
    notes: List[Dict[str, Any]] = []
    seen = set()
    turn_number = int((campaign.get("state", {}).get("meta", {}) or {}).get("turn", 0) or 0) + 1
    source_texts = [str(story_text or "").strip()]
    if seed_text:
        source_texts.append(str(seed_text or "").strip())

    for source_text in source_texts:
        if not source_text:
            continue
        relevant_sentences = story_sentences_for_actor(source_text, actor_display)[:5]
        for sentence in relevant_sentences:
            normalized_sentence = normalized_eval_text(sentence)
            if not normalized_sentence:
                continue
            if any(cue in normalized_sentence for cue in STORY_ACTION_CUES):
                text = sentence[:240].strip()
                key = ("action", normalized_eval_text(text))
                if key not in seen:
                    seen.add(key)
                    notes.append(
                        {
                            "id": make_id("journal"),
                            "kind": "action",
                            "turn_number": turn_number,
                            "text": f"Handlung: {text}",
                        }
                    )
                    break

        learned_names = [entry.get("name", "") for entry in extract_auto_learned_abilities(source_text, actor_display)]
        if learned_names:
            text = "Lernen: " + ", ".join(dict.fromkeys([name for name in learned_names if name]))
            key = ("learn", normalized_eval_text(text))
            if key not in seen:
                seen.add(key)
                notes.append(
                    {
                        "id": make_id("journal"),
                        "kind": "learning",
                        "turn_number": turn_number,
                        "text": text,
                    }
                )
        else:
            for sentence in story_sentences_for_actor(source_text, actor_display):
                normalized_sentence = normalized_eval_text(sentence)
                if any(cue in normalized_sentence for cue in STORY_LEARN_CUES):
                    text = sentence[:240].strip()
                    key = ("learn", normalized_eval_text(text))
                    if key not in seen:
                        seen.add(key)
                        notes.append(
                            {
                                "id": make_id("journal"),
                                "kind": "learning",
                                "turn_number": turn_number,
                                "text": f"Lernen: {text}",
                            }
                        )
                    break

        for sentence in story_sentences_for_actor(source_text, actor_display):
            normalized_sentence = normalized_eval_text(sentence)
            if any(cue in normalized_sentence for cue in STORY_EXPLORE_CUES):
                text = sentence[:240].strip()
                key = ("explore", normalized_eval_text(text))
                if key not in seen:
                    seen.add(key)
                    notes.append(
                        {
                            "id": make_id("journal"),
                            "kind": "exploration",
                            "turn_number": turn_number,
                            "text": f"Erkundung: {text}",
                        }
                    )
                break
    return notes[:4]

def inject_turn_story_journal(
    campaign: Dict[str, Any],
    working_state: Dict[str, Any],
    actor: str,
    story_text: str,
    patch: Dict[str, Any],
    *,
    seed_text: str = "",
) -> Dict[str, Any]:
    if actor not in (working_state.get("characters") or {}):
        return patch
    notes = build_turn_journal_notes(campaign, actor, story_text, seed_text=seed_text)
    if not notes:
        return patch
    target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
    journal_add = target_patch.setdefault("journal_add", {})
    journal_add.setdefault("notes", [])
    existing = {
        normalized_eval_text((entry or {}).get("text", ""))
        for entry in (journal_add.get("notes") or [])
        if isinstance(entry, dict)
    }
    for entry in notes:
        normalized_text = normalized_eval_text(entry.get("text", ""))
        if not normalized_text or normalized_text in existing:
            continue
        existing.add(normalized_text)
        journal_add["notes"].append(entry)
    return patch

def inject_story_unlock_abilities(
    campaign: Dict[str, Any],
    working_state: Dict[str, Any],
    actor: str,
    story_text: str,
    patch: Dict[str, Any],
    *,
    seed_text: str = "",
) -> Dict[str, Any]:
    if actor not in (working_state.get("characters") or {}):
        return patch
    actor_display = display_name_for_slot(campaign, actor)
    candidates = extract_auto_learned_abilities(story_text, actor_display)
    if seed_text:
        known = {normalized_eval_text(entry.get("name", "")) for entry in candidates}
        for candidate in extract_auto_learned_abilities(seed_text, actor_display):
            if normalized_eval_text(candidate.get("name", "")) not in known:
                candidates.append(candidate)
                known.add(normalized_eval_text(candidate.get("name", "")))
    if not candidates:
        return patch

    character = (working_state.get("characters", {}).get(actor, {}) or {})
    resource_name = resource_name_for_character(character, ((working_state.get("world") or {}).get("settings") or {}))
    existing_names = {
        normalized_eval_text((entry or {}).get("name", ""))
        for entry in ((character.get("skills") or {}).values())
        if isinstance(entry, dict) and entry.get("name")
    }
    target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
    existing_names.update(
        normalized_eval_text((skill or {}).get("name", ""))
        for skill in ((target_patch.get("skills_set") or {}).values())
        if isinstance(skill, dict) and skill.get("name")
    )
    target_patch.setdefault("skills_set", {})

    for candidate in candidates:
        normalized_name = normalized_eval_text(candidate["name"])
        if not normalized_name or normalized_name in existing_names:
            continue
        existing_names.add(normalized_name)
        skill_id = skill_id_from_name(candidate["name"])
        target_patch["skills_set"][skill_id] = normalize_dynamic_skill_state(
            {
                "id": skill_id,
                "name": candidate["name"],
                "rank": "F",
                "level": 1,
                "level_max": 10,
                "tags": candidate["tags"],
                "description": candidate["description"] or f"{actor_display} hat {candidate['name']} im Abenteuer erlernt.",
                "cost": {"resource": resource_name, "amount": 1} if "magie" in candidate["tags"] else None,
                "price": None,
                "cooldown_turns": None,
                "unlocked_from": "Story",
                "synergy_notes": None,
            },
            resource_name=resource_name,
        )
    return patch

def materialize_character_ability(
    character: Dict[str, Any],
    slot_name: str,
    ability_name: str,
    *,
    description: str,
    ability_type: str = "active",
    source: str = "story_auto",
) -> bool:
    clean_name = clean_auto_ability_name(ability_name)
    if not clean_name:
        return False
    resource_name = resource_name_for_character(character)
    existing_names = {
        normalized_eval_text((skill or {}).get("name", ""))
        for skill in ((character.get("skills") or {}).values())
        if isinstance(skill, dict)
    }
    if normalized_eval_text(clean_name) in existing_names:
        return False
    skill_id = skill_id_from_name(clean_name)
    character.setdefault("skills", {})[skill_id] = normalize_dynamic_skill_state(
        {
            "id": skill_id,
            "name": clean_name,
            "rank": "F",
            "level": 1,
            "level_max": 10,
            "tags": list(dict.fromkeys(["story_auto", "auto_unlock", *(["magie"] if ability_type == "active" else [])])),
            "description": (description or f"{clean_name} wurde in der Geschichte freigeschaltet.")[:220],
            "cost": {"resource": resource_name, "amount": 1} if ability_type == "active" else None,
            "price": None,
            "cooldown_turns": None,
            "unlocked_from": source or "Story",
            "synergy_notes": None,
        },
        resource_name=resource_name,
        unlocked_from=source or "Story",
    )
    return True

def materialize_story_abilities_from_turn_history(campaign: Dict[str, Any]) -> None:
    state = campaign.get("state", {}) or {}
    characters = state.get("characters", {}) or {}
    if not characters:
        return
    recent_turns = active_turns(campaign)[-12:]
    for turn in recent_turns:
        slot_name = turn.get("actor")
        if slot_name not in characters:
            continue
        character = characters[slot_name]
        actor_display = display_name_for_slot(campaign, slot_name)
        seen = set()
        for source_text in (
            turn.get("gm_text_display", ""),
            turn.get("input_text_display", "") if turn.get("action_type") == "story" else "",
            turn.get("input_text_raw", "") if turn.get("action_type") == "story" else "",
        ):
            for candidate in extract_auto_learned_abilities(source_text, actor_display):
                normalized_name = normalized_eval_text(candidate.get("name", ""))
                if not normalized_name or normalized_name in seen:
                    continue
                seen.add(normalized_name)
                materialize_character_ability(
                    character,
                    slot_name,
                    candidate.get("name", ""),
                    description=candidate.get("description", ""),
                    ability_type=candidate.get("type", "active"),
                    source="story_auto_history",
                )
