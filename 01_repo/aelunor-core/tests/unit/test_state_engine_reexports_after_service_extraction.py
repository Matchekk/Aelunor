import unittest

from app import main
from app.services import state_engine
from app.services.characters import derived_stats
from app.services.items import inventory
from app.services.llm import json_repair
from app.services.setup import answers, flow
from app.services.world import scene


class StateEngineServiceExtractionTests(unittest.TestCase):
    def test_public_state_engine_exports_are_intentionally_small(self) -> None:
        self.assertEqual(set(state_engine.EXPORTED_SYMBOLS), {"public_turn", "build_campaign_view"})
        self.assertIs(main.public_turn, state_engine.public_turn)
        self.assertIs(main.build_campaign_view, state_engine.build_campaign_view)

    def test_runtime_symbols_keep_internal_transition_path(self) -> None:
        runtime = state_engine.runtime_symbols()
        self.assertLessEqual(len(runtime), 200)
        self.assertNotIn("blank_character_state", runtime)
        self.assertNotIn("default_appearance_profile", runtime)
        for name in (
            "blank_patch",
            "normalize_patch_semantics",
            "ensure_item_shape",
            "normalize_equipment_update_payload",
            "current_question_id",
            "save_campaign",
        ):
            self.assertIs(runtime[name], getattr(state_engine, name))

    def test_inventory_logic_lives_in_items_module(self) -> None:
        item = {"name": "Rostiger Dolch", "tags": ["weapon"], "weight": 2}
        self.assertEqual(inventory.infer_item_slot_from_definition(item), "weapon")
        self.assertTrue(inventory.item_matches_equipment_slot(item, "weapon"))
        self.assertIs(state_engine.ensure_item_shape, inventory.ensure_item_shape)

    def test_derived_stats_logic_lives_in_character_module(self) -> None:
        character = {"attributes": {"str": 4, "dex": 3}, "inventory": {"items": []}, "equipment": {}}
        self.assertEqual(derived_stats.calculate_carry_limit(character), 18)
        self.assertEqual(derived_stats.calculate_defense(character, {}), 13)
        self.assertIs(state_engine.calculate_defense, derived_stats.calculate_defense)

    def test_setup_answer_and_flow_logic_lives_in_setup_modules(self) -> None:
        self.assertEqual(answers.extract_text_answer(["A", "B"]), "A, B")
        node = {"question_queue": ["class_start_mode", "class_seed"], "answers": {"class_start_mode": "Selbst"}}
        self.assertFalse(flow.setup_question_is_applicable(node, "class_seed"))
        self.assertIs(state_engine.current_question_id, flow.current_question_id)

    def test_scene_text_logic_lives_in_world_module(self) -> None:
        scene_id = scene.canonical_scene_id("Alter Turm")
        self.assertEqual(scene_id, "scene_alter-turm")
        self.assertFalse(scene.is_plausible_scene_name("Ort"))
        self.assertIs(state_engine.clean_scene_name, scene.clean_scene_name)

    def test_json_repair_logic_lives_in_llm_module(self) -> None:
        self.assertEqual(json_repair.first_balanced_json_object("vorher {\"ok\": true} nachher"), "{\"ok\": true}")


if __name__ == "__main__":
    unittest.main()
