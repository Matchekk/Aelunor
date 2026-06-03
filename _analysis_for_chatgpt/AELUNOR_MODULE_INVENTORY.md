# AELUNOR – MODULE INVENTORY

> Stand 2026-05-27. Pfade relativ zu `01_repo/aelunor-core/`.
> LOC = Zeilenzahl aus `wc -l` (inkl. Leerzeilen/Kommentare).

---

## Legende

- **Risk** = subjektives Änderungsrisiko (low/med/high) basierend auf LOC, Globals-Kopplung, Vertragsweite.
- **Tests** = grobe Testabdeckung (siehe `tests/unit/`).
- **Side Effects** = relevant für Refactoring (Persistenz, LLM, Globals, In-Memory-State).

---

## 1. Top-Level / Wiring

| Datei | LOC | Zweck | Wichtigste Funktionen / Klassen | Wichtigste Abhängigkeiten | Side Effects | Risk | Tests |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `app/main.py` | 2004 | FastAPI-App, Wiring, alle Konstanten/Schemas/Prompts, Service-Dep-Factories | `app=FastAPI(...)`, `extend_turn_patch_schema`, `setup_service_dependencies`, `claim_service_dependencies`, `turn_service_dependencies`, `context_service_dependencies`, `campaign_service_dependencies`, `presence_service_dependencies`, `sheets_service_dependencies`, `boards_service_dependencies`, `get_llm_status`, `state_engine.configure(globals())`, `turn_engine.configure(globals())` | `state_engine`, `turn_engine`, `setup_helpers`, `routers/*`, `services/*`, `prompts.json`, `setup_catalog.json` | Lädt JSON, mountet Static-Routen, ruft `ensure_campaign_storage()` beim Import | high | `test_main_state_engine_config.py` (6) |
| `app/helpers/setup_helpers.py` | – | Setup-Hilfslogik (Frage-Payload, Random-Preview-Glue) | `setup_helper_dependencies()` u. a. | `state_engine` | – | med | `test_setup_helpers.py` (4) |

---

## 2. Routers (`app/routers/`)

| Datei | Zweck | API |
| --- | --- | --- |
| `campaigns.py` | Kampagne erstellen/joinen/laden, Meta patchen, Zeit advance, Class unlock, Faction join, Export, Delete | `/api/campaigns*` |
| `claim.py` | Slot claim/release/takeover | `/api/campaigns/{cid}/claim*` |
| `setup.py` | Welt-/Char-Setup-Endpunkte (`next`, `answer`, `random`, `apply`) | `/api/campaigns/{cid}/setup/*` |
| `turns.py` | Turn create / edit / undo / retry | `/api/campaigns/{cid}/turns*` |
| `boards.py` | Plot Essentials, Author's Note, Player Diary, Story Cards, World Info | `/api/campaigns/{cid}/boards/*` |
| `context.py` | Context-Query mit LLM | `/api/campaigns/{cid}/context/query` |
| `presence.py` | Presence Activity, SSE-Stream | `/api/campaigns/{cid}/presence*` |
| `sheets.py` | Character + NPC Sheets | `/api/campaigns/{cid}/sheets/*` |

Alle sind dünne HTTP-Adapter. Risiko: low. Tests: jeweils Service-Tests indirekt.

---

## 3. Services (Top-Level)

