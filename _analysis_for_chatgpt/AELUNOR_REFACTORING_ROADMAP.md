# AELUNOR – REFACTORING ROADMAP

> Stand 2026-05-27. Pfade relativ zu `01_repo/aelunor-core/`.
> **Wichtig:** Diese Roadmap ist eine Analyse, keine Implementierungsvorschrift. Kein Schritt wurde bereits umgesetzt.

---

## 1. Aktueller Demonolithisierungsstand

**Bereits erledigt (lt. `docs/refactor_codex_log.md` und Code):**

- Codex-Subsystem komplett nach `app/services/world/codex.py` (741 LOC) ausgelagert.
- Race-/Beast-/Element-/Skill-/NPC-/Progression-Helfer in eigene Module unter `world/`.
- Injury-/Scar-State nach `world/injury_state.py`.
- Appearance-Default nach `world/appearance.py`.
- World-/Intro-/Character-Modifier-Defaults nach `world/state_defaults.py`.
- Class-Current-Default nach `world/progression.py`.
- Turn-Patch-Pipeline in 18 `turn/patch_apply_*.py`-Module + `patch_sanitizer.py` + `patch_validator.py` + `patch_pipeline.py` aufgespalten.
- Turn-Prompt-Bau nach `turn/prompt_payloads.py`.
- Story-Length-Guard nach `turn/story_length_guard.py`.
- Attribute-Context und Working-State-Prep in `turn/attribute_context.py` und `turn/setup_context.py`.
- Patch-Shape und Merge-Logik selbstständig in `services/patch_payloads.py`.
- Slot-Helfer in `services/state_basics.py`.
- Service-Dependency-Pattern (`*ServiceDependencies` Dataclasses) für Setup/Claim/Turn/Campaign/Context/Presence/Sheets/Boards.

**Noch offen:**

- `app/services/state_engine.py` ist mit 12 396 LOC weiterhin God-Modul. Es enthält Persistenz, LLM-Schnittstellen, Memory, Setup-Helfer, Patch-Helfer, Character-Derived-Rebuild, Auto-Item-/Auto-Injury-Extraktion, Codex-Trigger und Manifestations-Inferenz.
- `app/main.py` (2 004 LOC) enthält Konstanten, Schemas, Prompts, dynamische Schema-Manipulation, Service-Dep-Factories.
- `configure(main_globals)` macht World-/Turn-/Codex-Module abhängig von einer `app.main`-Wiring-Sitzung.
- Patch-Apply-Sequenz in `turn_engine.apply_patch` (Zeilen 568–704) verkettet 18 Subdomain-Aufrufe direkt im Engine-Modul.
- `turn_engine.create_turn_record` ist über 500 LOC lang, mit verschachtelten Narrator-Retry-Loops, Extractor-Loop und Post-Processing.
- Save-State-Versionierung fehlt.
- Canon-Gate aktiv nur für `progression`.

---

## 2. Schutznetz vor weiteren Schritten

**P0 – Tests, die zuerst existieren sollten:**

1. **Campaign Reload Roundtrip Test**
   - Setup: Kampagne erstellen (Fake-LLM), durchspielen einige Turns, `save_campaign` → `load_campaign` → erneutes `save_campaign` → JSON-Diff = 0.
   - Pfad: `tests/integration/test_reload_roundtrip.py`.
2. **`apply_patch` Subdomain-Smoke**
   - Für jede `turn/patch_apply_*`-Datei ein Test, der einen minimalen Patch-Slice durchschickt und vorher/nachher den relevanten Sub-State diff't.
   - Schon einige dieser Tests existieren in `test_state_engine.py`, aber nicht systematisch pro Subdomain.
3. **`run_canon_gate` Verhalten**
   - Aktive Domain (`progression`) wird gefiltert; inaktive Domains (`items`, `location`, `faction`, `injury`, `spellschool`) bleiben Identität.
4. **`normalize_campaign` Idempotenz**
   - `normalize_campaign(normalize_campaign(c)) == normalize_campaign(c)`.
5. **`turn_engine.create_turn_record` Phase-Events**
   - Sicherstellen, dass für jede Phase `success=True` Events emittiert werden (Trace-Log Smoke).

---

## 3. Mini-Schritte (priorisiert)

Jeder Schritt ist klein, lokal, testbar und nicht-verhaltensändernd. Reihenfolge ist als sichere Sequenz zu lesen.

### Schritt A – Konstanten-Auslagerung aus `app/main.py`

**Ziel:** `app/main.py` von trivialen Konstanten entlasten ohne Save-State-Effekt.

**Betroffene Dateien:**

