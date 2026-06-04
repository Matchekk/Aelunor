from typing import Any, Mapping


def build_setup_service_dependencies(runtime: Mapping[str, Any], *, setup_service: Any, live_state_service: Any) -> Any:
    return setup_service.SetupServiceDependencies(
        load_campaign=runtime["load_campaign"],
        authenticate_player=runtime["authenticate_player"],
        require_host=runtime["require_host"],
        is_host=runtime["is_host"],
        current_question_id=runtime["current_question_id"],
        clear_live_activity=live_state_service.clear_live_activity,
        start_blocking_action=live_state_service.start_blocking_action,
        clear_blocking_action=live_state_service.clear_blocking_action,
        ensure_question_ai_copy=runtime["ensure_question_ai_copy"],
        save_campaign=runtime["save_campaign"],
        build_world_question_state=runtime["build_world_question_state"],
        build_character_question_state=runtime["build_character_question_state"],
        progress_payload=runtime["progress_payload"],
        validate_answer_payload=runtime["validate_answer_payload"],
        store_setup_answer=runtime["store_setup_answer"],
        build_random_setup_preview=runtime["build_random_setup_preview"],
        apply_random_setup_preview=runtime["apply_random_setup_preview"],
        finalize_world_setup=runtime["finalize_world_setup"],
        finalize_character_setup=runtime["finalize_character_setup"],
        deep_copy=runtime["deep_copy"],
        build_world_summary=runtime["build_world_summary"],
        build_character_summary=runtime["build_character_summary"],
        normalize_world_settings=runtime["normalize_world_settings"],
        apply_world_summary_to_boards=runtime["apply_world_summary_to_boards"],
        apply_character_summary_to_state=runtime["apply_character_summary_to_state"],
        campaign_slots=runtime["campaign_slots"],
        target_turns_defaults=runtime["TARGET_TURNS_DEFAULTS"],
        pacing_profile_defaults=runtime["PACING_PROFILE_DEFAULTS"],
        world_question_map=runtime["WORLD_QUESTION_MAP"],
        character_question_map=runtime["CHARACTER_QUESTION_MAP"],
    )


def build_claim_service_dependencies(runtime: Mapping[str, Any], *, claim_service: Any) -> Any:
    return claim_service.ClaimServiceDependencies(
        load_campaign=runtime["load_campaign"],
        authenticate_player=runtime["authenticate_player"],
        player_claim=runtime["player_claim"],
        current_question_id=runtime["current_question_id"],
        ensure_question_ai_copy=runtime["ensure_question_ai_copy"],
        save_campaign=runtime["save_campaign"],
        is_host=runtime["is_host"],
    )


def build_turn_service_dependencies(runtime: Mapping[str, Any], *, turn_service: Any, live_state_service: Any) -> Any:
    return turn_service.TurnServiceDependencies(
        load_campaign=runtime["load_campaign"],
        authenticate_player=runtime["authenticate_player"],
        active_turns=runtime["active_turns"],
        intro_state=runtime["intro_state"],
        require_claim=runtime["require_claim"],
        new_turn_trace_context=runtime["new_turn_trace_context"],
        emit_turn_phase_event=runtime["emit_turn_phase_event"],
        clear_live_activity=live_state_service.clear_live_activity,
        start_blocking_action=live_state_service.start_blocking_action,
        clear_blocking_action=live_state_service.clear_blocking_action,
        create_turn_record=runtime["create_turn_record"],
        save_campaign=runtime["save_campaign"],
        classify_turn_exception=runtime["classify_turn_exception"],
        turn_flow_error_cls=runtime["TurnFlowError"],
        remember_recent_story=runtime["remember_recent_story"],
        rebuild_memory_summary=runtime["rebuild_memory_summary"],
        find_turn=runtime["find_turn"],
        reset_turn_branch=runtime["reset_turn_branch"],
        utc_now=runtime["utc_now"],
    )


def build_context_service_dependencies(runtime: Mapping[str, Any], *, context_service: Any) -> Any:
    return context_service.ContextServiceDependencies(
        load_campaign=runtime["load_campaign"],
        authenticate_player=runtime["authenticate_player"],
        player_claim=runtime["player_claim"],
        active_party=runtime["active_party"],
        campaign_slots=runtime["campaign_slots"],
        context_state_signature=runtime["context_state_signature"],
        parse_context_intent=runtime["parse_context_intent"],
        build_context_knowledge_index=runtime["build_context_knowledge_index"],
        resolve_context_target=runtime["resolve_context_target"],
        deterministic_context_result_from_entry=runtime["deterministic_context_result_from_entry"],
        build_context_result_payload=runtime["build_context_result_payload"],
        extract_story_target_evidence=runtime["extract_story_target_evidence"],
        build_reduced_context_snippets=runtime["build_reduced_context_snippets"],
        build_context_result_via_llm=runtime["build_context_result_via_llm"],
        context_result_to_answer_text=runtime["context_result_to_answer_text"],
    )


def build_campaign_service_dependencies(runtime: Mapping[str, Any], *, campaign_service: Any, live_state_service: Any) -> Any:
    return campaign_service.CampaignServiceDependencies(
        ensure_campaign_storage=runtime["ensure_campaign_storage"],
        create_campaign_record=runtime["create_campaign_record"],
        find_campaign_by_join_code=runtime["find_campaign_by_join_code"],
        new_player=runtime["new_player"],
        utc_now=runtime["utc_now"],
        hash_secret=runtime["hash_secret"],
        save_campaign=runtime["save_campaign"],
        load_campaign=runtime["load_campaign"],
        authenticate_player=runtime["authenticate_player"],
        require_host=runtime["require_host"],
        deep_copy=runtime["deep_copy"],
        intro_state=runtime["intro_state"],
        active_turns=runtime["active_turns"],
        can_start_adventure=runtime["can_start_adventure"],
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
        campaign_path=runtime["campaign_path"],
        clear_live_campaign_state=live_state_service.clear_campaign_state,
    )


def build_presence_service_dependencies(runtime: Mapping[str, Any], *, presence_service: Any, live_state_service: Any) -> Any:
    return presence_service.PresenceServiceDependencies(
        load_campaign=runtime["load_campaign"],
        authenticate_player=runtime["authenticate_player"],
        set_live_activity=live_state_service.set_live_activity,
        clear_live_activity=live_state_service.clear_live_activity,
        live_snapshot=live_state_service.live_snapshot,
    )


def build_sheets_service_dependencies(runtime: Mapping[str, Any], *, sheets_service: Any) -> Any:
    return sheets_service.SheetsServiceDependencies(
        load_campaign=runtime["load_campaign"],
        authenticate_player=runtime["authenticate_player"],
        build_party_overview=runtime["build_party_overview"],
        build_character_sheet_view=runtime["build_character_sheet_view"],
        build_npc_sheet_view=runtime["build_npc_sheet_view"],
    )


def build_boards_service_dependencies(runtime: Mapping[str, Any], *, boards_service: Any) -> Any:
    return boards_service.BoardsServiceDependencies(
        load_campaign=runtime["load_campaign"],
        authenticate_player=runtime["authenticate_player"],
        require_host=runtime["require_host"],
        save_campaign=runtime["save_campaign"],
        utc_now=runtime["utc_now"],
        deep_copy=runtime["deep_copy"],
        log_board_revision=runtime["log_board_revision"],
        default_player_diary_entry=runtime["default_player_diary_entry"],
        make_id=runtime["make_id"],
    )
