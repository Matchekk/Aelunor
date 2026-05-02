import copy

from app.services.world import codex


def _npc_id_from_name(name: str) -> str:
    slug = codex.normalize_codex_alias_text(name).replace(" ", "_")
    return f"npc_{slug[:48]}"


def _normalize_npc_alias(name: str) -> str:
    return codex.normalize_codex_alias_text(name)


def setup_module() -> None:
    codex.configure(
        {
            "BEAST_BLOCKS_BY_LEVEL": {
                1: ["identity"],
                2: ["appearance", "habitat"],
                3: ["behavior"],
            },
            "BEAST_CODEX_BLOCK_ORDER": [
                "identity",
                "appearance",
                "habitat",
                "behavior",
            ],
            "CODEX_KIND_BEAST": "beast",
            "CODEX_KIND_RACE": "race",
            "CODEX_KNOWLEDGE_LEVEL_MAX": 5,
            "CODEX_KNOWLEDGE_LEVEL_MIN": 0,
            "RACE_BLOCKS_BY_LEVEL": {
                1: ["identity"],
                2: ["society", "culture"],
                3: ["lore"],
            },
            "RACE_CODEX_BLOCK_ORDER": [
                "identity",
                "society",
                "culture",
                "lore",
            ],
            "deep_copy": copy.deepcopy,
            "normalize_npc_alias": _normalize_npc_alias,
            "npc_id_from_name": _npc_id_from_name,
        }
    )


def test_normalize_codex_alias_text_removes_articles_and_umlauts() -> None:
    assert codex.normalize_codex_alias_text("Die Schatten-Wölfe!") == "schatten woelfe"
    assert codex.normalize_codex_alias_text("  Ein  Äther-Ort  ") == "aether ort"


def test_stable_sorted_unique_strings_strips_dedupes_and_sorts_by_alias() -> None:
    values = ["Zorn", " äther ", "Berg", "Zorn", "", None]

    assert codex.stable_sorted_unique_strings(values) == ["äther", "Berg", "Zorn"]


def test_normalize_codex_entry_stable_clamps_and_preserves_block_order() -> None:
    entry = codex.normalize_codex_entry_stable(
        {
            "discovered": True,
            "knowledge_level": 99,
            "known_blocks": ["lore", "identity", "identity", "unknown", "culture"],
            "known_facts": ["Fakt A", " fakt a ", "Fakt B"],
            "known_individuals": ["B", "C", "A"],
            "encounter_count": -2,
            "first_seen_turn": -1,
            "last_updated_turn": 3,
        },
        kind="race",
    )

    assert entry["discovered"] is True
    assert entry["knowledge_level"] == 5
    assert entry["known_blocks"] == ["identity", "culture", "lore"]
    assert entry["known_facts"] == ["Fakt A", "Fakt B"]
    assert entry["known_individuals"] == ["A", "B", "C"]
    assert entry["encounter_count"] == 0
    assert entry["first_seen_turn"] == 0
    assert entry["last_updated_turn"] == 3


def test_world_alias_and_exact_name_indexes_are_stable_and_normalized() -> None:
    world = {
        "races": {
            "race_beta": {"name": "Beta Volk", "aliases": ["Wandler"]},
            "race_alpha": {"name": "Alpha Volk", "aliases": ["Wandler"]},
        },
        "beast_types": {
            "beast_wolf": {"name": "Schattenwölfe (Rudel)", "aliases": ["Nachtjäger"]},
        },
    }

    aliases = codex.build_world_alias_indexes(world)
    exact_names = codex.build_world_exact_name_index(world)

    assert aliases["race_alias_index"]["wandler"] == ["race_alpha", "race_beta"]
    assert aliases["beast_alias_index"]["schattenwoelfe"] == ["beast_wolf"]
    assert aliases["beast_alias_index"]["nachtjaeger"] == ["beast_wolf"]
    assert exact_names["race_names"]["alpha volk"] == ["race_alpha"]
    assert exact_names["beast_names"]["schattenwoelfe rudel"] == ["beast_wolf"]


def test_resolve_codex_entity_ids_reports_matches_and_ambiguity() -> None:
    result = codex.resolve_codex_entity_ids(
        "Ein Wandler sieht die Schattenwölfe.",
        {
            "wandler": ["race_beta", "race_alpha"],
            "schattenwoelfe": ["beast_wolf"],
        },
    )

    assert result["matched"] == ["beast_wolf"]
    assert result["matched_aliases"] == {"beast_wolf": ["schattenwoelfe"]}
    assert result["ambiguous"] == [
        {"alias": "wandler", "entity_ids": ["race_alpha", "race_beta"]}
    ]


def test_seed_npc_codex_from_story_cards_is_idempotent() -> None:
    campaign = {
        "boards": {
            "story_cards": [
                {"kind": "npc", "title": "Mira (Händlerin)", "content": "Kennt die alte Straße."},
                {"kind": "note", "title": "Kein NPC", "content": "Ignorieren."},
            ]
        },
        "state": {"meta": {"turn": 7}},
    }

    codex.seed_npc_codex_from_story_cards(campaign)
    codex.seed_npc_codex_from_story_cards(campaign)

    npc_codex = campaign["state"]["npc_codex"]
    alias_index = campaign["state"]["npc_alias_index"]
    assert list(npc_codex.keys()) == ["npc_mira_haendlerin"]
    entry = npc_codex["npc_mira_haendlerin"]
    assert entry["name"] == "Mira (Händlerin)"
    assert entry["first_seen_turn"] == 7
    assert entry["last_seen_turn"] == 7
    assert entry["backstory_short"] == "Kennt die alte Straße."
    assert alias_index["mira haendlerin"] == "npc_mira_haendlerin"
