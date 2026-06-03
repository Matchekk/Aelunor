PROGRESSION_CLAIM_TYPES = ("skill_claim", "skill_level_claim", "class_claim", "class_level_claim", "manifestation_claim")
PROGRESSION_EXTRACTOR_CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}
PROGRESSION_EXTRACTOR_CONFIDENCE_SCORE = {"low": 0.3, "medium": 0.6, "high": 0.85}
PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS = {"high": 0.75, "medium": 0.45}

RESOURCE_KEYS = ("hp", "stamina", "aether", "stress", "corruption", "wounds")
ATTRIBUTE_KEYS = ("str", "dex", "con", "int", "wis", "cha", "luck")

PROGRESSION_EVENT_TYPES = {
    "combat_victory", "combat_survival", "major_discovery", "milestone_progress", "boss_defeated", "class_breakthrough", "skill_mastery_use", "skill_manifestation", "training_success", "bond_event",
}
PROGRESSION_EVENT_SEVERITIES = {"low", "medium", "high"}
PROGRESSION_EVENT_SEVERITY_MULTIPLIER = {"low": 1.0, "medium": 1.35, "high": 1.8}
PROGRESSION_EVENT_BASE_XP = {
    "combat_victory": {"character": 28, "class": 18, "skill": 20},
    "combat_survival": {"character": 14, "class": 8, "skill": 10},
    "major_discovery": {"character": 24, "class": 14, "skill": 8},
    "milestone_progress": {"character": 36, "class": 24, "skill": 14},
    "boss_defeated": {"character": 55, "class": 34, "skill": 26},
    "class_breakthrough": {"character": 26, "class": 30, "skill": 8},
    "skill_mastery_use": {"character": 10, "class": 6, "skill": 16},
    "skill_manifestation": {"character": 22, "class": 14, "skill": 26},
    "training_success": {"character": 14, "class": 10, "skill": 14},
    "bond_event": {"character": 12, "class": 8, "skill": 6},
}
PROGRESSION_EVENT_PRIORITY = {
    "boss_defeated": 100, "milestone_progress": 90, "class_breakthrough": 82, "skill_manifestation": 76, "combat_victory": 66, "major_discovery": 62, "skill_mastery_use": 52, "training_success": 46, "combat_survival": 40, "bond_event": 34,
}
PROGRESSION_DENSITY_CAP_NON_MILESTONE = {"inferred": 1, "total": 3}
PROGRESSION_DENSITY_CAP_MILESTONE = {"inferred": 2, "total": 5}
PROGRESSION_SET_DIRECT_KEYS = {"level", "xp_total", "xp_current", "xp_to_next", "class_level", "class_xp", "class_xp_to_next"}

FIRST_SKILL_FORCE_PROBABILITY = 0.8
SKILL_KEYS = ("stealth", "perception", "survival", "athletics", "intimidation", "persuasion", "lore_occult", "crafting", "lockpicking", "endurance", "willpower", "tactics")
SKILL_RANKS = ("F", "E", "D", "C", "B", "A", "S")
SKILL_RANK_ORDER = {rank: index for index, rank in enumerate(SKILL_RANKS)}
CLASS_ASCENSION_STATUSES = {"none", "available", "active", "completed"}

