import unittest

from app.services.rag import RAGChunk, RetrievalQuery, retrieve_chunks


def _chunk(cid, text, *, campaign_id="camp-A", source_type="npc",
           header="", salience=0.5, canonical=True, metadata=None):
    return RAGChunk(
        id=cid,
        document_id=cid.split("#")[0],
        campaign_id=campaign_id,
        source_type=source_type,
        text=text,
        contextual_header=header or f"campaign_id={campaign_id} | source_type={source_type}",
        metadata=metadata or {},
        token_estimate=max(1, len(text) // 4),
        salience=salience,
        canonical=canonical,
    )


class RetrievalTests(unittest.TestCase):
    def test_campaign_id_prevents_cross_campaign_leak(self):
        chunks = [
            _chunk("a#chunk-0", "Aria guards the harbor", campaign_id="camp-A"),
            _chunk("b#chunk-0", "Aria guards the harbor", campaign_id="camp-B"),
        ]
        query = RetrievalQuery(text="Aria harbor", campaign_id="camp-A")
        results = retrieve_chunks(query, chunks)
        self.assertTrue(results)
        for result in results:
            self.assertEqual(result.chunk.campaign_id, "camp-A")

    def test_entity_match_finds_chunk(self):
        chunks = [
            _chunk("a#chunk-0", "An old fisherman tells a tale."),
            _chunk("b#chunk-0", "The knight Aria Stormborn defends the gate."),
        ]
        query = RetrievalQuery(
            text="who defends",
            campaign_id="camp-A",
            entities=("Aria Stormborn",),
        )
        results = retrieve_chunks(query, chunks)
        self.assertEqual(results[0].chunk.id, "b#chunk-0")
        self.assertTrue(any("entities" in r for r in results[0].reasons))

    def test_keyword_match_finds_chunk(self):
        chunks = [
            _chunk("a#chunk-0", "The dragon sleeps in the volcano."),
            _chunk("b#chunk-0", "A merchant sells bread in town."),
        ]
        query = RetrievalQuery(text="dragon volcano", campaign_id="camp-A")
        results = retrieve_chunks(query, chunks)
        self.assertEqual(results[0].chunk.id, "a#chunk-0")

    def test_source_types_filter_is_hard(self):
        chunks = [
            _chunk("a#chunk-0", "Aria the npc", source_type="npc"),
            _chunk("b#chunk-0", "Aria the location", source_type="location"),
        ]
        query = RetrievalQuery(
            text="Aria",
            campaign_id="camp-A",
            source_types=("location",),
        )
        results = retrieve_chunks(query, chunks)
        self.assertEqual([r.chunk.source_type for r in results], ["location"])

    def test_max_results_is_enforced(self):
        chunks = [_chunk(f"d{i}#chunk-0", "dragon dragon") for i in range(10)]
        query = RetrievalQuery(text="dragon", campaign_id="camp-A", max_results=3)
        results = retrieve_chunks(query, chunks)
        self.assertEqual(len(results), 3)

    def test_equal_scores_sort_deterministically_by_chunk_id(self):
        chunks = [
            _chunk("z#chunk-0", "dragon"),
            _chunk("a#chunk-0", "dragon"),
            _chunk("m#chunk-0", "dragon"),
        ]
        query = RetrievalQuery(text="dragon", campaign_id="camp-A")
        results = retrieve_chunks(query, chunks)
        ids = [r.chunk.id for r in results]
        self.assertEqual(ids, sorted(ids))

    def test_canonical_and_salience_only_lightly_affect_score(self):
        high = _chunk("a#chunk-0", "dragon", salience=1.0, canonical=True)
        low = _chunk("b#chunk-0", "dragon", salience=0.0, canonical=False)
        query = RetrievalQuery(text="dragon", campaign_id="camp-A")
        results = retrieve_chunks(query, [low, high])
        # higher salience/canonical wins the tie...
        self.assertEqual(results[0].chunk.id, "a#chunk-0")
        # ...but only by a small, bounded margin (less than one keyword).
        self.assertLess(results[0].score - results[1].score, 1.0)

    def test_unicode_german_fantasy_keywords_match(self):
        chunks = [
            _chunk("a#chunk-0", "Der König von Élarion bewacht die Sümpfe."),
            _chunk("b#chunk-0", "Ein Händler verkauft Brot in der Stadt."),
        ]
        # Umlauts/accents must survive tokenization and match case-insensitively.
        query = RetrievalQuery(text="könig sümpfe", campaign_id="camp-A")
        results = retrieve_chunks(query, chunks)
        self.assertEqual(results[0].chunk.id, "a#chunk-0")
        self.assertTrue(any("keywords" in r for r in results[0].reasons))

    def test_unicode_fantasy_name_is_a_single_token(self):
        chunks = [
            _chunk("a#chunk-0", "Der Fürst Thalûn reist nach Élarion."),
            _chunk("b#chunk-0", "Nichts Besonderes geschieht hier."),
        ]
        query = RetrievalQuery(text="Élarion", campaign_id="camp-A")
        results = retrieve_chunks(query, chunks)
        self.assertEqual(results[0].chunk.id, "a#chunk-0")

    def test_empty_query_returns_no_wild_results(self):
        chunks = [_chunk("a#chunk-0", "dragon", salience=1.0, canonical=True)]
        query = RetrievalQuery(text="", campaign_id="camp-A")
        self.assertEqual(retrieve_chunks(query, chunks), [])

    def test_non_positive_scores_are_dropped(self):
        chunks = [_chunk("a#chunk-0", "unrelated content here")]
        query = RetrievalQuery(text="dragon", campaign_id="camp-A")
        self.assertEqual(retrieve_chunks(query, chunks), [])


if __name__ == "__main__":
    unittest.main()
