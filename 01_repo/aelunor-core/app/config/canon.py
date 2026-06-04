CANON_GATE_DOMAINS_SUPPORTED = ("progression", "items", "location", "faction", "injury", "spellschool")
CANON_GATE_ACTIVE_DOMAINS = {"progression"}

# Canon-first runtime fields. These are the primary mutable gameplay truth.
CANON_CHARACTER_FIELDS = {
    "scene_id",
    "class_current",
    "skills",
    "inventory",
    "equipment",
    "injuries",
    "scars",
    "hp_current",
    "hp_max",
    "sta_current",
    "sta_max",
    "res_current",
    "res_max",
    "carry_current",
    "carry_max",
    "level",
    "xp_total",
    "xp_current",
    "xp_to_next",
    "recent_progression_events",
    "class_path_seeds",
    "progression",
}
