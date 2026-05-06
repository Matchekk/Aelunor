import hashlib
import json
import random
from typing import Any, Callable, Dict, List, Tuple


def generated_element_too_similar(
    candidate: Dict[str, Any],
    existing: List[Dict[str, Any]],
    *,
    normalize_codex_alias_text: Callable[[Any], str],
    element_similarity_blacklist: Dict[str, List[str]],
) -> Tuple[bool, str]:
    name_norm = normalize_codex_alias_text(candidate.get("name", ""))
    theme_norm = normalize_codex_alias_text(candidate.get("theme", ""))
    if not name_norm:
        return True, "EMPTY_NAME"
    for core_norm, terms in element_similarity_blacklist.items():
        if name_norm == core_norm:
            return True, "TOO_SIMILAR_TO_CORE"
        if any(term in name_norm for term in terms):
            return True, "TOO_SIMILAR_TO_CORE"
        if theme_norm and any(term in theme_norm for term in terms):
            return True, "TOO_SIMILAR_TO_CORE"
    for entry in existing:
        existing_name_norm = normalize_codex_alias_text(entry.get("name", ""))
        existing_theme_norm = normalize_codex_alias_text(entry.get("theme", ""))
        if not existing_name_norm:
            continue
        if name_norm == existing_name_norm:
            return True, "DUPLICATE_NAME"
        if name_norm.startswith(existing_name_norm) or existing_name_norm.startswith(name_norm):
            return True, "DUPLICATE_THEME"
        if theme_norm and existing_theme_norm and (
            theme_norm == existing_theme_norm
            or theme_norm in existing_theme_norm
            or existing_theme_norm in theme_norm
        ):
            return True, "DUPLICATE_THEME"
    return False, ""


def theme_flavor_options(anchor: str) -> List[Tuple[str, str, List[str], List[str]]]:
    motifs = [
        ("Resonanz von Schwingungen und Klang", "resonanz", ["desorientierung", "echo"], ["ruhe", "stille"]),
        ("Nebel aus Erinnerung und Täuschung", "nebel", ["blindheit", "verwirrung"], ["wind", "fokus"]),
        ("Asche als Rest alter Opfer", "asche", ["brandspur", "erstickung"], ["wasser", "reinigung"]),
        ("Sternenstaub und kosmische Splitter", "sterne", ["strahl", "markierung"], ["schatten", "erde"]),
        ("Leere und entziehende Kälte", "leere", ["auszehrung", "druck"], ["licht", "bindung"]),
        ("Traum zwischen Hoffnung und Alb", "traum", ["schlaf", "furcht"], ["klarheit", "lärm"]),
        ("Blutpakt und Lebensrausch", "blut", ["blutung", "rausch"], ["reinheit", "frost"]),
        ("Dornenwuchs und uraltes Grün", "dornen", ["fessel", "gift"], ["feuer", "schneide"]),
        ("Donnerglas und geladene Splitter", "donnerglas", ["schock", "bruch"], ["erde", "isolierung"]),
        ("Eidstahl aus gebundenem Metall", "eidstahl", ["schnitt", "druck"], ["magnet", "säure"]),
    ]
    return [(label, f"{theme} ({anchor})", status_tags, weak_tags) for theme, label, status_tags, weak_tags in motifs]


def theme_flavor(seed: random.Random, anchor: str) -> Tuple[str, str, List[str], List[str]]:
    choice = seed.choice(theme_flavor_options(anchor))
    return choice


def candidate_from_fallback_element(
    raw_name: str,
    short: str,
    theme: str,
    status_tags: List[str],
    weak_tags: List[str],
    anchor: str,
) -> Dict[str, Any]:
    return {
        "name": raw_name,
        "rarity": "ungewöhnlich",
        "description": f"{raw_name} prägt Konflikte dieser Welt durch {theme.lower()}.",
        "theme": theme,
        "origin": "generated",
        "strengths_against": [],
        "weaknesses_against": weak_tags[:2],
        "synergies_with": [],
        "status_effect_tags": status_tags[:2],
        "class_affinities": [short],
        "skill_affinities": [short],
        "discoverable": True,
        "lore_notes": [f"{raw_name} wird in {anchor} mit alten Ritualen verknüpft."],
        "visual_motif": short,
        "temperament": "unruhig",
        "environment_bias": anchor,
        "aliases": [],
    }


def generate_world_elements_fallback(
    summary: Dict[str, Any],
    *,
    deep_copy: Callable[[Any], Any],
    element_generated_names_fallback: List[str],
    pick_world_theme_anchor: Callable[[Dict[str, Any]], str],
    generated_element_too_similar: Callable[[Dict[str, Any], List[Dict[str, Any]]], Tuple[bool, str]],
) -> List[Dict[str, Any]]:
    seed_text = json.dumps(
        {"theme": summary.get("theme", ""), "tone": summary.get("tone", ""), "premise": summary.get("premise", "")},
        ensure_ascii=False,
        sort_keys=True,
    )
    seed = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    anchor = pick_world_theme_anchor(summary)
    names = deep_copy(element_generated_names_fallback)
    seed.shuffle(names)
    flavor_options = theme_flavor_options(anchor)
    flavor_start = seed.randrange(len(flavor_options)) if flavor_options else 0
    picked: List[Dict[str, Any]] = []
    for name_index, raw_name in enumerate(names):
        for flavor_index in range(len(flavor_options)):
            short, theme, status_tags, weak_tags = flavor_options[
                (flavor_start + name_index + flavor_index) % len(flavor_options)
            ]
            candidate = candidate_from_fallback_element(raw_name, short, theme, status_tags, weak_tags, anchor)
            too_similar, _reason = generated_element_too_similar(candidate, picked)
            if too_similar:
                continue
            picked.append(candidate)
            break
        if len(picked) >= 6:
            break
    return picked[:6]
