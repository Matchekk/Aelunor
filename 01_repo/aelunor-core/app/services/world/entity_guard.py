from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List


KNOWN_ENTITY_TYPES = {"person", "skill", "item", "location", "faction", "beast", "race", "title", "class", "plotpoint"}
GENERIC_TERMS = {
    "feuerball", "heiltrank", "magiergilde", "goblinhoehle", "goblinhöhle", "dunkler wald",
    "schattenklinge", "eisdrache", "kriegerklasse", "magieschild", "feuerklinge", "eispfeil",
    "orklager", "elfenreich", "drachenhoehle", "drachenhöhle", "fireball", "healing potion",
    "mage guild", "goblin cave", "dark forest", "shadow blade", "ice dragon", "warrior class",
    "magic shield", "fire slash", "ice arrow", "orc camp", "elven kingdom", "dragon cave",
}


def default_entity_guard_report(entity_type: str, name: str) -> dict:
    return {
        "entity_type": _entity_type(entity_type),
        "name": _text(name),
        "status": "unknown",
        "score": 50,
        "reasons": [],
        "matched_roots": [],
        "matched_examples": [],
        "forbidden_terms_found": [],
        "avoid_terms_found": [],
        "suggested_direction": "Use world-specific roots, power source terms, element vocabulary, race/faction language or naming patterns from the World Bible.",
        "requires_review": False,
    }


def assess_entity_name_against_world_bible(
    name: str,
    entity_type: str,
    world_bible: dict | None = None,
    *,
    context: dict | None = None,
) -> dict:
    report = default_entity_guard_report(entity_type, name)
    if not isinstance(world_bible, dict) or not world_bible:
        report["reasons"].append("World Bible missing; guard could not assess world specificity.")
        report["requires_review"] = True
        return report

    entity_type = report["entity_type"]
    name_norm = _norm(name)
    signals = collect_world_bible_name_signals(world_bible)
    naming_mode = infer_world_naming_mode(world_bible)
    score = 50

    forbidden = _matches_any(name_norm, signals["forbidden_terms"])
    avoid = _matches_any(name_norm, signals["avoid_terms"].get(entity_type, []) + signals["avoid_terms"].get("all", []))
    allowed = _matches_any(name_norm, signals["examples"].get(entity_type, []) + signals["allowed_terms"])
    generic = looks_like_generic_fantasy_name(name, entity_type)
    mode_match = name_matches_world_naming_mode(name, entity_type, naming_mode, world_bible)
    mode_conflict = _name_conflicts_with_mode(name, entity_type, naming_mode, world_bible)
    roots = _matching_terms(name_norm, signals["roots"])
    race_roots = _matching_terms(name_norm, signals["race_roots"])
    examples = _matching_examples(name, signals["examples"].get(entity_type, []) + signals["examples"].get("all", []))
    metaphysics = _matching_terms(name_norm, signals["metaphysics_terms"])
    material_or_element = _matching_terms(name_norm, signals["material_terms"] + signals["element_terms"])

    if roots:
        score += 20
        report["reasons"].append("Name uses World Bible roots.")
    if race_roots:
        score += 10
        report["reasons"].append("Name uses race-language roots.")
    if metaphysics:
        score += 15
        report["reasons"].append("Name references World Bible metaphysics.")
    if material_or_element:
        score += 15
        report["reasons"].append("Name references World Bible material, element or status vocabulary.")
    if examples:
        score += 15
        report["reasons"].append("Name resembles a World Bible naming example.")
    if mode_match:
        score += 20
        report["reasons"].append(f"Name fits inferred naming mode: {naming_mode}.")
    if _has_entity_rules(signals, entity_type):
        score += 5
        report["reasons"].append("World Bible has entity-specific naming rules.")
    if _is_multiterm(name) and not generic:
        score += 10
        report["reasons"].append("Name is structured and not purely generic.")

    if generic and not allowed:
        score -= 30
        report["reasons"].append("Name matches generic fantasy/RPG fallback term.")
    if forbidden and not allowed:
        score -= 40
        report["reasons"].append("Name appears in World Bible forbidden terms.")
    if avoid and not allowed:
        score -= 40
        report["reasons"].append("Name appears in entity avoid list.")
    if mode_conflict and not allowed:
        score -= 30
        report["reasons"].append(f"Name conflicts with inferred naming mode: {naming_mode}.")
    if not (roots or race_roots or examples or metaphysics or material_or_element or mode_match or allowed):
        score -= 10
        report["reasons"].append("Name does not use obvious World Bible signals.")
    if len(name_norm) <= 3 and not roots:
        score -= 15
        report["reasons"].append("Name is very short and has no World Bible root.")
    if entity_type not in KNOWN_ENTITY_TYPES:
        score -= 10
        report["reasons"].append("Entity type is not recognized by the guard.")

    if generic and not (forbidden or avoid) and not allowed:
        score = max(score, 20)
    report["score"] = max(0, min(100, int(score)))
    report["matched_roots"] = _unique(roots + race_roots + metaphysics + material_or_element)
    report["matched_examples"] = examples
    report["forbidden_terms_found"] = [] if allowed else forbidden
    report["avoid_terms_found"] = [] if allowed else avoid
    report["status"] = normalize_entity_guard_status(report["score"], forbidden_found=bool((forbidden or avoid) and not allowed))
    report["requires_review"] = report["status"] in {"weak", "generic", "forbidden", "needs_review", "unknown"}
    if not report["reasons"]:
        report["reasons"].append("Name assessed without strong positive or negative signals.")
    return report


