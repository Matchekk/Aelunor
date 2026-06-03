import re


PROGRESSION_CLAIM_CUES = {
    "skill_claim": ("lernt", "erlernt", "schaltet frei", "erhaelt die faehigkeit", "erhält die fähigkeit", "entwickelt", "meistert", "beherrscht nun"),
    "skill_level_claim": ("skill steigt", "skill-level", "skill level", "stufe des skills", "meisterschaft", "verbessert", "verfeinert"),
    "class_claim": ("klassenwechsel", "klasse gewechselt", "wird zum", "wird zur", "nimmt den klassenpfad", "schlaegt den klassenpfad ein", "schlägt den klassenpfad ein", "erwacht als"),
    "class_level_claim": ("klassenlevel", "class level", "klassenstufe", "rang steigt", "rangaufstieg", "aufstieg zu rang"),
    "manifestation_claim": ("manifestiert", "erstmanifestation", "entfesselt erstmals", "bricht hervor", "erweckt"),
}

NPC_GENERIC_NAME_TOKENS = {
    "wache", "soldat", "kind", "frau", "mann", "haendler", "händler", "ritter", "magier", "priester", "scharlatan", "bandit", "siedler", "reisender", "taenzer", "tänzer", "vagabund", "buerger", "bürger", "fremder", "fremde", "gegner", "monster", "kreatur",
}
ACTION_STOPWORDS = {
    "ich", "und", "oder", "aber", "doch", "dann", "mit", "dem", "den", "der", "die", "das", "ein", "eine", "einer", "einem", "einen", "paar", "mehr", "weiter", "aktuelle", "szene", "organisch", "ohne", "harten", "sprung", "fort", "bleib", "direkten", "konsequenzen", "letzten", "turns", "rede", "sage", "sag", "mache", "mach",
}
ENGLISH_LANGUAGE_MARKERS = {
    "what", "who", "why", "how", "next", "do", "the", "and", "with", "without", "into", "through", "toward", "from", "before", "after", "while", "where", "there", "their", "them", "they", "you", "your", "was", "were", "is", "are", "be", "been", "being", "this", "that", "these", "those", "road", "ruins", "kingdom", "border", "guard", "watchtower", "scene", "story",
}
GERMAN_LANGUAGE_MARKERS = {
    "der", "die", "das", "dem", "den", "des", "ein", "eine", "einer", "einem", "einen", "und", "oder", "aber", "nicht", "noch", "mit", "ohne", "durch", "gegen", "über", "unter", "zwischen", "während", "weil", "dass", "wenn", "hier", "dort", "wurde", "waren", "ist", "sind", "szene", "geschichte", "wache",
}

ABILITY_UNLOCK_TRIGGER_PATTERNS = [
    re.compile(
        r"(?:erlernt|erlent|wiedererlernt|lernt|meistert|beherrscht(?:\s+nun)?|schaltet(?:\s+\w+)?\s+frei|erhält|entwickelt|entfesselt)"
        r"\s+(?:die|den|das|eine|einen)?\s*(?:fähigkeit|technik|zauber|magie|gabe|kunst|ritual|formel|form)?\s*[„\"]([^\"“”]{3,60})[\"”]?",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:erlernt|erlent|wiedererlernt|lernt|meistert|beherrscht(?:\s+nun)?|schaltet(?:\s+\w+)?\s+frei|erhält|entwickelt|entfesselt)"
        r"\s+(?:die|den|das|eine|einen)?\s*(?:fähigkeit|technik|zauber|magie|gabe|kunst|ritual|formel|form)(?:\s+(?:der|des))?\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,60})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:erlernt|erlent|wiedererlernt|lernt|meistert|beherrscht(?:\s+nun)?|schaltet(?:\s+\w+)?\s+frei|erhält|entwickelt|entfesselt)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,40})",
        flags=re.IGNORECASE,
    ),
]
ABILITY_UNLOCK_GENERIC_NAMES = {"faehigkeit", "technik", "zauber", "magie", "gabe", "kunst", "ritual", "form", "formel", "neue faehigkeit", "neue technik", "neuer zauber", "neue magie", "diese magie", "jene magie"}
UNIVERSAL_SKILL_LIKE_NAMES = {
    "ausdauer", "harter koerper", "harter körper", "schneller schritt", "sechster sinn", "6ter sinn", "6. sinn", "wacher blick", "zäher wille", "zaeher wille", "ruhepuls", "scharfer blick", "taktisches gefuehl", "taktisches gefühl",
}

