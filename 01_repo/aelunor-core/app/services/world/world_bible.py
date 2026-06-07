from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List


WorldBible = Dict[str, Any]

GENERIC_FORBIDDEN_TERMS = [
    "Feuerball",
    "Heiltrank",
    "Magiergilde",
    "Goblinhoehle",
    "Schattenklinge",
    "Eisdrache",
    "Kriegerklasse",
    "Elfenreich",
    "Dunkler Wald",
]


def default_world_bible() -> WorldBible:
    return {
        "version": 1,
        "status": "generated",
        "created_from_setup": extract_world_bible_created_from_setup({}),
        "identity": {
            "world_name": "",
            "world_epithet": "",
            "core_pitch": "",
            "unique_hook": "",
            "genre_shape": "",
            "dominant_mood": "",
            "forbidden_generic_feel": [],
        },
        "linguistics": {
            "world_languages": {
                "primary_language": _default_language("common"),
                "ancient_language": _default_language("ancient"),
                "ritual_language": _default_language("ritual"),
            },
            "race_languages": {},
            "faction_dialects": {},
            "place_name_aliases": {},
            "translation_rules": {
                "partial_understanding_enabled": True,
                "levels": {
                    "none": "Nur fremde Laute oder Schrift erkennbar.",
                    "weak": "Einzelne Wortwurzeln erkennbar, aber keine sichere Bedeutung.",
                    "basic": "Grobe Bedeutung erkennbar, aber kultureller Kontext fehlt.",
                    "fluent": "Bedeutung und Kontext verstaendlich.",
                    "scholar": "Historische, religioese und doppelte Bedeutungen erkennbar.",
                },
                "misinterpretation_types": [
                    "place_vs_person",
                    "city_vs_sacred_site",
                    "monster_name_vs_warning",
                    "title_vs_name",
                    "ritual_term_vs_object",
                    "direction_vs_memory",
                ],
            },
            "comprehension_rules": [],
        },
        "naming_rules": {key: {"patterns": [], "examples": [], "avoid": []} for key in _naming_rule_keys()},
        "metaphysics": {
            "main_power_name": "",
            "main_power_description": "",
            "power_source": "",
            "power_cost": "",
            "power_limitations": [],
            "world_laws": [],
            "taboos": [],
            "death_rule": "",
            "healing_rule": "",
            "corruption_rule": "",
        },
        "elements": {
            "core_element_ids": [],
            "world_element_ids": [],
            "element_language_rules": [],
            "status_effect_vocabulary": [],
            "element_taboo_rules": [],
            "element_region_rules": [],
            "element_skill_rules": [],
        },
        "progression": {
            "rank_language": {rank: "" for rank in ("F", "E", "D", "C", "B", "A", "S")},
            "class_origin_rules": "",
            "class_naming_rules": [],
            "skill_manifestation_rules": [],
            "skill_cost_rules": [],
            "ascension_rules": "",
            "forbidden_progression_patterns": [],
        },
        "races_and_beasts": {
            "race_origin_rules": "",
            "race_naming_rules": [],
            "beast_origin_rules": "",
            "beast_naming_rules": [],
            "ecology_rules": [],
            "knowledge_discovery_rules": [],
        },
        "factions": {
            "faction_naming_rules": [],
            "power_structure_rules": [],
            "conflict_rules": [],
            "ideology_vocabulary": [],
            "forbidden_faction_patterns": [],
        },
        "regions": {
            "region_naming_rules": [],
            "biome_logic": [],
            "travel_rules": [],
            "danger_zone_rules": [],
            "settlement_rules": [],
        },
        "items": {
            "item_naming_rules": [],
            "rarity_language": {key: "" for key in ("common", "uncommon", "rare", "epic", "legendary")},
            "material_vocabulary": [],
            "curse_rules": [],
            "relic_rules": [],
            "earth_item_transformation_rules": [],
        },
        "tone_and_style": {
            "narration_rules": [],
            "forbidden_words": [],
            "preferred_motifs": [],
            "sensory_palette": {"sights": [], "sounds": [], "smells": [], "textures": []},
        },
        "ui_theme_hints": {
            "visual_motifs": [],
            "symbol_language": [],
            "dominant_colors_text": [],
            "background_style_hints": [],
            "region_style_variants": [],
        },
        "runtime_controls": {
            "generic_name_guard": True,
            "require_bible_derived_names": True,
            "allow_runtime_extensions": True,
            "runtime_extension_mode": "append_only",
            "secret_sections_hidden_from_players": True,
        },
        "revision": {"revision_id": 1, "created_turn": 0, "last_updated_turn": 0, "change_log": []},
    }