- neu: `app/config/codex_constants.py` (Block-Order, Blocks-by-Level, Default-Meta, Trigger-Sets).
- neu: `app/config/element_constants.py` (Element-Core-Names, Relations, Class-Path-Ranks, Generated-Names-Fallback, Similarity-Blacklist).
- neu: `app/config/progression_constants.py` (Event-Types, Severities, Base-XP, Priority, Density-Caps, Set-Direct-Keys).
- neu: `app/config/manifestation_constants.py` (Strong-/Effect-/Tactical-/Cost-Cues, Motif-Groups, Verb-Blacklist, Name-Stopwords).
- neu: `app/config/skill_constants.py` (Skill-Keys, Ranks, Rank-Order, Attribute-Map, Rank-Thresholds, Outcome-XP, Paths, Evolutions, Fusions).
- `app/main.py` importiert und re-exportiert (`from app.config.codex_constants import *` oder gezielt). State_engine/turn_engine sehen dieselben Symbole durch `configure(globals())`.

**Risiko:** Minimal, solange Konstanten 1:1 re-exportiert werden.

**Notwendige Tests:** Bestehende Tests müssen grün bleiben; `test_main_state_engine_config.py` ist der primäre Anker.

**Akzeptanzkriterien:** `pytest tests -q` weiter 242 passed; `EXPORTED_SYMBOLS` muss alle Konstanten sehen (über `state_engine.configure(globals())`).

### Schritt B – LLM-Schemas in `app/schemas/llm.py`

**Ziel:** Patch-/Response-/Extractor-Schemas raus aus `app/main.py`.

**Betroffene Dateien:**

- neu: `app/schemas/llm.py` mit `RESPONSE_SCHEMA`, `CANON_EXTRACTOR_SCHEMA`, `PROGRESSION_EXTRACTOR_SCHEMA`, `NPC_EXTRACTOR_SCHEMA`, `STORY_REWRITE_SCHEMA`, `CHARACTER_ATTRIBUTE_SCHEMA`, `MANIFESTATION_SKILL_NAME_SCHEMA`, `CONTEXT_RESPONSE_SCHEMA`, `ELEMENT_GENERATOR_SCHEMA`, `SETUP_RANDOM_SCHEMA`.
- `extend_turn_patch_schema` bleibt in `main.py`, ruft aber das importierte `RESPONSE_SCHEMA` und gibt Erweiterung zurück.

**Risiko:** Niedrig, rein read-only Konstanten.

**Tests:** Wieder vorhandene Tests; ggf. Schema-Vergleich vor/nach Refactor als Smoke.

**Akzeptanzkriterien:** `pytest` grün; keine API-Antwort hat sich strukturell geändert.

### Schritt C – System-Prompts in `app/prompts/system_prompts.py`

**Ziel:** Lange Prompt-Strings (CANON_EXTRACTOR_SYSTEM_PROMPT, NPC_EXTRACTOR_SYSTEM_PROMPT, MEMORY_SYSTEM_PROMPT, SETUP_QUESTION_SYSTEM_PROMPT, SETUP_RANDOM_SYSTEM_PROMPT, CHARACTER_ATTRIBUTE_SYSTEM_PROMPT, CONTEXT_ASSISTANT_SYSTEM_PROMPT, MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT, JSON-Kontrakte) bündeln.

**Risiko:** Niedrig.

**Tests:** Bestehend.

**Akzeptanzkriterien:** Inhalte unverändert (Diff-Vergleich mit Original-Strings).

### Schritt D – Patterns-/Regex-Listen in `app/text/patterns.py`

**Ziel:** `AUTO_INJURY_PATTERNS`, `AUTO_ITEM_ACQUIRE_PATTERNS`, `AUTO_ITEM_EQUIP_PATTERNS`, `ABILITY_UNLOCK_TRIGGER_PATTERNS`, sowie Cue-Mengen (`STORY_ACTION_CUES`, `STORY_EXPLORE_CUES`, `STORY_LEARN_CUES`, `COMBAT_NARRATIVE_HINTS`, `COMBAT_END_HINTS`, `ENGLISH_LANGUAGE_MARKERS`, `GERMAN_LANGUAGE_MARKERS`, `ACTION_STOPWORDS`, NPC-Generic-Names, …) bündeln.

**Risiko:** Niedrig.

**Tests:** Bestehende `test_turn_engine` / `test_state_engine` Tests, die auf Patterns angewiesen sind.

**Akzeptanzkriterien:** Funktional unverändert.

### Schritt E – Persistenz-Layer aus `state_engine.py` ziehen

