import unittest

from app.services.boards import diary, revisions


class BoardDiaryServiceTests(unittest.TestCase):
    def test_diary_default_preserves_public_keys(self) -> None:
        entry = diary.default_player_diary_entry("player_1", "Aria")

        self.assertEqual(entry["player_id"], "player_1")
        self.assertEqual(entry["display_name"], "Aria")
        self.assertEqual(entry["content"], "")
        self.assertEqual(entry["updated_by"], "player_1")
        self.assertIn("updated_at", entry)

    def test_private_diary_filter_hides_comment_lines_for_non_owner(self) -> None:
        content = "sichtbar\n// privat\n  // auch privat\nnoch sichtbar"

        self.assertEqual(
            diary.filter_private_diary_content(content, viewer_is_owner=False),
            "sichtbar\nnoch sichtbar",
        )
        self.assertEqual(diary.filter_private_diary_content(content, viewer_is_owner=True), content)

    def test_log_board_revision_preserves_revision_shape(self) -> None:
        campaign = {}

        revisions.log_board_revision(
            campaign,
            board="authors_note",
            op="patch",
            updated_by="player_1",
            previous={"content": "alt"},
            current={"content": "neu"},
            item_id=None,
            make_id=lambda prefix: f"{prefix}_1",
            utc_now=lambda: "2026-01-01T00:00:00Z",
        )

        self.assertEqual(
            campaign["board_revisions"][0],
            {
                "revision_id": "boardrev_1",
                "board": "authors_note",
                "op": "patch",
                "item_id": None,
                "updated_by": "player_1",
                "updated_at": "2026-01-01T00:00:00Z",
                "previous": {"content": "alt"},
                "current": {"content": "neu"},
            },
        )


if __name__ == "__main__":
    unittest.main()