def normalize_world_bible(raw: Any, setup_answers: Any = None, world: Any = None) -> WorldBible:
    raw_dict = _dict(raw)
    if _should_generate_fallback(raw_dict, setup_answers):
        raw_dict = generate_world_bible_fallback(setup_answers, world=world)
    bible = _merge_defaults(default_world_bible(), raw_dict)
    bible["version"] = 1
    bible["status"] = _string(bible.get("status"), "generated") or "generated"
    bible["created_from_setup"] = _normalize_created_from_setup(bible.get("created_from_setup"))
    if setup_answers and not any(_string(v) or _list(v) for v in bible["created_from_setup"].values()):
        bible["created_from_setup"] = extract_world_bible_created_from_setup(setup_answers)
    _normalize_language_blocks(bible)
    _normalize_rule_blocks(bible)
    _normalize_world_element_ids(bible, world)
    return bible


def generate_world_bible_fallback(setup_answers: Any, world: Any = None) -> WorldBible:
    setup = extract_world_bible_created_from_setup(setup_answers)
    seed = _stable_seed(setup)
    roots = _roots_for_setup(setup, seed)
    world_name = _string(_value(setup_answers, "world_name")) or _generated_name(roots, seed)
    resource = setup["resource_name"] or "Aether"
    theme = setup["theme"] or "Unbekannte Welt"
    tone = setup["tone"] or "angespannt"
    conflict = setup["central_conflict"] or theme
    bible = default_world_bible()
    bible["created_from_setup"] = setup
    bible["identity"].update(
        {
            "world_name": world_name,
            "world_epithet": f"die Welt von {resource}",
            "core_pitch": conflict,
            "unique_hook": f"{resource} folgt sichtbaren Kosten, Tabus und kultureller Sprache.",
            "genre_shape": theme,
            "dominant_mood": tone,
            "forbidden_generic_feel": GENERIC_FORBIDDEN_TERMS,
        }
    )
    _apply_fallback_linguistics(bible, roots, world_name, resource)
    _apply_fallback_rules(bible, roots, resource, setup)
    _normalize_world_element_ids(bible, world)
    return normalize_world_bible(bible, world=world)


def build_world_bible_prompt_summary(bible: Any) -> str:
    normalized = normalize_world_bible(bible)
    identity = normalized["identity"]
    metaphysics = normalized["metaphysics"]
    linguistics = normalized["linguistics"]
    roots = _collect_roots(linguistics["world_languages"])
    forbidden = _unique_strings(
        normalized["identity"].get("forbidden_generic_feel", [])
        + normalized["tone_and_style"].get("forbidden_words", [])
    )
    skill_rules = normalized["naming_rules"]["skills"]["patterns"] or normalized["progression"]["skill_manifestation_rules"]
    item_rules = normalized["naming_rules"]["items"]["patterns"] or normalized["items"]["item_naming_rules"]
    return "\n".join(
        [
            "WORLD BIBLE SUMMARY:",
            f"World: {identity.get('world_name') or 'Unbenannte Welt'}, {identity.get('world_epithet') or identity.get('core_pitch')}.",
            f"Tone: {identity.get('dominant_mood') or ', '.join(normalized['tone_and_style'].get('narration_rules') or []) or 'weltgebunden'}.",
            f"Main Power: {metaphysics.get('main_power_name') or 'Unbenannte Kraft'} - {metaphysics.get('main_power_description') or 'Quelle, Kosten und Grenzen aus der Bible ableiten.'}",
            f"Naming: Nutze Roots wie {', '.join(roots[:8]) or 'weltinterne Roots'}. Vermeide generische Fantasy-Namen.",
            "Race Languages: Intelligente Races koennen eigene Endonyme, Ortsnamen und Fehluebersetzungen haben.",
            "Translation/Aliases: Mehrsprachige Ortsnamen koennen gleiche Orte bezeichnen und bei schwachem Verstaendnis falsche Kategorien erzeugen.",
            f"Skills: {'; '.join(skill_rules[:4]) or 'Skills aus Handlung, Kosten, Quelle und Weltmetaphysik ableiten.'}",
            f"Items: {'; '.join(item_rules[:4]) or 'Items brauchen Herkunft, Material, Nebenwirkung und weltsprachliche Namen.'}",
            f"Forbidden: {', '.join(forbidden[:12]) or 'Generische Begriffe ohne Weltlogik.'}",
        ]
    )


