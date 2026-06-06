from types import SimpleNamespace
from typing import Any, Callable, Mapping

from app.services.campaigns import lifecycle as campaign_lifecycle
from app.services.campaigns import party as campaign_party
from app.services.campaigns import persistence as campaign_persistence
from app.services.campaigns import views as campaign_views
from app.services.boards import diary as board_diary
from app.services.boards import revisions as board_revisions
from app.services.sheets import character as character_sheet_service
from app.services.sheets import npc as npc_sheet_service
from app.services.state_basics import make_join_code


def _state_engine_symbol(runtime: Mapping[str, Any], name: str) -> Any:
    if name in runtime:
        return runtime[name]
    from app.services import state_engine

    return getattr(state_engine, name)


def _campaign_repository(runtime: Mapping[str, Any]) -> Any:
    return campaign_persistence.resolve_campaign_repository(
        configured=runtime.get("CAMPAIGN_REPOSITORY"),
        data_dir=runtime["DATA_DIR"],
        campaigns_dir=runtime["CAMPAIGNS_DIR"],
    )


def _campaign_path(runtime: Mapping[str, Any]) -> Callable[[str], str]:
    repository = _campaign_repository(runtime)
    return lambda campaign_id: campaign_persistence.campaign_path(repository, campaign_id)


def _list_campaign_ids(runtime: Mapping[str, Any]) -> Callable[[], Any]:
    repository = _campaign_repository(runtime)
    return lambda: campaign_persistence.list_campaign_ids(repository)


def _load_campaign(runtime: Mapping[str, Any]) -> Callable[[str], Any]:
    repository = _campaign_repository(runtime)
    ports = campaign_persistence.CampaignLoadPorts(
        repository=repository,
        normalize_campaign=_state_engine_symbol(runtime, "normalize_campaign"),
    )
    return lambda campaign_id: campaign_persistence.load_campaign(campaign_id, ports=ports)


def _live_state_service(runtime: Mapping[str, Any], explicit: Any = None) -> Any:
    return explicit or runtime["live_state_service"]


def _save_campaign(runtime: Mapping[str, Any], *, live_state_service: Any = None) -> Callable[..., None]:
    repository = _campaign_repository(runtime)
    ports = campaign_persistence.CampaignSavePorts(
        repository=repository,
        normalize_campaign=_state_engine_symbol(runtime, "normalize_campaign"),
        utc_now=runtime["utc_now"],
        emit_turn_phase_event=runtime["emit_turn_phase_event"],
        turn_flow_error=runtime["turn_flow_error"],
        live_state_service=_live_state_service(runtime, live_state_service),
        logger=runtime.get("LOGGER"),
    )

    def save(campaign: Any, *, reason: str = "campaign_updated", trace_ctx: Any = None) -> None:
        campaign_persistence.save_campaign(campaign, reason=reason, trace_ctx=trace_ctx, ports=ports)

    return save


def _create_campaign_record(runtime: Mapping[str, Any], *, live_state_service: Any = None) -> Callable[..., Any]:
    save_campaign = _save_campaign(runtime, live_state_service=live_state_service)
    ports = campaign_lifecycle.CampaignCreatePorts(
        make_join_code=make_join_code,
        deep_copy=runtime["deep_copy"],
        initial_state=runtime["INITIAL_STATE"],
        default_boards=campaign_lifecycle.default_boards,
        default_setup=_state_engine_symbol(runtime, "default_setup"),
        normalize_campaign=_state_engine_symbol(runtime, "normalize_campaign"),
        current_question_id=_state_engine_symbol(runtime, "current_question_id"),
        ensure_question_ai_copy=_state_engine_symbol(runtime, "ensure_question_ai_copy"),
        remember_recent_story=_state_engine_symbol(runtime, "remember_recent_story"),
        rebuild_memory_summary=_state_engine_symbol(runtime, "rebuild_memory_summary"),
        save_campaign=save_campaign,
    )

    def create(
        title: str,
        display_name: str,
        *,
        legacy_state: Any = None,
        imported_turns: Any = None,
        legacy_flag: Any = None,
    ) -> Any:
        return campaign_lifecycle.create_campaign_record(
            title,
            display_name,
            legacy_state=legacy_state,
            imported_turns=imported_turns,
            legacy_flag=legacy_flag,
            ports=ports,
        )

    return create


