import unittest

from app.services.llm.json_repair import (
    extract_json_payload,
    first_balanced_json_object,
    repair_truncated_json_object,
    schema_fallback_instruction,
    strip_json_fences,
)


class LlmJsonRepairServiceTests(unittest.TestCase):
    def test_strip_json_fences_removes_outer_json_fence_only(self) -> None:
        self.assertEqual(strip_json_fences('```json\n{"ok": true}\n```'), '{"ok": true}')
        self.assertEqual(strip_json_fences('Text ```json\n{"ok": true}\n```'), 'Text ```json\n{"ok": true}\n```')

    def test_first_balanced_json_object_ignores_braces_inside_strings(self) -> None:
        text = 'vorher {"text": "Klammer } im String", "ok": true} danach {"no": true}'

        self.assertEqual(first_balanced_json_object(text), '{"text": "Klammer } im String", "ok": true}')

    def test_extract_json_payload_falls_back_to_balanced_object_in_text(self) -> None:
        self.assertEqual(extract_json_payload('Antwort: {"ok": true} Ende'), {"ok": True})

    def test_repair_truncated_json_object_uses_last_safe_point(self) -> None:
        repaired = repair_truncated_json_object('{"story": "A", "patch": {}, "requests": [], "broken": ')

        self.assertEqual(repaired, {"story": "A", "patch": {}, "requests": []})

    def test_schema_fallback_instruction_uses_turn_contract_for_turn_response_schema(self) -> None:
        instruction = schema_fallback_instruction({"required": ["story", "patch", "requests"]})

        self.assertIn("story", instruction)
        self.assertNotIn('"required"', instruction)


if __name__ == "__main__":
    unittest.main()
