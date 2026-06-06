import unittest

from app.services.setup import randomizer


class SetupRandomizerServiceTests(unittest.TestCase):
    def test_validate_answer_payload_delegates_existing_select_other_behavior(self) -> None:
        question = {"id": "q", "label": "Q", "type": "select", "required": True, "allow_other": True, "options": ["A"]}

        result = randomizer.validate_answer_payload(question, {"other_text": "Eigen"})

        self.assertEqual(result, {"selected": "Sonstiges", "other_text": "Eigen"})


if __name__ == "__main__":
    unittest.main()
