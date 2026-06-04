import unittest

from app.services import state_engine
from app.services.state.dependencies import StateEngineDependencies


class StateDependencyTests(unittest.TestCase):
    def test_dependency_model_can_be_created_and_merged(self) -> None:
        first = StateEngineDependencies(campaign_repository=object())
        second = StateEngineDependencies(ollama_adapter=object(), logger=object())
        merged = first.merged(second)

        self.assertIs(merged.campaign_repository, first.campaign_repository)
        self.assertIs(merged.ollama_adapter, second.ollama_adapter)
        self.assertIs(merged.logger, second.logger)

    def test_legacy_mapping_configures_explicit_ports_only(self) -> None:
        repository = object()
        adapter = object()
        logger = object()

        deps = StateEngineDependencies.from_mapping(
            {
                "CAMPAIGN_REPOSITORY": repository,
                "OLLAMA_ADAPTER": adapter,
                "LOGGER": logger,
                "UNRELATED": object(),
            }
        )

        self.assertIs(deps.campaign_repository, repository)
        self.assertIs(deps.ollama_adapter, adapter)
        self.assertIs(deps.logger, logger)
        self.assertFalse(hasattr(deps, "UNRELATED"))

    def test_state_engine_configure_accepts_dependency_object(self) -> None:
        state_engine.configure_dependencies(StateEngineDependencies())
        self.assertTrue(getattr(state_engine, "_CONFIGURED", False))


if __name__ == "__main__":
    unittest.main()
