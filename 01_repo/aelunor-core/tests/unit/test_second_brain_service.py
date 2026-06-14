"""Prototype tests for the Campaign Second Brain.

Exercises all four pillars offline and deterministically: persistence
(file reopen), semantic recall (hash embedder), entity graph (co-mention
expansion), and auto consolidation (chronicle + salience decay).
"""

from __future__ import annotations

import os

from app.services.second_brain import (
    DeterministicHashEmbedding,
    SecondBrain,
    SecondBrainStore,
    cosine_similarity,
)


def _state() -> dict:
    return {
        "campaign": {
            "title": "The Ashen Pact",
            "summary": "A conspiracy festers inside the royal citadel.",
            "theme": "betrayal",
        },
        "world": {
            "name": "Aelunor",
            "summary": "A fractured realm of feuding houses.",
            "region": "Northreach",
        },
        "npcs": [
            {
                "id": "npc-veyra",
                "name": "Veyra",
                "description": "A cunning spy loyal to the crown, weaving secrets.",
                "role": "spymaster",
                "location_id": "loc-citadel",
            },
            {
                "id": "npc-toren",
                "name": "Toren",
                "description": "A blacksmith in the citadel who knows Veyra well.",
                "location_id": "loc-citadel",
            },
        ],
        "locations": [
            {
                "id": "loc-citadel",
                "name": "Citadel",
                "description": "The royal citadel where Veyra operates.",
                "npcs": ["Veyra", "Toren"],
            }
        ],
        "quests": [
            {
                "id": "q-pact",
                "title": "The Ashen Pact",
                "description": "Uncover the conspiracy involving Veyra.",
                "npcs": ["Veyra"],
                "status": "active",
            }
        ],
    }


def test_ingest_persists_nodes_and_edges():
    brain = SecondBrain()
    written = brain.ingest_state("camp1", _state())
    assert written >= 5  # campaign, world, 2 npcs, location, quest

    nodes = brain.store.get_nodes("camp1")
    kinds = {n.kind for n in nodes}
    assert {"npc", "location", "quest", "world_summary"} <= kinds

    edges = brain.store.get_edges("camp1")
    # The citadel co-mentions Veyra and Toren -> at least two graph edges.
    citadel_edges = [e for e in edges if e.src_id.endswith("loc-citadel")]
    assert len(citadel_edges) >= 2


def test_persistence_survives_store_reopen(tmp_path):
    db_path = os.path.join(tmp_path, "brain.db")
    store_a = SecondBrainStore(db_path)
    SecondBrain(store=store_a).ingest_state("camp1", _state())
    store_a.close()

    store_b = SecondBrainStore(db_path)
    reopened = SecondBrain(store=store_b)
    results = reopened.recall("camp1", "spy in the citadel", entities=("Veyra",))
    assert any("veyra" in r.node.id for r in results)
    store_b.close()


def test_semantic_recall_ranks_relevant_node():
    embedder = DeterministicHashEmbedding(dim=128)
    brain = SecondBrain(embedder=embedder)
    brain.ingest_state("camp1", _state())

    results = brain.recall("camp1", "a cunning spy weaving secrets", max_results=3)
    assert results
    assert results[0].node.id.endswith("npc-veyra")
    assert any("semantic" in " ".join(r.reasons) for r in results)


def test_embedding_is_deterministic_and_normalized():
    embedder = DeterministicHashEmbedding(dim=64)
    a1 = embedder.embed(["the cunning spy"])[0]
    a2 = embedder.embed(["the cunning spy"])[0]
    assert a1 == a2  # process-stable, no PYTHONHASHSEED leakage
    assert abs(cosine_similarity(a1, a2) - 1.0) < 1e-9
    # Shared tokens -> closer than disjoint tokens.
    near = embedder.embed(["the cunning spy network"])[0]
    far = embedder.embed(["a quiet mountain lake"])[0]
    assert cosine_similarity(a1, near) > cosine_similarity(a1, far)


def test_graph_expansion_surfaces_neighbors():
    # Controlled graph so the neighbor shares NO tokens with the query: it
    # can only surface via the edge, not lexically.
    from app.services.second_brain import KnowledgeEdge, KnowledgeNode

    brain = SecondBrain()
    brain.store.upsert_nodes(
        [
            KnowledgeNode(id="c:a", campaign_id="c", kind="npc", name="Aurora",
                          text="a starlight beacon guides sailors"),
            KnowledgeNode(id="c:b", campaign_id="c", kind="location", name="Mistral",
                          text="quiet harbor docks at dawn"),
        ]
    )
    brain.store.upsert_edges(
        [KnowledgeEdge(campaign_id="c", src_id="c:a", dst_id="c:b", relation="located_at")]
    )

    results = brain.recall("c", "starlight beacon", max_results=10, graph_hops=1)
    ids = {r.node.id for r in results}
    assert "c:a" in ids  # lexical match
    assert "c:b" in ids  # neighbor with no lexical overlap -> graph only
    b_result = next(r for r in results if r.node.id == "c:b")
    assert "graph neighbor" in " ".join(b_result.reasons)


def test_consolidation_folds_old_turns_into_chronicle():
    brain = SecondBrain()
    for i in range(1, 13):
        brain.remember_turn("camp1", turn_index=i, text=f"The party did deed {i}.")

    report = brain.maintain("camp1", current_turn=13, keep_recent=4)
    assert report["consolidated"] is True

    chronicle = brain.store.get_node("camp1", report["chronicle_id"])
    assert chronicle is not None and chronicle.kind == "chronicle"
    assert "deed 1" in chronicle.text  # old turn folded in

    # Old folded turns are demoted; recent ones keep full salience.
    old = brain.store.get_node("camp1", "camp1:turn:1")
    recent = brain.store.get_node("camp1", "camp1:turn:12")
    assert old.salience < recent.salience
    assert old.metadata.get("folded") is True


def test_salience_decays_with_age():
    brain = SecondBrain()
    brain.remember_turn("camp1", turn_index=1, text="An old rumor.", salience=0.8)
    before = brain.store.get_node("camp1", "camp1:turn:1").salience

    from app.services.second_brain import decay_salience

    decay_salience(brain.store, "camp1", current_turn=25, half_life_turns=12)
    after = brain.store.get_node("camp1", "camp1:turn:1").salience
    assert after < before


def test_recall_is_campaign_scoped():
    brain = SecondBrain()
    brain.ingest_state("camp1", _state())
    brain.ingest_state("camp2", {"campaign": {"title": "Other", "summary": "Nothing here."}})

    results = brain.recall("camp2", "spy in the citadel", entities=("Veyra",))
    assert all(r.node.campaign_id == "camp2" for r in results)
    assert not any("veyra" in r.node.id for r in results)


def test_context_block_is_bounded_and_labeled():
    brain = SecondBrain()
    brain.ingest_state("camp1", _state())
    block = brain.context_block("camp1", "the spy Veyra", entities=("Veyra",), max_chars=600)
    assert block.startswith("[CAMPAIGN MEMORY]")
    assert block.endswith("[/CAMPAIGN MEMORY]")
    assert len(block) <= 600
