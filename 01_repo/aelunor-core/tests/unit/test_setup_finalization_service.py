import unittest
from typing import Any, Dict

from app.services import state_engine
from app.services.setup import summaries


class SetupFinalizationServiceTests(unittest.TestCase):
    def test_apply_character_summary_to_state_sets_core_bio_and_class(self) -> None:
        campaign: Dict[str, Any] = {
            "setup": {
                "characters": {
                    "slot_1": {
                        "summary": {
                            "display_name": "Aria",
                            "gender": "weiblich",
                            "age_bucket": "Jung (20-25)",
                            "class_start_mode": "selbst",
                            "class_custom_name": "Klingenwacht",
                            "class_custom_tags": ["blade"],
                        }
                    }
                }
            },
            "state": {
                "meta": {"world_time": {"absolute_day": 7}},
                "world": {"settings": {"resource_name": "Mana"}},
                "characters": {"slot_1": {"progression": {}, "res_current": 3, "res_max": 4}},
                "items": {},
            },
        }
        deps = summaries.CharacterSummaryStateDependencies(
            clean_creator_item_name=lambda value: str(value or "").strip(),
            derive_age_stage=lambda _age: "young",
            enable_legacy_shadow_writeback=False,
            generate_character_attribute_weights=lambda *_args: {"weights": {"str": 120}, "source": "test"},
            infer_age_years=lambda _value: 22,
            level_one_attribute_budget=lambda _campaign: 10,
            level_one_attribute_cap=lambda _campaign: 10,
            level_one_attributes_from_weights=lambda _campaign, _weights: {"str": 10},
            normalize_attribute_weight_pool=lambda value, **_kwargs: dict(value or {}),
            normalize_class_current=lambda value: dict(value or {}) if value else None,
            normalize_creator_item_list=lambda value: list(value or []),
            normalize_world_time=lambda meta: {"absolute_day": int(((meta or {}).get("world_time") or {}).get("absolute_day", 1))},
            normalized_eval_text=lambda value: str(value or "").strip().lower(),
            reconcile_canonical_resources=lambda *_args: None,
            reconcile_creator_inventory_items=lambda *_args: None,
            rebuild_character_derived=lambda *_args: None,
            refresh_skill_progression=lambda *_args: None,
            strip_legacy_shadow_fields=lambda *_args: None,
            sync_scars_into_appearance=lambda *_args: None,
            write_legacy_shadow_fields=lambda *_args: None,
        )

        summaries.apply_character_summary_to_state(campaign, "slot_1", deps=deps)

        character = campaign["state"]["characters"]["slot_1"]
        self.assertEqual(character["bio"]["name"], "Aria")
        self.assertEqual(character["progression"]["resource_name"], "Mana")
        self.assertEqual(character["class_current"]["name"], "Klingenwacht")
        self.assertEqual(len(state_engine.runtime_symbols()), 42)


if __name__ == "__main__":
    unittest.main()