AUTO_ITEM_ACQUIRE_PATTERNS = [
    re.compile(
        r"(?:hebt|hebe|findet|finde|entdeckt|entdecke|pluendert|plündert|pluendere|plündere|lootet|loote|erbeutet|erbeute|erhält|erhaelt|erhalte|nimmt|nehme|steckt|stecke|packt|packe|sammelt|sammle)\s+"
        r"(?:(?:ich|er|sie|wir|ihr|man)\s+)?(?:den|die|das|einen|eine|ein|einem|einer)?\s*([^,.!?;\n]{3,80}?)(?:\s+auf|\s+ein|\s+an\s+sich|\s+bei\s+sich|\s+und\b|,|\.|$)",
        flags=re.IGNORECASE,
    ),
]
AUTO_ITEM_EQUIP_PATTERNS = [
    re.compile(
        r"(?:zieht|ziehe|zueckt|zückt|zuecke|zücke|führt|fuehrt|fuehre|führe|schwingt|schwinge|hält|haelt|halte|greift|greife|richtet|richte|zielt|ziele)\s+"
        r"(?:(?:ich|er|sie|wir|ihr|man)\s+)?(?:den|die|das|einen|eine|ein|seinen|seine|ihr|ihre)?\s*([^,.!?;\n]{3,80}?)(?:\s+in\s+der\s+hand|\s+gegen|\s+auf|\s+vor\s+(?:mich|ihn|sie|ihm|ihr|sich|uns|euch)|\s+und\b|,|\.|$)",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:trägt|trage|traegt|tragt|legt\s+an|lege\s+an|rüstet|ruestet|rüste|rueste|gürtet|guertet|gürte|guerte|schnallt|schnalle)\s+"
        r"(?:(?:ich|er|sie|wir|ihr|man)\s+)?(?:den|die|das|einen|eine|ein|seinen|seine|ihr|ihre)?\s*([^,.!?;\n]{3,80}?)(?:\s+an|\s+um|\s+bei\s+sich|\s+und\b|,|\.|$)",
        flags=re.IGNORECASE,
    ),
]
AUTO_ITEM_GENERIC_NAMES = {"gegenstand", "objekt", "item", "waffe", "rüstung", "ruestung", "ding", "ausrüstung", "ausruestung", "zeug", "kram"}
ITEM_WEAPON_KEYWORDS = {"schwert", "klinge", "dolch", "messer", "axt", "hammer", "speer", "lanze", "stab", "bogen", "armbrust", "peitsche", "flegel", "waffe"}
ITEM_OFFHAND_KEYWORDS = {"schild", "buckler", "fokus", "fokuskristall", "orb"}
ITEM_CHEST_KEYWORDS = {"rüstung", "ruestung", "panzer", "harnisch", "mantel", "robe", "weste", "brustplatte"}
ITEM_TRINKET_KEYWORDS = {"amulett", "ring", "talisman", "anhänger", "anhaenger", "kette", "reliquie", "totem"}
ITEM_DETAIL_CLAUSE_MARKERS = (" mit ", " für ", " fuer ", " welches ", " welcher ", " welche ", " das ", " der ", " die ")
EQUIPMENT_SLOT_ALIASES = {
    "armor": "chest", "brust": "chest", "body": "chest", "weapon": "weapon", "mainhand": "weapon", "offhand": "offhand", "shield": "offhand", "trinket": "trinket", "amulet": "amulet", "ring": "ring_1", "ring1": "ring_1", "ring_1": "ring_1", "ring2": "ring_2", "ring_2": "ring_2", "head": "head", "helmet": "head", "gloves": "gloves", "hands": "gloves", "boots": "boots", "feet": "boots",
}
EQUIPMENT_CANONICAL_SLOTS = {"weapon", "offhand", "head", "chest", "gloves", "boots", "amulet", "ring_1", "ring_2", "trinket"}

