from typing import Dict

WORLD_SETUP_CHAPTERS = {
    "foundations": {
        "label": "Grundton der Welt",
        "questions": {"theme", "tone", "difficulty", "player_count", "campaign_length"},
    },
    "laws_power": {
        "label": "Mächte und Gesetze",
        "questions": {"resource_name", "ruleset", "attribute_range", "world_laws", "outcome_model"},
    },
    "danger_conflict": {
        "label": "Gefahren und Konflikte",
        "questions": {"death_possible", "monsters_density", "resource_scarcity", "healing_frequency", "central_conflict", "factions", "taboos"},
    },
    "structure": {
        "label": "Weltstruktur",
        "questions": {"world_structure"},
    },
}

CHAR_SETUP_CHAPTERS = {
    "identity": {
        "label": "Identität",
        "questions": {"char_name", "char_gender", "char_age"},
    },
    "origin": {
        "label": "Herkunft",
        "questions": {"earth_life", "personality_tags"},
    },
    "class_affinity": {
        "label": "Begabung und Klasse",
        "questions": {"strength", "weakness", "class_start_mode", "class_seed", "class_custom_name", "class_custom_description", "class_custom_tags"},
    },
    "drive": {
        "label": "Motivation und Einstieg",
        "questions": {"current_focus", "first_goal", "isekai_price", "earth_items", "signature_item"},
    },
}

LEGACY_SELECT_ALIASES: Dict[str, Dict[str, str]] = {
    "theme": {
        "grimdark": "Grimdark",
        "dark fantasy": "Dark Fantasy",
        "high fantasy": "High Fantasy",
    },
    "tone": {
        "ernst": "Ernst",
        "hart": "Hart",
        "hoffnungsvoll": "Hoffnungsvoll",
        "zerrissen": "Zerrissen",
    },
    "monsters_density": {
        "regelmaessig": "Regelmäßig",
        "regelmassig": "Regelmäßig",
    },
    "char_gender": {
        "maennlich": "Männlich",
        "male": "Männlich",
        "weiblich": "Weiblich",
        "female": "Weiblich",
        "nichtbinaer": "Nichtbinär",
        "nicht-binaer": "Nichtbinär",
        "nonbinary": "Nichtbinär",
    },
    "class_start_mode": {
        "ki jetzt": "KI jetzt",
        "selbst": "Ich definiere selbst",
        "story": "Erst in der Story",
    },
}
