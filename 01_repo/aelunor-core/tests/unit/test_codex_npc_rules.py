import app.main  # noqa: F401
from app.services.canon.npc_extractor import apply_npc_upserts, best_matching_npc_id
from app.services.world.codex import default_beast_codex_entry, default_race_codex_entry, normalize_codex_entry_stable
from app.services.world.npc import npc_id_from_name, normalize_npc_alias


def test_npc_alias_normalization_currently_strips_articles_and_titles() -> None:
    assert normalize_npc_alias("die Lady Mara") == "mara"
    assert npc_id_from_name("Lady Mara") == "npc_lady_mara"


def test_duplicate_npc_name_or_alias_currently_resolves_to_existing_id() -> None:
    state = {
        "npc_codex": {"npc_mara": {"npc_id": "npc_mara", "name": "Lady Mara"}},
        "npc_alias_index": {"mara": "npc_mara"},
    }

    assert best_matching_npc_id(state, "Mara") == "npc_mara"
    assert best_matching_npc_id(state, "Lady Mara") == "npc_mara"


def test_apply_npc_upserts_currently_merges_duplicate_alias_into_existing_entry() -> None:
    campaign = {"state": {}, "claims": {}, "players": {}}
    state = {
        "characters": {},
        "npc_codex": {"npc_mara": {"npc_id": "npc_mara", "name": "Lady Mara", "mention_count": 1}},
        "npc_alias_index": {"mara": "npc_mara"},
        "world": {"settings": {"resource_name": "Aether"}},
    }

    touched = apply_npc_upserts(
        campaign,
        state,
        [{"name": "Mara", "goal": "Findet die Ruine", "relevance_score": 3}],
        source_text="Mara sucht die Ruine.",
        turn_number=5,
    )

    assert touched == ["npc_mara"]
    assert list(state["npc_codex"]) == ["npc_mara"]
    assert state["npc_codex"]["npc_mara"]["goal"] == "Findet die Ruine"
    assert state["npc_alias_index"]["mara"] == "npc_mara"


def test_race_and_beast_codex_default_entries_have_stable_keys() -> None:
    assert default_race_codex_entry("race_ember").keys() == {
        "discovered",
        "knowledge_level",
        "known_blocks",
        "known_facts",
        "encounter_count",
        "first_seen_turn",
        "last_updated_turn",
        "known_individuals",
    }
    assert default_beast_codex_entry("beast_wolf").keys() == {
        "discovered",
        "knowledge_level",
        "known_blocks",
        "known_facts",
        "encounter_count",
        "first_seen_turn",
        "last_updated_turn",
        "defeated_count",
        "observed_abilities",
    }


def test_codex_knowledge_level_is_currently_clamped_to_configured_range() -> None:
    race = normalize_codex_entry_stable({"id": "race_ember", "knowledge_level": 999}, kind="race")
    beast = normalize_codex_entry_stable({"id": "beast_wolf", "knowledge_level": -3}, kind="beast")

    assert race["knowledge_level"] == 4
    assert beast["knowledge_level"] == 0
