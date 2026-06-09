import unittest
import json

from app.services import memory


class MemoryServiceTests(unittest.TestCase):
    def _ports(self, turns):
        return memory.MemoryPorts(
            active_turns=lambda _campaign: turns,
            active_party=lambda _campaign: ["slot_1"],
            display_name_for_slot=lambda _campaign, slot: {"slot_1": "Aria"}.get(slot, slot),
            is_slot_id=lambda value: str(value).startswith("slot_"),
            blank_patch=lambda: {"characters": {}, "map_add_nodes": [], "events_add": []},
            canonical_scene_id=lambda name: "scene_" + name.lower().replace(" ", "_"),
            derive_scene_name=lambda _campaign, _slot: "Start",
            extract_descriptive_scene_name=lambda _text: "",
            extract_scene_candidates=lambda _text, _actor: [],
            is_generic_scene_identifier=lambda _scene_id, _name: False,
            normalized_eval_text=lambda text: text.lower(),
            compact_conditions=lambda character: character.get("conditions", [])[:3],
            normalize_character_state=lambda character, *_args: character,
            world_attribute_scale=lambda _campaign: {"label": "1-10", "min": 1, "max": 10},
            element_core_names=["Feuer", "Wasser"],
            build_world_element_summary=lambda _state, **_kwargs: [],
            build_race_codex_summary=lambda _state, **_kwargs: [],
            build_beast_codex_summary=lambda _state, **_kwargs: [],
            build_npc_codex_summary=lambda _state, **_kwargs: [],
            call_ollama_text=lambda *_args: (_ for _ in ()).throw(RuntimeError("offline")),
            utc_now=lambda: "2026-01-01T00:00:00Z",
        )

    def test_recent_story_keeps_last_twenty_active_gm_entries(self) -> None:
        turns = [{"gm_text_display": f"GM {index}"} for index in range(25)]
        campaign = {"state": {}}

        memory.remember_recent_story(campaign, ports=self._ports(turns))

        self.assertEqual(campaign["state"]["recent_story"][0], "GM 5")
        self.assertEqual(campaign["state"]["recent_story"][-1], "GM 24")
        self.assertEqual(len(campaign["state"]["recent_story"]), 20)

    def test_rebuild_memory_summary_preserves_fallback_shape(self) -> None:
        turns = [
            {
                "turn_number": 3,
                "actor": "slot_1",
                "action_type": "do",
                "input_text_display": "Ich lausche.",
                "gm_text_display": "Der Wind antwortet.",
            }
        ]
        campaign = {
            "campaign_meta": {"title": "Aelunor"},
            "setup": {"world": {"summary": {"tone": "leise"}}},
            "state": {"characters": {"slot_1": {"scene_id": "scene_1", "conditions": ["wach"]}}},
            "boards": {},
        }

        memory.rebuild_memory_summary(campaign, ports=self._ports(turns))

        summary = campaign["boards"]["memory_summary"]
        self.assertEqual(summary["updated_through_turn"], 3)
        self.assertEqual(summary["updated_at"], "2026-01-01T00:00:00Z")
        self.assertIn("Letzte Aktion von Aria", summary["content"])

    def test_build_context_packet_compacts_large_world_and_setup_runtime_blocks(self) -> None:
        campaign = {
            "setup": {
                "version": 4,
                "world": {
                    "completed": True,
                    "question_queue": ["theme"] * 100,
                    "answers": {"theme": {"selected": "Dark"}},
                    "summary": {"premise": "Dunkel"},
                    "question_runtime": {"theme": {"ai_copy": "x" * 10000}},
                },
                "characters": {
                    "slot_1": {
                        "completed": True,
                        "question_queue": ["char_name"] * 100,
                        "answers": {"char_name": "Aria"},
                        "summary": {"display_name": "Aria"},
                        "question_runtime": {"char_name": {"ai_copy": "x" * 10000}},
                    }
                },
            },
            "boards": {"memory_summary": {"content": "Noch nichts."}},
            "turns": [],
            "claims": {"slot_1": "player_1"},
        }
        state = {
            "meta": {"turn": 1},
            "world": {
                "settings": {"resource_name": "Flux"},
                "notes": "Start",
                "bible": {"identity": {"world_name": "Myrufluxis"}, "metaphysics": {"rules": ["x" * 5000]}},
                "elements": {f"element_{idx}": {"name": "x" * 2000} for idx in range(50)},
                "element_class_paths": {f"path_{idx}": {"description": "x" * 2000} for idx in range(50)},
            },
            "map": {},
            "characters": {"slot_1": {"bio": {"name": "Aria"}, "living_profile": {"sensory": "x" * 5000}}},
            "items": {},
        }

        packet = json.loads(memory.build_context_packet(campaign, state, "slot_1", "do", ports=self._ports([])))

        self.assertNotIn("question_queue", packet["setup"]["world"])
        self.assertNotIn("question_runtime", packet["setup"]["characters"]["slot_1"])
        self.assertNotIn("elements", packet["world"])
        self.assertNotIn("element_class_paths", packet["world"])
        self.assertNotIn("bible", packet["world"])
        self.assertNotIn("living_profile", packet["characters"]["slot_1"])
        self.assertEqual(packet["world_elements"], {})


if __name__ == "__main__":
    unittest.main()
