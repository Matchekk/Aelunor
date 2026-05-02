# Codex-Refactor Log

## Verschobene Funktionen
- [x] beast_profile_block_facts -> codex.py (Gruppe D)
- [x] build_entity_alias_variants -> codex.py (Gruppe B)
- [x] build_world_alias_indexes -> codex.py (Gruppe B)
- [x] build_world_exact_name_index -> codex.py (Gruppe B)
- [x] codex_block_order -> codex.py (Gruppe A)
- [x] codex_blocks_for_level -> codex.py (Gruppe A)
- [x] codex_facts_for_blocks -> codex.py (Gruppe A)
- [x] codex_seed_for_state -> codex.py (Gruppe D)
- [x] default_beast_codex_entry -> codex.py (Gruppe D)
- [x] default_npc_entry -> codex.py (Gruppe C)
- [x] default_race_codex_entry -> codex.py (Gruppe D)
- [x] ensure_world_codex_from_setup -> codex.py (Gruppe D)
- [x] merge_known_facts_stable -> codex.py (Gruppe A)
- [x] normalize_codex_alias_text -> codex.py (Gruppe A)
- [x] normalize_codex_entry_stable -> codex.py (Gruppe A)
- [x] normalize_npc_codex_state -> codex.py (Gruppe C)
- [x] normalize_npc_entry -> codex.py (Gruppe C)
- [x] normalize_world_codex_structures -> codex.py (Gruppe A)
- [x] race_profile_block_facts -> codex.py (Gruppe D)
- [x] resolve_codex_entity_ids -> codex.py (Gruppe B)
- [x] safe_last_token_variants -> codex.py (Gruppe B)
- [x] seed_npc_codex_from_story_cards -> codex.py (Gruppe C)
- [x] stable_sorted_unique_strings -> codex.py (Gruppe A)
- [x] strip_codex_name_prefix -> codex.py (Gruppe A)
- [x] world_codex_sort_key -> codex.py (Gruppe A)

## Externe Abhängigkeiten (TODOs)
- ensure_world_codex_from_setup ruft ensure_world_element_system_from_setup auf -> muss nach element.py ausgelagert werden
- ensure_world_codex_from_setup ruft generate_world_beast_profiles auf -> muss nach beast.py ausgelagert werden
- ensure_world_codex_from_setup ruft generate_world_name auf -> muss nach world/naming.py ausgelagert werden
- ensure_world_codex_from_setup ruft generate_world_race_profiles auf -> muss nach race.py ausgelagert werden
- normalize_npc_codex_state ruft normalize_dynamic_skill_state auf -> muss nach skills.py ausgelagert werden
- normalize_npc_codex_state ruft normalize_element_id_list auf -> muss nach element.py ausgelagert werden
- normalize_npc_codex_state ruft normalize_resource_name auf -> muss nach progression.py ausgelagert werden
- normalize_npc_codex_state ruft normalize_skill_elements_for_world auf -> muss nach element.py ausgelagert werden
- normalize_npc_entry ruft next_character_xp_for_level auf -> muss nach progression.py ausgelagert werden
- normalize_npc_entry ruft normalize_class_current auf -> muss nach progression.py ausgelagert werden
- normalize_npc_entry ruft normalize_resource_name auf -> muss nach progression.py ausgelagert werden
- normalize_npc_entry ruft normalize_skill_store auf -> muss nach skills.py ausgelagert werden
- normalize_world_codex_structures ruft build_element_alias_index auf -> muss nach element.py ausgelagert werden
- normalize_world_codex_structures ruft element_sort_key auf -> muss nach element.py ausgelagert werden
- normalize_world_codex_structures ruft normalize_beast_profile auf -> muss nach beast.py ausgelagert werden
- normalize_world_codex_structures ruft normalize_element_class_paths auf -> muss nach element.py ausgelagert werden
- normalize_world_codex_structures ruft normalize_element_profile auf -> muss nach element.py ausgelagert werden
- normalize_world_codex_structures ruft normalize_element_relations auf -> muss nach element.py ausgelagert werden
- normalize_world_codex_structures ruft normalize_race_profile auf -> muss nach race.py ausgelagert werden

## Aufgeloeste Utility-Abhängigkeiten
- clamp -> app/services/world/math_utils.py
- stable_sorted_mapping -> app/services/world/collections.py
- normalized_eval_text -> app/services/world/text_normalization.py
- strip_name_parenthetical -> app/services/world/naming.py

## Aufgeloeste NPC-Abhängigkeiten
- npc_id_from_name -> app/services/world/npc.py
- normalize_npc_alias -> app/services/world/npc.py

## Offene Tests
- [ ] Keine neuen Tests geschrieben - Grund: Scope war reines Verschieben/Re-Exportieren ohne neue Testdateien.

## Nicht verschoben (Begründung)
- normalize_race_profile - gehoert zum Race-System und bleibt fuer spaeteren race.py-Refactor in state_engine.py.
- normalize_beast_profile - gehoert zum Beast-System und bleibt fuer spaeteren beast.py-Refactor in state_engine.py.
- Element-, Skill-, Progression- und Naming-Helfer - bleiben bewusst in state_engine.py, um diesen Schritt auf das Codex-Subsystem zu begrenzen.
