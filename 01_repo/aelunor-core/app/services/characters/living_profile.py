from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List


LivingProfile = Dict[str, Any]


def default_living_profile() -> LivingProfile:
    return {
        "version": 1,
        "status": "generated",
        "identity": {
            "name": "",
            "aliases": [],
            "public_role": "",
            "private_role": "",
            "archetype": "",
            "subversion": "",
            "first_impression": "",
            "core_contrast": "",
        },
        "origin_context": {
            "origin_type": "custom",
            "home_context": "",
            "social_class": "",
            "formative_events": [],
            "inherited_burdens": [],
            "starting_beliefs": [],
            "starting_status": "",
            "why_the_story_starts_now": "",
        },
        "self_image": {
            "how_they_describe_themselves": "",
            "what_they_are_proud_of": "",
            "what_they_hide": "",
            "what_they_deny": "",
            "what_they_are_wrong_about": "",
            "desired_identity": "",
            "feared_identity": "",
        },
        "personality_model": {
            "primary_traits": [],
            "secondary_traits": [],
            "contradictions": [],
            "values": [],
            "fears": [],
            "desires": [],
            "boundaries": [],
            "temptations": [],
            "petty_flaws": [],
            "virtues": [],
        },
        "behavior_model": {
            "default_behavior": "",
            "under_pressure": "",
            "when_afraid": "",
            "when_angry": "",
            "when_hurt": "",
            "when_embarrassed": "",
            "when_protecting_someone": "",
            "when_losing_control": "",
            "when_winning": "",
            "when_failing": "",
            "decision_biases": [],
            "habitual_actions": [],
            "signature_moves_social": [],
            "signature_moves_combat": [],
            "anti_patterns": [],
            "typical_patterns": [],
        },
        "speech_model": {
            "voice_summary": "",
            "sentence_style": "",
            "vocabulary": [],
            "catchphrases": [],
            "verbal_tics": [],
            "humor_style": "",
            "formality_level": "",
            "emotional_leakage": "",
            "languages": {},
            "things_they_never_say": [],
        },
        "social_model": {
            "trust_style": "",
            "attachment_style": "",
            "leadership_style": "",
            "conflict_style": "",
            "flirting_style": "",
            "friendship_style": "",
            "authority_response": "",
            "party_role_social": "",
            "relationship_patterns": [],
            "specific_bonds": {},
        },
        "emotional_model": {
            "baseline_mood": "",
            "current_mood": "",
            "stress_response": "",
            "comfort_sources": [],
            "destabilizers": [],
            "emotional_triggers": [],
            "recovery_behavior": "",
            "suppressed_emotions": [],
        },
        "motivation_model": {
            "short_term_goal": "",
            "long_term_goal": "",
            "hidden_goal": "",
            "need": "",
            "want": "",
            "fear_of_loss": "",
            "line_they_will_cross": "",
            "line_they_refuse_to_cross": "",
        },
        "conflict_model": {
            "inner_conflict": "",
            "external_conflicts": [],
            "moral_dilemmas": [],
            "temptation_hooks": [],
            "rivalry_hooks": [],
            "shame_points": [],
            "breaking_points": [],
            "redemption_hooks": [],
        },
        "growth_model": {
            "arc_direction": "",
            "possible_growth": [],
            "possible_corruption": [],
            "lessons_learned": [],
            "regressions": [],
            "milestones": [],
            "identity_shifts": [],
            "class_growth_link": "",
            "skill_growth_link": "",
        },
        "world_resonance": {
            "genre_fit": "",
            "power_system_interaction": "",
            "element_or_force_affinities": [],
            "cultural_friction": [],
            "language_exposure": [],
            "faction_resonance": [],
            "monster_fear_or_fascination": [],
            "signature_world_mark": "",
            "how_the_world_changes_them": "",
        },
        "memory_model": {
            "defining_moments": [],
            "recent_behavior_patterns": [],
            "promises_made": [],
            "promises_broken": [],
            "people_they_failed": [],
            "people_they_saved": [],
            "running_jokes": [],
            "repeated_choices": [],
            "language_misunderstandings": [],
        },
        "roleplay_rules": {
            "player_controlled": True,
            "ai_may_infer_micro_reactions": True,
            "ai_may_not_override_major_choices": True,
            "ai_may_suggest_typical_behavior": True,
            "ai_may_update_profile_from_actions": True,
            "protected_character_facts": [],
            "forbidden_character_drift": [],
        },
        "consistency_controls": {
            "core_traits_locked": [],
            "flexible_traits": [],
            "current_arc_phase": "",
            "drift_warnings": [],
            "last_profile_update_turn": 0,
            "profile_confidence": "medium",
            "needs_player_confirmation": [],
        },
        "revision": {"revision_id": 1, "created_turn": 0, "last_updated_turn": 0, "change_log": []},
    }


