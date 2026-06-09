import copy
import unittest

from app.services.rag import (
    RetrievalQuery,
    build_rag_document_id,
    build_rag_documents_from_campaign_state,
    chunk_document,
    retrieve_chunks,
)


def _by_source(documents):
    grouped = {}
    for doc in documents:
        grouped.setdefault(doc.source_type, []).append(doc)
    return grouped


def _rich_state():
    return {
        "title": "Die Krone von Élarion",
        "premise": "Ein junger Fürst sucht die verlorene Krone.",
        "theme": "Verrat und Hoffnung",
        "world": {
            "name": "Élarion",
            "description": "Ein Reich aus Sümpfen und alten Königswegen.",
            "lore": ["Der erste König fiel im Nebel.", "Die Sümpfe verschlucken Geheimnisse."],
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
            },
            {"id": "npc-empty"},
        ],
        "quests": [
            {
                "id": "q-crown",
                "title": "Finde die Krone",
                "status": "open",
                "goal": "Die Krone aus den Sümpfen bergen.",
                "npcs": ["Aria Sturmgeboren"],
                "locations": ["Hafen von Thalûn"],
            }
        ],
        "timeline": [
            {
                "turn_id": "t-1",
                "index": 1,
                "summary": "Die Gruppe erreicht den Hafen.",
                "events": ["Ankunft", "Treffen mit Aria"],
                "location_id": "loc-harbor",
            }
        ],
    }


class CampaignSummaryMappingTests(unittest.TestCase):
    def test_maps_campaign_summary_document(self):
        state = {
            "title": "Die Krone von Élarion",
            "summary": "Eine Chronik über Verrat.",
            "premise": "Ein Fürst sucht die Krone.",
            "theme": "Hoffnung",
        }
        docs = build_rag_documents_from_campaign_state("camp-A", state)
        summaries = _by_source(docs).get("campaign_summary", [])
        self.assertEqual(len(summaries), 1)
        doc = summaries[0]
        self.assertEqual(doc.campaign_id, "camp-A")
        self.assertIn("Eine Chronik über Verrat.", doc.text)
        self.assertEqual(doc.metadata.get("title"), "Die Krone von Élarion")
        self.assertEqual(doc.metadata.get("name"), "Die Krone von Élarion")


class SectionMappingTests(unittest.TestCase):
    def test_maps_locations_npcs_quests_and_turn_summaries(self):
        docs = build_rag_documents_from_campaign_state("camp-A", _rich_state())
        grouped = _by_source(docs)
        for source_type in ("location", "npc", "quest", "turn_summary"):
            self.assertIn(source_type, grouped, f"missing {source_type}")

        location = grouped["location"][0]
        self.assertEqual(location.metadata.get("location_id"), "loc-harbor")
        self.assertIn("Aria", location.metadata.get("entities", []))

        npc = grouped["npc"][0]
        self.assertEqual(npc.metadata.get("npc_id"), "npc-aria")
        self.assertEqual(npc.metadata.get("location_id"), "loc-harbor")

        quest = grouped["quest"][0]
        self.assertEqual(quest.metadata.get("quest_id"), "q-crown")
        self.assertEqual(quest.metadata.get("status"), "open")

        turn = grouped["turn_summary"][0]
        self.assertEqual(turn.metadata.get("turn_id"), "t-1")
        self.assertEqual(turn.metadata.get("index"), 1)
        self.assertTrue(turn.id.endswith("turn_summary:t-1"))

    def test_ignores_missing_or_malformed_sections(self):
        state = {
            "title": "Nur ein Titel",
            "premise": "Etwas Inhalt.",
            "world": None,
            "locations": None,
            "npcs": [None, "garbage", 42, {}],
            "quests": "not-a-list",
            "timeline": {"bad": ["raw", "log"]},
        }
        docs = build_rag_documents_from_campaign_state("camp-A", state)
        # Only the campaign summary should survive; nothing crashes.
        self.assertEqual({d.source_type for d in docs}, {"campaign_summary"})
        for doc in docs:
            self.assertTrue(doc.text.strip())

    def test_empty_state_yields_no_documents(self):
        self.assertEqual(build_rag_documents_from_campaign_state("camp-A", {}), [])
        self.assertEqual(build_rag_documents_from_campaign_state("camp-A", None), [])


class DeterminismTests(unittest.TestCase):
    def test_does_not_mutate_input_state(self):
        state = _rich_state()
        before = copy.deepcopy(state)
        build_rag_documents_from_campaign_state("camp-A", state)
        self.assertEqual(state, before)

    def test_document_ids_are_deterministic(self):
        state = _rich_state()
        first = build_rag_documents_from_campaign_state("camp-A", state)
        second = build_rag_documents_from_campaign_state("camp-A", state)
        self.assertEqual([d.id for d in first], [d.id for d in second])
        self.assertTrue(all(d.id for d in first))

    def test_document_id_helper_is_stable(self):
        self.assertEqual(
            build_rag_document_id("camp-A", "npc", "Aria Sturmgeboren"),
            build_rag_document_id("camp-A", "npc", "Aria Sturmgeboren"),
        )
        self.assertEqual(
            build_rag_document_id("camp-A", "npc", "Aria Sturmgeboren"),
            "camp-A:npc:aria-sturmgeboren",
        )


class TextBudgetTests(unittest.TestCase):
    def test_limits_large_text_fields(self):
        state = {
            "title": "Lang",
            "summary": "A" * 9000,
            "premise": "B" * 9000,
        }
        docs = build_rag_documents_from_campaign_state("camp-A", state, max_text_chars=500)
        self.assertTrue(docs)
        for doc in docs:
            self.assertLessEqual(len(doc.text), 500)

    def test_unicode_content_is_preserved(self):
        state = {
            "title": "König und Fürst",
            "premise": "Élarion und die Sümpfe bleiben erhalten.",
        }
        docs = build_rag_documents_from_campaign_state("camp-A", state)
        text = docs[0].text
        for token in ("König", "Fürst", "Élarion", "Sümpfe"):
            self.assertIn(token, text)


class IntegrationTests(unittest.TestCase):
    def test_mapper_documents_work_with_existing_chunking_and_retrieval(self):
        docs = build_rag_documents_from_campaign_state("camp-A", _rich_state())
        chunks = [chunk for doc in docs for chunk in chunk_document(doc)]
        self.assertTrue(chunks)

        npc_query = RetrievalQuery(
            text="wer verteidigt das Tor",
            campaign_id="camp-A",
            entities=("Aria Sturmgeboren",),
        )
        npc_results = retrieve_chunks(npc_query, chunks)
        self.assertTrue(npc_results)
        self.assertEqual(npc_results[0].chunk.source_type, "npc")

        location_query = RetrievalQuery(text="Hafen Thalûn", campaign_id="camp-A")
        location_results = retrieve_chunks(location_query, chunks)
        self.assertTrue(location_results)
        self.assertTrue(
            any(r.chunk.source_type == "location" for r in location_results)
        )


if __name__ == "__main__":
    unittest.main()