def extract_world_bible_created_from_setup(setup_answers: Any) -> Dict[str, Any]:
    return {
        "theme": _string(_value(setup_answers, "theme")),
        "tone": _string(_value(setup_answers, "tone")),
        "difficulty": _string(_value(setup_answers, "difficulty")),
        "resource_name": _string(_value(setup_answers, "resource_name")),
        "world_structure": _string(_value(setup_answers, "world_structure")),
        "world_laws": _list(_value(setup_answers, "world_laws")),
        "central_conflict": _string(_value(setup_answers, "central_conflict")),
        "factions_raw": _factions_text(_value(setup_answers, "factions_raw") or _value(setup_answers, "factions")),
        "taboos": _string(_value(setup_answers, "taboos")),
    }


def normalize_race_language(raw: Any, fallback_race_id: str = "") -> Dict[str, Any]:
    data = _dict(raw)
    race_id = _string(data.get("race_id"), fallback_race_id)
    roots = data.get("common_roots")
    if isinstance(roots, list):
        roots = {str(root): "" for root in roots if _string(root)}
    return {
        "race_id": race_id,
        "language_name": _string(data.get("language_name")),
        "self_name_for_race": _string(data.get("self_name_for_race")),
        "external_name_for_race": _string(data.get("external_name_for_race")),
        "sound": _string(data.get("sound")),
        "phonetic_rules": _list(data.get("phonetic_rules")),
        "common_roots": {str(k): _string(v) for k, v in _dict(roots).items() if _string(k)},
        "naming_patterns": {key: _list((_dict(data.get("naming_patterns"))).get(key)) for key in ("people", "settlements", "sacred_sites", "titles", "beasts", "skills")},
        "translation_behavior": {
            "literal_translation": _bool((_dict(data.get("translation_behavior"))).get("literal_translation"), True),
            "partial_understanding_creates_wrong_category": _bool((_dict(data.get("translation_behavior"))).get("partial_understanding_creates_wrong_category"), True),
            "concepts_without_common_equivalent": _list((_dict(data.get("translation_behavior"))).get("concepts_without_common_equivalent")),
        },
    }


def normalize_place_name_alias(raw: Any, fallback_location_id: str = "") -> Dict[str, Any]:
    data = _dict(raw)
    aliases = []
    for alias in _list_dicts(data.get("aliases")):
        aliases.append(
            {
                "language": _string(alias.get("language")),
                "name": _string(alias.get("name")),
                "literal_meaning": _string(alias.get("literal_meaning")),
                "cultural_meaning": _string(alias.get("cultural_meaning")),
                "used_by": _list(alias.get("used_by")),
                "misleading_for": _list(alias.get("misleading_for")),
                "likely_wrong_interpretation": _string(alias.get("likely_wrong_interpretation")),
            }
        )
    return {
        "canonical_id": _string(data.get("canonical_id"), fallback_location_id),
        "common_name": _string(data.get("common_name")),
        "aliases": aliases,
    }


def _default_language(role: str) -> Dict[str, Any]:
    return {"name": "", "role": role, "sound": "", "phonetic_rules": [], "common_roots": [], "example_words": {}}


def _naming_rule_keys() -> Iterable[str]:
    return ("people", "settlements", "regions", "ruins", "factions", "skills", "items", "beasts", "titles")


def _normalize_created_from_setup(raw: Any) -> Dict[str, Any]:
    normalized = extract_world_bible_created_from_setup(raw)
    normalized["world_laws"] = _list((_dict(raw)).get("world_laws"))
    return normalized


def _normalize_language_blocks(bible: WorldBible) -> None:
    linguistics = bible.setdefault("linguistics", {})
    world_languages = _dict(linguistics.get("world_languages"))
    for key, role in (("primary_language", "common"), ("ancient_language", "ancient"), ("ritual_language", "ritual")):
        language = _merge_defaults(_default_language(role), _dict(world_languages.get(key)))
        language["role"] = _string(language.get("role"), role) or role
        language["phonetic_rules"] = _list(language.get("phonetic_rules"))
        language["common_roots"] = _list(language.get("common_roots"))
        language["example_words"] = _dict(language.get("example_words"))
        world_languages[key] = language
    linguistics["world_languages"] = world_languages
    linguistics["race_languages"] = {str(k): normalize_race_language(v, str(k)) for k, v in _dict(linguistics.get("race_languages")).items()}
    linguistics["place_name_aliases"] = {str(k): normalize_place_name_alias(v, str(k)) for k, v in _dict(linguistics.get("place_name_aliases")).items()}


