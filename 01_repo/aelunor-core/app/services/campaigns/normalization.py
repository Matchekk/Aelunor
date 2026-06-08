from dataclasses import dataclass
from typing import Any, Callable, Dict

from app.catalogs.runtime_catalogs import CATALOG_VERSION
from app.config.codex import CODEX_DEFAULT_META
from app.config.feature_flags import ENABLE_HEURISTIC_NORMALIZE_BACKFILL
from app.config.runtime import PHASES
from app.services.campaigns import lifecycle, party, views
from app.services.world.world_bible import normalize_world_bible


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class CampaignNormalizationPorts:
    deep_copy: Callable[[Any], Any]
    initial_state: CampaignState
    is_legacy_campaign: Callable[[CampaignState], bool]
    migrate_campaign_to_dynamic_slots: Callable[[CampaignState], None]
    default_intro_state: Callable[[], CampaignState]
    default_setup: Callable[[], CampaignState]
    default_character_setup_node: Callable[[], CampaignState]
    build_world_question_queue: Callable[[], Any]
    build_character_question_queue: Callable[[], Any]
    normalize_world_time: Callable[[CampaignState], CampaignState]
    normalize_world_settings: Callable[[Any], CampaignState]
    normalize_meta_timing: Callable[[CampaignState], CampaignState]
    normalize_combat_meta: Callable[[CampaignState], CampaignState]
    normalize_attribute_influence_meta: Callable[[CampaignState], CampaignState]
    normalize_extraction_quarantine_meta: Callable[[CampaignState], CampaignState]
    normalize_meta_migrations: Callable[[CampaignState], CampaignState]
    active_pacing_profile: Callable[[CampaignState], CampaignState]
    milestone_state_for_turn: Callable[[int, CampaignState], CampaignState]
    normalize_world_codex_structures: Callable[[CampaignState], None]
    normalize_npc_codex_state: Callable[[CampaignState], None]
    seed_npc_codex_from_story_cards: Callable[[CampaignState], None]
    ensure_world_codex_from_setup: Callable[[CampaignState, CampaignState], None]
    blank_character_state: Callable[[str], CampaignState]
    normalize_character_state: Callable[..., CampaignState]
    normalize_element_id_list: Callable[[Any, CampaignState], Any]
    normalize_class_current: Callable[[Any], Any]
    resolve_class_element_id: Callable[[CampaignState, CampaignState], Any]
    resource_name_for_character: Callable[[CampaignState, CampaignState], str]
    normalize_dynamic_skill_state: Callable[..., CampaignState]
    normalize_skill_elements_for_world: Callable[[CampaignState, CampaignState], CampaignState]
    reconcile_creator_inventory_items: Callable[[CampaignState, CampaignState], None]
    initialize_dynamic_slots: Callable[[CampaignState, int], None]
    run_legacy_normalize_backfill: Callable[[CampaignState], None]
    compute_turn_budget_estimates: Callable[[CampaignState], CampaignState]


def _ensure_dict(container: Dict[str, Any], key: str, default_factory: Callable[[], Any]) -> Any:
    """Replace a missing or non-dict (e.g. JSON ``null``) container with a default.

    ``dict.setdefault`` only fills missing keys; a key explicitly set to ``null``
    in a hand-edited / truncated save survives as ``None`` and then crashes the
    load path on ``.setdefault``/``.get``. This coerces such values to a usable
    dict so corrupt saves degrade gracefully instead of raising a 500."""
    value = container.get(key)
    if not isinstance(value, dict):
        value = default_factory()
        container[key] = value
    return value