**Ziel:** `save_campaign`, `load_campaign`, `campaign_path`, `list_campaign_ids`, `ensure_campaign_storage`, `find_campaign_by_join_code`, `save_json`, `load_json` nach `app/services/storage/campaign_storage.py`.

**Risiko:** Mittel. Diese Funktionen werden über `EXPORTED_SYMBOLS` re-exportiert und von vielen Services konsumiert. Sie nutzen Globals (`CAMPAIGNS_DIR`, `LEGACY_STATE_PATH`).

**Vorgehen:**

1. Schritte A–D vorher abgeschlossen.
2. Dataclass `CampaignStorageConfig(campaigns_dir, legacy_state_path)`.
3. Funktionen mit explicit `storage_config: CampaignStorageConfig` Argumenten.
4. `state_engine.py` behält Thin-Wrapper, die `storage_config` aus globals lesen.

**Tests vorab:**

- Roundtrip-Test (s. P0).
- `test_state_engine` Tests für Save/Load.

**Akzeptanzkriterien:** Tests grün, kein API-Verhalten ändert sich.

### Schritt F – `turn_engine.create_turn_record` aufspalten

**Ziel:** 5 lesbare Phasen.

**Vorgeschlagene Aufteilung:**

- `turn/turn_record_phase_prepare.py` → `prepare_phase(campaign, actor, action_type, content) -> PreparedTurn`
- `turn/turn_record_phase_narrator.py` → `run_narrator_loop(prepared) -> NarratorOutput`
- `turn/turn_record_phase_extract.py` → `run_extractor_pass(prepared, narrator_output) -> ExtractorResult`
- `turn/turn_record_phase_post.py` → `post_process(prepared, narrator_output, extractor_result) -> PostProcessedTurn`
- `turn/records.py` (bereits vorhanden) → `build_turn_record_payload(...)` (unverändert).

**Risiko:** Mittel, weil viele Variablen geteilt sind. Aufteilung muss Werte (state_before, working_state, prompt_payload, …) sauber als Dataclasses übergeben.

**Tests:** `test_turn_engine.py`, `test_turn_pipeline_fake_llm.py`.

**Akzeptanzkriterien:** Tests grün; Trace-Events bleiben identisch.

### Schritt G – `apply_patch` Orchestrator

**Ziel:** `apply_patch` aus `turn_engine.py` raus. Aktuell direkt im Modul, ruft die `patch_apply_*`-Helfer in fester Reihenfolge.

**Vorschlag:** Neue Datei `app/services/turn/patch_apply_orchestrator.py`:

```python
def apply_patch(state, patch, *, attribute_cap, deps: ApplyPatchDependencies) -> dict:
    ...
```

`ApplyPatchDependencies` bündelt alle benötigten Normalizer/Helfer (Resource-Namer, Skill-Helper, Equipment-Slot-Helper, Class-Helper). Wird in `turn_engine.configure(...)` einmal befüllt.

**Risiko:** Mittel-hoch wegen Subdomain-Sondercases (Late Normalization, Shadow Resource Write).

**Akzeptanzkriterien:** Tests grün; Trace-Events identisch.

### Schritt H – Auto-Extraktion (Items/Abilities/Injuries) extrahieren

`extract_auto_story_items`, `extract_auto_story_injuries`, `extract_auto_learned_abilities`, `extract_auto_class_change`, dazu `clean_*`-Helper, `infer_item_slot_from_text`, `infer_auto_skill_tags`, `infer_auto_class_tags` nach `app/services/extraction/auto_text.py`.

**Risiko:** Mittel. Diese Funktionen sind text-getrieben und über viele Regex-Patterns + Cue-Listen verzahnt.

**Tests vorab:** Charakterisierungstests, die für je 2–3 typische Story-Texte die Extraktion festklopfen.

### Schritt I – Memory + Recent Story extrahieren

`remember_recent_story`, `heuristic_memory_summary`, `rebuild_memory_summary`, `build_context_packet` nach `app/services/memory/memory_summary.py`.

**Risiko:** Mittel. `build_context_packet` ist heißer Pfad (jeder Turn).

**Tests vorab:** Charakterisierungstest mit Beispiel-Campaign-State.

### Schritt J – Canon Extractor isolieren

`call_canon_extractor`, `build_extractor_context_packet`, `normalize_extractor_output_patch`, `merge_safe_patch_additive`, `build_heuristic_candidates`, `safe_candidates_to_patch`, `classify_heuristic_candidate`, `append_extraction_quarantine` nach `app/services/extraction/canon_extractor.py`.

**Risiko:** Mittel-hoch. Diese Stelle ist eng mit Canon-Gate verzahnt.

