from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


TRIVIAL_ROOTS = {
    "and",
    "the",
    "with",
    "world",
    "survi",
    "survival",
    "dark",
    "fantasy",
    "modern",
    "academy",
    "theme",
    "danger",
    "dangerous",
}

FANTASY_ROOTS = ["ssar", "vael", "karn", "nok", "thar", "veyr", "ael", "morn", "hal", "keth"]
SUPERHERO_ROOTS = ["pulse", "zero", "drive", "glass", "gear", "rank", "hero", "class", "neon", "bracer"]
POST_APOCALYPTIC_ROOTS = ["rust", "ash", "dawn", "vault", "scrap", "signal", "route", "husk", "ember", "ridge"]


def infer_setup_naming_mode(setup: Dict[str, Any]) -> str:
    text = _norm(" ".join(_string_values(setup.values())))
    fantasy_signals = (
        "dark fantasy",
        "fantasy",
        "cursed",
        "curse",
        "magic",
        "magie",
        "relic",
        "relikt",
        "race",
        "races",
        "beast",
        "beasts",
        "echsen",
        "voelker",
        "invented language",
        "metaphysics",
        "eid",
        "blut",
    )
    if any(token in text for token in ("superhero", "hero academy", "quirk", "support gear", "pro hero", "class 1")):
        return "superhero_academy"
    if any(token in text for token in fantasy_signals):
        return "dark_fantasy" if "dark" in text or "cursed" in text or "blut" in text or "eid" in text else "invented_fantasy"
    if any(token in text for token in ("postapok", "apokal", "wasteland", "vault", "scrap")):
        return "post_apocalyptic"
    return "custom"


def fallback_roots_for_setup(setup: Dict[str, Any], seed: str) -> List[str]:
    mode = infer_setup_naming_mode(setup)
    if mode == "superhero_academy":
        base = SUPERHERO_ROOTS
    elif mode == "post_apocalyptic":
        base = POST_APOCALYPTIC_ROOTS
    else:
        base = FANTASY_ROOTS
    offset = int(seed[:2], 16) % len(base)
    return _unique_strings(base[offset:] + base[:offset])[:10]


def fallback_naming_examples(setup: Dict[str, Any], roots: List[str], resource: str) -> Dict[str, List[str]]:
    mode = infer_setup_naming_mode(setup)
    if mode == "superhero_academy":
        return {
            "people": ["Akira Tanaka", "Rei Hoshikawa", "Daichi Mori"],
            "settlements": ["Hoshino Academy", "Training Arena", "Pro Hero Office"],
            "regions": ["Hoshino Campus", "Agency District", "License Hall"],
            "ruins": ["Old Training Wing", "Retired Arena", "Closed Support Lab"],
            "factions": ["Hoshino Academy", "Class 1-B", "Pro Hero Office"],
            "skills": ["Zero-Point Grip", "Bakuen Step", "Glass Nerve"],
            "items": ["Support Gear", "Training Bracer", "Quirk Stabilizer"],
            "beasts": ["Training Dummy", "Rescue Drone", "Combat Bot"],
            "titles": ["Pro Hero", "Support Trainee", "Class Representative"],
        }
    if mode == "post_apocalyptic":
        return {
            "people": ["Mara Venn", "Joss Rake", "Nia Vale"],
            "settlements": ["Rustwake", "Vault Seven", "Ashline Depot"],
            "regions": ["The Glass Flats", "Signal Ridge", "The Red Route"],
            "ruins": ["Husk Station", "Old Reactor", "Dead Mall"],
            "factions": ["The Signal Keepers", "Scrap Choir", "Route Wardens"],
            "skills": ["Scrap-Step", "Signal Read", "Ash Lung"],
            "items": ["Filter Mask", "Rustblade", "Signal Battery"],
            "beasts": ["Glass Hound", "Ash Wretch", "Vault Mite"],
            "titles": ["Route Warden", "Vault Runner", "Signal Keeper"],
        }
    return {
        "people": ["Mara Venn", "Ssar-Keth", "Vaelren"],
        "settlements": ["Ssereth-Vael", "Nok-Thar", "Karnvar"],
        "regions": ["Karnvar", "Nok-Thar", "Vaelmark"],
        "ruins": ["Bluttor von Karnvar", "Aschewarte", "Nok-Thar-Gewaelbe"],
        "factions": ["Orden des Bluttores", "Die Ssereth-Hueter", "Karnwacht"],
        "skills": ["Karn-Griff", "Eid der Asche", "Dritter Atem"],
        "items": [f"{resource}glas-Klinge", "Karnstahl-Siegel", "Veyrglas-Klinge"],
        "beasts": ["Aschenmaul", "Vael-Schliefer", "Karnbeisser"],
        "titles": ["Bluttor-Hueter", "Eidlaeuferin", "Aschezeuge"],
    }


def fallback_race_languages(setup: Dict[str, Any], roots: List[str]) -> Dict[str, Dict[str, Any]]:
    mode = infer_setup_naming_mode(setup)
    text = _norm(" ".join(_string_values(setup.values())))
    if mode not in {"dark_fantasy", "invented_fantasy", "isekai_fantasy"}:
        return {}
    if not any(token in text for token in ("race", "races", "beast", "beasts", "echsen", "voelker", "monster")):
        return {}
    common_roots = {
        "ssar": "warm, lebendig, atmend",
        "keth": "Stein, Tor oder heiliger Ort",
        "vael": "Eid, Grenze oder bewachter Name",
        "nok": "Nacht, Schuld oder verborgenes Wissen",
    }
    return {
        "race_lizardfolk": {
            "race_id": "race_lizardfolk",
            "language_name": "Ssarrek",
            "self_name_for_race": "Ssar-Keth",
            "external_name_for_race": "Echsenmenschen",
            "sound": "klickend, trocken, mit s-Lauten und harten Endkonsonanten",
            "phonetic_rules": ["Doppel-s markiert lebendige Waerme.", "Keth-Endungen bezeichnen Orte oder heilige Steine."],
            "common_roots": {root: common_roots[root] for root in common_roots if root in set(roots) | set(common_roots)},
            "naming_patterns": {
                "people": ["Ssar-{Rufname}", "{Root}-Keth"],
                "settlements": ["Ssereth-{Eidroot}", "{Root}-Thar"],
                "sacred_sites": ["{Root}-Keth", "Tor von {Root}"],
                "titles": ["{Root}-Hueter", "Stimmen von {Root}"],
                "beasts": ["{Root}-Schliefer", "{Root}maul"],
                "skills": ["{Root}-Griff", "Eid von {Root}"],
            },
            "translation_behavior": {
                "literal_translation": True,
                "partial_understanding_creates_wrong_category": True,
                "concepts_without_common_equivalent": ["lebender Ort", "Eidstein", "Name als Schuld"],
            },
        }
    }


def clean_language_roots(roots: Iterable[Any]) -> List[str]:
    return _unique_strings(root for root in roots if _valid_root(root))


def _valid_root(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return bool(re.fullmatch(r"[a-z][a-z0-9-]{2,12}", text)) and text not in TRIVIAL_ROOTS


def _string_values(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for value in values:
        if isinstance(value, dict):
            out.extend(_string_values(value.values()))
        elif isinstance(value, (list, tuple, set)):
            out.extend(_string_values(value))
        else:
            text = str(value or "").strip()
            if text:
                out.append(text)
    return out


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result
