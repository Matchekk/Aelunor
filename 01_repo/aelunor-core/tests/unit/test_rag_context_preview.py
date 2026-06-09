import copy
import unittest

from app.services.rag import (
    RagContextPreviewDependencies,
    preview_campaign_rag_context,
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
            {"turn_id": "t-1", "summary": "Die Reise zum König beginnt im Hafen."}
        ],
    }


def _fake_campaign(state=None):
    return {"id": "camp-1", "state": _fake_state() if state is None else state}


class _AuthRecorder:
    """Fake authenticate_player that records how it was called."""

    def __init__(self):
        self.calls = []

    def __call__(self, campaign, player_id, player_token, required=False):
        self.calls.append(
            {
                "campaign": campaign,
                "player_id": player_id,
                "player_token": player_token,
                "required": required,
            }
        )


def _deps(campaign, auth=None):
    return RagContextPreviewDependencies(
        load_campaign=lambda campaign_id: campaign,
        authenticate_player=auth or _AuthRecorder(),
    )


def _preview(campaign, *, campaign_id="camp-1", auth=None, **kwargs):
    return preview_campaign_rag_context(
        campaign_id=campaign_id,
        text=kwargs.pop("text", "Aria Krone Hafen"),
        player_id=kwargs.pop("player_id", "p-1"),
        player_token=kwargs.pop("player_token", "tok"),
        deps=_deps(campaign, auth),
        **kwargs,
    )


class PreviewTests(unittest.TestCase):
    def test_preview_builds_index_results_and_context(self):
        preview = _preview(_fake_campaign())

        self.assertEqual(preview["campaign_id"], "camp-1")
        self.assertGreater(preview["index"]["document_count"], 0)
        self.assertGreater(preview["index"]["chunk_count"], 0)
        self.assertTrue(preview["results"])
        self.assertIn("<RAG_MEMORY>", preview["context"])
        # source_types in the index summary are deterministically sorted.
        self.assertEqual(
            preview["index"]["source_types"],
            sorted(preview["index"]["source_types"]),
        )
        first = preview["results"][0]
        self.assertEqual(first["rank"], 1)
        self.assertLessEqual(len(first["text_excerpt"]), 280)

    def test_preview_authenticates_player(self):
        auth = _AuthRecorder()
        _preview(_fake_campaign(), auth=auth)

        self.assertEqual(len(auth.calls), 1)
        self.assertTrue(auth.calls[0]["required"])
        self.assertEqual(auth.calls[0]["player_id"], "p-1")
        self.assertEqual(auth.calls[0]["player_token"], "tok")

    def test_preview_does_not_mutate_campaign(self):
        campaign = _fake_campaign()
        before = copy.deepcopy(campaign)
        _preview(campaign)
        self.assertEqual(campaign, before)

    def test_preview_empty_state_returns_warnings_and_empty_context(self):
        for bad in ({}, None, [], "not-a-mapping"):
            with self.subTest(state=bad):
                preview = _preview({"id": "camp-1", "state": bad})
                self.assertEqual(preview["index"]["document_count"], 0)
                self.assertEqual(preview["index"]["chunk_count"], 0)
                self.assertEqual(preview["results"], [])
                self.assertEqual(preview["context"], "")
                self.assertTrue(preview["warnings"])
                self.assertTrue(
                    any("document" in w for w in preview["warnings"])
                )

    def test_preview_respects_source_type_filter(self):
        preview = _preview(
            _fake_campaign(), text="Krone Sümpfe", source_types=["quest"]
        )
        self.assertTrue(preview["results"])
        self.assertTrue(
            all(r["source_type"] == "quest" for r in preview["results"])
        )
        self.assertEqual(preview["query"]["source_types"], ["quest"])

    def test_preview_respects_max_results_max_items_max_chars(self):
        preview = _preview(
            _fake_campaign(),
            text="Aria Krone Hafen König Sümpfe",
            max_results=2,
            max_items=2,
            max_chars=600,
        )
        self.assertLessEqual(len(preview["results"]), 2)
        self.assertLessEqual(len(preview["context"]), 600)
        # max_items respected -> never a third tagged entry.
        self.assertNotIn("[3]", preview["context"])

    def test_preview_rejects_or_clamps_bad_limits(self):
        # Negative and oversized values are clamped, not raised.
        preview = _preview(
            _fake_campaign(),
            max_results=-5,
            max_items=999,
            max_chars=10**9,
        )
        self.assertEqual(preview["query"]["max_results"], 0)  # clamped to floor
        self.assertEqual(preview["query"]["max_items"], 10)  # clamped to ceiling
        self.assertEqual(preview["query"]["max_chars"], 8000)  # clamped to ceiling
        # max_results clamped to 0 -> no results surfaced.
        self.assertEqual(preview["results"], [])

        # Garbage (non-int) values fall back to documented defaults.
        garbage = _preview(
            _fake_campaign(), max_results="x", max_items=None, max_chars="y"
        )
        self.assertEqual(garbage["query"]["max_results"], 5)
        self.assertEqual(garbage["query"]["max_items"], 5)
        self.assertEqual(garbage["query"]["max_chars"], 2500)

    def test_preview_max_chars_too_small_warns(self):
        preview = _preview(_fake_campaign(), max_chars=5)
        self.assertEqual(preview["context"], "")
        self.assertTrue(preview["results"])  # results exist...
        self.assertTrue(
            any("max_chars" in w for w in preview["warnings"])
        )

    def test_preview_unicode_query(self):
        for keyword in ("König", "Fürst", "Élarion", "Sümpfe"):
            with self.subTest(keyword=keyword):
                preview = _preview(_fake_campaign(), text=keyword)
                self.assertTrue(
                    preview["results"], f"no result for {keyword!r}"
                )

    def test_preview_no_cross_campaign_leak(self):
        preview = _preview(_fake_campaign(), campaign_id="camp-a")
        self.assertEqual(preview["campaign_id"], "camp-a")
        self.assertTrue(preview["results"])
        for result in preview["results"]:
            # chunk/document ids are namespaced by the requested campaign id.
            self.assertTrue(result["document_id"].startswith("camp-a:"))
            self.assertTrue(result["chunk_id"].startswith("camp-a:"))

    def test_preview_entities_normalized_in_echo(self):
        preview = _preview(
            _fake_campaign(),
            entities=["  Aria Sturmgeboren  ", "", "Aria Sturmgeboren"],
        )
        # Trimmed, de-duplicated, empties dropped.
        self.assertEqual(preview["query"]["entities"], ["Aria Sturmgeboren"])


if __name__ == "__main__":
    unittest.main()
