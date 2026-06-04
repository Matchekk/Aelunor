ELEMENT_TOTAL_COUNT = 12
ELEMENT_CORE_NAMES = ("Feuer", "Wasser", "Erde", "Luft", "Licht", "Schatten")
ELEMENT_RELATIONS = {"dominant", "strong", "neutral", "weak", "countered"}
ELEMENT_RELATION_SCORE = {
    "dominant": 1.35,
    "strong": 1.18,
    "neutral": 1.0,
    "weak": 0.88,
    "countered": 0.72,
}
ELEMENT_CLASS_PATH_RANKS = ("F", "C", "B", "A", "S")
ELEMENT_CLASS_PATH_MIN = 1
ELEMENT_CLASS_PATH_MAX = 3
ELEMENT_GENERATED_NAMES_FALLBACK = [
    "Resonanz",
    "Nebel",
    "Asche",
    "Klangkern",
    "Runenfluss",
    "Sternenfrost",
    "Dornengeist",
    "Leere",
    "Traum",
    "Blut",
    "Eidstahl",
    "Donnerglas",
]
ELEMENT_SIMILARITY_BLACKLIST = {
    "feuer": {"flamme", "brand", "glut", "inferno", "hitz"},
    "wasser": {"flut", "strom", "gezeiten", "regen", "welle"},
    "erde": {"stein", "fels", "boden", "lehm"},
    "luft": {"wind", "sturm", "hauch", "aetherwind"},
    "licht": {"sonne", "strahl", "heilig", "glanz"},
    "schatten": {"nacht", "dunkel", "umbra", "finsternis"},
}