def _normalize_rule_blocks(bible: WorldBible) -> None:
    for group in _naming_rule_keys():
        block = bible["naming_rules"].setdefault(group, {})
        block["patterns"] = _list(block.get("patterns"))
        block["examples"] = _list(block.get("examples"))
        block["avoid"] = _list(block.get("avoid"))
    for key in ("power_limitations", "world_laws", "taboos"):
        bible["metaphysics"][key] = _list(bible["metaphysics"].get(key))
    for key in ("class_naming_rules", "skill_manifestation_rules", "skill_cost_rules", "forbidden_progression_patterns"):
        bible["progression"][key] = _list(bible["progression"].get(key))
    for section, keys in {
        "races_and_beasts": ("race_naming_rules", "beast_naming_rules", "ecology_rules", "knowledge_discovery_rules"),
        "factions": ("faction_naming_rules", "power_structure_rules", "conflict_rules", "ideology_vocabulary", "forbidden_faction_patterns"),
        "regions": ("region_naming_rules", "biome_logic", "travel_rules", "danger_zone_rules", "settlement_rules"),
        "items": ("item_naming_rules", "material_vocabulary", "curse_rules", "relic_rules", "earth_item_transformation_rules"),
        "tone_and_style": ("narration_rules", "forbidden_words", "preferred_motifs"),
    }.items():
        for key in keys:
            bible[section][key] = _list(bible[section].get(key))


def _apply_fallback_linguistics(bible: WorldBible, roots: List[str], world_name: str, resource: str) -> None:
    bible["linguistics"]["world_languages"]["primary_language"].update(
        {"name": f"{world_name}-Gemeinsprache", "sound": "hart, erinnernd, mit kurzen Roots", "phonetic_rules": ["Konsonantencluster tragen Herkunft.", "Bindestriche markieren kulturelle Doppeldeutung."], "common_roots": roots[:6], "example_words": {roots[0]: "Quelle", roots[1]: "Ort", roots[2]: "Eid"}}
    )
    bible["linguistics"]["world_languages"]["ancient_language"].update({"name": f"Alt-{world_name}", "sound": "sakral und bruechig", "common_roots": roots[2:8]})
    bible["linguistics"]["world_languages"]["ritual_language"].update({"name": f"{resource}-Litanei", "sound": "formelhaft, kostengebunden", "common_roots": roots[1:7]})
    bible["linguistics"]["comprehension_rules"] = ["Schwaches Verstaendnis erkennt Roots, aber nicht Kategorie oder kulturellen Kontext.", "Alias-Aufloesung ist Codex-Wissen, keine automatische Spielerwahrheit."]


def _apply_fallback_rules(bible: WorldBible, roots: List[str], resource: str, setup: Dict[str, Any]) -> None:
    bible["metaphysics"].update({"main_power_name": resource, "main_power_description": f"{resource} entsteht aus Handlung, Erinnerung und Preis.", "power_source": setup["world_structure"] or "Weltgesetz", "power_cost": "Jede Wirkung braucht Quelle, Risiko oder Nachhall.", "world_laws": setup["world_laws"], "taboos": _list(setup["taboos"]), "death_rule": "Tod ist eine kanonische Konsequenz, wenn das Setup ihn erlaubt.", "healing_rule": "Heilung benoetigt Material, Zeit, Schuld oder Ressourcen.", "corruption_rule": "Macht ohne bezahlten Preis hinterlaesst Spuren."})
    for key in _naming_rule_keys():
        bible["naming_rules"][key]["avoid"] = GENERIC_FORBIDDEN_TERMS
    bible["naming_rules"]["skills"]["patterns"] = [f"{roots[0].title()}-{roots[2].title()} + Handlung", f"{resource} + Kosten + sichtbare Spur"]
    bible["naming_rules"]["items"]["patterns"] = [f"Materialroot {roots[3]} + Herkunft + Nebenwirkung", "Keine generischen Verbrauchsitems ohne Kultur."]
    bible["progression"].update({"class_origin_rules": "Klassen entstehen aus Biografie, Handlung und Weltresonanz.", "class_naming_rules": ["Klassen tragen Weltroots, Eid, Ort oder Preis."], "skill_manifestation_rules": ["Skills manifestieren aus Handlung, Trauma, Elementresonanz und Kosten."], "skill_cost_rules": [f"{resource} ist begrenzt und nie kostenlos."], "ascension_rules": "Aufstieg braucht Milestone, Risiko und kanonische Begruendung.", "forbidden_progression_patterns": ["kostenlose Heilung", "beliebige Klassen ohne Ursprung"]})
    bible["races_and_beasts"].update({"race_origin_rules": "Intelligente Races haben Endonyme, Exonyme und eigene Naming-Logik.", "race_naming_rules": ["Race-Namen aus Sprache, Selbstbild und Fremdzuschreibung ableiten."], "beast_origin_rules": "Beasts folgen Oekologie, Spur und Entdeckung.", "beast_naming_rules": ["Beast-Namen aus Verhalten, Habitat oder Warnroots ableiten."], "ecology_rules": ["Kein Monster ohne Habitat, Spur oder Nahrungskette."], "knowledge_discovery_rules": ["Codex-Wissen wird durch Kontakt, Lore oder Kampf freigelegt."]})
    bible["items"].update({"material_vocabulary": [roots[3], roots[4], resource, f"{resource}-Rest"], "item_naming_rules": bible["naming_rules"]["items"]["patterns"], "earth_item_transformation_rules": ["Erdgegenstaende werden durch Material, Herkunft und Weltkosten umgedeutet."]})
    bible["tone_and_style"].update({"narration_rules": [setup["tone"] or "konkret, koerperlich, weltgebunden"], "forbidden_words": GENERIC_FORBIDDEN_TERMS, "preferred_motifs": [setup["theme"], setup["central_conflict"], resource]})


