import unittest

from app.services.rag import RAGDocument, chunk_document


def _doc(text, **kwargs):
    base = dict(
        id="doc-1",
        campaign_id="camp-A",
        source_type="npc",
        text=text,
        metadata={"title": "Aria", "location": "Harbor"},
    )
    base.update(kwargs)
    return RAGDocument(**base)


class ChunkingTests(unittest.TestCase):
    def test_small_document_yields_single_chunk(self):
        chunks = chunk_document(_doc("A short fact about Aria."))
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "A short fact about Aria.")

    def test_header_contains_campaign_and_source_type(self):
        header = chunk_document(_doc("Some text."))[0].contextual_header
        self.assertIn("campaign_id=camp-A", header)
        self.assertIn("source_type=npc", header)
        self.assertIn("title=Aria", header)
        self.assertIn("location=Harbor", header)

    def test_long_text_splits_into_multiple_chunks(self):
        text = " ".join(f"word{i}" for i in range(400))
        chunks = chunk_document(_doc(text), max_chars=200, overlap_chars=20)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            # max_chars is approximate but never wildly exceeded.
            self.assertLessEqual(len(chunk.text), 200)

    def test_chunk_ids_are_deterministic(self):
        text = " ".join(f"word{i}" for i in range(400))
        first = chunk_document(_doc(text), max_chars=200, overlap_chars=20)
        second = chunk_document(_doc(text), max_chars=200, overlap_chars=20)
        self.assertEqual([c.id for c in first], [c.id for c in second])
        self.assertEqual(first[0].id, "doc-1#chunk-0")
        self.assertEqual(first[1].id, "doc-1#chunk-1")

    def test_empty_and_whitespace_text_do_not_crash(self):
        self.assertEqual(chunk_document(_doc("")), [])
        self.assertEqual(chunk_document(_doc("   \n\t  ")), [])

    def test_token_estimate_is_positive(self):
        chunk = chunk_document(_doc("A short fact about Aria."))[0]
        self.assertGreaterEqual(chunk.token_estimate, 1)


if __name__ == "__main__":
    unittest.main()