| Datei | LOC | Zweck | Wichtigste Funktionen / Klassen | Abhängigkeiten | Side Effects | Risk | Tests |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `services/state_engine.py` | 12396 | God-Modul: Persistenz, Normalisierung, Patch-Helfer, LLM-Aufrufe, Character-/World-/Codex-/Progression-Wrapper, Setup-Backend, Migration | `configure`, `load_campaign`, `save_campaign`, `normalize_campaign`, `apply_patch`-Helfer, `call_ollama_*`, `build_context_packet`, `call_canon_extractor`, `call_npc_extractor`, `call_progression_canon_extractor`, `run_canon_gate`, `rebuild_character_derived`, `apply_progression_events`, `apply_world_time_advance`, `build_campaign_view`, `intro_state`, `try_generate_adventure_intro`, ca. 400 weitere | Fast komplett. Hängt an injizierten `main_globals`. Importiert alle World-Module + `patch_payloads` + `state_basics`. | JSON I/O, Random, Network (Ollama), Datums-/UUID-Generierung | **high** | `test_state_engine.py` (139), `test_world_*` indirekt |
| `services/turn_engine.py` | 1309 | Turn-Pipeline-Orchestrator, Repetition-/Quality-Guards, `apply_patch`-Sequenz, `create_turn_record` | `TurnFlowError`, `classify_turn_exception`, `apply_patch`, `enforce_*_limits`, `rewrite_story_length_guard`, `create_turn_record`, `find_turn`, `reset_turn_branch`, `validate_patch`, `sanitize_patch` | `turn/patch_*` cluster, `state_engine`-Globals, `requests` | LLM (`call_ollama_*`), Logging | high | `test_turn_engine.py` (46), `test_turn_pipeline_fake_llm.py` |
| `services/turn_service.py` | 238 | HTTP-Service-Layer für Turn-Operations | `create_turn`, `edit_turn`, `undo_turn`, `retry_turn`, `TurnServiceDependencies` | `turn_engine` + injizierte Deps | Save-Campaign, Live-State | med | `test_turn_service.py` (2) |
| `services/setup_service.py` | 407 | Welt-/Charakter-Setup-Backend | `next_world_setup_question`, `answer_world_setup`, `random_world_setup`, `apply_random_world_setup`, gleich pro Slot, `_world_setup_payload`, `_character_setup_payload`, `SetupServiceDependencies` | `state_engine`-Helper, `live_state_service` | Save-Campaign, Live-State | med | `test_setup_service.py` (6) |
| `services/campaign_service.py` | 271 | Kampagne CRUD + Intro Retry + Time/Class/Faction Updates | `create_campaign`, `join_campaign`, `get_campaign`, `retry_campaign_intro`, `advance_campaign_time`, `unlock_character_class`, `join_character_faction`, `patch_campaign_meta`, `export_campaign`, `delete_campaign`, `CampaignServiceDependencies` | `state_engine`-Helper, `live_state_service` | JSON I/O (delete), Save-Campaign | med | `test_campaign_service.py` (2) |
| `services/claim_service.py` | 94 | Slot Claim/Takeover | `claim_slot`, `release_slot`, `takeover_slot`, `ClaimServiceDependencies` | `state_engine`-Helper | Save-Campaign | low-med | `test_claim_service.py` (3) |
| `services/boards_service.py` | 201 | Plot/Author/Diary/Story Cards/World Info | `patch_plot_essentials`, `patch_authors_note`, `patch_player_diary`, `create_story_card`, `patch_story_card`, `create_world_info`, `patch_world_info`, `BoardsServiceDependencies` | `state_engine`-Helper | Save-Campaign, log_board_revision | med | `test_boards_service.py` (2) |
| `services/context_service.py` | 173 | In-Game-Kontextfragen via LLM | `query_context`, `ContextServiceDependencies` | `state_engine` (Context-Builders, LLM) | LLM-Calls | med | `test_context_service.py` (1) |
| `services/presence_service.py` | 153 | Presence Activity + SSE-Ticket | `set_presence_activity`, `clear_presence_activity`, `issue_stream_ticket`, `PresenceServiceDependencies` | `live_state_service` | In-Memory State + Tokens | med | `test_presence_service.py` (4) |
| `services/live_state_service.py` | 299 | In-Memory Live-State (Presence, Blocking Actions, SSE-Subscribers) | `live_state_for_campaign`, `set_live_activity`, `start_blocking_action`, `clear_blocking_action`, `campaign_event_stream`, `live_snapshot` | – | Threading.Lock, queues, ttl-Cleanup | med | `test_live_state_service.py` (2) |
| `services/sheets_service.py` | 57 | Char/NPC-Sheet Views | `build_character_sheet`, `build_npc_sheet`, `SheetsServiceDependencies` | `state_engine`-Helper | – | low | – |
| `services/patch_payloads.py` | 136 | Patch-Shape Contract: `blank_patch`, `normalize_patch_payload`, `normalize_patch_semantics`, `merge_character_patch_update`, `merge_patch_payloads` | – | – | low | indirekt durch turn-Tests |
| `services/state_basics.py` | 42 | Slot-/Join-Code-Helfer: `make_join_code`, `slot_id`, `slot_index`, `is_slot_id`, `ordered_slots`, `blank_patch` | – | – | low | indirekt |

---

## 4. Turn-Pipeline-Cluster (`app/services/turn/`)