def _ensure_campaign_storage(runtime: Mapping[str, Any], *, live_state_service: Any = None) -> Callable[[], None]:
    repository = _campaign_repository(runtime)
    ports = campaign_lifecycle.CampaignStoragePorts(
        data_dir=runtime["DATA_DIR"],
        campaigns_dir=runtime["CAMPAIGNS_DIR"],
        legacy_state_path=runtime["LEGACY_STATE_PATH"],
        ensure_storage_dirs=runtime["ensure_storage_dirs"],
        list_campaign_ids=_list_campaign_ids(runtime),
        load_json=lambda path: campaign_persistence.load_json(repository, path),
        deep_copy=runtime["deep_copy"],
        make_turn_id=lambda: runtime["make_id"]("turn"),
        blank_patch=_state_engine_symbol(runtime, "blank_patch"),
        create_campaign_record=_create_campaign_record(runtime, live_state_service=live_state_service),
    )
    return lambda: campaign_lifecycle.ensure_campaign_storage(ports=ports)


def _find_campaign_by_join_code(runtime: Mapping[str, Any]) -> Callable[[str], Any]:
    ports = campaign_lifecycle.JoinCodeLookupPorts(
        list_campaign_ids=_list_campaign_ids(runtime),
        campaign_path=_campaign_path(runtime),
        load_campaign=_load_campaign(runtime),
    )
    return lambda join_code: campaign_lifecycle.find_campaign_by_join_code(join_code, ports=ports)


def _party_view_ports(runtime: Mapping[str, Any]) -> Any:
    return SimpleNamespace(
        blank_character_state=_state_engine_symbol(runtime, "blank_character_state"),
        normalize_character_state=_state_engine_symbol(runtime, "normalize_character_state"),
        normalize_class_current=_state_engine_symbol(runtime, "normalize_class_current"),
        next_character_xp_for_level=_state_engine_symbol(runtime, "next_character_xp_for_level"),
        resource_name_for_character=_state_engine_symbol(runtime, "resource_name_for_character"),
        clamp=_state_engine_symbol(runtime, "clamp"),
        derive_scene_name=_state_engine_symbol(runtime, "derive_scene_name"),
    )


def _build_party_overview(runtime: Mapping[str, Any]) -> Callable[[Any], Any]:
    ports = _party_view_ports(runtime)
    return lambda campaign: campaign_party.build_party_overview(campaign, ports=ports)


def _character_sheet_ports(runtime: Mapping[str, Any]) -> Any:
    return character_sheet_service.CharacterSheetPorts(
        normalize_character_state=_state_engine_symbol(runtime, "normalize_character_state"),
        reconcile_canonical_resources=_state_engine_symbol(runtime, "reconcile_canonical_resources"),
        build_compat_resources_view=_state_engine_symbol(runtime, "build_compat_resources_view"),
        list_inventory_items=_state_engine_symbol(runtime, "list_inventory_items"),
        ensure_item_shape=_state_engine_symbol(runtime, "ensure_item_shape"),
        resource_name_for_character=_state_engine_symbol(runtime, "resource_name_for_character"),
        normalize_class_current=_state_engine_symbol(runtime, "normalize_class_current"),
        normalize_dynamic_skill_state=_state_engine_symbol(runtime, "normalize_dynamic_skill_state"),
        class_affinity_match=_state_engine_symbol(runtime, "class_affinity_match"),
        effective_skill_progress_multiplier=_state_engine_symbol(runtime, "effective_skill_progress_multiplier"),
        skill_rank_sort_value=_state_engine_symbol(runtime, "skill_rank_sort_value"),
        build_skill_fusion_hints=_state_engine_symbol(runtime, "build_skill_fusion_hints"),
        calculate_derived_bonus=_state_engine_symbol(runtime, "calculate_derived_bonus"),
        world_attribute_scale=_state_engine_symbol(runtime, "world_attribute_scale"),
        display_name_for_slot=campaign_party.display_name_for_slot,
        derive_scene_name=_state_engine_symbol(runtime, "derive_scene_name"),
        next_character_xp_for_level=_state_engine_symbol(runtime, "next_character_xp_for_level"),
    )


def _build_character_sheet_view(runtime: Mapping[str, Any]) -> Callable[[Any, str], Any]:
    ports = _character_sheet_ports(runtime)
    return lambda campaign, slot_name: character_sheet_service.build_character_sheet_view(campaign, slot_name, ports=ports)


def _npc_sheet_ports(runtime: Mapping[str, Any]) -> Any:
    return npc_sheet_service.NpcSheetPorts(
        normalize_npc_entry=_state_engine_symbol(runtime, "normalize_npc_entry"),
        scene_name_from_state=_state_engine_symbol(runtime, "scene_name_from_state"),
        normalize_class_current=_state_engine_symbol(runtime, "normalize_class_current"),
        normalize_resource_name=_state_engine_symbol(runtime, "normalize_resource_name"),
        normalize_dynamic_skill_state=_state_engine_symbol(runtime, "normalize_dynamic_skill_state"),
        skill_rank_sort_value=_state_engine_symbol(runtime, "skill_rank_sort_value"),
        next_character_xp_for_level=_state_engine_symbol(runtime, "next_character_xp_for_level"),
    )


