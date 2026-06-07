from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.config.combat import COMBAT_NARRATIVE_HINTS
from app.config.progression import DEFAULT_DYNAMIC_SKILL_LEVEL_MAX, FIRST_SKILL_FORCE_PROBABILITY
from app.core.ids import deep_copy, make_id
from app.prompts.system_prompts import MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT
from app.schemas.llm import MANIFESTATION_SKILL_NAME_SCHEMA
from app.services.canon.progression_gate import (
    is_skill_manifestation_name_plausible,
    normalize_progression_event_list,
    patch_has_explicit_skill_progression_for_actor,
)
from app.services.characters.resources import resource_name_for_character
from app.services.extraction.items import sentence_mentions_actor_name
from app.services.progression import skills
from app.services.world.codex import normalize_codex_alias_text, stable_sorted_unique_strings
from app.services.world.element_class_paths import resolve_class_element_id as _resolve_class_element_id
from app.services.world.element_ids import normalize_element_id_list as _normalize_element_id_list
from app.services.world.element_profiles import element_id_from_name as _element_id_from_name
from app.services.world.math_utils import clamp
from app.services.world.progression import normalize_class_current
from app.services.world.text_normalization import first_sentences, normalized_eval_text
from app.text.patterns import (
    MANIFESTATION_COST_CUES,
    MANIFESTATION_EFFECT_CUES,
    MANIFESTATION_MOTIF_GROUPS,
    MANIFESTATION_STRONG_CUES,
    MANIFESTATION_TACTICAL_CUES,
    MANIFESTATION_WORLD_REACTION_CUES,
)


def _missing_dependency(name: str) -> Callable[..., Any]:
    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"Progression manifestation dependency is not configured: {name}")
    return _missing


@dataclass(frozen=True)
class ManifestationDependencies:
    call_ollama_schema: Callable[..., Dict[str, Any]] = _missing_dependency("call_ollama_schema")
    ollama_temperature: float = 0.6