LEGACY_ROLE_CLASS_MAP = {
    "frontline": {"id": "class_vorhut", "name": "Vorhut", "rank": "F", "affinity_tags": ["körper", "kampf", "schutz"], "description": "Geht voran, hält Treffer aus und bindet die schlimmste Gefahr zuerst."},
    "scout": {"id": "class_spaeher", "name": "Späher", "rank": "F", "affinity_tags": ["bewegung", "heimlichkeit", "sinn"], "description": "Lebt von Überblick, Fährten und riskanten Vorstößen."},
    "face": {"id": "class_unterhaendler", "name": "Unterhändler", "rank": "F", "affinity_tags": ["sozial", "sprache", "einfluss"], "description": "Zwingt Gespräche, Drohungen und Deals in eine brauchbare Richtung."},
    "support": {"id": "class_waechter", "name": "Wächter", "rank": "F", "affinity_tags": ["schutz", "heilung", "standhaft"], "description": "Hält andere auf den Beinen und stabilisiert chaotische Lagen."},
    "tueftler": {"id": "class_schrotttueftler", "name": "Schrotttüftler", "rank": "F", "affinity_tags": ["technik", "improvisation", "werkzeug"], "description": "Macht aus Schrott, Relikten und Notlösungen einen Vorteil."},
    "occult": {"id": "class_okkultist", "name": "Okkultist", "rank": "F", "affinity_tags": ["okkult", "ritual", "schatten"], "description": "Greift nach verbotenen Wahrheiten und zahlt dafür einen Preis."},
}
LEGACY_SKILL_NAME_MAP = {
    "stealth": "Schleichen", "perception": "Wahrnehmung", "survival": "Überleben", "athletics": "Athletik", "intimidation": "Einschüchtern", "persuasion": "Überzeugen", "lore_occult": "Okkultes Wissen", "crafting": "Handwerk", "lockpicking": "Schlösser öffnen", "endurance": "Ausdauer", "willpower": "Willenskraft", "tactics": "Taktik",
}
LEGACY_SKILL_TAGS = {
    "stealth": ["bewegung", "heimlichkeit"],
    "perception": ["sinn", "wahrnehmung"],
    "survival": ["wildnis", "ausdauer"],
    "athletics": ["körper", "kraft"],
    "intimidation": ["sozial", "druck"],
    "persuasion": ["sozial", "sprache"],
    "lore_occult": ["wissen", "okkult"],
    "crafting": ["technik", "handwerk"],
    "lockpicking": ["technik", "präzision"],
    "endurance": ["körper", "regeneration"],
    "willpower": ["geist", "widerstand"],
    "tactics": ["kampf", "strategie"],
}
RESISTANCE_KEYS = ("physical", "fire", "cold", "lightning", "poison", "bleed", "shadow", "holy", "curse", "fear")
SKILL_ATTRIBUTE_MAP = {
    "stealth": "dex", "perception": "wis", "survival": "wis", "athletics": "str", "intimidation": "cha", "persuasion": "cha", "lore_occult": "int", "crafting": "int", "lockpicking": "dex", "endurance": "con", "willpower": "wis", "tactics": "int",
}
SKILL_RANK_THRESHOLDS = (("S", 14), ("A", 11), ("B", 9), ("C", 7), ("D", 5), ("E", 3), ("F", 1))
SKILL_OUTCOME_XP = {"success": 12, "partial": 8, "fail": 5}
SKILL_PATHS = {
    "stealth": ["Shadow Veil", "Ghost Scout", "Cursed Slip"],
    "perception": ["Hunter Sight", "Arc Sense", "Dread Echo"],
    "survival": ["Ash Walker", "Beast Route", "Starved Resolve"],
    "athletics": ["Breaker Frame", "Wild Rush", "Blood Sprint"],
    "intimidation": ["Grave Voice", "Tyrant Stare", "Panic Chorus"],
    "persuasion": ["Silver Tongue", "False Halo", "Oath Binder"],
    "lore_occult": ["Hex Reader", "Curse Weaving", "Void Lexicon"],
    "crafting": ["Trap Architect", "Relic Smith", "Blight Tinkerer"],
    "lockpicking": ["Whisper Keys", "Ruin Fingers", "Void Picks"],
    "endurance": ["Iron Body", "Last Ember", "Pain Vessel"],
    "willpower": ["Soul Brace", "Moon Mind", "Hollow Oath"],
    "tactics": ["Kill Box", "War Reader", "Night Marshal"],
}
SKILL_EVOLUTIONS = {
    "stealth": ["Shadow Veil", "Silent Steps", "Night Skin"],
    "perception": ["Predator Glimpse", "Thread Sense", "Fear Scent"],
    "athletics": ["Breaker Surge", "Iron Leap", "Ruin Charge"],
    "lore_occult": ["Curse Weaving", "Hex Memory", "Blood Lexicon"],
    "crafting": ["Trap Architect", "Relic Stitching", "Ash Forge"],
    "endurance": ["Iron Body", "Pain Engine", "Grave Stance"],
    "tactics": ["Kill Grid", "Night Marshal", "Ambush Doctrine"],
}
SKILL_FUSIONS = {
    ("perception", "stealth"): {"id": "skill_predator_sense", "name": "Predator Sense", "rank": "S"},
    ("athletics", "endurance"): {"id": "skill_iron_body", "name": "Iron Body", "rank": "S"},
    ("lore_occult", "willpower"): {"id": "skill_curse_weaving", "name": "Curse Weaving", "rank": "S"},
    ("crafting", "tactics"): {"id": "skill_trap_architect", "name": "Trap Architect", "rank": "S"},
}
DEFAULT_DYNAMIC_SKILL_LEVEL_MAX = 10
DEFAULT_NUMERIC_SKILL_DELTA_XP = 20
