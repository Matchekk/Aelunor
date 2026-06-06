import unittest

from app.services.boards import public


class BoardPublicServiceTests(unittest.TestCase):
    def test_public_boards_filters_only_other_players_private_diary_lines(self) -> None:
        campaign = {
            "boards": {
                "authors_note": {"content": "note"},
                "player_diaries": {
                    "player_1": {"content": "me\n// mine"},
                    "player_2": {"content": "them\n// hidden"},
                },
            }
        }

        result = public.build_public_boards(campaign, "player_1")

        self.assertEqual(result["player_diaries"]["player_1"]["content"], "me\n// mine")
        self.assertEqual(result["player_diaries"]["player_2"]["content"], "them")
        self.assertEqual(campaign["boards"]["player_diaries"]["player_2"]["content"], "them\n// hidden")


if __name__ == "__main__":
    unittest.main()
