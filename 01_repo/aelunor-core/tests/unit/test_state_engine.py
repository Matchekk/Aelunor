import copy
import unittest

from app.services import state_engine


class StateEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        state_engine.configure(
            {
                "SLOT_PREFIX": "slot_",
                "deep_copy": copy.deepcopy,
            }
        )

    def test_slot_helpers_roundtrip(self) -> None:
        self.assertEqual(state_engine.slot_id(3), "slot_3")
        self.assertEqual(state_engine.slot_index("slot_3"), 3)
        self.assertTrue(state_engine.is_slot_id("slot_3"))
        self.assertEqual(state_engine.slot_index("invalid"), 9999)
        self.assertFalse(state_engine.is_slot_id("invalid"))

    def test_normalize_patch_semantics_scene_set_alias(self) -> None:
        patch = {
            "characters": {
                "slot_1": {
                    "scene_set": "scene_forest",
                    "bio_set": {"name": "Mati"},
                }
            }
        }
        normalized = state_engine.normalize_patch_semantics(patch)
        char_patch = normalized["characters"]["slot_1"]
        self.assertEqual(char_patch["scene_id"], "scene_forest")
        self.assertNotIn("scene_set", char_patch)

    def test_merge_patch_payloads_combines_lists_and_maps(self) -> None:
        first = {
            "characters": {"slot_1": {"inventory_add": ["item_a"]}},
            "items_new": {"item_a": {"name": "A"}},
            "events_add": ["e1"],
        }
        second = {
            "characters": {"slot_1": {"inventory_add": ["item_b"]}},
            "items_new": {"item_b": {"name": "B"}},
            "events_add": ["e2"],
        }
        merged = state_engine.merge_patch_payloads(first, second)
        self.assertIn("item_a", merged["items_new"])
        self.assertIn("item_b", merged["items_new"])
        self.assertEqual(merged["events_add"], ["e1", "e2"])
        self.assertEqual(merged["characters"]["slot_1"]["inventory_add"], ["item_a", "item_b"])

    def test_setup_phase_display_distinguishes_ready_and_active(self) -> None:
        self.assertEqual(state_engine.setup_phase_display("world_setup"), "Weltaufbau")
        self.assertEqual(state_engine.setup_phase_display("character_setup_open"), "Charakterwerdung")
        self.assertEqual(state_engine.setup_phase_display("ready_to_start"), "Bereit zum Start")
        self.assertEqual(state_engine.setup_phase_display("active"), "Aktive Spielphase")


if __name__ == "__main__":
    unittest.main()
