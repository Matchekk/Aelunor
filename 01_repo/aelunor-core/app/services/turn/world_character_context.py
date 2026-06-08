from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from app.services.characters.living_profile import build_living_profile_prompt_summary
from app.services.world.world_bible import build_world_bible_prompt_summary


def build_world_bible_context_block(campaign: dict, *, max_chars: int = 1800) -> str:
    bible = (((campaign.get("state") or {}).get("world") or {}).get("bible") or {})
    if not isinstance(bible, dict) or not bible:
        return _truncate("WORLD BIBLE SUMMARY:\nKeine World Bible verfuegbar; nutze vorhandene Campaign-Regeln und vermeide generische Begriffe.", max_chars)
    return _truncate(build_world_bible_prompt_summary(bible), max_chars)


def build_living_character_context_block(
    campaign: dict,
    actor_slot: str | None = None,
    *,
    max_chars: int = 2200,
) -> str:
    character = _character_for_slot(campaign, actor_slot)
    if not character:
        return _truncate("ACTIVE CHARACTER LIVING SUMMARY:\nKein aktiver Charakter-Slot erkannt.", max_chars)
    profile = character.get("living_profile") if isinstance(character, dict) else {}
    if not isinstance(profile, dict) or not profile:
        name = _character_name(character, actor_slot)
        return _truncate(f"ACTIVE CHARACTER LIVING SUMMARY:\n{name}: Kein Living Profile verfuegbar; Spielerentscheidungen respektieren.", max_chars)
    summary = build_living_profile_prompt_summary(profile, character=character)
    return _truncate(summary.replace("LIVING CHARACTER SUMMARY", "ACTIVE CHARACTER LIVING SUMMARY", 1), max_chars)


def build_party_living_context_block(
    campaign: dict,
    actor_slot: str | None = None,
    *,
    max_chars: int = 1800,
) -> str:
    rows: List[str] = ["PARTY LIVING SUMMARY:"]
    for slot_name, character in _party_characters(campaign):
        if actor_slot and slot_name == actor_slot:
            continue
        profile = character.get("living_profile") if isinstance(character, dict) else {}
        identity = profile.get("identity") if isinstance(profile, dict) else {}
        behavior = profile.get("behavior_model") if isinstance(profile, dict) else {}
        motivation = profile.get("motivation_model") if isinstance(profile, dict) else {}
        patterns = behavior.get("typical_patterns") if isinstance(behavior, dict) else []
        pattern_text = _pattern_preview(patterns)
        rows.append(
            "- "
            + _character_name(character, slot_name)
            + ": "
            + _join_nonempty(
                [
                    identity.get("archetype") if isinstance(identity, dict) else "",
                    pattern_text,
                    motivation.get("want") if isinstance(motivation, dict) else "",
                ],
                "; ",
            )
        )
    if len(rows) == 1:
        rows.append("Keine weiteren Living Profiles verfuegbar.")
    return _truncate("\n".join(rows), max_chars)


def build_style_consistency_guard_block(campaign: dict, actor_slot: str | None = None) -> str:
    return "\n".join(
        [
            "STYLE AND CONSISTENCY GUARD:",
            "- Nutze die World Bible als verbindliche Quelle fuer Namen, Sprachen, Ortsaliasse, Skills, Items, Monster, Races, Fraktionen, Titel und magische Begriffe.",
            "- Vermeide generische Fantasy-/RPG-Begriffe, wenn die World Bible spezifischere Begriffe ermoeglicht.",
            "- Neue Skills brauchen Quelle, Kosten/Risiko oder klare Beziehung zu Handlung, Weltlogik, Klasse oder Charakter.",
            "- Neue Orte, Items, Monster und Fraktionen muessen zur Welt-DNA passen.",
            "- Race-Linguistik und Place-Aliases duerfen zu Teilverstaendnis oder Fehlinterpretationen fuehren, wenn ein Charakter die Sprache nur schwach versteht.",
            "- Living Profiles beschreiben typische Muster, Stimme, Motivation und Grenzen.",
            "- Living World: Weltreaktionen aus Ripple Effects ableiten; Probleme sind lokale Symptome groesserer Druckwellen.",
            "- Orte, Fraktionen und NPCs handeln aus Ressource, Angst, Status, Kultur und Beziehung, nicht aus isolierter Lore.",
            "- Keine harte Hauptquest aufzwingen, wenn Spieler andere Spuren verfolgen; Ursache ueber Spuren und Konsequenzen zeigen.",
            "- Living Character: Emotionen ueber Koerper, Handlung, Sprache und Subtext zeigen, nicht nur labeln.",
            "- Spezies-Tendenz, kulturelle Norm, individuelle Biografie und momentane Situation strikt trennen; nie vom Label direkt zur Handlung springen.",
            "- Nichtmenschliche Figuren fremd, aber kausal verstehbar schreiben; keine Spezies-Stereotype, keine Diagnosen, keine deterministische Rassenlogik.",
            "- Spielercharaktere duerfen nicht durch KI-Entscheidungen entmuendigt werden.",
            "- Bei Spielercharakteren nur Mikroreaktionen, typische Impulse, Koerpersprache, Unsicherheit, Versuchung oder innere Spannung andeuten.",
            "- Keine grosse Entscheidung, kein Verrat, kein Mord, keine Romanze, kein Skill-Einsatz und kein freiwilliges Opfer ohne passende Spieleraktion.",
        ]
    )


