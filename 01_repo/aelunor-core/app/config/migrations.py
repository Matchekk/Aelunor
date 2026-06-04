# Compatibility shadow fields: readable for old saves, optional writeback only.
LEGACY_SHADOW_FIELDS = {
    "resources",
    "hp",
    "stamina",
    "equip",
    "abilities",
    "potential",
}

# Migration-only inputs from old state shapes.
MIGRATION_ONLY_FIELDS = {
    "bio.party_role",
    "class_state",
    "equip",
    "abilities",
    "resources",
    "hp",
    "stamina",
    "potential",
}
