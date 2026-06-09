import copy
import unittest

from app.services.rag import (
    CampaignMemoryIndex,
    build_campaign_memory_context,
    build_campaign_memory_index,
    retrieve_campaign_memory,
)


def _fake_state():
    """Small synthetic structured campaign state (no real campaign data)."""
    return {
        "title": "Die Krone von Élarion",
        "premise": "Ein junger Fürst sucht die verlorene Krone.",
        "theme": "Verrat und Hoffnung",
        "world": {
            "name": "Élarion",
            "description": "Ein Reich der Sümpfe und alten Königswege.",
        },
        "locations": {
            "loc-harbor": {
                "name": "Hafen von Thalûn",
                "description": "Ein belebter Hafen im Norden.",
                "status": "umkämpft",
                "npcs": ["Aria"],
            }
        },
        "npcs": [
            {
                "id": "npc-aria",
                "name": "Aria Sturmgeboren",
                "role": "Wächterin",
                "description": "Verteidigt das Tor von Thalûn.",
                "location_id": "loc-harbor",
            }
        ],
        "quests": [
            {
                "id": "q-crown",
                "title": "Finde die Krone",
                "status": "open",
                "goal": "Die Krone aus den Sümpfen bergen.",
                "npcs": ["Aria Sturmgeboren"],
            }
        ],
        "timeline": [
            {
                "turn_id": "t-1",
                "summary": "Die Reise zum König beginnt im Hafen.",
            }
        ],
    }


class BuildIndexTests(unittest.TestCase):
    def test_builds_index_from_structured_state(self):
        index = build_campaign_memory_index("camp-1", _fake_state())

        self.assertIsInstance(index, CampaignMemoryIndex)
        self.assertEqual(index.campaign_id, "camp-1")
        self.assertIsInstance(index.documents, tuple)
        self.assertIsInstance(index.chunks, tuple)
        self.assertTrue(index.documents)
        self.assertTrue(index.chunks)
        source_types = {doc.source_type for doc in index.documents}
        self.assertIn("npc", source_types)
        self.assertIn("location", source_types)
        self.assertIn("quest", source_types)
        # Every chunk stays scoped to the index campaign.
        self.assertTrue(all(c.campaign_id == "camp-1" for c in index.chunks))

    def test_empty_state_builds_empty_index(self):
        for bad in ({}, None, [], "not-a-mapping", 123):
            index = build_campaign_memory_index("camp-empty", bad)
            self.assertEqual(index.documents, ())
            self.assertEqual(index.chunks, ())
            self.assertEqual(index.campaign_id, "camp-empty")

    def test_invalid_campaign_id_is_rejected(self):
        for bad in ("", "   ", None, 42):
            with self.assertRaises(ValueError):
                build_campaign_memory_index(bad, _fake_state())

    def test_index_building_does_not_mutate_input_state(self):
        state = _fake_state()
        before = copy.deepcopy(state)
        build_campaign_memory_index("camp-1", state)
        self.assertEqual(state, before)

    def test_index_is_deterministic(self):
        state = _fake_state()
        first = build_campaign_memory_index("camp-1", copy.deepcopy(state))
        second = build_campaign_memory_index("camp-1", copy.deepcopy(state))

        self.assertEqual(
            [doc.id for doc in first.documents],
            [doc.id for doc in second.documents],
        )
        self.assertEqual(
            [chunk.id for chunk in first.chunks],
            [chunk.id for chunk in second.chunks],
        )


class RetrieveTests(unittest.TestCase):
    def test_retrieve_campaign_memory_finds_relevant_npc_or_location(self):
        index = build_campaign_memory_index("camp-1", _fake_state())
        results = retrieve_campaign_memory(
            index, text="Aria", entities=("Aria Sturmgeboren",)
        )
        self.assertTrue(results)
        top_types = {r.chunk.source_type for r in results}
        self.assertTrue(top_types & {"npc", "location", "quest"})

    def test_retrieve_campaign_memory_respects_source_type_filter(self):
        index = build_campaign_memory_index("camp-1", _fake_state())
        results = retrieve_campaign_memory(
            index, text="Krone Sümpfe", source_types=("quest",)
        )
        self.assertTrue(results)
        self.assertTrue(all(r.chunk.source_type == "quest" for r in results))

    def test_retrieve_campaign_memory_does_not_cross_campaigns(self):
        state = _fake_state()
        index_a = build_campaign_memory_index("camp-a", copy.deepcopy(state))
        index_b = build_campaign_memory_index("camp-b", copy.deepcopy(state))
        self.assertTrue(index_b.chunks)  # same content exists under camp-b

        results = retrieve_campaign_memory(index_a, text="Aria Krone Hafen")
        self.assertTrue(results)
        self.assertTrue(all(r.chunk.campaign_id == "camp-a" for r in results))

    def test_retrieve_on_empty_index_returns_empty(self):
        index = build_campaign_memory_index("camp-empty", {})
        self.assertEqual(retrieve_campaign_memory(index, text="Aria"), [])

    def test_unicode_retrieval_through_index(self):
        index = build_campaign_memory_index("camp-1", _fake_state())
        for keyword in ("König", "Fürst", "Élarion", "Sümpfe"):
            with self.subTest(keyword=keyword):
                results = retrieve_campaign_memory(index, text=keyword)
                self.assertTrue(results, f"no result for {keyword!r}")


class ContextTests(unittest.TestCase):
    def test_build_campaign_memory_context_returns_bounded_block(self):
        index = build_campaign_memory_index("camp-1", _fake_state())
        block = build_campaign_memory_context(
            index, text="Aria Krone Hafen", max_items=2, max_chars=2500
        )
        self.assertTrue(block.startswith("<RAG_MEMORY>"))
        self.assertTrue(block.rstrip().endswith("</RAG_MEMORY>"))
        self.assertLessEqual(len(block), 2500)
        # Conflict note from the existing context builder stays intact.
        self.assertIn("supporting memory only", block)
        # max_items respected: entries are tagged [1], [2], ...
        self.assertNotIn("[3]", block)

    def test_context_empty_on_no_matches(self):
        index = build_campaign_memory_index("camp-empty", {})
        block = build_campaign_memory_context(index, text="Aria")
        self.assertEqual(block, "")


if __name__ == "__main__":
    unittest.main()