| Datei | LOC | Zweck | Wichtige Symbole | Risk |
| --- | ---: | --- | --- | --- |
| `__init__.py` | 1 | Marker | – | low |
| `patch_pipeline.py` | 181 | Event-Wrapper für Patch-Phasen | `apply_patch_with_events`, `sanitize_patch_with_events`, `validate_patch_with_events`, `call_canon_extractor_with_events` | low |
| `patch_sanitizer.py` | 201 | Patch-Sanitisierung mit `PatchSanitizerDependencies` | `sanitize_patch` | med (zentral) |
| `patch_validator.py` | 185 | Patch-Validierung mit `PatchValidatorDependencies` | `validate_patch` | med (zentral) |
| `patch_limits.py` | 113 | Non-Milestone-Limits, Progression-Set-Mode-Limits | `enforce_non_milestone_patch_limits`, `enforce_progression_set_mode_limits` | low |
| `patch_apply_abilities.py` | 69 | Abilities/Potential-Updates pro Char | `apply_patch_character_ability_potential_updates` | low |
| `patch_apply_bio.py` | 12 | Bio-Updates | `apply_patch_character_bio_updates` | low |
| `patch_apply_class.py` | 56 | Class-State Updates | `apply_patch_character_class_updates` | low |
| `patch_apply_conditions.py` | 17 | Conditions Add/Remove | `apply_patch_character_condition_effect_updates` | low |
| `patch_apply_events.py` | 13 | events_add Append | `apply_patch_event_updates` | low |
| `patch_apply_injuries.py` | 54 | Injuries Add/Update/Heal, Scars | `apply_patch_character_injury_appearance_updates` | low |
| `patch_apply_inventory.py` | 31 | inventory_add/_remove, equipment_set | `apply_patch_character_inventory_equipment_updates` | low |
| `patch_apply_items.py` | 12 | items_new → state["items"] | `apply_patch_item_updates` | low |
| `patch_apply_journal_factions.py` | 35 | Journal + Factions split (zweistufig) | `apply_patch_character_journal_faction_updates` | low |
| `patch_apply_map.py` | 20 | Map Nodes/Edges Add | `apply_patch_map_updates` | low |
| `patch_apply_meta.py` | 7 | Meta-Phase Update | `apply_patch_meta_updates` | low |
| `patch_apply_normalization.py` | 43 | Late Normalization pro Char (resources reconcile, derived, scars→appearance) | `apply_patch_character_late_normalization` | med |
| `patch_apply_plotpoints.py` | 33 | plotpoints_add/_update | `apply_patch_plotpoint_updates` | low |
| `patch_apply_progression.py` | 40 | progression_set/_update + class_set/_update | `apply_patch_character_progression_updates` | low |
| `patch_apply_resources.py` | 84 | resources_set/_delta + attributes_set/_delta | `apply_patch_character_resource_attribute_updates` | med |
| `patch_apply_skills.py` | 111 | skills_set/_delta, XP, Level, Cooldowns | `apply_patch_character_skill_updates` | med |
| `patch_apply_time.py` | 15 | time_advance Wrapper | `apply_patch_time_advance` | low |
| `prompt_payloads.py` | 117 | Turn-Prompt-Bau (System+User) | `build_turn_system_prompt`, `build_turn_user_prompt` | med |
| `records.py` | 72 | Turn-Record-Payload | `build_turn_record_payload` | low |
| `setup_context.py` | 23 | Working-State-Prep | `prepare_turn_working_state` | low |
| `attribute_context.py` | 36 | Attribute Profile/Bias/Hints | `build_turn_attribute_context` | low |
| `flow_errors.py` | 25 | Narrator-Turn-Fehler | `build_narrator_turn_error` | low |
| `story_length_guard.py` | 77 | Story-Min/Max-Rewrite via LLM | `rewrite_story_length_guard` | med |

---

## 5. World-Cluster (`app/services/world/`)