def normalize_living_profile(
    raw: Any,
    character: Any = None,
    world_bible: Any = None,
    setup_answers: Any = None,
) -> LivingProfile:
    raw_dict = _dict(raw)
    if _should_generate_fallback(raw_dict, character, setup_answers):
        raw_dict = generate_living_profile_fallback(character or {}, world_bible=world_bible, setup_answers=setup_answers)
    profile = _merge_defaults(default_living_profile(), raw_dict)
    profile["version"] = 1
    profile["status"] = _string(profile.get("status"), "generated") or "generated"
    _normalize_profile_lists(profile)
    _normalize_typical_patterns(profile)
    _normalize_speech_languages(profile)
    _normalize_controls(profile)
    return profile


def generate_living_profile_fallback(character: Any, world_bible: Any = None, setup_answers: Any = None) -> LivingProfile:
    character = _dict(character)
    bio = _dict(character.get("bio"))
    setup = _dict(setup_answers)
    name = _string(bio.get("name") or _value(setup, "display_name") or _value(setup, "char_name"))
    personality = _unique_strings(_list(bio.get("personality")) + _list(_value(setup, "personality_tags")))
    strength = _string(bio.get("strength") or _value(setup, "strength"))
    weakness = _string(bio.get("weakness") or _value(setup, "weakness"))
    focus = _string(bio.get("focus") or _value(setup, "current_focus"))
    goal = _string(bio.get("goal") or _value(setup, "first_goal"))
    class_current = _dict(character.get("class_current"))
    class_name = _string(class_current.get("name"))
    world_identity = _dict(_dict(world_bible).get("identity"))
    metaphysics = _dict(_dict(world_bible).get("metaphysics"))
    seed = _stable_seed({"name": name, "personality": personality, "strength": strength, "weakness": weakness, "goal": goal, "class": class_name})
    primary_trait = personality[0] if personality else _fallback_trait(seed)
    public_role = class_name or focus or "handelnde Figur"
    archetype = _join_phrase([primary_trait, public_role], " ")
    profile = default_living_profile()
    profile["identity"].update(
        {
            "name": name,
            "public_role": public_role,
            "private_role": strength or goal,
            "archetype": archetype,
            "subversion": weakness,
            "first_impression": _first_impression(primary_trait, focus),
            "core_contrast": _core_contrast(primary_trait, weakness, strength),
        }
    )
    profile["origin_context"].update(_fallback_origin_context(bio, setup))
    profile["self_image"].update(
        {
            "what_they_are_proud_of": strength,
            "what_they_hide": weakness,
            "desired_identity": goal or strength,
            "feared_identity": weakness,
        }
    )
    profile["personality_model"].update(
        {
            "primary_traits": personality[:4],
            "secondary_traits": _unique_strings([focus, strength])[:4],
            "contradictions": [_core_contrast(primary_trait, weakness, strength)] if weakness else [],
            "values": _values_from_text(strength, goal),
            "fears": [weakness] if weakness else [],
            "desires": [goal] if goal else [],
            "virtues": [strength] if strength else [],
            "petty_flaws": [weakness] if weakness else [],
        }
    )
    profile["behavior_model"].update(
        {
            "default_behavior": _default_behavior(primary_trait, public_role),
            "under_pressure": _pressure_behavior(weakness),
            "when_afraid": _fear_behavior(personality),
            "when_protecting_someone": _protective_behavior(strength),
            "decision_biases": _unique_strings([strength, weakness, focus]),
            "anti_patterns": _anti_patterns(weakness),
            "typical_patterns": _fallback_patterns(strength, weakness, personality, goal),
        }
    )
    profile["speech_model"].update(_fallback_speech_model(personality, weakness))
    profile["social_model"].update({"party_role_social": public_role, "relationship_patterns": _unique_strings([primary_trait, weakness])})
    profile["emotional_model"].update({"baseline_mood": primary_trait, "current_mood": primary_trait, "stress_response": _pressure_behavior(weakness), "destabilizers": [weakness] if weakness else [], "emotional_triggers": _unique_strings([goal, weakness])})
    profile["motivation_model"].update({"short_term_goal": goal, "long_term_goal": goal, "need": strength, "want": goal, "fear_of_loss": weakness, "line_they_refuse_to_cross": "Spielerentscheidung respektieren; keine harte Grenze ohne Spieler bestaetigen."})
    profile["conflict_model"].update({"inner_conflict": _core_contrast(primary_trait, weakness, strength), "external_conflicts": _list(character.get("faction_memberships")), "shame_points": [weakness] if weakness else [], "redemption_hooks": [goal] if goal else []})
    profile["growth_model"].update({"arc_direction": "aus wiederholten Entscheidungen ableiten", "class_growth_link": class_name, "skill_growth_link": _skill_names(character)})
    profile["world_resonance"].update(_fallback_world_resonance(world_identity, metaphysics, character, bio))
    profile["roleplay_rules"]["protected_character_facts"] = _unique_strings([name, class_name, strength, weakness])
    profile["consistency_controls"]["core_traits_locked"] = _unique_strings([primary_trait, strength, weakness])[:5]
    return normalize_living_profile(profile)


