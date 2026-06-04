import hashlib
import json
import random
from typing import Any, Callable, Dict, Optional, Set, Tuple

from app.services.world.naming import generate_unique_fantasy_name, pick_world_theme_anchor


def generate_world_race_profiles(
    summary: Dict[str, Any],
    *,
    seed_hint: str = "",
    normalize_codex_alias_text: Callable[[str], str],
    clamp: Callable[[int, int, int], int],
    race_id_from_name: Callable[[str], str],
    normalize_race_profile: Callable[..., Optional[Dict[str, Any]]],
    default_race_profile: Callable[[str, str], Dict[str, Any]],
    stable_sorted_mapping: Callable[..., Dict[str, Dict[str, Any]]],
    world_codex_sort_key: Callable[[Tuple[str, Dict[str, Any]]], Tuple[str, str]],
) -> Dict[str, Dict[str, Any]]:
    anchor = pick_world_theme_anchor(summary, normalize_codex_alias_text=normalize_codex_alias_text)
    seed_text = json.dumps(
        {"theme": summary.get("theme", ""), "tone": summary.get("tone", ""), "conflict": summary.get("central_conflict", ""), "anchor": anchor, "seed": seed_hint},
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    race_count = clamp(5 + rng.randint(0, 2), 5, 7)
    used_names: Set[str] = set()
    race_suffixes = ["ar", "en", "iden", "ari", "orn", "eth", "yr"]
    temperaments = ["ruhig", "wachsam", "stur", "berechnend", "pflichtbewusst", "wechselhaft", "intensiv"]
    archetypes = [
        {"kind": "menschenvolk", "rarity": "gewöhnlich", "description_short": "Anpassungsfähiges Volk mit schneller sozialer Dynamik.", "appearance": "Vielfältige Erscheinungsbilder und praktische Reiseausrüstung.", "homeland": "Grenzstädte und Handelsachsen", "culture": "Pragmatisch, fraktionsnah und zielorientiert", "strength_tags": ["anpassung", "diplomatie", "handwerk"], "weakness_tags": ["interne_spaltung", "kurze_lebensspanne"], "class_affinities": ["ritter", "schuetze", "haendler"], "skill_affinities": ["führung", "taktik", "überleben"], "social_reputation": "dominant, aber umkämpft", "notable_traits": ["schnelle lernkurve", "fraktionsnetzwerke"]},
        {"kind": "langlebiges magiervolk", "rarity": "selten", "description_short": "Langlebiges Volk mit strenger Erinnerungskultur und arkaner Disziplin.", "appearance": "Feine Gesichtszüge und leuchtende Runenlinien.", "homeland": "Haine, Archive und uralte Observatorien", "culture": "Ritualisiert und wissenszentriert", "strength_tags": ["arkane_praezision", "mentale_disziplin"], "weakness_tags": ["fragile_koerper", "ueberheblichkeit"], "class_affinities": ["runenweber", "mystiker", "hüter"], "skill_affinities": ["analyse", "barrieren", "kanalisierung"], "social_reputation": "respektiert und gefürchtet", "notable_traits": ["langes gedächtnis", "rituelle namenbindung"]},
        {"kind": "robustes bergvolk", "rarity": "ungewöhnlich", "description_short": "Robustes Volk mit strikten Eiden und handwerklicher Kriegskultur.", "appearance": "Massiger Körperbau, Narben und metallene Tätowierungen.", "homeland": "Gebirgsschächte, Basaltfesten und Erzpfade", "culture": "Ehrenkodex, Schuldbücher und Werkbanktradition", "strength_tags": ["zähigkeit", "rüstungshandwerk", "nahkampf"], "weakness_tags": ["starre_riten", "langsame_anpassung"], "class_affinities": ["vorhut", "schmied", "waechter"], "skill_affinities": ["schildtechnik", "metallkunde", "standhaftigkeit"], "social_reputation": "verlässlich, aber unnachgiebig", "notable_traits": ["eidsiegel", "steinlieder"]},
    ]
    while len(archetypes) < race_count:
        archetypes.append(
            {
                "kind": rng.choice(["schleierkultur", "resonanzvolk", "nomadenvolk", "karglandvolk", "lichtordenvolk"]),
                "rarity": rng.choice(["gewöhnlich", "ungewöhnlich", "selten"]),
                "description_short": rng.choice(["Eigenständiges Volk mit starker Bindung an lokale Weltgesetze.", "Grenzvolk, dessen Überleben auf strengen Pakten beruht.", "Kultur mit ausgeprägter Ritual- und Verpflichtungslogik."]),
                "appearance": rng.choice(["Markante Hautmuster und rituelle Kleidungsschichten.", "Körpermale, die bei Ressourcennutzung sichtbar pulsieren.", "Praktische Panzerstoffe mit kulturellen Siegelzeichen."]),
                "homeland": rng.choice(["Nebelgrenzen und zerfallene Grenzruinen", "Aschepfade, Kraterfelder und Schutzzelte", "Klüfte, Archive und halbversunkene Bastionen"]),
                "culture": rng.choice(["Schwurbündnisse, Ahnenpfade und strenge Mentorenlinien", "Tauschrituale, Schuldzeichen und Pflichtkataloge", "Prüfpfade, Bündnisrecht und Überlebensethos"]),
                "strength_tags": rng.sample(["täuschung", "resonanz", "ausdauer", "spurlesen", "barriere", "segen"], 3),
                "weakness_tags": rng.sample(["lichtempfindlich", "dogmatisch", "starre_riten", "wasserknappheit", "überlastung"], 2),
                "class_affinities": rng.sample(["späher", "hexer", "hüter", "katalysator", "jäger", "totemkrieger"], 3),
                "skill_affinities": rng.sample(["verschleierung", "kanalisierung", "fährtenlesen", "durchhaltewillen", "sigillen"], 3),
                "social_reputation": rng.choice(["misstrauisch beobachtet", "politisch umkämpft", "respektiert als Grenzmacht"]),
                "notable_traits": rng.sample(["namensmasken", "resonanzkrisen", "ahnenmasken", "wahrheitssiegel", "schuldbänder"], 2),
            }
        )
    races: Dict[str, Dict[str, Any]] = {}
    for template in archetypes[:race_count]:
        name = generate_unique_fantasy_name(rng, used_names, anchor=anchor, suffixes=race_suffixes, normalize_codex_alias_text=normalize_codex_alias_text)
        race_id = race_id_from_name(name)
        temperament = rng.choice(temperaments)
        races[race_id] = normalize_race_profile({**template, "id": race_id}, fallback_id=race_id) or default_race_profile(race_id, template.get("name", ""))
        races[race_id]["name"] = name
        races[race_id]["temperament"] = temperament
        races[race_id]["aliases"] = [f"Volk von {name}", f"{name}er"]
    return stable_sorted_mapping(races, key_fn=world_codex_sort_key)


def generate_world_beast_profiles(
    summary: Dict[str, Any],
    *,
    seed_hint: str = "",
    normalize_codex_alias_text: Callable[[str], str],
    clamp: Callable[[int, int, int], int],
    beast_id_from_name: Callable[[str], str],
    normalize_beast_profile: Callable[..., Optional[Dict[str, Any]]],
    default_beast_profile: Callable[[str, str], Dict[str, Any]],
    stable_sorted_mapping: Callable[..., Dict[str, Dict[str, Any]]],
    world_codex_sort_key: Callable[[Tuple[str, Dict[str, Any]]], Tuple[str, str]],
) -> Dict[str, Dict[str, Any]]:
    anchor = pick_world_theme_anchor(summary, normalize_codex_alias_text=normalize_codex_alias_text)
    seed_text = json.dumps(
        {"theme": summary.get("theme", ""), "tone": summary.get("tone", ""), "density": summary.get("monsters_density", ""), "anchor": anchor, "seed": seed_hint},
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    beast_count = clamp(6 + rng.randint(0, 6), 6, 12)
    used_names: Set[str] = set()
    beast_suffixes = ["fang", "wyrm", "krall", "stachel", "geist", "mimik", "hydra", "schnitter"]
    categories = ["bestie", "aberration", "flugbestie", "koloss", "geistbestie", "schwarm", "konstrukt", "wasserbestie"]
    habitats = ["Nebelwälder", "Obeliskenruinen", "Kraterpfade", "Grenzgräben und Ruinenfelder", "Felsstädte und Kapellenruinen", "Vergiftete Feuchtlande", "Versunkene Tempel"]
    behaviors = ["jagt aus dem Hinterhalt und umkreist verwundete Ziele", "patrouilliert feste Reviere und reagiert auf Ressourcenimpulse", "lockt Gruppen in ungünstige Positionen", "verteidigt Brutreviere aggressiv"]
    beasts: Dict[str, Dict[str, Any]] = {}
    for _ in range(beast_count):
        name = generate_unique_fantasy_name(rng, used_names, anchor=anchor, suffixes=beast_suffixes, normalize_codex_alias_text=normalize_codex_alias_text)
        beast_id = beast_id_from_name(name)
        template = {
            "id": beast_id,
            "name": name,
            "category": rng.choice(categories),
            "danger_rating": clamp(2 + rng.randint(0, 10), 1, 20),
            "habitat": rng.choice(habitats),
            "behavior": rng.choice(behaviors),
            "appearance": rng.choice(["Panzerartige Hautsegmente mit unruhigem Schimmer.", "Sehniger Körperbau mit markanten Klingen- und Hornstrukturen.", "Schattenhafte Konturen, die im Kampf flackern."]),
            "strength_tags": rng.sample(["hinterhalt", "wucht", "regeneration", "schnelligkeit", "panzerung", "schwarmdruck"], 2),
            "weakness_tags": rng.sample(["blendlicht", "feuer", "eis", "resonanzzauber", "netzfallen", "ritualkreide"], 2),
            "combat_style": rng.choice(["schnelle Flankenangriffe", "Dauerdruck über Reichweite", "kurze Burst-Angriffe aus Tarnung", "wuchtige Zonenangriffe"]),
            "known_abilities": rng.sample(["Nebeltritt", "Kernstoß", "Dornenwurf", "Kältefessel", "Truemmerwelle", "Sogkante"], 2),
            "loot_tags": rng.sample(["kernsplitter", "sehnenfaser", "schuppenstück", "geiststaub", "kralle"], 2),
            "lore_notes": [rng.choice(["Meidet geweihte Feuerlinien.", "Reagiert stark auf resonierende Metallklänge.", "Wird bei knapper Ressource aggressiver."])],
            "aliases": [f"{name}-Typ", f"{name}rudel"],
        }
        beasts[beast_id] = normalize_beast_profile(template, fallback_id=beast_id) or default_beast_profile(beast_id, name)
    return stable_sorted_mapping(beasts, key_fn=world_codex_sort_key)
