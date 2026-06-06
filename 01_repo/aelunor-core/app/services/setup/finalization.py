from typing import Any, Dict, Optional

from app.helpers import setup_helpers


def finalize_world_setup(campaign: Dict[str, Any], player_id: Optional[str], *, deps: setup_helpers.SetupHelperDependencies) -> None:
    setup_helpers.finalize_world_setup(campaign, player_id, deps=deps)


def finalize_character_setup(
    campaign: Dict[str, Any],
    slot_name: str,
    *,
    deps: setup_helpers.SetupHelperDependencies,
) -> Optional[Dict[str, Any]]:
    return setup_helpers.finalize_character_setup(campaign, slot_name, deps=deps)