| Datei | LOC | Zweck | Wichtige Symbole | Risk |
| --- | ---: | --- | --- | --- |
| `codex.py` | 741 | Codex-Subsystem (Welt + NPC), Alias-Index, Block-Facts, Seeding | `CodexRuntimeDependencies`, `ElementNormalizationPort`, `SkillNormalizationPort`, `_codex_deps`, `codex_block_order`, `codex_blocks_for_level`, `normalize_codex_entry_stable`, `normalize_world_codex_structures`, `normalize_npc_codex_state`, `normalize_npc_entry`, `seed_npc_codex_from_story_cards`, `ensure_world_codex_from_setup`, ... | high (Save-State-Effekte) |
| `progression.py` | 126 | Class-Current + Resource-Name + XP | `default_class_current`, `normalize_class_current`, `next_character_xp_for_level`, `normalize_resource_name` | med |
| `injury_state.py` | 63 | Injury/Scar Default + Normalize | `default_injury_state`, `default_scar_state`, `normalize_injury_state`, `normalize_scar_state` | low |
| `appearance.py` | 80 | Appearance-Default + Event-ID + Record | `default_appearance_profile`, `appearance_event_id`, `format_appearance_message`, `record_appearance_change`, `active_faction_ids` | low |
| `state_defaults.py` | 32 | Welt-/Intro-/Char-Modifier-Defaults | `default_world_time`, `default_intro_state`, `default_character_modifiers` | low |
| `npc.py` | 28 | NPC-ID + Alias | `npc_id_from_name`, `normalize_npc_alias` | low |
| `species_profiles.py` | 127 | Race-/Beast-Profile | `default_race_profile`, `normalize_race_profile`, `default_beast_profile`, `normalize_beast_profile`, `race_id_from_name`, `beast_id_from_name` | med |
| `world_settings.py` | 220 | Pacing, Campaign-Length, Turn-Budget | `normalize_world_settings`, `active_pacing_profile`, `compute_turn_budget_estimates`, `build_pacing_instruction_block`, `update_turn_timing_ema`, `milestone_state_for_turn`, `default_campaign_length_settings` | med |
| `attribute_influence.py` | 289 | Attribute-Bias auf Patch + Resolution | `compute_attribute_bias`, `derive_attribute_relevance`, `compose_attribute_prompt_hints`, `apply_attribute_bias_to_resolution`, `apply_attribute_bias_to_patch`, `normalize_attribute_influence_meta` | med |
| `combat.py` | 381 | Combat-Meta + Scaling | `default_combat_meta`, `normalize_combat_meta`, `infer_combat_context`, `patch_has_combat_signal`, `update_combat_meta_after_turn`, `compute_character_combat_score`, `compute_npc_combat_score`, `apply_combat_scaling_to_patch`, `skill_rank_power_weight` | med |
| `element_ids.py` | 29 | Element-ID-Listen | `normalize_element_id_list` | low |
| `element_profiles.py` | 80 | Element-Profile | `default_element_profile`, `normalize_element_profile`, `element_id_from_name` | med |
| `element_relations.py` | 240 | Element-Relations | `build_element_alias_index`, `build_default_element_relations`, `normalize_element_relations`, `resolve_element_relation`, `set_element_relation`, `element_pair_rule_ids` | med |
| `element_class_paths.py` | 239 | Element-Klassenpfade | `generate_element_class_paths`, `normalize_element_class_paths`, `normalize_class_path_rank_node`, `resolve_class_element_id` | med |
| `element_generation.py` | 271 | LLM-/Fallback-Element-Generation | `generate_world_element_profiles`, `generate_world_elements_with_llm`, `generate_world_elements_fallback`, `theme_flavor` | med (LLM-Call) |
| `element_skills.py` | 18 | `normalize_skill_elements_for_world` | – | low |
| `element_entities.py` | 68 | Element-Profile pro Entity (Character/NPC) | `entity_element_profile_for_character`, `entity_element_profile_for_npc`, `element_matchup_multiplier` | low |
| `skill_costs.py` | 81 | Skill-Cost Inference + Apply | `infer_skill_cost_deltas_from_text`, `apply_skill_cost_deltas_to_patch`, `normalize_skill_cost` | low |
| `skill_ranks.py` | 23 | Skill-Rank Mapping | `next_skill_xp_for_level`, `normalize_skill_rank`, `skill_rank_for_level` | low |
| `skill_state.py` | 66 | Skill-State Normalisierung | `normalize_skill_progression_fields`, `normalize_skill_element_fields`, `normalize_power_rating`, `normalize_cooldown_turns`, … | low |
| `math_utils.py` | 5 | `clamp` | – | low |
| `naming.py` | 9 | `strip_name_parenthetical` | – | low |
| `text_normalization.py` | 7 | `normalized_eval_text` | – | low |
| `collections.py` | 12 | `stable_sorted_mapping` | – | low |

---

## 6. Schemas & Helpers

| Datei | LOC | Zweck |
| --- | ---: | --- |
| `app/schemas/api.py` | – | Pydantic-Inputs für Router (TurnCreateIn, JoinCampaignIn, SetupAnswerIn, ContextQueryIn, …) |
| `app/serializers/campaign_view.py` | – | `build_campaign_view`, `public_turn`, `build_public_boards`, Filter private Diary. |

---

## 7. Tests (`tests/`)

