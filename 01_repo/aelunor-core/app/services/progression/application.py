from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional

from app.config.progression import PROGRESSION_EVENT_BASE_XP, PROGRESSION_EVENT_SEVERITY_MULTIPLIER, PROGRESSION_EVENT_TYPES
from app.core.ids import deep_copy
from app.services.canon.progression_gate import (
    normalize_progression_event,
    normalize_progression_event_list,
    normalize_progression_event_severity,
    reduce_progression_event_density,
)
from app.services.characters.resources import resource_name_for_character
from app.services.progression import classes, manifestation, skills
from app.services.world.progression import normalize_class_current
from app.services.world.text_normalization import normalized_eval_text


def _missing_dependency(name: str) -> Callable[..., Any]:
    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"Progression application dependency is not configured: {name}")
    return _missing


@dataclass(frozen=True)
class ProgressionApplicationDependencies:
    blank_character_state: Callable[..., Dict[str, Any]] = _missing_dependency("blank_character_state")
    normalize_world_time: Callable[..., Dict[str, Any]] = _missing_dependency("normalize_world_time")
    sync_appearance_changes: Callable[..., List[Dict[str, Any]]] = _missing_dependency("sync_appearance_changes")


_DEPS = ProgressionApplicationDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def blank_character_state(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.blank_character_state(*args, **kwargs)


def normalize_world_time(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.normalize_world_time(*args, **kwargs)


def sync_appearance_changes(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    return _DEPS.sync_appearance_changes(*args, **kwargs)


def append_character_change_events(
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    *,
    turn_number: int,
) -> List[str]:
    world_time = normalize_world_time(state_after.get("meta", {}))
    absolute_day = int(world_time["absolute_day"])
    messages = []
    for slot_name, after_character in (state_after.get("characters") or {}).items():
        before_character = (state_before.get("characters") or {}).get(slot_name) or blank_character_state(slot_name)
        events = sync_appearance_changes(
            before_character,
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
        )
        messages.extend(event["message"] for event in events if event.get("message"))
    if messages:
        state_after.setdefault("events", [])
        state_after["events"].extend(messages)
    return messages

def infer_progression_events_from_patch(
    *,
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str = "",
    story_text: str = "",
) -> List[Dict[str, Any]]:
    turn_number = int((state_after.get("meta") or {}).get("turn", 0) or 0)
    inferred: List[Dict[str, Any]] = []
    patch_characters = patch.get("characters") or {}

    for slot_name, upd in patch_characters.items():
        if not isinstance(upd, dict) or slot_name not in (state_after.get("characters") or {}):
            continue
        if upd.get("progression_events"):
            explicit_events = normalize_progression_event_list(
                upd.get("progression_events"),
                actor=slot_name,
                source_turn=turn_number,
            )
            for event in explicit_events:
                metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
                metadata["origin"] = "explicit_patch"
                event["metadata"] = metadata
            inferred.extend(explicit_events)
        hp_delta = int(upd.get("hp_delta", 0) or 0)
        stamina_delta = int(upd.get("stamina_delta", 0) or 0)
        res_delta_raw = 0
        if isinstance(upd.get("resources_delta"), dict):
            res_delta_raw = int(
                (upd.get("resources_delta") or {}).get("res", 0)
                or (upd.get("resources_delta") or {}).get("aether", 0)
                or 0
            )
        if hp_delta < 0 and action_type in {"do", "story", "say"}:
            inferred.append(
                {
                    "type": "combat_survival",
                    "actor": slot_name,
                    "severity": "medium" if hp_delta <= -3 else "low",
                    "reason": "Überstandene Kampffolge",
                    "source_turn": turn_number,
                    "target_skill_id": None,
                    "target_class_id": None,
                    "tags": ["combat"],
                    "metadata": {"hp_delta": hp_delta, "origin": "inferred_patch"},
                    "skill": {},
                }
            )
        if (stamina_delta < 0 or res_delta_raw < 0) and upd.get("skills_delta"):
            for skill_id in (upd.get("skills_delta") or {}).keys():
                    inferred.append(
                        {
                            "type": "skill_mastery_use",
                        "actor": slot_name,
                        "target_skill_id": str(skill_id),
                        "severity": "low",
                        "reason": "Skillnutzung unter Belastung",
                        "source_turn": turn_number,
                        "target_class_id": None,
                        "tags": ["skill_use"],
                            "metadata": {"stamina_delta": stamina_delta, "res_delta": res_delta_raw, "origin": "inferred_patch"},
                            "skill": {},
                        }
                    )
        if upd.get("class_set") or upd.get("class_update"):
            target_class_id = str(
                ((normalize_class_current(upd.get("class_set")) or (upd.get("class_update") or {})).get("id") or "")
            ).strip() or None
            inferred.append(
                {
                    "type": "class_breakthrough",
                    "actor": slot_name,
                    "target_skill_id": None,
                    "target_class_id": target_class_id,
                    "severity": "medium",
                    "reason": "Klassenfortschritt",
                    "source_turn": turn_number,
                    "tags": ["class"],
                    "metadata": {"origin": "inferred_patch"},
                    "skill": {},
                }
            )

    for plot_update in (patch.get("plotpoints_update") or []):
        if not isinstance(plot_update, dict):
            continue
        if str(plot_update.get("status") or "").strip().lower() != "done":
            continue
        inferred.append(
            {
                "type": "milestone_progress",
                "actor": actor,
                "target_skill_id": None,
                "target_class_id": None,
                "severity": "medium",
                "reason": f"Plotpoint abgeschlossen: {plot_update.get('id', '')}",
                "source_turn": turn_number,
                "tags": ["milestone"],
                "metadata": {"plotpoint_id": str(plot_update.get("id") or ""), "origin": "inferred_patch"},
                "skill": {},
            }
        )

    story_events = " ".join(str(entry or "") for entry in (patch.get("events_add") or []))
    story_norm = normalized_eval_text(story_events)
    if any(word in story_norm for word in ("boss", "erzgegner", "endgegner")) and any(
        word in story_norm for word in ("besiegt", "gefallen", "zerstoert", "zerstört")
    ):
        inferred.append(
            {
                "type": "boss_defeated",
                "actor": actor,
                "target_skill_id": None,
                "target_class_id": None,
                "severity": "high",
                "reason": "Boss wurde besiegt",
                "source_turn": turn_number,
                "tags": ["combat", "boss"],
                "metadata": {"origin": "inferred_patch"},
                "skill": {},
            }
        )
    elif any(word in story_norm for word in ("gegner", "kreatur", "feind", "monster")) and any(
        word in story_norm for word in ("besiegt", "fällt", "zerstoert", "zerstört", "ausgeschaltet")
    ):
        inferred.append(
            {
                "type": "combat_victory",
                "actor": actor,
                "target_skill_id": None,
                "target_class_id": None,
                "severity": "medium",
                "reason": "Kampfsieg",
                "source_turn": turn_number,
                "tags": ["combat"],
                "metadata": {"origin": "inferred_patch"},
                "skill": {},
            }
        )
    inferred.extend(
        manifestation.infer_manifestation_progression_events_from_story(
            state_before=state_before,
            state_after=state_after,
            patch=patch,
            actor=actor,
            action_type=action_type,
            player_text=player_text,
            story_text=story_text,
        )
    )
    return inferred

def apply_progression_event_xp(
    *,
    character: Dict[str, Any],
    event: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]],
    actor_slot: str,
) -> List[str]:
    messages: List[str] = []
    event_type = str(event.get("type") or "").strip().lower()
    if event_type not in PROGRESSION_EVENT_TYPES:
        return messages
    severity = normalize_progression_event_severity(event.get("severity"))
    severity_mult = PROGRESSION_EVENT_SEVERITY_MULTIPLIER.get(severity, 1.0)
    speed_mult = skills.progression_speed_multiplier(world_settings)
    base = PROGRESSION_EVENT_BASE_XP.get(event_type, PROGRESSION_EVENT_BASE_XP["milestone_progress"])

    character_gain = max(1, int(round(base["character"] * severity_mult * speed_mult)))
    class_gain = max(0, int(round(base["class"] * severity_mult * speed_mult)))
    skill_gain = max(0, int(round(base["skill"] * severity_mult * speed_mult)))

    before_level = int(character.get("level", 1) or 1)
    skills.apply_system_xp(character, character_gain)
    after_level = int(character.get("level", 1) or 1)
    if after_level > before_level:
        char_name = str(((character.get("bio") or {}).get("name") or actor_slot).strip())
        messages.append(f"{char_name} steigt auf Lv {after_level} auf.")

    if class_gain > 0:
        messages.extend(classes.apply_class_xp(character, class_gain, event_reason=str(event.get("reason") or "")))

    target_skill_id = str(event.get("target_skill_id") or "").strip()
    if event_type == "skill_manifestation" and not target_skill_id:
        skill_payload = deep_copy(event.get("skill") or {})
        if isinstance(skill_payload, dict) and skill_payload.get("name"):
            target_skill_id = skills.skill_id_from_name(str(skill_payload.get("name") or ""))
            event["target_skill_id"] = target_skill_id
    if skill_gain > 0 and target_skill_id:
        outcomes = {1: "small", 2: "normal", 3: "major"}
        bucket = 1 if severity == "low" else 2 if severity == "medium" else 3
        for _ in range(max(1, int(round(skill_gain / 12.0)))):
            messages.extend(skills.grant_skill_xp(character, target_skill_id, outcomes[bucket], world_settings=world_settings))
    skills.append_recent_progression_event(character, event)
    return messages

def apply_progression_events(
    campaign: Dict[str, Any],
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    player_text: str = "",
    story_text: str = "",
) -> Dict[str, Any]:
    world_settings = ((state_after.get("world") or {}).get("settings") or {})
    world_model = state_after.get("world") if isinstance(state_after.get("world"), dict) else {}
    turn_number = int((state_after.get("meta") or {}).get("turn", 0) or 0)
    normalized_events = infer_progression_events_from_patch(
        state_before=state_before,
        state_after=state_after,
        patch=patch,
        actor=actor,
        action_type=action_type,
        player_text=player_text,
        story_text=story_text,
    )
    normalized_events = reduce_progression_event_density(
        normalized_events,
        state_after=state_after,
        action_type=action_type,
    )
    event_messages: List[str] = []
    applied_events: List[Dict[str, Any]] = []
    for raw_event in normalized_events:
        event = normalize_progression_event(raw_event, actor=actor, source_turn=turn_number)
        if not event:
            continue
        slot_name = str(event.get("actor") or "").strip()
        if slot_name not in (state_after.get("characters") or {}):
            continue
        character = (state_after.get("characters") or {}).get(slot_name) or {}
        skills.ensure_progression_shape(character)
        skills.ensure_character_progression_core(character)
        manifestation_msg = manifestation.manifest_skill_from_progression_event(
            character=character,
            actor_slot=slot_name,
            event=event,
            world=state_after.get("world") if isinstance(state_after.get("world"), dict) else {},
            world_settings=world_settings,
        )
        if manifestation_msg:
            event_messages.append(manifestation_msg)
            metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
            if metadata.get("seed_eligible"):
                seed = manifestation.manifestation_seed_from_skill(
                    event.get("skill") if isinstance(event.get("skill"), dict) else {},
                    source_turn=int(event.get("source_turn", 0) or 0),
                    confidence=float(metadata.get("manifestation_confidence", 0.0) or 0.0),
                )
                seed_message = manifestation.upsert_class_path_seed(character, seed) if seed else None
                if seed_message:
                    event_messages.append(seed_message)
        event_messages.extend(
            apply_progression_event_xp(
                character=character,
                event=event,
                world_settings=world_settings,
                actor_slot=slot_name,
            )
        )
        event_type = str(event.get("type") or "").strip().lower()
        event_messages.extend(
            classes.ensure_class_rank_core_skills(
                character,
                world_model,
                world_settings,
                unlock_extra=event_type in {"milestone_progress", "class_breakthrough", "boss_defeated", "skill_manifestation"},
            )
        )
        applied_events.append(event)
        state_after["characters"][slot_name] = character
    if event_messages:
        state_after.setdefault("events", [])
        state_after["events"].extend(event_messages)
    return {"events": applied_events, "messages": event_messages}

def build_skill_system_requests(
    campaign: Dict[str, Any],
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
) -> List[Dict[str, Any]]:
    requests: List[Dict[str, Any]] = []
    world_settings = (((state_after.get("world") or {}).get("settings") or {}))
    for slot_name, after_character in (state_after.get("characters") or {}).items():
        before_character = ((state_before.get("characters") or {}).get(slot_name) or {})
        before_level = int(before_character.get("level", 1) or 1)
        after_level = int(after_character.get("level", 1) or 1)
        if after_level > before_level:
            requests.append(
                {
                    "type": "clarify",
                    "actor": slot_name,
                    "question": f"Neues Level erreicht ({after_level}). Soll der Fokus als nächstes eher auf Klasse oder Skill-Meisterung liegen?",
                }
            )
        before_class = normalize_class_current(before_character.get("class_current"))
        after_class = normalize_class_current(after_character.get("class_current"))
        if after_class and (not before_class or int(after_class.get("level", 1) or 1) > int((before_class or {}).get("level", 1) or 1)):
            requests.append(
                {
                    "type": "choice",
                    "actor": slot_name,
                    "question": f"Klassenfortschritt für {after_class.get('name', 'Klasse')}: Welche Richtung soll gestärkt werden?",
                    "options": ["Offensive Schärfung", "Defensive Stabilität", "Ressourcenkontrolle", "Eigener Plan"],
                }
            )
        skill_hints = skills.build_skill_fusion_hints(after_character.get("skills") or {}, resource_name=resource_name_for_character(after_character, world_settings))
        if skill_hints:
            top_hint = skill_hints[0]
            requests.append(
                {
                    "type": "choice",
                    "actor": slot_name,
                    "question": f"{top_hint.get('label')} Soll der Erzähler eine Evolution erzählerisch vorbereiten?",
                    "options": ["Ja, vorbereiten", "Nein, vorerst nicht", "Eigener Plan"],
                }
            )
            break
    return requests[:2]
