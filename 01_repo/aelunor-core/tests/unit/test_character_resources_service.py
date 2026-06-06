import unittest

from app.services.characters import resources


class CharacterResourcesServiceTests(unittest.TestCase):
    def test_resource_delta_payload_zeroes_every_resource_key(self) -> None:
        payload = resources.resource_delta_payload()
        self.assertTrue(payload)
        self.assertTrue(all(value == 0 for value in payload.values()))

    def test_canonical_resource_deltas_from_update_maps_known_fields(self) -> None:
        deltas = resources.canonical_resource_deltas_from_update(
            {"hp_delta": -3, "stamina_delta": 2, "resources_delta": {"aether": 5, "carry": 4}}
        )
        self.assertEqual(deltas["hp_current"], -3)
        self.assertEqual(deltas["sta_current"], 2)
        self.assertEqual(deltas["res_current"], 5)
        self.assertEqual(deltas["carry_current"], 4)

    def test_canonical_resources_set_from_payload_clamps_current_to_max(self) -> None:
        canonical = resources.canonical_resources_set_from_payload(
            {"hp": {"current": 99, "max": 20}},
            character={},
        )
        self.assertEqual(canonical["hp_max"], 20)
        self.assertEqual(canonical["hp_current"], 20)

    def test_canonical_resources_set_from_payload_ignores_non_dict(self) -> None:
        self.assertEqual(resources.canonical_resources_set_from_payload(None, character={}), {})


if __name__ == "__main__":
    unittest.main()