def _build_npc_sheet_view(runtime: Mapping[str, Any]) -> Callable[[Any, str], Any]:
    ports = _npc_sheet_ports(runtime)
    return lambda campaign, npc_id: npc_sheet_service.build_npc_sheet_view(campaign, npc_id, ports=ports)


def _log_board_revision(runtime: Mapping[str, Any]) -> Callable[..., None]:
    return lambda campaign, **kwargs: board_revisions.log_board_revision(
        campaign,
        **kwargs,
        make_id=runtime["make_id"],
        utc_now=runtime["utc_now"],
    )


def build_setup_service_dependencies(runtime: Mapping[str, Any], *, setup_service: Any, live_state_service: Any) -> Any:
    return setup_service.SetupServiceDependencies(
        load_campaign=_load_campaign(runtime),
        authenticate_player=campaign_lifecycle.authenticate_player,
        require_host=campaign_lifecycle.require_host,
        is_host=campaign_views.is_host,
        current_question_id=runtime["current_question_id"],
        clear_live_activity=live_state_service.clear_live_activity,
        start_blocking_action=live_state_service.start_blocking_action,
        clear_blocking_action=live_state_service.clear_blocking_action,
        ensure_question_ai_copy=runtime["ensure_question_ai_copy"],
        save_campaign=_save_campaign(runtime, live_state_service=live_state_service),
        build_world_question_state=_state_engine_symbol(runtime, "build_world_question_state"),
        build_character_question_state=_state_engine_symbol(runtime, "build_character_question_state"),
        progress_payload=_state_engine_symbol(runtime, "progress_payload"),
        validate_answer_payload=_state_engine_symbol(runtime, "validate_answer_payload"),
        store_setup_answer=_state_engine_symbol(runtime, "store_setup_answer"),
        build_random_setup_preview=_state_engine_symbol(runtime, "build_random_setup_preview"),
        apply_random_setup_preview=_state_engine_symbol(runtime, "apply_random_setup_preview"),
        finalize_world_setup=_state_engine_symbol(runtime, "finalize_world_setup"),
        finalize_character_setup=_state_engine_symbol(runtime, "finalize_character_setup"),
        deep_copy=runtime["deep_copy"],
        build_world_summary=_state_engine_symbol(runtime, "build_world_summary"),
        build_character_summary=_state_engine_symbol(runtime, "build_character_summary"),
        normalize_world_settings=runtime["normalize_world_settings"],
        apply_world_summary_to_boards=_state_engine_symbol(runtime, "apply_world_summary_to_boards"),
        apply_character_summary_to_state=_state_engine_symbol(runtime, "apply_character_summary_to_state"),
        campaign_slots=campaign_party.campaign_slots,
        target_turns_defaults=runtime["TARGET_TURNS_DEFAULTS"],
        pacing_profile_defaults=runtime["PACING_PROFILE_DEFAULTS"],
        world_question_map=runtime["WORLD_QUESTION_MAP"],
        character_question_map=runtime["CHARACTER_QUESTION_MAP"],
    )


def build_claim_service_dependencies(runtime: Mapping[str, Any], *, claim_service: Any) -> Any:
    return claim_service.ClaimServiceDependencies(
        load_campaign=_load_campaign(runtime),
        authenticate_player=campaign_lifecycle.authenticate_player,
        player_claim=campaign_party.player_claim,
        current_question_id=runtime["current_question_id"],
        ensure_question_ai_copy=runtime["ensure_question_ai_copy"],
        save_campaign=_save_campaign(runtime),
        is_host=campaign_views.is_host,
    )


def build_turn_service_dependencies(runtime: Mapping[str, Any], *, turn_service: Any, live_state_service: Any) -> Any:
    return turn_service.TurnServiceDependencies(
        load_campaign=_load_campaign(runtime),
        authenticate_player=campaign_lifecycle.authenticate_player,
        active_turns=campaign_views.active_turns,
        intro_state=campaign_lifecycle.intro_state,
        require_claim=campaign_lifecycle.require_claim,
        new_turn_trace_context=runtime["new_turn_trace_context"],
        emit_turn_phase_event=runtime["emit_turn_phase_event"],
        clear_live_activity=live_state_service.clear_live_activity,
        start_blocking_action=live_state_service.start_blocking_action,
        clear_blocking_action=live_state_service.clear_blocking_action,
        create_turn_record=runtime["create_turn_record"],
        save_campaign=_save_campaign(runtime, live_state_service=live_state_service),
        classify_turn_exception=runtime["classify_turn_exception"],
        turn_flow_error_cls=runtime["TurnFlowError"],
        remember_recent_story=runtime["remember_recent_story"],
        rebuild_memory_summary=runtime["rebuild_memory_summary"],
        find_turn=runtime["find_turn"],
        reset_turn_branch=runtime["reset_turn_branch"],
        utc_now=runtime["utc_now"],
    )


