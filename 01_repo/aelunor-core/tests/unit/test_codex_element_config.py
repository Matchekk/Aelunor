import unittest

from app import main
from app.config import codex as codex_config
from app.config import elements as element_config
from app.services import state_engine
from app.services.world import codex


class CodexElementConfigWiringTests(unittest.TestCase):
    def test_main_reexports_codex_config_names(self) -> None:
        names = (
            "CODEX_KNOWLEDGE_LEVEL_MIN",
            "CODEX_KNOWLEDGE_LEVEL_MAX",
            "CODEX_KIND_RACE",
            "CODEX_KIND_BEAST",
            "RACE_CODEX_BLOCK_ORDER",
            "BEAST_CODEX_BLOCK_ORDER",
            "RACE_BLOCKS_BY_LEVEL",
            "BEAST_BLOCKS_BY_LEVEL",
            "CODEX_DEFAULT_META",
            "CODEX_RACE_TRIGGER_LORE",
            "CODEX_RACE_TRIGGER_CONTACT",
            "CODEX_BEAST_TRIGGER_COMBAT",
            "CODEX_BEAST_TRIGGER_DEFEAT",
            "CODEX_BEAST_TRIGGER_ABILITY",
            "NPC_STATUS_ALLOWED",
        )

        for name in names:
            self.assertIs(getattr(main, name), getattr(codex_config, name), name)

    def test_main_reexports_element_config_names(self) -> None:
        names = (
            "ELEMENT_TOTAL_COUNT",
            "ELEMENT_CORE_NAMES",
            "ELEMENT_RELATIONS",
            "ELEMENT_RELATION_SCORE",
            "ELEMENT_CLASS_PATH_RANKS",
            "ELEMENT_CLASS_PATH_MIN",
            "ELEMENT_CLASS_PATH_MAX",
            "ELEMENT_GENERATED_NAMES_FALLBACK",
            "ELEMENT_SIMILARITY_BLACKLIST",
        )

        for name in names:
            self.assertIs(getattr(main, name), getattr(element_config, name), name)

    def test_configured_state_engine_keeps_codex_and_element_globals_available(self) -> None:
        for name in (
            "CODEX_KIND_RACE",
            "CODEX_KIND_BEAST",
            "RACE_BLOCKS_BY_LEVEL",
            "BEAST_BLOCKS_BY_LEVEL",
            "CODEX_DEFAULT_META",
            "NPC_STATUS_ALLOWED",
            "ELEMENT_CORE_NAMES",
            "ELEMENT_RELATIONS",
            "ELEMENT_RELATION_SCORE",
            "ELEMENT_CLASS_PATH_RANKS",
            "ELEMENT_TOTAL_COUNT",
        ):
            self.assertIs(getattr(state_engine, name), getattr(main, name), name)

    def test_codex_runtime_dependencies_keep_config_values(self) -> None:
        deps = codex._codex_deps()

        self.assertEqual(deps.codex_kind_race, "race")
        self.assertEqual(deps.codex_kind_beast, "beast")
        self.assertEqual(deps.codex_knowledge_level_min, 0)
        self.assertEqual(deps.codex_knowledge_level_max, 4)
        self.assertIs(deps.race_codex_block_order, main.RACE_CODEX_BLOCK_ORDER)
        self.assertIs(deps.beast_codex_block_order, main.BEAST_CODEX_BLOCK_ORDER)
        self.assertIs(deps.race_blocks_by_level, main.RACE_BLOCKS_BY_LEVEL)
        self.assertIs(deps.beast_blocks_by_level, main.BEAST_BLOCKS_BY_LEVEL)
        self.assertEqual(deps.element_core_names, main.ELEMENT_CORE_NAMES)
        self.assertEqual(deps.npc_status_allowed, main.NPC_STATUS_ALLOWED)

    def test_element_config_keeps_current_relation_and_path_values(self) -> None:
        self.assertEqual(state_engine.normalize_element_relation("DOMINANT"), "dominant")
        self.assertEqual(main.ELEMENT_RELATION_SCORE["countered"], 0.72)
        self.assertEqual(main.ELEMENT_CLASS_PATH_RANKS, ("F", "C", "B", "A", "S"))


if __name__ == "__main__":
    unittest.main()