def assess_skill_name_against_world_bible(name: str, world_bible: dict | None = None, *, context: dict | None = None) -> dict:
    return assess_entity_name_against_world_bible(name, "skill", world_bible, context=context)


def assess_item_name_against_world_bible(name: str, world_bible: dict | None = None, *, context: dict | None = None) -> dict:
    return assess_entity_name_against_world_bible(name, "item", world_bible, context=context)


def assess_location_name_against_world_bible(name: str, world_bible: dict | None = None, *, context: dict | None = None) -> dict:
    return assess_entity_name_against_world_bible(name, "location", world_bible, context=context)


def assess_faction_name_against_world_bible(name: str, world_bible: dict | None = None, *, context: dict | None = None) -> dict:
    return assess_entity_name_against_world_bible(name, "faction", world_bible, context=context)


def assess_beast_name_against_world_bible(name: str, world_bible: dict | None = None, *, context: dict | None = None) -> dict:
    return assess_entity_name_against_world_bible(name, "beast", world_bible, context=context)


def build_entity_guard_report(entities: list[dict], world_bible: dict | None = None) -> dict:
    reports = [
        assess_entity_name_against_world_bible(entity.get("name", ""), entity.get("entity_type", ""), world_bible)
        for entity in (entities or [])
        if isinstance(entity, dict)
    ]
    summary = {"total": len(reports), "ok": 0, "weak": 0, "generic": 0, "forbidden": 0, "needs_review": 0, "unknown": 0}
    for report in reports:
        summary[report["status"]] = summary.get(report["status"], 0) + 1
    return {"summary": summary, "reports": reports}


def collect_world_bible_name_signals(world_bible: dict | None) -> dict:
    bible = world_bible if isinstance(world_bible, dict) else {}
    naming_rules = _dict(bible.get("naming_rules"))
    signals = {
        "roots": [],
        "race_roots": [],
        "examples": {"all": []},
        "avoid_terms": {"all": []},
        "allowed_terms": [],
        "forbidden_terms": [],
        "metaphysics_terms": [],
        "material_terms": [],
        "element_terms": [],
        "patterns": {},
    }
    linguistics = _dict(bible.get("linguistics"))
    for language in _dict(linguistics.get("world_languages")).values():
        language = _dict(language)
        signals["roots"].extend(_terms(language.get("common_roots")))
        signals["roots"].extend(_terms(_dict(language.get("example_words")).values()))
    for language in _dict(linguistics.get("race_languages")).values():
        language = _dict(language)
        common_roots = _dict(language.get("common_roots"))
        signals["race_roots"].extend(_terms(list(common_roots.keys())))
        signals["race_roots"].extend(_terms(list(common_roots.values())))
        for patterns in _dict(language.get("naming_patterns")).values():
            signals["patterns"].setdefault("all", []).extend(_terms(patterns))
            signals["patterns"].setdefault("plotpoint", []).extend(_terms(patterns))
    signals["race_roots"].extend(_terms(_dict(linguistics.get("faction_dialects")).values()))
    for key, rule in naming_rules.items():
        entity_key = _rule_entity_type(key)
        rule = _dict(rule)
        examples = _terms(rule.get("examples"))
        signals["examples"].setdefault(entity_key, []).extend(examples)
        if key in {"titles", "factions", "regions", "settlements", "people"}:
            signals["examples"].setdefault("plotpoint", []).extend(examples)
        signals["examples"]["all"].extend(examples)
        signals["allowed_terms"].extend(examples)
        signals["avoid_terms"].setdefault(entity_key, []).extend(_terms(rule.get("avoid")))
        signals["patterns"].setdefault(entity_key, []).extend(_terms(rule.get("patterns")))
    identity = _dict(bible.get("identity"))
    tone = _dict(bible.get("tone_and_style"))
    metaphysics = _dict(bible.get("metaphysics"))
    elements = _dict(bible.get("elements"))
    items = _dict(bible.get("items"))
    signals["forbidden_terms"].extend(_terms(identity.get("forbidden_generic_feel")))
    signals["forbidden_terms"].extend(_terms(tone.get("forbidden_words")))
    signals["metaphysics_terms"].extend(_terms([metaphysics.get("main_power_name"), metaphysics.get("power_source"), metaphysics.get("power_cost")]))
    signals["metaphysics_terms"].extend(_terms(tone.get("preferred_motifs")))
    signals["element_terms"].extend(_terms(elements.get("status_effect_vocabulary")) + _terms(elements.get("element_language_rules")))
    signals["material_terms"].extend(_terms(items.get("material_vocabulary")) + _terms(_dict(items.get("rarity_language")).values()))
    return {key: _dedupe_signal(value) for key, value in signals.items()}