_DEPS = ManifestationDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def call_ollama_schema(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _DEPS.call_ollama_schema(*args, **kwargs)


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def _hash_unit_interval(seed_text: str) -> float:
    digest = hashlib.sha256(str(seed_text or "").encode("utf-8")).hexdigest()[:12]
    return int(digest, 16) / float(0xFFFFFFFFFFFF)


def normalize_element_id_list(values: Any, world: Optional[Dict[str, Any]] = None) -> List[str]:
    return _normalize_element_id_list(
        values,
        world,
        normalize_codex_alias_text=normalize_codex_alias_text,
        element_id_from_name=element_id_from_name,
    )


def element_id_from_name(name: str) -> str:
    return _element_id_from_name(
        name,
        normalize_codex_alias_text=normalize_codex_alias_text,
        make_id=make_id,
    )


def resolve_class_element_id(current_class: Optional[Dict[str, Any]], world: Dict[str, Any]) -> Optional[str]:
    return _resolve_class_element_id(
        current_class,
        world,
        normalize_class_current=normalize_class_current,
        normalize_element_id_list=normalize_element_id_list,
    )


def canonicalize_manifested_skill_payload(
    *,
    raw_skill: Dict[str, Any],
    character: Dict[str, Any],
    world: Optional[Dict[str, Any]] = None,
    world_settings: Optional[Dict[str, Any]] = None,
    default_source: str = "Manifestation",
) -> Optional[Dict[str, Any]]:
    resource_name = resource_name_for_character(character, world_settings)
    proposed_name = str(raw_skill.get("name") or raw_skill.get("id") or "").strip()
    raw_power_rating = int(raw_skill.get("power_rating", 0) or 0)
    actor_name = str(((character.get("bio") or {}).get("name") or character.get("slot_id") or "").strip())
    if not is_skill_manifestation_name_plausible(proposed_name, actor_name):
        return None
    skill = skills.normalize_dynamic_skill_state(
        {
            "id": raw_skill.get("id") or skills.skill_id_from_name(proposed_name),
            "name": proposed_name,
            "rank": skills.normalize_skill_rank(raw_skill.get("rank")),
            "level": max(1, int(raw_skill.get("level", 1) or 1)),
            "level_max": max(1, int(raw_skill.get("level_max", DEFAULT_DYNAMIC_SKILL_LEVEL_MAX) or DEFAULT_DYNAMIC_SKILL_LEVEL_MAX)),
            "xp": max(0, int(raw_skill.get("xp", 0) or 0)),
            "next_xp": max(1, int(raw_skill.get("next_xp", skills.next_skill_xp_for_level(1)) or skills.next_skill_xp_for_level(1))),
            "mastery": clamp(int(raw_skill.get("mastery", 0) or 0), 0, 100),
            "tags": [str(tag).strip() for tag in (raw_skill.get("tags") or []) if str(tag).strip()],
            "description": str(raw_skill.get("description") or "").strip(),
            "effect_summary": str(raw_skill.get("effect_summary") or "").strip(),
            "power_rating": int(raw_skill.get("power_rating", 0) or 0),
            "growth_potential": str(raw_skill.get("growth_potential") or "").strip(),
            "cost": raw_skill.get("cost"),
            "price": raw_skill.get("price"),
            "cooldown_turns": raw_skill.get("cooldown_turns"),
            "unlocked_from": str(raw_skill.get("unlocked_from") or default_source),
            "manifestation_source": str(raw_skill.get("manifestation_source") or default_source),
            "category": raw_skill.get("category"),
            "class_affinity": raw_skill.get("class_affinity"),
            "elements": raw_skill.get("elements"),
            "element_primary": raw_skill.get("element_primary"),
            "element_synergies": raw_skill.get("element_synergies"),
        },
        resource_name=resource_name,
        unlocked_from=default_source,
    )
    if not skill.get("description"):
        skill["description"] = f"{skill['name']} wurde unter Druck manifestiert."
    if not skill.get("effect_summary"):
        skill["effect_summary"] = skill["description"][:180]
    if raw_power_rating <= 0:
        skill["power_rating"] = max(1, (skills.skill_rank_sort_value(skill.get("rank")) + 1) * 6 + int(skill.get("level", 1) or 1))
    else:
        skill["power_rating"] = max(1, raw_power_rating)
    if not skill.get("growth_potential"):
        skill["growth_potential"] = "mittel"
    resolved_elements = normalize_element_id_list(skill.get("elements") or [], world or {})
    if not resolved_elements:
        class_element = resolve_class_element_id(character.get("class_current"), world or {})
        if class_element:
            resolved_elements = [class_element]
    skill["elements"] = resolved_elements
    primary_candidates = normalize_element_id_list([skill.get("element_primary")], world or {})
    skill["element_primary"] = primary_candidates[0] if primary_candidates else (resolved_elements[0] if resolved_elements else None)
    if skill.get("element_primary") and skill["element_primary"] not in skill["elements"]:
        skill["elements"].insert(0, skill["element_primary"])
    return skill

def manifestation_seed_from_skill(skill_payload: Dict[str, Any], *, source_turn: int, confidence: float) -> Optional[Dict[str, Any]]:
    if not isinstance(skill_payload, dict):
        return None
    skill_name = str(skill_payload.get("name") or "").strip()
    if not skill_name:
        return None
    normalized = normalized_eval_text(skill_name)
    if not normalized:
        return None
    if any(tag in normalized for tag in ("pilz", "spore", "myzel", "wurzel", "ranke", "garten")):
        seed_name = "Myzelpfad"
        seed_tags = ["spore", "nature", "myzel"]
    elif any(tag in normalized for tag in ("licht", "sonne", "glanz")):
        seed_name = "Lichtpfad"
        seed_tags = ["light"]
    elif any(tag in normalized for tag in ("schatten", "nacht", "finster")):
        seed_name = "Schattenpfad"
        seed_tags = ["shadow"]
    else:
        seed_name = f"{skill_name} Pfad"
        seed_tags = [token for token in normalized.split(" ") if token][:2]
    seed_id = f"seed_{re.sub(r'[^a-z0-9]+', '_', normalized_eval_text(seed_name)).strip('_') or 'latent'}"
    return {
        "id": seed_id,
        "name": seed_name,
        "theme_tags": seed_tags[:4],
        "source_turn": max(0, int(source_turn or 0)),
        "confidence": clamp_float(float(confidence or 0.0), 0.0, 1.0),
        "status": "latent",
        "related_skill_ids": [skills.skill_id_from_name(skill_name)],
    }

def upsert_class_path_seed(character: Dict[str, Any], seed: Dict[str, Any]) -> Optional[str]:
    if not isinstance(seed, dict):
        return None
    skills.ensure_character_progression_core(character)
    seed_id = str(seed.get("id") or "").strip()
    if not seed_id:
        return None
    seeds = character.setdefault("class_path_seeds", [])
    existing = next((entry for entry in seeds if isinstance(entry, dict) and str(entry.get("id") or "").strip() == seed_id), None)
    if existing:
        existing["confidence"] = max(
            clamp_float(float(existing.get("confidence", 0.0) or 0.0), 0.0, 1.0),
            clamp_float(float(seed.get("confidence", 0.0) or 0.0), 0.0, 1.0),
        )
        existing["source_turn"] = max(int(existing.get("source_turn", 0) or 0), int(seed.get("source_turn", 0) or 0))
        existing["theme_tags"] = stable_sorted_unique_strings(list(existing.get("theme_tags") or []) + list(seed.get("theme_tags") or []), limit=8)
        existing["related_skill_ids"] = stable_sorted_unique_strings(list(existing.get("related_skill_ids") or []) + list(seed.get("related_skill_ids") or []), limit=8)
        return None
    seeds.append(deep_copy(seed))
    skills.ensure_character_progression_core(character)
    return f"Pfad-Saat entdeckt: {seed.get('name', seed_id)}."

def infer_manifested_skill_name_with_llm(
    *,
    motif: str,
    actor_name: str,
    player_text: str,
    story_text: str,
    existing_names: Set[str],
) -> str:
    motif_key = str(motif or "").strip().lower()
    motif_token_gate: Dict[str, Tuple[str, ...]] = {
        "spore": ("myzel", "spore", "wurzel", "ranke", "pilz", "garten", "moos"),
        "light": ("licht", "strahl", "glanz", "sonnen", "heilig"),
        "shadow": ("schatten", "nacht", "finster", "dunkel"),
        "flame": ("feuer", "flamme", "glut", "asche", "brand"),
        "frost": ("frost", "eis", "reif", "kälte"),
        "storm": ("sturm", "wind", "donner", "blitz"),
        "martial": ("klinge", "stoß", "hieb", "parade", "kampf"),
    }
    required_tokens = motif_token_gate.get(motif_key, ())

    def motif_token_match(name: str) -> bool:
        if not required_tokens:
            return True
        normalized_name = normalized_eval_text(name)
        return any(token in normalized_name for token in required_tokens)

    motif_seed_names: Dict[str, List[str]] = {
        "spore": ["Myzelgriff", "Sporenfessel", "Wurzelstoß", "Gartenklaue"],
        "light": ["Lichtlanze", "Strahlenschnitt", "Sonnenimpuls", "Heiligglanz"],
        "shadow": ["Schattenriss", "Nachtfessel", "Finsterhieb", "Dunkelgriff"],
        "flame": ["Glutstoß", "Flammenriss", "Aschenklinge", "Feuerschwinge"],
        "frost": ["Frostriss", "Eisfessel", "Reifstoß", "Kältehieb"],
        "storm": ["Donnerschnitt", "Sturmimpuls", "Windriss", "Blitzgriff"],
        "martial": ["Klingenfokus", "Stoßtechnik", "Parierhieb", "Kampftakt"],
    }
    motif_label = {
        "spore": "Sporen/Natur",
        "light": "Licht",
        "shadow": "Schatten",
        "flame": "Feuer/Glut",
        "frost": "Frost/Eis",
        "storm": "Sturm/Wind/Donner",
        "martial": "Klingenkampf/Körpertechnik",
    }.get(motif_key, "Mystik")
    user_prompt = (
        f"Akteur: {actor_name}\n"
        f"Motiv: {motif_label}\n"
        f"Spieleraktion: {player_text[:360]}\n"
        f"Story-Kontext: {story_text[:520]}\n"
        f"Vergebene Skillnamen (verboten): {', '.join(sorted([name for name in existing_names if name])) or '-'}\n"
        "Gib einen neuartigen, glaubwürdigen Skillnamen zurück."
    )
    for _ in range(2):
        candidate = ""
        try:
            payload = call_ollama_schema(
                MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT,
                user_prompt,
                MANIFESTATION_SKILL_NAME_SCHEMA,
                timeout=60,
                temperature=max(0.55, float(_DEPS.ollama_temperature)),
            )
            candidate = str((payload or {}).get("name") or "").strip()
        except Exception:
            candidate = ""
        candidate = re.sub(r"\s+", " ", candidate).strip(" .,:;!?\"'`")
        normalized_candidate = normalized_eval_text(candidate)
        if (
            candidate
            and normalized_candidate
            and normalized_candidate not in existing_names
            and is_skill_manifestation_name_plausible(candidate, actor_name)
            and motif_token_match(candidate)
        ):
            return candidate
    for fallback_candidate in motif_seed_names.get(motif_key, []):
        normalized_fallback = normalized_eval_text(fallback_candidate)
        if normalized_fallback and normalized_fallback not in existing_names and is_skill_manifestation_name_plausible(fallback_candidate, actor_name):
            return fallback_candidate
    fallback = f"{motif_label} Manifestation".replace("/", " ")
    fallback = re.sub(r"\s+", " ", fallback).strip()
    if normalized_eval_text(fallback) in existing_names or not is_skill_manifestation_name_plausible(fallback, actor_name):
        fallback = f"{motif_label} Impuls".replace("/", " ")
    fallback = re.sub(r"\s+", " ", fallback).strip()
    if not is_skill_manifestation_name_plausible(fallback, actor_name) or normalized_eval_text(fallback) in existing_names:
        return ""
    return fallback

def infer_manifestation_progression_events_from_story(
    *,
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    story_text: str,
) -> List[Dict[str, Any]]:
    if action_type == "canon" or actor not in (state_after.get("characters") or {}):
        return []
    if patch_has_explicit_skill_progression_for_actor(patch, actor):
        return []
    character_before = ((state_before.get("characters") or {}).get(actor) or {})
    character_after = ((state_after.get("characters") or {}).get(actor) or {})

    actor_name = str(((character_after.get("bio") or {}).get("name") or actor).strip() or actor)
    story_norm = normalized_eval_text(story_text)
    player_norm = normalized_eval_text(player_text)
    combined_norm = f"{story_norm} {player_norm}".strip()
    if not combined_norm:
        return []
    first_skill_missing = not bool(character_after.get("skills") or {})
    actor_bound = sentence_mentions_actor_name(story_text, actor_name) or any(player_norm.startswith(prefix) for prefix in ("ich ", "ich,", "ich."))
    first_manifest = any(cue in combined_norm for cue in MANIFESTATION_STRONG_CUES)
    concrete_effect_story = any(cue in story_norm for cue in MANIFESTATION_EFFECT_CUES)
    concrete_effect_player = any(cue in player_norm for cue in MANIFESTATION_EFFECT_CUES)
    concrete_effect = concrete_effect_story or concrete_effect_player
    combat_present = any(cue in combined_norm for cue in COMBAT_NARRATIVE_HINTS)
    force_roll = _hash_unit_interval(
        f"first_skill_force|{int((state_after.get('meta') or {}).get('turn', 0) or 0)}|{actor}|{combined_norm[:160]}"
    )
    force_first_skill = bool(
        first_skill_missing
        and action_type in {"do", "say", "story"}
        and combat_present
        and force_roll <= FIRST_SKILL_FORCE_PROBABILITY
    )
    tactical = any(cue in combined_norm for cue in MANIFESTATION_TACTICAL_CUES)
    world_reaction = any(cue in combined_norm for cue in MANIFESTATION_WORLD_REACTION_CUES)
    cost_signal = any(cue in combined_norm for cue in MANIFESTATION_COST_CUES)
    motif_matches = []
    for motif, tokens in MANIFESTATION_MOTIF_GROUPS.items():
        if any(token in combined_norm for token in tokens):
            motif_matches.append(motif)
    identity = bool(motif_matches)
    story_support = (
        concrete_effect_story
        or any(token in story_norm for token in MANIFESTATION_TACTICAL_CUES)
        or any(token in story_norm for token in MANIFESTATION_WORLD_REACTION_CUES)
        or any(token in story_norm for token in MANIFESTATION_COST_CUES)
        or any(any(token in story_norm for token in tokens) for tokens in MANIFESTATION_MOTIF_GROUPS.values())
    )
    score = sum([1 if actor_bound else 0, 1 if first_manifest else 0, 1 if concrete_effect else 0, 1 if identity else 0, 1 if tactical else 0, 1 if world_reaction else 0, 1 if cost_signal else 0])
    if force_first_skill:
        if not actor_bound or not (concrete_effect or combat_present):
            return []
        if not motif_matches:
            motif_matches = ["martial"]
            identity = True
    else:
        if not (actor_bound and first_manifest and concrete_effect and identity):
            return []
        if not story_support:
            return []
        if score < 5:
            return []

    existing_names = {
        normalized_eval_text((entry or {}).get("name", ""))
        for entry in ((character_after.get("skills") or {}).values())
        if isinstance(entry, dict)
    }
    motif_tags = {
        "spore": ["manifestation", "nature", "spore", "control"],
        "light": ["manifestation", "light", "offense"],
        "shadow": ["manifestation", "shadow", "control"],
        "flame": ["manifestation", "flame", "offense"],
        "frost": ["manifestation", "frost", "control"],
        "storm": ["manifestation", "storm", "offense"],
        "martial": ["manifestation", "martial", "offense"],
    }
    selected_motif = motif_matches[0]
    base_name = infer_manifested_skill_name_with_llm(
        motif=selected_motif,
        actor_name=actor_name,
        player_text=player_text,
        story_text=story_text,
        existing_names=existing_names,
    )
    if not base_name:
        return []
    motif = selected_motif
    tags = motif_tags.get(motif, ["manifestation", "storm", "offense"])
    candidate_skill_id = skills.skill_id_from_name(base_name)
    existing_event_skill_ids = set()
    actor_patch = ((patch.get("characters") or {}).get(actor) or {}) if isinstance((patch.get("characters") or {}), dict) else {}
    for event in normalize_progression_event_list(actor_patch.get("progression_events"), actor=actor, source_turn=0):
        target_skill_id = str(event.get("target_skill_id") or "").strip()
        if target_skill_id:
            existing_event_skill_ids.add(target_skill_id)
    if candidate_skill_id in existing_event_skill_ids:
        return []

    confidence = clamp_float(0.45 + (score * 0.08), 0.0, 0.98)
    return [
        {
            "type": "skill_manifestation",
            "actor": actor,
            "target_skill_id": candidate_skill_id,
            "target_class_id": None,
            "target_element_id": None,
            "severity": "high" if score >= 6 else "medium",
            "tags": tags,
            "source_turn": int((state_after.get("meta") or {}).get("turn", 0) or 0),
            "reason": "Starke narrative Erstmanifestation",
            "metadata": {
                "origin": "inferred_story_manifestation_force" if force_first_skill else "inferred_story_manifestation",
                "manifestation_score": score,
                "manifestation_confidence": confidence,
                "motif": motif,
                "seed_eligible": bool(score >= 6),
                "first_skill_force": bool(force_first_skill),
            },
            "skill": {
                "id": candidate_skill_id,
                "name": base_name,
                "rank": "F",
                "level": 1,
                "xp": 0,
                "next_xp": skills.next_skill_xp_for_level(1),
                "tags": tags,
                "description": first_sentences(story_text or player_text, 2)[:220] or f"{base_name} manifestiert sich erstmals unter starkem Druck.",
                "effect_summary": "Eine neue Kraftmanifestation mit klarer taktischer Wirkung.",
                "power_rating": 10,
                "growth_potential": "hoch" if score >= 6 else "mittel",
                "cost": {"resource": resource_name_for_character(character_after, ((state_after.get("world") or {}).get("settings") or {})), "amount": 2},
                "manifestation_source": "NarrativeInfer",
            },
        }
    ]

def manifest_skill_from_progression_event(
    *,
    character: Dict[str, Any],
    actor_slot: str,
    event: Dict[str, Any],
    world: Optional[Dict[str, Any]],
    world_settings: Optional[Dict[str, Any]],
) -> Optional[str]:
    if str(event.get("type") or "").strip().lower() != "skill_manifestation":
        return None
    skill_store = character.setdefault("skills", {})
    target_skill_id = str(event.get("target_skill_id") or "").strip()
    if target_skill_id and target_skill_id in skill_store:
        return None
    payload = deep_copy(event.get("skill") or {})
    if not isinstance(payload, dict) or not payload.get("name"):
        return None
    skill = canonicalize_manifested_skill_payload(
        raw_skill=payload,
        character=character,
        world=world,
        world_settings=world_settings,
        default_source=f"Progression:{event.get('type', 'skill_manifestation')}",
    )
    if not skill:
        return None
    existing = skill_store.get(skill["id"])
    skill_store[skill["id"]] = (
        skills.merge_dynamic_skill(existing, skill, resource_name=resource_name_for_character(character, world_settings))
        if existing
        else skill
    )
    event["target_skill_id"] = skill["id"]
    char_name = str(((character.get("bio") or {}).get("name") or actor_slot).strip())
    return f"{char_name} manifestiert den neuen Skill {skill['name']} ({skill['rank']})."