def build_living_profile_prompt_summary(profile: Any, character: Any = None) -> str:
    normalized = normalize_living_profile(profile, character=character)
    name = normalized["identity"].get("name") or _string(_dict(_dict(character).get("bio")).get("name")) or "Unbenannter Charakter"
    patterns = normalized["behavior_model"].get("typical_patterns") or []
    pattern_lines = [
        f"- Wenn {p['trigger']}, {p['reaction']}; Tell: {p['tell'] or 'keine feste Spur'}."
        for p in patterns[:4]
    ]
    if not pattern_lines:
        pattern_lines = ["- Noch keine festen Patterns; nur vorsichtige Mikroreaktionen andeuten."]
    return "\n".join(
        [
            f"LIVING CHARACTER SUMMARY - {name}:",
            f"Archetype: {normalized['identity'].get('archetype') or 'offen'}; Subversion: {normalized['identity'].get('subversion') or 'offen'}.",
            f"Core Contrast: {normalized['identity'].get('core_contrast') or normalized['conflict_model'].get('inner_conflict') or 'noch offen'}.",
            "Typical Patterns:",
            *pattern_lines,
            f"Voice: {normalized['speech_model'].get('voice_summary') or 'natuerlich'}; {normalized['speech_model'].get('sentence_style') or 'situativ'}.",
            f"Motivation: {normalized['motivation_model'].get('want') or normalized['motivation_model'].get('short_term_goal') or 'noch offen'}.",
            f"Fear/Shame: {', '.join(normalized['conflict_model'].get('shame_points') or normalized['personality_model'].get('fears') or []) or 'noch offen'}.",
            f"Boundaries: {', '.join(normalized['personality_model'].get('boundaries') or normalized['roleplay_rules'].get('protected_character_facts') or []) or 'Spielerfakten respektieren'}.",
            f"Anti-Patterns: {', '.join(normalized['behavior_model'].get('anti_patterns') or []) or 'keine beliebige Persoenlichkeitsdrift'}.",
            "AI Control: Spielerentscheidungen nicht ueberschreiben; nur Mikroreaktionen, Stimmung und typische Impulse andeuten.",
        ]
    )


