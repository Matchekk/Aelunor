CODEX_KNOWLEDGE_LEVEL_MIN = 0
CODEX_KNOWLEDGE_LEVEL_MAX = 4
CODEX_KIND_RACE = "race"
CODEX_KIND_BEAST = "beast"

RACE_CODEX_BLOCK_ORDER = [
    "identity",
    "appearance",
    "culture",
    "homeland",
    "class_affinities",
    "skill_affinities",
    "strengths",
    "weaknesses",
    "relations",
    "notable_individuals",
]
BEAST_CODEX_BLOCK_ORDER = [
    "identity",
    "appearance",
    "habitat",
    "behavior",
    "combat_style",
    "known_abilities",
    "strengths",
    "weaknesses",
    "loot",
    "lore",
]
RACE_BLOCKS_BY_LEVEL = {
    0: [],
    1: ["identity", "appearance"],
    2: ["culture", "homeland", "relations"],
    3: ["class_affinities", "skill_affinities", "strengths", "weaknesses"],
    4: ["notable_individuals"],
}
BEAST_BLOCKS_BY_LEVEL = {
    0: [],
    1: ["identity", "appearance", "habitat"],
    2: ["behavior", "combat_style"],
    3: ["known_abilities", "strengths", "weaknesses", "loot"],
    4: ["lore"],
}
CODEX_DEFAULT_META = {
    "version": 1,
    "shared_knowledge": True,
}

CODEX_RACE_TRIGGER_LORE = {
    "archiv",
    "chronik",
    "legende",
    "lore",
    "forschung",
    "forscht",
    "bibliothek",
    "tafel",
    "buch",
    "aufzeichnung",
    "codex",
    "lehrtext",
}
CODEX_RACE_TRIGGER_CONTACT = {
    "begegnet",
    "trifft",
    "spricht",
    "verhandelt",
    "diplomatie",
    "hilfe",
    "misstrauen",
    "bittet",
    "verfolgt",
    "rettet",
}
CODEX_BEAST_TRIGGER_COMBAT = {
    "kampf",
    "angriff",
    "klaue",
    "biss",
    "zahn",
    "gift",
    "schlag",
    "trifft",
    "duell",
    "monster",
    "bestie",
}
CODEX_BEAST_TRIGGER_DEFEAT = {
    "besiegt",
    "erlegt",
    "getoetet",
    "getötet",
    "vernichtet",
    "erschlagen",
    "faellt",
    "fällt",
}
CODEX_BEAST_TRIGGER_ABILITY = {
    "faehigkeit",
    "fähigkeit",
    "atem",
    "zauber",
    "schrei",
    "aura",
    "sprung",
    "regen",
    "giftwolke",
}
NPC_STATUS_ALLOWED = {"active", "unknown", "gone"}
