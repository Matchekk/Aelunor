import ast
import unittest
from pathlib import Path

from app.services import state_engine
from app.services.progression import manifestation


CORE_ROOT = Path(__file__).resolve().parents[2]
MANIFESTATION_PATH = CORE_ROOT / "app" / "services" / "progression" / "manifestation.py"


class ProgressionManifestationServiceTests(unittest.TestCase):
    def test_manifestation_helpers_live_in_target_module(self) -> None:
        tree = ast.parse(MANIFESTATION_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        for name in (
            "infer_manifested_skill_name_with_llm",
            "infer_manifestation_progression_events_from_story",
            "manifest_skill_from_progression_event",
        ):
            self.assertIn(name, function_names)

    def test_manifestation_name_generation_uses_configured_fake_llm(self) -> None:
        calls = []

        def fake_schema(_system, user, _schema, **kwargs):
            calls.append((user, kwargs))
            return {"name": "Klingenfokus"}

        manifestation.configure(call_ollama_schema=fake_schema, ollama_temperature=0.7)

        name = manifestation.infer_manifested_skill_name_with_llm(
            motif="martial",
            actor_name="Ada",
            player_text="Ich pariere den Schlag.",
            story_text="Ada findet in der Parade einen klaren Fokus.",
            existing_names=set(),
        )

        self.assertEqual(name, "Klingenfokus")
        self.assertEqual(calls[0][1]["temperature"], 0.7)

    def test_canonicalize_manifested_skill_payload_wires_element_ports(self) -> None:
        world = {
            "elements": {"elem_fire": {"name": "Fire"}},
            "element_alias_index": {"fire": ["elem_fire"]},
        }
        character = {
            "slot_id": "slot_1",
            "bio": {"name": "Ada"},
            "class_current": {"name": "Flame Guard", "element_id": "elem_fire"},
        }

        skill = manifestation.canonicalize_manifested_skill_payload(
            raw_skill={
                "name": "Flame Focus",
                "rank": "F",
                "elements": ["Fire"],
                "element_primary": "Fire",
            },
            character=character,
            world=world,
            world_settings={},
        )

        self.assertIsNotNone(skill)
        self.assertEqual(skill["elements"], ["elem_fire"])
        self.assertEqual(skill["element_primary"], "elem_fire")
        self.assertLess(len(state_engine.runtime_symbols()), 25)


if __name__ == "__main__":
    unittest.main()