def build_world_character_context_packet(
    campaign: dict,
    actor_slot: str | None = None,
    *,
    max_chars: int = 5200,
) -> Dict[str, str]:
    world_bible_summary = build_world_bible_context_block(campaign, max_chars=1800)
    active_character_living_summary = build_living_character_context_block(campaign, actor_slot, max_chars=2200)
    party_living_summary = build_party_living_context_block(campaign, actor_slot, max_chars=1800)
    style_consistency_guard = build_style_consistency_guard_block(campaign, actor_slot)
    combined_text = "\n\n".join(
        [
            "=== WORLD AND CHARACTER CONSISTENCY CONTEXT ===",
            world_bible_summary,
            active_character_living_summary,
            party_living_summary,
            style_consistency_guard,
            "=== END CONSISTENCY CONTEXT ===",
        ]
    )
    combined_text = _truncate(combined_text, max_chars)
    return {
        "world_bible_summary": world_bible_summary,
        "active_character_living_summary": active_character_living_summary,
        "party_living_summary": party_living_summary,
        "style_consistency_guard": style_consistency_guard,
        "combined_text": combined_text,
    }


def _character_for_slot(campaign: dict, actor_slot: Optional[str]) -> Dict[str, Any]:
    if not actor_slot:
        return {}
    characters = ((campaign.get("state") or {}).get("characters") or {})
    character = characters.get(actor_slot)
    return character if isinstance(character, dict) else {}


def _party_characters(campaign: dict) -> Iterable[tuple[str, Dict[str, Any]]]:
    characters = ((campaign.get("state") or {}).get("characters") or {})
    active_party = ((campaign.get("state") or {}).get("party") or {}).get("active")
    ordered_slots = active_party if isinstance(active_party, list) and active_party else list(characters.keys())
    for slot_name in ordered_slots:
        character = characters.get(slot_name)
        if isinstance(character, dict):
            yield str(slot_name), character


def _character_name(character: Dict[str, Any], fallback_slot: Optional[str]) -> str:
    bio = character.get("bio") if isinstance(character, dict) else {}
    profile = character.get("living_profile") if isinstance(character, dict) else {}
    identity = profile.get("identity") if isinstance(profile, dict) else {}
    return str((identity or {}).get("name") or (bio or {}).get("name") or fallback_slot or "Unbekannter Charakter").strip()


def _pattern_preview(patterns: Any) -> str:
    if not isinstance(patterns, list):
        return ""
    parts = []
    for pattern in patterns[:2]:
        if not isinstance(pattern, dict):
            continue
        trigger = str(pattern.get("trigger") or "").strip()
        reaction = str(pattern.get("reaction") or "").strip()
        if trigger or reaction:
            parts.append(f"wenn {trigger}: {reaction}".strip())
    return " | ".join(parts)


def _join_nonempty(values: Iterable[Any], separator: str) -> str:
    return separator.join(str(value).strip() for value in values if str(value or "").strip())


def _truncate(text: str, max_chars: int) -> str:
    max_chars = max(120, int(max_chars or 120))
    text = str(text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 24].rstrip() + "\n[... gekuerzt]"