def infer_world_naming_mode(world_bible: dict | None) -> str:
    bible = world_bible if isinstance(world_bible, dict) else {}
    text = _norm(" ".join(_string_values([
        _dict(bible.get("identity")).get("genre_shape"),
        _dict(bible.get("identity")).get("core_pitch"),
        _dict(bible.get("identity")).get("dominant_mood"),
        _dict(bible.get("created_from_setup")).get("theme"),
        _dict(bible.get("created_from_setup")).get("tone"),
        _dict(bible.get("created_from_setup")).get("world_structure"),
        _dict(bible.get("tone_and_style")).get("preferred_motifs"),
        _dict(bible.get("naming_rules")),
    ])))
    if any(needle in text for needle in ("superheld", "superhero", "hero academy", "quirk", "academy", "akademie", "class 1", "pro hero")):
        return "superhero_academy"

    fantasy_needles = (
        "dark fantasy",
        "duester",
        "dunkel",
        "sakral",
        "blut",
        "eide",
        "eid",
        "grim",
        "fantasy",
        "magie",
        "magic",
        "cursed",
        "curse",
        "relikt",
        "relic",
        "beast",
        "race",
        "races",
        "echsen",
        "metaphys",
        "invented language",
        "element",
    )
    if any(needle in text for needle in fantasy_needles):
        return "dark_fantasy" if any(needle in text for needle in ("dark fantasy", "duester", "dunkel", "sakral", "blut", "eid", "cursed", "curse", "relikt", "relic")) else "invented_fantasy"
    if any(needle in text for needle in ("isekai", "reinkarn", "summoned", "beschworen")):
        return "isekai_fantasy"

    checks = [
        ("modern_japanese", ("japan", "tokyo", "mha", "anime", "schul", "academy", "akademie")),
        ("cyberpunk", ("cyber", "neon", "konzern", "corp", "implant", "runner", "net")),
        ("sci_fi", ("sci fi", "space", "raumschiff", "kolonie", "planet", "alien")),
        ("pirate", ("pirat", "hafen", "schiff", "reef", "captain", "kapitaen", "sturm")),
        ("post_apocalyptic", ("postapok", "apokal", "wasteland")),
        ("mystery", ("mystery", "detektiv", "geheimnis", "okkult", "ermittlung")),
        ("modern_global", ("modern", "gegenwart", "schule", "stadt", "hospital", "high school")),
    ]
    for mode, needles in checks:
        if any(needle in text for needle in needles):
            return mode
    return "custom" if text else "unknown"


def name_matches_world_naming_mode(name: str, entity_type: str, naming_mode: str, world_bible: dict | None = None) -> bool:
    name_text = _text(name)
    name_norm = _norm(name_text)
    if naming_mode in {"modern_japanese", "superhero_academy"}:
        return _looks_japanese_person_name(name_text) or _contains_japanese_name_token(name_text) or any(token in name_norm for token in ("academy", "akademie", "class", "hero", "quirk", "support gear", "license", "office"))
    if naming_mode == "modern_global":
        return _looks_modern_person_name(name_text) or any(token in name_norm for token in ("hospital", "high", "school", "central", "westbridge", "office"))
    if naming_mode == "cyberpunk":
        return bool(re.search(r"\b(sector|neon|ghost|ice|dyne|corp|net|jack|static)\b|\".+\"", name_norm))
    if naming_mode == "pirate":
        return any(token in name_norm for token in ("captain", "harbor", "hafen", "reef", "salt", "storm", "widow", "blackwake", "old "))
    if naming_mode in {"invented_fantasy", "dark_fantasy", "isekai_fantasy"}:
        return bool(re.search(r"[a-zäöü]+-[a-zäöü]+", name_norm)) or bool(_matching_terms(name_norm, collect_world_bible_name_signals(world_bible).get("roots", [])))
    return False


def collect_world_naming_examples(world_bible: dict | None, entity_type: str = "") -> list[str]:
    signals = collect_world_bible_name_signals(world_bible)
    key = _entity_type(entity_type)
    return _unique(signals["examples"].get(key, []) + signals["examples"].get("all", []))


