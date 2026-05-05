import copy

from app import main
from app.services.world import codex


def _npc_id_from_name(name: str) -> str:
    slug = codex.normalize_codex_alias_text(name).replace(" ", "_")
    return f"npc_{slug[:48]}"


def _normalize_npc_alias(name: str) -> str:
    return codex.normalize_codex_alias_text(name)


def setup_module() -> None:
    assert main.app is not None
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
    assert codex.normalize_codex_alias_text("Der_die Das eine Aether_Quelle") == "aether quelle"


def test_build_entity_alias_variants_documents_parenthetical_and_short_aliases() -> None:
    variants = codex.build_entity_alias_variants(
        "Orden der Schatten-Wölfe (Rudel)",
        ["Nacht_Jäger"],
    )

    assert variants[:5] == [
        "orden schatten woelfe rudel",
        "rudel",
        "rudels",
        "rudele",
        "rudelen",
    ]
    assert "orden schatten woelfe" in variants
    assert "schatten woelfe" in variants
    assert "woelf" in variants
    assert "nacht jaeger" in variants
    assert "jaeger" in variants


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


def test_normalize_codex_entry_stable_handles_beasts_and_invalid_raw_data() -> None:
    invalid = codex.normalize_codex_entry_stable("not-a-dict", kind="beast")
    beast = codex.normalize_codex_entry_stable(
        {
            "knowledge_level": -7,
            "known_blocks": ["behavior", "identity", "identity", "unknown"],
            "defeated_count": -4,
            "observed_abilities": ["Biss", " biss ", "Sprung"],
            "first_seen_turn": 5,
            "last_updated_turn": 2,
        },
        kind="beast",
    )

    assert invalid["knowledge_level"] == 0
    assert invalid["known_blocks"] == []
    assert beast["knowledge_level"] == 0
    assert beast["known_blocks"] == ["identity", "behavior"]
    assert beast["defeated_count"] == 0
    assert set(beast["observed_abilities"]) == {"Biss", "biss", "Sprung"}
    assert beast["first_seen_turn"] == 5
    assert beast["last_updated_turn"] == 5


def test_codex_blocks_for_level_clamps_to_configured_bounds() -> None:
    assert codex.codex_blocks_for_level("race", 99) == ["identity", "society", "culture", "lore"]
    assert codex.codex_blocks_for_level("beast", -1) == []


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
    assert aliases["race_alias_index"]["volk"] == ["race_alpha", "race_beta"]


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


def test_resolve_codex_entity_ids_uses_exact_names_without_overriding_aliases() -> None:
    result = codex.resolve_codex_entity_ids(
        "Alpha Volk trifft Schattenwolf.",
        {"alpha volk": ["race_alias"]},
        {"alpha volk": ["race_exact"], "schattenwolf": ["beast_wolf"]},
    )

    assert result["matched"] == ["beast_wolf", "race_alias"]
    assert result["matched_aliases"] == {
        "beast_wolf": ["schattenwolf"],
        "race_alias": ["alpha volk"],
    }


def test_normalize_world_codex_structures_cleans_world_and_codex_state() -> None:
    state = {
        "setup": {"world": {"summary": {"tone": "test"}}},
        "world": {
            "races": {
                "z": {"name": "Zeta Volk", "aliases": ["Wandler"]},
                "bad": {"aliases": ["NoName"]},
                "a": {"name": "Alpha Volk", "aliases": ["Erste"]},
            },
            "beast_types": {
                "wolf": {"name": "Schatten-Wolf", "aliases": ["Nachtjäger"], "danger_rating": 99},
                "bad": "not-a-profile",
            },
            "elements": {
                "fire": {"name": "Feuer", "aliases": ["Flamme"]},
                "void": {"name": "Leere", "aliases": ["Nichts"]},
            },
            "element_relations": {"fire": {"void": "dominant"}},
        },
        "codex": {
            "meta": {"custom": "yes"},
            "races": {"a": {"knowledge_level": 99, "known_blocks": ["culture", "identity"]}},
            "beasts": {
                "wolf": {
                    "knowledge_level": -1,
                    "defeated_count": 2,
                    "observed_abilities": ["Biss", "Biss"],
                }
            },
        },
    }

    codex.normalize_world_codex_structures(state)

    assert list(state["world"]["races"].keys()) == ["a", "z"]
    assert list(state["world"]["beast_types"].keys()) == ["wolf"]
    assert list(state["world"]["elements"].keys()) == ["fire", "void"]
    assert state["world"]["beast_types"]["wolf"]["danger_rating"] == 20
    assert state["world"]["elements"]["fire"]["origin"] == "core"
    assert state["world"]["elements"]["void"]["origin"] == "generated"
    assert state["world"]["race_alias_index"]["volk"] == ["a", "z"]
    assert state["world"]["beast_alias_index"]["nachtjaeger"] == ["wolf"]
    assert state["world"]["element_alias_index"]["flamme"] == ["fire"]
    assert state["world"]["element_relations"]["fire"]["void"] == "dominant"
    assert sorted(state["world"]["element_class_paths"].keys()) == ["fire", "void"]
    assert state["codex"]["meta"]["custom"] == "yes"
    assert state["codex"]["meta"]["version"] == 1
    assert state["codex"]["races"]["a"]["knowledge_level"] == 5
    assert state["codex"]["races"]["a"]["known_blocks"] == ["identity", "culture"]
    assert state["codex"]["beasts"]["wolf"]["knowledge_level"] == 0
    assert state["codex"]["beasts"]["wolf"]["observed_abilities"] == ["Biss"]


