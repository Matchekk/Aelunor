import unittest

from app.services.world.time import apply_world_time_advance, normalize_world_time


class WorldTimeServiceTests(unittest.TestCase):
    def test_normalize_world_time_stabilizes_minimal_meta(self) -> None:
        world_time = normalize_world_time({})

        self.assertEqual(world_time["absolute_day"], 1)
        self.assertEqual(world_time["year"], 1)
        self.assertEqual(world_time["month"], 1)
        self.assertEqual(world_time["day"], 1)
        self.assertEqual(world_time["time_of_day"], "night")

    def test_apply_world_time_advance_updates_meta_and_world_shadow(self) -> None:
        state = {"meta": {"world_time": {"absolute_day": 30, "time_of_day": "morning", "weather": "Nebel"}}}

        apply_world_time_advance(state, 2, "evening")

        self.assertEqual(state["meta"]["world_time"]["absolute_day"], 32)
        self.assertEqual(state["world"]["day"], 2)
        self.assertEqual(state["world"]["time"], "evening")
        self.assertEqual(state["world"]["weather"], "Nebel")


if __name__ == "__main__":
    unittest.main()