def normalize_typical_pattern(raw: Any) -> Dict[str, Any]:
    data = _dict(raw)
    confidence = _string(data.get("confidence"), "medium").lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    return {
        "trigger": _string(data.get("trigger")),
        "reaction": _string(data.get("reaction")),
        "cost": _string(data.get("cost")),
        "tell": _string(data.get("tell")),
        "confidence": confidence,
    }


def normalize_language_profile(raw: Any) -> Dict[str, Any]:
    data = _dict(raw)
    return {
        "language": _string(data.get("language") or data.get("name")),
        "comprehension": _string(data.get("comprehension"), "unknown") or "unknown",
        "speaking": _string(data.get("speaking"), "unknown") or "unknown",
        "literacy": _string(data.get("literacy"), "unknown") or "unknown",
        "notes": _list(data.get("notes")),
    }


def _fallback_origin_context(bio: Dict[str, Any], setup: Dict[str, Any]) -> Dict[str, Any]:
    earth_life = _string(bio.get("earth_life") or _value(setup, "earth_life"))
    price = _string(bio.get("isekai_price") or _value(setup, "isekai_price"))
    earth_items = _list(bio.get("earth_items") or _value(setup, "earth_items"))
    return {
        "origin_type": "cross_world" if earth_life or price or earth_items else "custom",
        "home_context": earth_life,
        "formative_events": _unique_strings([earth_life, price]),
        "inherited_burdens": [price] if price else [],
        "starting_beliefs": _list(bio.get("background_tags")),
        "starting_status": _string(bio.get("age")),
        "why_the_story_starts_now": _string(bio.get("goal") or _value(setup, "first_goal")),
    }


def _fallback_world_resonance(world_identity: Dict[str, Any], metaphysics: Dict[str, Any], character: Dict[str, Any], bio: Dict[str, Any]) -> Dict[str, Any]:
    power_name = _string(metaphysics.get("main_power_name"))
    world_name = _string(world_identity.get("world_name"))
    elements = _unique_strings(_list(character.get("element_affinities")) + _list(character.get("element_resistances")))
    return {
        "genre_fit": _string(world_identity.get("genre_shape") or world_identity.get("core_pitch")),
        "power_system_interaction": f"reagiert auf {power_name}" if power_name else "",
        "element_or_force_affinities": elements,
        "cultural_friction": _list(bio.get("background_tags")),
        "language_exposure": [],
        "faction_resonance": _list(character.get("faction_memberships")),
        "signature_world_mark": world_name,
        "how_the_world_changes_them": "durch wiederholte Entscheidungen und Kosten sichtbar machen",
    }


def _fallback_speech_model(personality: List[str], weakness: str) -> Dict[str, Any]:
    humor = "trocken oder ausweichend" if _contains(personality, ("humor", "witz", "sarkas")) else ""
    return {
        "voice_summary": ", ".join(personality[:3]) or "noch offen",
        "sentence_style": "konkret, reaktiv, charaktergebunden",
        "vocabulary": personality[:5],
        "humor_style": humor,
        "emotional_leakage": f"weicht aus bei {weakness}" if weakness else "",
        "things_they_never_say": ["Ich entscheide ohne Spielerwillen."],
    }


def _fallback_patterns(strength: str, weakness: str, personality: List[str], goal: str) -> List[Dict[str, Any]]:
    patterns: List[Dict[str, Any]] = []
    if _contains([strength, goal], ("besch", "rett", "schutz", "helf", "loyal")):
        patterns.append({"trigger": "jemand ist akut in Gefahr", "reaction": "greift schnell ein, bevor der Plan vollstaendig ist", "cost": "uebersieht eigene Risiken", "tell": "wird kurz still und bewegt sich zuerst", "confidence": "medium"})
    if _contains(personality, ("humor", "witz", "sarkas")):
        patterns.append({"trigger": "echte Angst oder Naehe sichtbar wird", "reaction": "macht einen Witz oder provoziert", "cost": "verhindert Naehe", "tell": "grinst zu schnell", "confidence": "medium"})
    if _contains([weakness], ("unged", "uebermut", "impuls", "stolz")):
        patterns.append({"trigger": "Warten oder Unterordnung noetig waere", "reaction": "handelt zu frueh oder fordert heraus", "cost": "bringt den Plan unter Druck", "tell": "spricht knapper und schneller", "confidence": "medium"})
    if not patterns:
        patterns.append({"trigger": "die Lage kippt gegen die Gruppe", "reaction": "faellt auf die staerkste bekannte Eigenschaft zurueck", "cost": "blendet widersprechende Hinweise aus", "tell": "wiederholt eine vertraute Geste", "confidence": "low"})
    return [normalize_typical_pattern(pattern) for pattern in patterns[:5]]


