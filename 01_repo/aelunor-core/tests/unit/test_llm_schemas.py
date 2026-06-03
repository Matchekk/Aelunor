import copy
import unittest

from app.schemas.llm import (
    build_canon_extractor_schema,
    build_progression_extractor_schema,
    extend_turn_patch_schema,
)


class LlmSchemaTests(unittest.TestCase):
    def _minimal_response_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "patch": {"type": "object", "properties": {}},
            },
            "$defs": {
                "char_patch": {
                    "type": "object",
                    "properties": {
                        "skills_set": {
                            "type": "object",
                            "additionalProperties": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "object", "properties": {"name": {"type": "string"}}},
                                ]
                            },
                        },
                        "skills_delta": {"type": "object"},
                        "class_set": {"type": "object", "properties": {}},
                    },
                }
            },
        }

    def test_extend_turn_patch_schema_preserves_input_and_adds_contract_fields(self) -> None:
        original = self._minimal_response_schema()
        snapshot = copy.deepcopy(original)

        extended = extend_turn_patch_schema(original)

        self.assertEqual(original, snapshot)
        char_patch = extended["$defs"]["char_patch"]["properties"]
        self.assertIn("scene_set", char_patch)
        self.assertIn("progression_events", char_patch)
        self.assertIn("anyOf", char_patch["skills_delta"]["additionalProperties"])
        skill_object = char_patch["skills_set"]["additionalProperties"]["anyOf"][1]
        self.assertIn("effect_summary", skill_object["properties"])
        self.assertIn("element_id", char_patch["class_set"]["properties"])

    def test_extractor_schema_builders_deep_copy_response_patch_contract(self) -> None:
        response_schema = extend_turn_patch_schema(self._minimal_response_schema())

        canon_schema = build_canon_extractor_schema(response_schema)
        progression_schema = build_progression_extractor_schema(response_schema)

        canon_schema["properties"]["patch"]["properties"]["local_only"] = {"type": "string"}
        self.assertNotIn("local_only", response_schema["properties"]["patch"]["properties"])
        character_patch = progression_schema["properties"]["character_patch"]["properties"]
        self.assertIn("skills_set", character_patch)
        self.assertIn("progression_events", character_patch)
        self.assertEqual(progression_schema["required"], ["confidence", "character_patch"])


if __name__ == "__main__":
    unittest.main()