| Datei | Tests | Bereich |
| --- | ---: | --- |
| `tests/conftest.py` | – | Repo-Root in sys.path |
| `tests/unit/test_state_engine.py` | 139 | Largest: Appearance, Combat, Codex, Progression, Patch, Element |
| `tests/unit/test_turn_engine.py` | 46 | Turn-Pipeline Slice |
| `tests/unit/test_world_codex.py` | 15 | Codex |
| `tests/unit/test_world_progression.py` | 4 | Class-Current |
| `tests/unit/test_setup_service.py` | 6 | Setup-Service |
| `tests/unit/test_main_state_engine_config.py` | 6 | Garantiert Globals-Wiring |
| `tests/unit/test_setup_helpers.py` | 4 | Setup-Helpers |
| `tests/unit/test_presence_service.py` | 4 | Presence |
| `tests/unit/test_claim_service.py` | 3 | Claim |
| `tests/unit/test_campaign_view_serializer.py` | 3 | View/Public-Filter |
| `tests/unit/test_campaign_service.py` | 2 | Campaign |
| `tests/unit/test_boards_service.py` | 2 | Boards |
| `tests/unit/test_live_state_service.py` | 2 | Live-State |
| `tests/unit/test_turn_service.py` | 2 | Turn-Service |
| `tests/unit/test_context_service.py` | 1 | Context |
| `tests/integration/test_core_flow_smoke.py` | – | Core-Flow Backend |
| `tests/integration/test_core_flow_http_smoke.py` | – | HTTP-Smoke |
| `tests/integration/test_turn_pipeline_fake_llm.py` | – | Turn-Pipeline mit Fake LLM |

Gesamt: **242 passed in 1.34s**.

---

## 8. Scripts (`scripts/`)

| Datei | Zweck |
| --- | --- |
| `check_codex_system.py` | Codex-Integritätsprüfung |
| `check_element_system.py` | Element-System-Prüfung |
| `check_extraction_quarantine.py` | Quarantine-Logik |
| `check_legacy_state_consolidation.py` | Legacy-Migration-Prüfung |
| `check_narrative_manifestation.py` | Manifestations-Erkennung |
| `check_normalize_passive.py` | Passive Normalization |
| `check_progression_canon_gate.py` | Canon-Gate für Progression |
| `check_progression_system.py` | Progression-Konsistenz |
| `check_turn_error_classification.py` | Error-Code-Coverage |
| `benchmark_models.py`, `organic_longrun.py`, `report_longrun.py`, `watch_longrun.py` | Longrun-Benchmark-Tools |
| `rebuild_gm_app.ps1`, `start_v1_dev.ps1`, `stop_v1_dev.ps1` | Windows-Dev-Scripts |

---

## 9. Beobachtungen & Empfehlungen pro Modul (Kurzform)

- **`state_engine.py`**: 11 importierte World-/Subsystem-Module + globale Injektion. `EXPORTED_SYMBOLS` (Liste von ca. 400 Namen) ist Public Surface; jede Auslagerung braucht synchron Anpassung dort.
- **`turn_engine.py`**: `create_turn_record` ist über 500 LOC lang. Phasen sind klar abgrenzbar (Working-State, Narrator-Loop, Extractor-Loop, Post-Process, Record-Build). Sinnvoll für saubere Extraction.
- **`turn/patch_apply_*`**: Sehr kleine Module mit klaren Verträgen. Schon ideal für Sub-Tests.
- **`world/codex.py`**: `CodexRuntimeDependencies` ist gut, hängt aber an `app.main`-Globals. Ein realer DI-Container würde helfen.
- **`patch_payloads.py`**: Selbst-erhaltend (kein `configure`). Solider Mini-Kontrakt.
- **`live_state_service.py`**: Threading + queues. Wenn jemals Cluster gewünscht, ist das nicht thread-safe genug; aktuell OK für single-process.
- **`setup_service.py`**: 30+ Callables in `SetupServiceDependencies`. Großer Dataclass-Vertrag.

---

## 10. Unsicherheiten / nicht verifizierte Aussagen

- LOC ist mechanisch; semantische "Größe" eines Moduls kann abweichen.
- Patch-Apply-Reihenfolge in `turn_engine.apply_patch` wurde gelesen, aber nicht alle Subdomain-Sonderfälle (Legacy-Migration, Shadow-Resource-Write) sind in diese Analyse vollständig dokumentiert.
- Für UI-Module (React/Vite) wurde nur die Verzeichnisstruktur ausgewertet; keine Detail-Modulinventur.
- Scripts sind nur nach Namen klassifiziert; nicht ausgeführt.