def _normalize_profile_lists(profile: LivingProfile) -> None:
    list_keys = {
        "identity": ("aliases",),
        "origin_context": ("formative_events", "inherited_burdens", "starting_beliefs"),
        "personality_model": ("primary_traits", "secondary_traits", "contradictions", "values", "fears", "desires", "boundaries", "temptations", "petty_flaws", "virtues"),
        "behavior_model": ("decision_biases", "habitual_actions", "signature_moves_social", "signature_moves_combat", "anti_patterns"),
        "speech_model": ("vocabulary", "catchphrases", "verbal_tics", "things_they_never_say"),
        "social_model": ("relationship_patterns",),
        "emotional_model": ("comfort_sources", "destabilizers", "emotional_triggers", "suppressed_emotions"),
        "conflict_model": ("external_conflicts", "moral_dilemmas", "temptation_hooks", "rivalry_hooks", "shame_points", "breaking_points", "redemption_hooks"),
        "growth_model": ("possible_growth", "possible_corruption", "lessons_learned", "regressions", "milestones", "identity_shifts"),
        "world_resonance": ("element_or_force_affinities", "cultural_friction", "language_exposure", "faction_resonance", "monster_fear_or_fascination"),
        "memory_model": ("defining_moments", "recent_behavior_patterns", "promises_made", "promises_broken", "people_they_failed", "people_they_saved", "running_jokes", "repeated_choices", "language_misunderstandings"),
    }
    for section, keys in list_keys.items():
        for key in keys:
            profile[section][key] = _list(profile[section].get(key))


def _normalize_typical_patterns(profile: LivingProfile) -> None:
    profile["behavior_model"]["typical_patterns"] = [
        normalize_typical_pattern(entry)
        for entry in _list(profile["behavior_model"].get("typical_patterns"))
        if isinstance(entry, dict)
    ]


def _normalize_speech_languages(profile: LivingProfile) -> None:
    languages = _dict(profile["speech_model"].get("languages"))
    profile["speech_model"]["languages"] = {str(key): normalize_language_profile(value) for key, value in languages.items()}


def _normalize_controls(profile: LivingProfile) -> None:
    rules = profile["roleplay_rules"]
    for key in ("player_controlled", "ai_may_infer_micro_reactions", "ai_may_not_override_major_choices", "ai_may_suggest_typical_behavior", "ai_may_update_profile_from_actions"):
        rules[key] = _bool(rules.get(key), True)
    rules["protected_character_facts"] = _list(rules.get("protected_character_facts"))
    rules["forbidden_character_drift"] = _list(rules.get("forbidden_character_drift"))
    controls = profile["consistency_controls"]
    for key in ("core_traits_locked", "flexible_traits", "drift_warnings", "needs_player_confirmation"):
        controls[key] = _list(controls.get(key))
    controls["last_profile_update_turn"] = max(0, int(controls.get("last_profile_update_turn", 0) or 0))
    if controls.get("profile_confidence") not in {"low", "medium", "high"}:
        controls["profile_confidence"] = "medium"


def _should_generate_fallback(raw: Dict[str, Any], character: Any, setup_answers: Any) -> bool:
    if not character and not setup_answers:
        return False
    identity = _dict(raw.get("identity"))
    behavior = _dict(raw.get("behavior_model"))
    return not raw or (not _string(identity.get("name")) and not _list(behavior.get("typical_patterns")))