def normalize_entity_guard_status(score: int, forbidden_found: bool = False) -> str:
    if forbidden_found:
        return "forbidden"
    if score >= 70:
        return "ok"
    if score >= 40:
        return "weak"
    if score >= 20:
        return "generic"
    return "needs_review"


def looks_like_generic_fantasy_name(name: str, entity_type: str = "") -> bool:
    name_norm = _norm(name)
    return any(term in name_norm for term in GENERIC_TERMS)


def _name_conflicts_with_mode(name: str, entity_type: str, naming_mode: str, world_bible: dict | None) -> bool:
    name_norm = _norm(name)
    if naming_mode in {"modern_japanese", "modern_global", "superhero_academy", "cyberpunk"}:
        return looks_like_generic_fantasy_name(name, entity_type)
    if naming_mode in {"invented_fantasy", "dark_fantasy", "isekai_fantasy"}:
        return _looks_modern_person_name(name) and not _explicit_examples_allow(name, world_bible, entity_type)
    return False


def _explicit_examples_allow(name: str, world_bible: dict | None, entity_type: str) -> bool:
    return bool(_matching_examples(name, collect_world_naming_examples(world_bible, entity_type)))


def _has_entity_rules(signals: dict, entity_type: str) -> bool:
    return bool(signals.get("patterns", {}).get(entity_type) or signals.get("examples", {}).get(entity_type))


def _matching_terms(name_norm: str, terms: Iterable[str]) -> List[str]:
    found = []
    for term in terms:
        term_norm = _norm(term)
        if len(term_norm) >= 3 and term_norm in name_norm:
            found.append(_text(term))
    return _unique(found)


def _matches_any(name_norm: str, terms: Iterable[str]) -> List[str]:
    return _matching_terms(name_norm, terms)


def _matching_examples(name: str, examples: Iterable[str]) -> List[str]:
    name_norm = _norm(name)
    name_loose = _loose_possessive_norm(name)
    found = []
    for example in examples:
        example_norm = _norm(example)
        if example_norm and (example_norm in name_norm or example_norm in name_loose or name_norm in example_norm or SequenceMatcher(None, name_norm, example_norm).ratio() >= 0.72):
            found.append(_text(example))
    return _unique(found)


def _looks_modern_person_name(name: str) -> bool:
    parts = [part for part in re.split(r"\s+", _text(name)) if part]
    return len(parts) == 2 and all(part[:1].isupper() and part[1:].islower() for part in parts)


def _looks_japanese_person_name(name: str) -> bool:
    common = {"akira", "mina", "daichi", "yume", "sato", "tanaka", "kuroda", "hoshino", "kaminari", "mika", "ren"}
    parts = set(_norm(name).split())
    return bool(parts & common) and _looks_modern_person_name(name)


def _contains_japanese_name_token(name: str) -> bool:
    common = {"akira", "mina", "daichi", "yume", "sato", "tanaka", "kuroda", "hoshino", "kaminari", "mika", "ren", "rei", "mori"}
    return bool(set(_norm(name).split()) & common)


def _is_multiterm(name: str) -> bool:
    return bool(re.search(r"[\s'\-:]", _text(name)))


def _rule_entity_type(key: str) -> str:
    mapping = {"people": "person", "settlements": "location", "regions": "location", "ruins": "location", "beasts": "beast", "factions": "faction", "skills": "skill", "items": "item", "titles": "title", "plotpoints": "plotpoint"}
    return mapping.get(str(key), str(key))


def _entity_type(value: Any) -> str:
    return _rule_entity_type(_norm(value) or "unknown")


def _terms(value: Any) -> List[str]:
    if isinstance(value, dict):
        raw = list(value.keys()) + list(value.values())
    elif isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = [value]
    terms = []
    for entry in raw:
        text = _text(entry)
        if text:
            terms.append(text)
            terms.extend(part for part in re.split(r"[,;/]+", text) if len(_norm(part)) >= 3)
    return _unique(terms)


def _dedupe_signal(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _unique(entries) for key, entries in value.items()}
    return _unique(value)


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_values(values: Iterable[Any]) -> List[str]:
    out = []
    for value in values:
        if isinstance(value, dict):
            out.extend(_string_values(value.values()))
        elif isinstance(value, (list, tuple, set)):
            out.extend(_string_values(value))
        else:
            text = _text(value)
            if text:
                out.append(text)
    return out


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    text = _text(value).lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _loose_possessive_norm(value: Any) -> str:
    words = _norm(value).split()
    return " ".join(word[:-1] if len(word) > 4 and word.endswith("s") else word for word in words)


def _unique(values: Iterable[Any]) -> List[str]:
    result = []
    seen = set()
    for value in values:
        text = _text(value)
        key = _norm(text)
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result