def _normalize_world_element_ids(bible: WorldBible, world: Any) -> None:
    world_dict = _dict(world)
    elements = _dict(world_dict.get("elements"))
    element_ids = sorted(str(key) for key in elements.keys() if _string(key))
    if element_ids and not bible["elements"].get("world_element_ids"):
        bible["elements"]["world_element_ids"] = element_ids
    bible["elements"]["core_element_ids"] = _list(bible["elements"].get("core_element_ids"))
    bible["elements"]["world_element_ids"] = _list(bible["elements"].get("world_element_ids"))


def _should_generate_fallback(raw: Dict[str, Any], setup_answers: Any) -> bool:
    if not setup_answers or not any(extract_world_bible_created_from_setup(setup_answers).values()):
        return False
    identity = _dict(raw.get("identity"))
    created = _dict(raw.get("created_from_setup"))
    return not raw or (not _string(identity.get("world_name")) and not any(extract_world_bible_created_from_setup(created).values()))


def _roots_for_setup(setup: Dict[str, Any], seed: str) -> List[str]:
    source = " ".join(str(setup.get(key) or "") for key in ("theme", "tone", "resource_name", "world_structure", "central_conflict"))
    tokens = [re.sub(r"[^A-Za-z0-9]+", "", part).lower()[:5] for part in source.split()]
    roots = [token for token in tokens if len(token) >= 3]
    fallback = ["veyr", "keth", "orn", "thar", "nok", "ael", "kar", "ssar", "morn", "hal"]
    offset = int(seed[:2], 16) % len(fallback)
    return _unique_strings(roots + fallback[offset:] + fallback[:offset])[:10]


def _generated_name(roots: List[str], seed: str) -> str:
    left = roots[int(seed[2:4], 16) % len(roots)]
    right = roots[int(seed[4:6], 16) % len(roots)]
    return f"{left.title()}{right.title()[:4]}"


def _stable_seed(value: Any) -> str:
    return hashlib.sha1(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


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
    return _string(raw, default) if isinstance(default, str) else copy.deepcopy(raw if raw is not None else default)


def _collect_roots(world_languages: Dict[str, Any]) -> List[str]:
    roots: List[str] = []
    for language in _dict(world_languages).values():
        roots.extend(_list(_dict(language).get("common_roots")))
    return _unique_strings(roots)


def _value(source: Any, key: str) -> Any:
    if not isinstance(source, dict):
        return ""
    value = source.get(key)
    if isinstance(value, dict):
        if "value" in value:
            return value.get("value")
        selected = value.get("selected")
        selected_values = selected if isinstance(selected, list) else ([selected] if selected else [])
        other_values = value.get("other_values") if isinstance(value.get("other_values"), list) else []
        values = selected_values + other_values
        return values or value.get("other_text") or value.get("selected") or ""
    return value


def _factions_text(value: Any) -> str:
    if isinstance(value, list):
        rows = []
        for entry in value:
            if isinstance(entry, dict):
                rows.append(": ".join(part for part in (_string(entry.get("name")), _string(entry.get("goal")), _string(entry.get("methods"))) if part))
            elif _string(entry):
                rows.append(_string(entry))
        return "\n".join(rows)
    return _string(value)


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


def _list_dicts(value: Any) -> List[Dict[str, Any]]:
    return [entry for entry in _list(value) if isinstance(entry, dict)]


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
