import unittest

from app import main
from app.services import state_engine
from app.services.campaigns import lifecycle, party, views


class DependencyFactoriesCampaignPortsTests(unittest.TestCase):
    def test_campaign_ports_are_bound_to_extracted_services(self) -> None:
        setup_deps = main.setup_service_dependencies()
        self.assertIs(setup_deps.authenticate_player, lifecycle.authenticate_player)
        self.assertIs(setup_deps.require_host, lifecycle.require_host)
        self.assertIs(setup_deps.is_host, views.is_host)
        self.assertIs(setup_deps.campaign_slots, party.campaign_slots)

        claim_deps = main.claim_service_dependencies()
        self.assertIs(claim_deps.authenticate_player, lifecycle.authenticate_player)
        self.assertIs(claim_deps.player_claim, party.player_claim)
        self.assertIs(claim_deps.is_host, views.is_host)

        campaign_deps = main.campaign_service_dependencies()
        self.assertIs(campaign_deps.new_player, lifecycle.new_player)
        self.assertIs(campaign_deps.authenticate_player, lifecycle.authenticate_player)
        self.assertIs(campaign_deps.require_host, lifecycle.require_host)
        self.assertIs(campaign_deps.intro_state, lifecycle.intro_state)
        self.assertIs(campaign_deps.active_turns, views.active_turns)
        self.assertIs(campaign_deps.can_start_adventure, lifecycle.can_start_adventure)

        boards_deps = main.boards_service_dependencies()
        self.assertIs(boards_deps.default_player_diary_entry, party.default_player_diary_entry)

    def test_campaign_ports_no_longer_require_runtime_bridge_entries(self) -> None:
        runtime = state_engine.runtime_symbols()
        removed_campaign_symbols = {
            "authenticate_player",
            "build_party_overview",
            "campaign_path",
            "can_start_adventure",
            "create_campaign_record",
            "default_player_diary_entry",
            "ensure_campaign_storage",
            "find_campaign_by_join_code",
            "intro_state",
            "is_host",
            "load_campaign",
            "new_player",
            "player_claim",
            "require_claim",
            "require_host",
            "save_campaign",
        }
        self.assertTrue(removed_campaign_symbols.isdisjoint(runtime))

        self.assertNotIn("load_campaign", main.state_engine_runtime())
        self.assertTrue(callable(main.setup_service_dependencies().load_campaign))
        self.assertTrue(callable(main.campaign_service_dependencies().create_campaign_record))


if __name__ == "__main__":
    unittest.main()