**Tests vorab:** Existierende Extractor-Tests (in `test_state_engine.py`) verifizieren, dass Output identisch bleibt.

---

## 4. Größere Ziele (P3)

**Save-State-Versionierung**

- `campaign_meta.schema_version` einführen (Start: `1`).
- `app/services/storage/migrations/` als Pipeline von Funktionen `migrate_v1_to_v2(state) -> state`.
- `load_campaign` ruft `migrate(state)` vor `normalize_campaign`.
- Risiko hoch (kann Save-State sichtbar verändern); braucht eine Charakterisierungs-Test-Suite mit Beispiel-Save-States.

**Canon-Gate-Erweiterung**

- Pro Domain (items/location/faction/injury/spellschool) eigene Validation, Confidence-Score, Quarantäne.
- Erst aktivieren, wenn Tests pro Domain bestehen.

**DI-Container statt `configure(globals())`**

- Eine echte `AelunorContext`-Dataclass, die alle injizierten Symbole hält, plus Factory in `app/main.py`. World-/Turn-Module nehmen `AelunorContext` als Parameter.
- Sehr großer Schritt; nur sinnvoll nachdem A–I durch sind.

**`app/main.py` reduziert auf Wiring**

- Endziel < 400 LOC, nur App-Bau, Static-Mounts, Router-Wiring, Health-Endpoint.

---

## 5. Empfohlene Reihenfolge (TL;DR)

1. **P0 Schutznetz-Tests** (Roundtrip, Subdomain-Apply-Smoke, Canon-Gate-Identität, Normalize-Idempotenz).
2. **Schritt A**: Konstanten in `app/config/*`.
3. **Schritt B**: Schemas in `app/schemas/llm.py`.
4. **Schritt C**: Prompts in `app/prompts/`.
5. **Schritt D**: Patterns/Cues in `app/text/patterns.py`.
6. **Schritt E**: Persistenz raus aus `state_engine.py`.
7. **Schritt F**: `create_turn_record` aufspalten.
8. **Schritt G**: `apply_patch` Orchestrator.
9. **Schritt H**: Auto-Extraktion.
10. **Schritt I**: Memory.
11. **Schritt J**: Canon Extractor.
12. **P3**: Versioning, Canon-Gate-Domains, DI-Container.

Nach jedem Schritt: `pytest tests -q` + `python -m py_compile app/main.py` + Update von `docs/codex_state_engine_dependency_inventory.md`.

---

## 6. Was NICHT als Refactor angefasst werden sollte

- `app/services/patch_payloads.py` – stabil, self-contained.
- `app/services/state_basics.py` – stabil.
- `world/math_utils.py`, `world/collections.py`, `world/text_normalization.py`, `world/naming.py` – Mini-Utilities, kein Refactor nötig.
- Pydantic-Schemas in `app/schemas/api.py` – Public Contract.
- Router-Module – sind bewusst dünn.
- Setup-Catalog/Prompts-JSON-Dateien – nicht Code, sondern Daten.

---

## 7. Risiken pro Refactor-Achse

| Achse | Risiko | Mitigation |
| --- | --- | --- |
| Konstanten / Schemas / Prompts | sehr niedrig | Re-Export aus `app.main` halten, bestehende Tests reichen |
| Persistenz | mittel | Roundtrip-Test, Save-Diff-Test |
| Turn-Pipeline-Split | mittel | Fake-LLM-Integrationstest |
| Auto-Extraktion | mittel | Charakterisierungstest pro Story-Text-Beispiel |
| Canon-Extractor | hoch | Vorher Heuristik-Candidate-Test |
| Versionierung | hoch | Beispiel-Save-States als Fixture |
| Canon-Gate-Domains | hoch | Pro Domain eigener Regressionstest, nicht alle gleichzeitig aktivieren |
| DI-Container | sehr hoch | Erst nachdem alle anderen Schritte stabil sind |

---

## 8. Unsicherheiten

- Diese Roadmap ist konservativ. Die exakte Subdomain-Reihenfolge in `apply_patch` darf nicht verändert werden — sie wirkt sich auf Late Normalization aus.
- Schritt E hat verstecktes Risiko, weil `state_engine.save_campaign` indirekt durch Side-Effects (Live-State-Cleanup?) wirken kann; im aktuellen Code nicht gesehen, aber nicht ausgeschlossen.
- Schritt F könnte den `prompt_payload` im Turn-Record verändern, wenn unaufmerksam aufgeteilt; das wäre ein Public-Contract-Bruch.
- Tests in `test_state_engine.py` sind tief gekoppelt an Modul-Funktionen (139 Tests). Jede Auslagerung muss diese als Quasi-Snapshot betrachten.
