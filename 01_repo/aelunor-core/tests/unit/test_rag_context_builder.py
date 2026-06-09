import unittest

from app.services.rag import (
    RAGChunk,
    RetrievalResult,
    build_rag_context,
)


def _result(cid, text, score):
    chunk = RAGChunk(
        id=cid,
        document_id=cid.split("#")[0],
        campaign_id="camp-A",
        source_type="npc",
        text=text,
        contextual_header="campaign_id=camp-A | source_type=npc",
        metadata={},
        token_estimate=max(1, len(text) // 4),
        salience=0.5,
        canonical=True,
    )
    return RetrievalResult(chunk=chunk, score=score, reasons=("keywords:1",))


class ContextBuilderTests(unittest.TestCase):
    def test_no_results_returns_empty_string(self):
        self.assertEqual(build_rag_context([]), "")

    def test_block_contains_open_and_close_tags(self):
        block = build_rag_context([_result("a#chunk-0", "Aria guards.", 2.0)])
        self.assertIn("<RAG_MEMORY>", block)
        self.assertIn("</RAG_MEMORY>", block)
        self.assertTrue(block.rstrip().endswith("</RAG_MEMORY>"))

    def test_structured_state_precedence_hint_present(self):
        block = build_rag_context([_result("a#chunk-0", "Aria guards.", 2.0)])
        self.assertIn("structured", block.lower())
        self.assertIn("precedence", block.lower())

    def test_max_items_is_enforced(self):
        results = [_result(f"d{i}#chunk-0", f"fact {i}", 5.0 - i) for i in range(6)]
        block = build_rag_context(results, max_items=2)
        self.assertIn("[1]", block)
        self.assertIn("[2]", block)
        self.assertNotIn("[3]", block)

    def test_max_chars_is_enforced_without_breaking_tags(self):
        results = [_result(f"d{i}#chunk-0", "x" * 200, 5.0 - i) for i in range(6)]
        block = build_rag_context(results, max_items=6, max_chars=600)
        self.assertLessEqual(len(block), 600)
        if block:
            self.assertTrue(block.rstrip().endswith("</RAG_MEMORY>"))
            self.assertTrue(block.startswith("<RAG_MEMORY>"))

    def test_result_order_is_preserved(self):
        results = [
            _result("a#chunk-0", "first fact", 9.0),
            _result("b#chunk-0", "second fact", 8.0),
            _result("c#chunk-0", "third fact", 7.0),
        ]
        block = build_rag_context(results)
        self.assertLess(block.index("first fact"), block.index("second fact"))
        self.assertLess(block.index("second fact"), block.index("third fact"))


if __name__ == "__main__":
    unittest.main()