def build_context_service_dependencies(runtime: Mapping[str, Any], *, context_service: Any) -> Any:
    from app.services import context as context_module
    from app.services.extraction import heuristics as extraction_heuristics

    return context_service.ContextServiceDependencies(
        load_campaign=_load_campaign(runtime),
        authenticate_player=campaign_lifecycle.authenticate_player,
        player_claim=campaign_party.player_claim,
        active_party=campaign_party.active_party,
        campaign_slots=campaign_party.campaign_slots,
        context_state_signature=context_module.context_state_signature,
        parse_context_intent=context_module.parse_context_intent,
        build_context_knowledge_index=context_module.build_context_knowledge_index,
        resolve_context_target=context_module.resolve_context_target,
        deterministic_context_result_from_entry=context_module.deterministic_context_result_from_entry,
        build_context_result_payload=context_module.build_context_result_payload,
        extract_story_target_evidence=extraction_heuristics.extract_story_target_evidence,
        build_reduced_context_snippets=context_module.build_reduced_context_snippets,
        build_context_result_via_llm=context_module.build_context_result_via_llm,
        context_result_to_answer_text=context_module.context_result_to_answer_text,
    )


def build_campaign_service_dependencies(runtime: Mapping[str, Any], *, campaign_service: Any, live_state_service: Any) -> Any:
    return campaign_service.CampaignServiceDependencies(
        ensure_campaign_storage=_ensure_campaign_storage(runtime, live_state_service=live_state_service),
        create_campaign_record=_create_campaign_record(runtime, live_state_service=live_state_service),
        find_campaign_by_join_code=_find_campaign_by_join_code(runtime),
        new_player=campaign_lifecycle.new_player,
        utc_now=runtime["utc_now"],
        hash_secret=runtime["hash_secret"],
        save_campaign=_save_campaign(runtime, live_state_service=live_state_service),
        load_campaign=_load_campaign(runtime),
        authenticate_player=campaign_lifecycle.authenticate_player,
        require_host=campaign_lifecycle.require_host,
        deep_copy=runtime["deep_copy"],
        intro_state=campaign_lifecycle.intro_state,
        active_turns=campaign_views.active_turns,
        can_start_adventure=campaign_lifecycle.can_start_adventure,
        clear_live_activity=live_state_service.clear_live_activity,
        start_blocking_action=live_state_service.start_blocking_action,
        clear_blocking_action=live_state_service.clear_blocking_action,
        try_generate_adventure_intro=runtime["try_generate_adventure_intro"],
        apply_world_time_advance=runtime["apply_world_time_advance"],
        rebuild_all_character_derived=runtime["rebuild_all_character_derived"],
        append_character_change_events=runtime["append_character_change_events"],
        normalize_class_current=runtime["normalize_class_current"],
        rebuild_character_derived=runtime["rebuild_character_derived"],
        normalize_world_time=runtime["normalize_world_time"],
        campaign_path=_campaign_path(runtime),
        clear_live_campaign_state=live_state_service.clear_campaign_state,
    )


def build_presence_service_dependencies(runtime: Mapping[str, Any], *, presence_service: Any, live_state_service: Any) -> Any:
    return presence_service.PresenceServiceDependencies(
        load_campaign=_load_campaign(runtime),
        authenticate_player=campaign_lifecycle.authenticate_player,
        set_live_activity=live_state_service.set_live_activity,
        clear_live_activity=live_state_service.clear_live_activity,
        live_snapshot=live_state_service.live_snapshot,
    )


def build_sheets_service_dependencies(runtime: Mapping[str, Any], *, sheets_service: Any) -> Any:
    return sheets_service.SheetsServiceDependencies(
        load_campaign=_load_campaign(runtime),
        authenticate_player=campaign_lifecycle.authenticate_player,
        build_party_overview=_build_party_overview(runtime),
        build_character_sheet_view=_build_character_sheet_view(runtime),
        build_npc_sheet_view=_build_npc_sheet_view(runtime),
    )


def build_boards_service_dependencies(runtime: Mapping[str, Any], *, boards_service: Any) -> Any:
    return boards_service.BoardsServiceDependencies(
        load_campaign=_load_campaign(runtime),
        authenticate_player=campaign_lifecycle.authenticate_player,
        require_host=campaign_lifecycle.require_host,
        save_campaign=_save_campaign(runtime),
        utc_now=runtime["utc_now"],
        deep_copy=runtime["deep_copy"],
        log_board_revision=_log_board_revision(runtime),
        default_player_diary_entry=board_diary.default_player_diary_entry,
        make_id=runtime["make_id"],
    )