def normalize_campaign(campaign: CampaignState, *, ports: CampaignNormalizationPorts) -> CampaignState:
    _ensure_dict(campaign, "state", lambda: ports.deep_copy(ports.initial_state))
    _ensure_dict(campaign, "players", dict)
    _ensure_dict(campaign, "boards", lifecycle.default_boards)
    campaign.setdefault("claims", {})
    campaign.setdefault("turns", [])
    campaign.setdefault("board_revisions", [])
    campaign.setdefault("legacy_migration", None)

    if ports.is_legacy_campaign(campaign):
        ports.migrate_campaign_to_dynamic_slots(campaign)

    state = campaign["state"]
    _ensure_dict(state, "meta", lambda: ports.deep_copy(ports.initial_state["meta"]))
    if state["meta"].get("phase") == "character_creation":
        state["meta"]["phase"] = "character_setup_open"
    if state["meta"].get("phase") == "character_setup":
        state["meta"]["phase"] = "character_setup_open"
    if state["meta"].get("phase") == "adventure":
        state["meta"]["phase"] = "active"
    if state["meta"].get("phase") not in PHASES:
        state["meta"]["phase"] = "lobby"
    existing_intro_state = state["meta"].get("intro_state")
    if isinstance(existing_intro_state, dict):
        normalized_intro_state = ports.default_intro_state()
        normalized_intro_state.update(existing_intro_state)
        existing_intro_state.clear()
        existing_intro_state.update(normalized_intro_state)
        state["meta"]["intro_state"] = existing_intro_state
    else:
        state["meta"]["intro_state"] = ports.default_intro_state()
    state["meta"]["world_time"] = ports.normalize_world_time(state["meta"])
    _ensure_dict(state, "world", lambda: ports.deep_copy(ports.initial_state["world"]))
    state["world"].setdefault("settings", {})
    state["world"]["settings"] = ports.normalize_world_settings(state["world"].get("settings") or {})
    state["world"].setdefault("elements", {})
    state["world"].setdefault("element_relations", {})
    state["world"].setdefault("element_alias_index", {})
    state["world"].setdefault("element_class_paths", {})
    state["world"]["bible"] = normalize_world_bible(state["world"].get("bible"), world=state["world"])
    state["world"]["day"] = state["meta"]["world_time"]["day"]
    state["world"]["time"] = state["meta"]["world_time"]["time_of_day"]
    state["world"]["weather"] = state["meta"]["world_time"]["weather"]
    ports.normalize_meta_timing(state["meta"])
    ports.normalize_combat_meta(state["meta"])
    ports.normalize_attribute_influence_meta(state["meta"])
    ports.normalize_extraction_quarantine_meta(state["meta"])
    migrations_meta = ports.normalize_meta_migrations(state["meta"])
    milestone_defaults = ports.milestone_state_for_turn(
        int(state["meta"].get("turn", 0) or 0),
        ports.active_pacing_profile(state),
    )
    state["meta"]["last_milestone_turn"] = int(state["meta"].get("last_milestone_turn", milestone_defaults["last"]) or milestone_defaults["last"])
    state["meta"]["next_milestone_turn"] = int(state["meta"].get("next_milestone_turn", milestone_defaults["next"]) or milestone_defaults["next"])
    state.setdefault("map", {"nodes": {}, "edges": []})
    state.setdefault("plotpoints", [])
    state.setdefault("scenes", {})
    state.setdefault("items", {})
    state.setdefault("characters", {})
    state.setdefault("recent_story", [])
    state.setdefault("events", [])
    state.setdefault("codex", {"races": {}, "beasts": {}, "meta": ports.deep_copy(CODEX_DEFAULT_META)})
    state.setdefault("npc_codex", {})
    state.setdefault("npc_alias_index", {})
    ports.normalize_world_codex_structures(state)

    boards = campaign["boards"]
    boards.setdefault("plot_essentials", lifecycle.default_boards()["plot_essentials"])
    boards.setdefault("authors_note", lifecycle.default_boards()["authors_note"])
    boards.setdefault("story_cards", [])
    boards.setdefault("world_info", [])
    boards.setdefault("memory_summary", lifecycle.default_boards()["memory_summary"])
    _ensure_dict(boards, "player_diaries", dict)
    for player_id, player in (campaign.get("players") or {}).items():
        player = player if isinstance(player, dict) else {}
        boards["player_diaries"].setdefault(
            player_id,
            party.default_player_diary_entry(player_id, player.get("display_name", "")),
        )
        boards["player_diaries"][player_id]["display_name"] = player.get("display_name", "")

    ports.normalize_npc_codex_state(campaign)
    if not bool(migrations_meta.get("npc_codex_seeded_from_story_cards")):
        if not state.get("npc_codex"):
            ports.seed_npc_codex_from_story_cards(campaign)
            ports.normalize_npc_codex_state(campaign)
        migrations_meta["npc_codex_seeded_from_story_cards"] = True

    setup = _ensure_dict(campaign, "setup", ports.default_setup)
    if setup.get("version") != 4:
        fallback = ports.default_setup()
        fallback["world"].update(setup.get("world") if isinstance(setup.get("world"), dict) else {})
        fallback["characters"].update(setup.get("characters") if isinstance(setup.get("characters"), dict) else {})
        setup = campaign["setup"] = fallback
    setup.setdefault("engine", {})
    setup["engine"]["world_catalog_version"] = CATALOG_VERSION
    setup["engine"]["character_catalog_version"] = CATALOG_VERSION
    _ensure_dict(setup, "world", lambda: ports.default_setup()["world"])
    setup["world"]["question_queue"] = ports.build_world_question_queue()
    setup["world"].setdefault("answers", {})
    setup["world"].setdefault("summary", {})
    setup["world"].setdefault("raw_transcript", [])
    setup["world"].setdefault("question_runtime", {})
    setup.setdefault("characters", {})
    if setup["world"].get("completed"):
        ports.ensure_world_codex_from_setup(state, setup["world"].get("summary") or {})
        state["world"]["bible"] = normalize_world_bible(
            state["world"].get("bible"),
            setup_answers=setup["world"].get("summary") or setup["world"].get("answers") or {},
            world=state["world"],
        )

    effective_world_time = ports.normalize_world_time(state["meta"])
    for slot_name in party.campaign_slots(campaign):
        state["characters"].setdefault(slot_name, ports.blank_character_state(slot_name))
        setup["characters"].setdefault(slot_name, ports.default_character_setup_node())
        character_setup_node = setup["characters"].get(slot_name) or {}
        state["characters"][slot_name] = ports.normalize_character_state(
            state["characters"][slot_name],
            slot_name,
            state.get("items", {}),
            effective_world_time,
            world_bible=(state.get("world") or {}).get("bible"),
            setup_answers=character_setup_node.get("summary") or character_setup_node.get("answers") or {},
        )
        character = state["characters"][slot_name]
        for field in ("element_affinities", "element_resistances", "element_weaknesses"):
            character[field] = ports.normalize_element_id_list(character.get(field) or [], state.get("world") or {})
        normalized_class = ports.normalize_class_current(character.get("class_current"))
        if normalized_class:
            resolved_class_element = ports.resolve_class_element_id(normalized_class, state.get("world") or {})
            if resolved_class_element:
                normalized_class["element_id"] = resolved_class_element
                normalized_class["element_tags"] = list(dict.fromkeys([*(normalized_class.get("element_tags") or []), resolved_class_element]))
            character["class_current"] = ports.normalize_class_current(normalized_class)
        resource_name = ports.resource_name_for_character(character, state["world"].get("settings") or {})
        normalized_skills: Dict[str, Dict[str, Any]] = {}
        for skill_id, skill_value in ((character.get("skills") or {}).items()):
            normalized_skill = ports.normalize_dynamic_skill_state(skill_value, skill_id=str(skill_id), resource_name=resource_name)
            normalized_skill = ports.normalize_skill_elements_for_world(normalized_skill, state.get("world") or {})
            normalized_skills[normalized_skill["id"]] = normalized_skill
        character["skills"] = normalized_skills
        ports.reconcile_creator_inventory_items(state, character)
        setup["characters"][slot_name]["question_queue"] = ports.build_character_question_queue()
        setup["characters"][slot_name].setdefault("answers", {})
        setup["characters"][slot_name].setdefault("summary", {})
        setup["characters"][slot_name].setdefault("raw_transcript", [])
        setup["characters"][slot_name].setdefault("question_runtime", {})
        campaign["claims"].setdefault(slot_name, None)

    if setup["world"].get("completed") and not party.campaign_slots(campaign):
        ports.initialize_dynamic_slots(campaign, int(setup["world"].get("summary", {}).get("player_count") or 1))

    if campaign.get("turns") and any(turn.get("status") == "active" for turn in campaign.get("turns", [])):
        state["meta"]["phase"] = "active"
        if state["meta"]["intro_state"].get("status") in ("idle", "pending", "failed"):
            state["meta"]["intro_state"]["status"] = "generated"
        if not state["meta"]["intro_state"].get("generated_turn_id"):
            state["meta"]["intro_state"]["generated_turn_id"] = views.active_turns(campaign)[0]["turn_id"]
    elif setup["world"].get("completed"):
        state["meta"]["phase"] = "ready_to_start" if lifecycle.can_start_adventure(campaign) else "character_setup_open"
    elif state["meta"].get("phase") not in {"lobby", "world_setup"}:
        state["meta"]["phase"] = "world_setup"

    if ENABLE_HEURISTIC_NORMALIZE_BACKFILL:
        ports.run_legacy_normalize_backfill(campaign)
    ports.compute_turn_budget_estimates(state)
    return campaign