STORY_ACTION_CUES = ("greift", "attackiert", "schlägt", "rennt", "stürmt", "weicht", "blockt", "zieht", "hebt", "untersucht", "scannt", "beobachtet", "spricht", "flüstert", "kanalisiert", "wirkt", "konzentriert", "handelt", "versucht")
STORY_EXPLORE_CUES = ("entdeckt", "erkundet", "erreicht", "betritt", "findet", "stößt auf", "stoesst auf", "gelangt", "folgt")
STORY_LEARN_CUES = ("erlernt", "erlent", "lernt", "wiedererlernt", "meistert", "beherrscht", "begreift", "erkennt", "versteht", "entwickelt", "entfesselt", "manifestiert", "entsteht", "hervorgeht", "formt sich")
CONTEXT_META_DRIFT_MARKERS = ("analyse des textes", "bereitgestellten text", "anleitung fuer den autor", "anleitung für den autor", "keine neuen story-elemente", "formatierungsvorschläge", "formatierungsvorschlaege")

MANIFESTATION_STRONG_CUES = {"manifestiert", "entfesselt", "bricht hervor", "erstmals", "zum ersten mal", "erweckt", "wird geboren"}
MANIFESTATION_EFFECT_CUES = {
    "schlägt", "schlagen", "drängt", "drängen", "fesselt", "fesseln", "blockiert", "blockieren", "verlangsamt", "verlangsamen", "durchbohrt", "durchbohren", "zerreißt", "zerreissen", "brechen", "schützt", "schützen", "versperrt", "versperren", "kontrolliert", "kontrollieren",
}
MANIFESTATION_TACTICAL_CUES = {"kampffeld", "deckung", "kontrolle", "schutz", "barriere", "angriff", "position", "ritual"}
MANIFESTATION_WORLD_REACTION_CUES = {"gegner", "weicht", "stolpert", "erschrickt", "reagiert", "umgebung", "boden", "wand"}
MANIFESTATION_COST_CUES = {"kostet", "schmerz", "belastet", "erschöpft", "vergiftung", "lebensenergie", "kontrollverlust", "risiko"}
MANIFESTATION_MOTIF_GROUPS = {
    "spore": ("pilz", "spore", "myzel", "garten", "wurzel", "ranke", "moos"),
    "light": ("licht", "strahl", "sonne", "glanz", "heilig"),
    "shadow": ("schatten", "nacht", "dunkel", "finster", "schwärze"),
    "flame": ("feuer", "flamme", "glut", "asche"),
    "frost": ("eis", "frost", "kälte", "reif"),
    "storm": ("blitz", "sturm", "donner", "wind"),
    "martial": ("schwert", "klinge", "hieb", "stoß", "parade", "speer", "lanze", "faust", "tritt", "bogen"),
}
SKILL_MANIFESTATION_VERB_BLACKLIST = {
    "kaempfen", "kämpfen", "rennen", "laufen", "springen", "ausweichen", "bewegen", "schlagen", "treffen", "manifestiert", "manifestierte", "einleiten", "einleitete", "entfesseln", "entfesselte", "erlernen", "erlernte", "weiter",
}
SKILL_MANIFESTATION_NAME_STOPWORDS = {"von", "und", "mit", "ohne", "durch", "gegen", "unter", "ueber"}
SKILL_MANIFESTATION_NAME_TOKEN_BLACKLIST = {"klasse", "class", "spieler", "character", "charakter", "npc"}

AUTO_INJURY_PATTERNS = (
    re.compile(r"\b((?:tiefer?|tiefe|tiefen|klaffender?|klaffende|blutiger?|blutige|frischer?|frische|heftiger?|heftige)\s+)?(Schnitt(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b((?:tiefer?|tiefe|tiefen|klaffender?|klaffende|blutiger?|blutige|frischer?|frische)\s+)?(Stichwunde(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b((?:tiefer?|tiefe|tiefen|blutiger?|blutige)\s+)?(Bisswunde(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b((?:schwere|heftige|frische)\s+)?(Brandwunde(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b((?:schwere|heftige)\s+)?(Prellung(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b(gebrochene[rsnm]?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b(verstauchte[rsnm]?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
)