def _merge_defaults(default: Any, raw: Any) -> Any:
    if isinstance(default, dict):
        result = copy.deepcopy(default)
        for key, value in _dict(raw).items():
            result[key] = _merge_defaults(result[key], value) if key in result else copy.deepcopy(value)
        return result
    if isinstance(default, list):
        return _list(raw)
    if isinstance(default, bool):
        return _bool(raw, default)
    if isinstance(default, int):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default
    return _string(raw, default) if isinstance(default, str) else copy.deepcopy(raw if raw is not None else default)


def _value(source: Any, key: str) -> Any:
    value = _dict(source).get(key)
    if isinstance(value, dict):
        if "value" in value:
            return value.get("value")
        selected = value.get("selected")
        selected_values = selected if isinstance(selected, list) else ([selected] if selected else [])
        other_values = value.get("other_values") if isinstance(value.get("other_values"), list) else []
        return selected_values + other_values or value.get("other_text") or ""
    return value


def _skill_names(character: Dict[str, Any]) -> str:
    names = []
    for skill_id, skill in _dict(character.get("skills")).items():
        names.append(_string(_dict(skill).get("name") or skill_id))
    return ", ".join(_unique_strings(names)[:6])


def _values_from_text(strength: str, goal: str) -> List[str]:
    return _unique_strings([strength, goal])


def _anti_patterns(weakness: str) -> List[str]:
    return [f"nicht beliebig gegen Schwachpunkt '{weakness}' handeln"] if weakness else ["keine harte Persoenlichkeitswende ohne Storygrund"]


def _default_behavior(primary_trait: str, public_role: str) -> str:
    return f"agiert zuerst aus {primary_trait or 'bekannter Haltung'} als {public_role or 'Figur'}"


def _pressure_behavior(weakness: str) -> str:
    return f"faellt in {weakness} zurueck" if weakness else "zeigt die bisher staerkste bekannte Reaktion"


def _fear_behavior(personality: List[str]) -> str:
    if _contains(personality, ("humor", "witz", "sarkas")):
        return "macht Witze oder provoziert"
    return "wird vorsichtiger und koerperlich lesbar"


def _protective_behavior(strength: str) -> str:
    return "stellt Schutz vor Selbstsicherheit" if _contains([strength], ("besch", "rett", "schutz", "helf")) else ""


def _first_impression(primary_trait: str, focus: str) -> str:
    return _join_phrase([primary_trait, focus], ", ") or "noch offen"


def _core_contrast(primary_trait: str, weakness: str, strength: str) -> str:
    if weakness and strength:
        return f"wirkt durch {strength} stabil, wird aber von {weakness} herausgefordert"
    if weakness:
        return f"wirkt {primary_trait or 'kontrolliert'}, versteckt aber {weakness}"
    return f"wirkt {primary_trait or 'offen'}, muss aber erst durch Entscheidungen schaerfer werden"


def _fallback_trait(seed: str) -> str:
    return ["vorsichtig", "direkt", "loyal", "neugierig"][int(seed[:2], 16) % 4]


def _contains(values: Iterable[Any], needles: Iterable[str]) -> bool:
    text = " ".join(_string(value).lower() for value in values)
    return any(needle in text for needle in needles)


def _stable_seed(value: Any) -> str:
    return hashlib.sha1(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _join_phrase(parts: Iterable[Any], separator: str) -> str:
    return separator.join(_string(part) for part in parts if _string(part))


def _string(value: Any, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    return re.sub(r"\s+", " ", text)


def _list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [entry for entry in value if entry not in (None, "")]
    if isinstance(value, tuple):
        return [entry for entry in value if entry not in (None, "")]
    if isinstance(value, dict):
        return [entry for entry in list(value.get("selected") or []) + list(value.get("other_values") or []) if entry]
    text = _string(value)
    return [part.strip() for part in re.split(r"[\n,;]+", text) if part.strip()]


def _dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "ja"}:
            return True
        if lowered in {"false", "0", "no", "nein"}:
            return False
    return default


def _unique_strings(values: Iterable[Any]) -> List[str]:
    result = []
    seen = set()
    for value in values:
        text = _string(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result