def test_default_npc_entry_documents_core_defaults() -> None:
    entry = codex.default_npc_entry("npc_mira", " Mira ")

    assert entry["npc_id"] == "npc_mira"
    assert entry["name"] == "Mira"
    assert entry["race"] == "Unbekannt"
    assert entry["status"] == "active"
    assert entry["tags"] == ["npc", "story_relevant"]
    assert entry["xp_to_next"] == 120
    assert entry["hp_current"] == 10
    assert entry["skills"] == {}


def test_normalize_npc_entry_preserves_current_clamping_and_skill_behavior() -> None:
    entry = codex.normalize_npc_entry(
        {
            "name": "  Mira  ",
            "status": "invalid_status",
            "level": 9999,
            "mention_count": 0,
            "relevance_score": -5,
            "history_notes": [f"n{i}" for i in range(25)],
            "hp_max": -1,
            "hp_current": 99,
            "sta_max": -1,
            "res_max": -1,
            "class_current": {"name": "Schattenbinder", "rank": "A", "level": 2},
            "skills": {"s1": {"name": "Klingen Tanz", "level": 3, "rank": "B"}},
            "progression": {"resource_name": "Mana Dunkel Extra Lang 123456789"},
        },
        fallback_npc_id="npc_fallback",
    )

    assert entry["npc_id"] == "npc_fallback"
    assert entry["name"] == "Mira"
    assert entry["status"] == "active"
    assert entry["level"] == 999
    assert entry["mention_count"] == 1
    assert entry["relevance_score"] == 0
    assert entry["history_notes"] == [f"n{i}" for i in range(5, 25)]
    assert entry["hp_max"] == 1
    assert entry["hp_current"] == 1
    assert entry["sta_max"] == 0
    assert entry["res_max"] == 0
    assert entry["class_current"]["class_id"] == "class_schattenbinder"
    assert entry["class_current"]["class_rank"] == "A"
    assert list(entry["skills"].keys()) == ["skill_klingen_tanz"]
    assert entry["skills"]["skill_klingen_tanz"]["rank"] == "B"


def test_normalize_npc_entry_rejects_missing_names_and_generates_ids() -> None:
    assert codex.normalize_npc_entry({"race": "Mensch"}) is None

    entry = codex.normalize_npc_entry({"name": "Alra"})

    assert entry["npc_id"] == "npc_alra"
    assert entry["name"] == "Alra"


def test_normalize_npc_codex_state_rebuilds_entries_and_aliases() -> None:
    campaign = {
        "state": {
            "world": {
                "elements": {"fire": {"name": "Feuer"}},
                "element_alias_index": {"feuer": ["fire"]},
            },
            "npc_codex": {
                "keep": {
                    "name": "Alra",
                    "npc_id": "npc_alra",
                    "element_affinities": ["Feuer", "unknown"],
                    "skills": {
                        "flame": {
                            "name": "Flammen Ruf",
                            "elements": ["Feuer"],
                            "element_primary": "Feuer",
                        }
                    },
                },
                "drop": {"race": "NoName"},
            },
            "npc_alias_index": {"Alra Alias": "npc_alra", "bad": "missing"},
        }
    }

    codex.normalize_npc_codex_state(campaign)

    state = campaign["state"]
    assert list(state["npc_codex"].keys()) == ["npc_alra"]
    assert state["npc_alias_index"] == {"alra": "npc_alra", "alra alias": "npc_alra"}
    entry = state["npc_codex"]["npc_alra"]
    assert entry["element_affinities"] == ["fire"]
    assert list(entry["skills"].keys()) == ["skill_flammen_ruf"]
    assert entry["skills"]["skill_flammen_ruf"]["elements"] == ["fire"]
    assert entry["skills"]["skill_flammen_ruf"]["element_primary"] == "fire"


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
