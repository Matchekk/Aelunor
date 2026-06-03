# AELUNOR – ChatGPT Handoff

> Verdichtete Übergabe für ChatGPT/Codex.
> Stand 2026-05-27.
> Tests: 242 passed in 1.34s.

---

## Was ist Aelunor?

Aelunor ist ein lokales, browserbasiertes Multiplayer-Story-RPG mit KI-Game-Master. Spieler erstellen eine Kampagne, beantworten Welt- und Charakter-Setup-Fragen, claimen Slots und spielen gemeinsam Story-Turns. Ein optionaler LLM (Ollama, gemma/llama-Klasse, Default-Modell konfigurierbar) liefert GM-Antworten als JSON mit `story`, `patch` und `requests`. Ein zweiter LLM-Pfad (Canon Extractor) extrahiert harte Kanon-Änderungen. Ein dritter (NPC Extractor) erkennt story-relevante NPCs. Patches verändern den Campaign-State (Charaktere, Items, Map, Plotpoints, Events). Presence/SSE liefert Live-Updates. Persistenz ist JSON-Dateien unter `07_runtime/campaigns/`.

Story-first UX hat Vorrang vor Admin-Dashboards. MVP-Stabilität vor Feature-Ausbau. Tests dürfen nie echtes Ollama aufrufen.

---

## Code-Stack

Aktives Repo: `01_repo/aelunor-core/`.

```
app/
├── main.py                # 2004 LOC – Wiring, Konstanten, Schemas, Prompts, Service-Dep-Factories
├── routers/               # 8 dünne HTTP-Adapter
├── services/
│   ├── state_engine.py    # 12396 LOC – God-Modul (Persistenz, LLM, Memory, Patch-Helfer, Codex-Glue)
│   ├── turn_engine.py     # 1309 LOC – Turn-Pipeline-Orchestrator
│   ├── patch_payloads.py  # Patch-Shape Contract
│   ├── state_basics.py    # Slot-Helper
│   ├── campaign_service.py, claim_service.py, setup_service.py, boards_service.py,
│   │   context_service.py, live_state_service.py, presence_service.py, sheets_service.py,
│   │   turn_service.py
│   ├── turn/              # 28 Module: patch_pipeline, patch_sanitizer, patch_validator,
│   │                       18× patch_apply_*, patch_limits, prompt_payloads, records,
│   │                       setup_context, attribute_context, flow_errors, story_length_guard
│   └── world/             # 24 Module: codex, progression, injury_state, appearance,
│                           state_defaults, element_* (8 Stück), combat, attribute_influence,
│                           skill_* (4 Stück), npc, species_profiles, world_settings,
│                           math_utils, collections, naming, text_normalization
├── schemas/api.py         # Pydantic-Inputs
├── serializers/campaign_view.py
└── prompts.json, setup_catalog.json
ui/                        # React/Vite v1, gemountet auf /v1
tests/                     # 242 Tests (139 state_engine, 46 turn_engine, 15 world_codex, …)
```

Frontend (Vite/React 18, TS, React Query, Zustand) ist feature-orientiert unter `ui/src/features/{session,claim,setup,play,scenes,boards,drawers,context}` plus `entities/{campaign,presence,settings,theme}` plus `shared/`. Legacy-UI unter `app/static/` ist eingefroren.

---

## Wichtigste Module

| Modul | Rolle |
| --- | --- |
| `app/main.py` | App-Wiring, alle LLM-Schemas, Prompts, ca. 200 Konstanten, Service-Dep-Factories, `state_engine.configure(globals())`, `turn_engine.configure(globals())`. |
| `app/services/state_engine.py` | Persistiert Campaigns als JSON, normalisiert State beim Load, baut Campaign-Views, hält Setup-Helper, ruft Ollama (`call_ollama_json`, `call_ollama_schema`), enthält Canon-Extractor, NPC-Extractor, Memory-Summary, Auto-Extraktion (Items/Injuries/Abilities), Codex-Trigger, Class-/Element-/Skill-Helper. Globals werden via `configure(main_globals)` injiziert. Re-exportiert ca. 400 Symbole nach `app.main` via `EXPORTED_SYMBOLS`. |
| `app/services/turn_engine.py` | Turn-Pipeline: Patch sanitizen, validieren, anwenden; Narrator-Retry-Loop mit Repetition-/Quality-Guards; Story-Length-Guard; Canon-Extractor-Pass; Progression-Events; NPC- und Codex-Trigger; Turn-Record-Bau. Globale Injektion via `configure(main_globals)`. |
| `app/services/patch_payloads.py` | Patch-Shape (`blank_patch`), `normalize_patch_payload`, `normalize_patch_semantics`, `merge_character_patch_update`, `merge_patch_payloads`. Self-contained, kein `configure`. |
| `app/services/turn/patch_*` | Sanitizer/Validator/Limits + 18 Apply-Subdomains; alle mit eigenen `*Dependencies`-Dataclasses. |
| `app/services/world/codex.py` | Codex-Subsystem: Race/Beast/NPC-Normalisierung, Alias-Indizes, Block-Facts, Welt-Codex-Seeding aus Setup. Hat eigene `CodexRuntimeDependencies` Dataclass. |
| `app/services/live_state_service.py` | In-Memory Presence + Blocking Action + SSE-Subscriber-Queues. Nicht persistiert. |

---

## Wie ein Turn funktioniert

`POST /api/campaigns/{cid}/turns` mit `TurnCreateIn{actor, action_type ∈ {do,say,story,canon}, content}` und Headern `X-Player-Id`, `X-Player-Token`.

1. **`turn_service.create_turn`**: Auth + Slot + Phase=`active` + Intro + Claim. Trace-Context öffnen. `start_blocking_action`.
2. **`turn_engine.create_turn_record`**:
   - `prepare_turn_working_state` → deep-copy state, Pacing-Block, Story-Char-Min/Max, Milestone-Info.
   - `infer_combat_context` + `build_combat_scaling_context`.
   - `build_turn_attribute_context` → Profile, Bias, Prompt-Hints.
   - `build_context_packet` → JSON-Bundle.
   - `build_turn_user_prompt` + `build_turn_system_prompt`.
   - Falls `action_type == "canon"`: nur Canon-Extractor laufen lassen, Patch sanitize/limit/validate/apply.
   - Sonst: bis zu 3 Versuche `call_ollama_json`. Retries bei Format-Fehler, Inactive-Character-Refs, Repetition/Quality-Issues, abgeschnittenen Texten.
   - `rewrite_story_length_guard`: LLM-Rewrite, falls Story zu kurz/lang.
   - `sanitize_patch` (Narrator-Patch) → `apply_attribute_bias_to_patch` → `infer_skill_cost_deltas_from_text` → `apply_skill_cost_deltas_to_patch` → `apply_combat_scaling_to_patch`.
   - `enforce_non_milestone_patch_limits` + `enforce_progression_set_mode_limits`.
   - `validate_patch` → `apply_patch` (Narrator).
   - Zwei Extractor-Passes (source=player + source=narrator): sanitize/limit/validate/apply.
3. **Post-Apply**:
   - `update_turn_timing_ema`, `compute_turn_budget_estimates`, `milestone_state_for_turn`.
   - `merge_patch_payloads(narrator_patch, extractor_patch)`.
   - `run_canon_gate` (aktiv nur `progression`).
   - `apply_progression_events` + `apply_skill_events`.
   - `call_npc_extractor` + `apply_npc_upserts`.
   - `collect_codex_triggers` + `apply_codex_triggers`.
   - `build_skill_system_requests`.
   - `build_turn_record_payload` (mit `state_before`, `state_after`, beiden Patches, Prompt-Payload, Combat, Progression, Codex, NPC).
   - `normalize_npc_codex_state`, `remember_recent_story`, `rebuild_memory_summary`.
4. `save_campaign` → JSON.
5. Antwort: `{turn_id, trace_id, campaign: build_campaign_view(...)}` (filtert private Diary).

**Fehler** werden als `TurnFlowError(error_code, phase, trace_id, user_message)` propagiert und zu `HTTPException 500` mit Headern `X-Turn-Trace-Id` + `X-Turn-Error-Code`. Phase-Events landen im Logger `isekai.turns`.

---

## Patch-Shape (Public Contract)

```json
{
  "meta": {},
  "characters": {"slot_1": {"bio_set": {}, "resources_set": {}, "skills_set": {},
    "skills_delta": {}, "inventory_add": [], "equipment_set": {},
    "class_set": {}, "class_update": {}, "progression_events": [],
    "injuries_add": [], "scars_add": [], "appearance_flags_add": [], ...}},
  "items_new": {"item_xxx": {"name": "...", "slot": "weapon", ...}},
  "plotpoints_add": [...], "plotpoints_update": [...],
  "map_add_nodes": [...], "map_add_edges": [...],
  "events_add": ["..."]
}
```

`apply_patch` Reihenfolge: items → plotpoints → map → time → pro Character (bio, resources/attributes, skills, conditions, inventory/equipment, abilities/potential, progression, journal, class, faction, injuries/appearance, late-normalization) → meta → events.

---

## Welche Refactorings sind bereits passiert?

Aus `docs/refactor_codex_log.md` und Code:

- Codex-Subsystem komplett nach `world/codex.py` extrahiert; `CodexRuntimeDependencies` als interne DI.
- Race-/Beast-/Element-/Skill-/NPC-/Progression-Helfer als eigene `world/`-Module.
- Injury/Scar, Appearance, World-Time, Intro-State, Character-Modifiers, Class-Current-Default in eigenen Modulen.
- Turn-Patch-Pipeline pro Subdomain extrahiert (`turn/patch_apply_*.py`, 18 Stück), plus `patch_sanitizer.py`, `patch_validator.py`, `patch_pipeline.py`, `patch_limits.py`.
- Service-Dep-Pattern (`*ServiceDependencies` Dataclasses) für alle Services.
- Patch-Shape und Merge in `services/patch_payloads.py` (self-contained).
- Slot-Helfer in `services/state_basics.py`.

**Noch nicht extrahiert:** Persistenz, LLM-Aufrufe, Memory, Auto-Extraktion (Items/Abilities/Injuries), Setup-Backend-Helfer, Character-Derived-Rebuild, Canon-Extractor, Konstanten/Schemas/Prompts in `main.py`.

---

## Was sind die nächsten sinnvollen Schritte?

Empfehlung (klein → groß):

1. **P0 Schutznetz**: Campaign-Reload-Roundtrip-Test, Subdomain-Apply-Smoke pro `patch_apply_*`, Canon-Gate-Identitäts-Test für inaktive Domains, `normalize_campaign` Idempotenz-Test.
2. **Konstanten aus `app/main.py`** in `app/config/codex_constants.py`, `app/config/element_constants.py`, `app/config/progression_constants.py`, `app/config/manifestation_constants.py`, `app/config/skill_constants.py`. Re-Export aus `main.py` halten.
3. **LLM-Schemas** in `app/schemas/llm.py` (RESPONSE_SCHEMA, CANON_EXTRACTOR_SCHEMA, PROGRESSION_EXTRACTOR_SCHEMA, NPC_EXTRACTOR_SCHEMA, STORY_REWRITE_SCHEMA, CHARACTER_ATTRIBUTE_SCHEMA, MANIFESTATION_SKILL_NAME_SCHEMA, CONTEXT_RESPONSE_SCHEMA, ELEMENT_GENERATOR_SCHEMA, SETUP_RANDOM_SCHEMA). `extend_turn_patch_schema` bleibt in `main.py`.
4. **System-Prompts** in `app/prompts/system_prompts.py`.
5. **Patterns/Cues** in `app/text/patterns.py` (AUTO_INJURY_PATTERNS, AUTO_ITEM_*_PATTERNS, ABILITY_UNLOCK_TRIGGER_PATTERNS, STORY_*_CUES, COMBAT_*_HINTS, ENGLISH/GERMAN_LANGUAGE_MARKERS, ACTION_STOPWORDS).
6. **Persistenz** raus aus `state_engine.py` → `app/services/storage/campaign_storage.py`.
7. **`create_turn_record` aufspalten** in 5 Phasen (prepare/narrator/extract/post/build).
8. **`apply_patch` Orchestrator** als eigenes Modul.
9. **Auto-Extraktion** (Items/Abilities/Injuries) als `app/services/extraction/auto_text.py`.
10. **Memory** als `app/services/memory/memory_summary.py`.
11. **Canon-Extractor** als `app/services/extraction/canon_extractor.py`.

P3 (groß, nicht jetzt): Save-State-Versionierung, Canon-Gate-Erweiterung, echter DI-Container statt `configure(globals())`.

---

## Regeln, die ChatGPT/Codex bei künftiger Arbeit einhalten soll

**Architektur**

- Router bleiben dünne HTTP-Adapter. Fachlogik gehört in `app/services/`.
- `app/main.py` ist Wiring/Composition. Neue Fachlogik dort nur, wenn sie bestehendes Wiring ergänzt.
- Service-Dependencies werden über die `*ServiceDependencies` Dataclasses injiziert, **nicht** über Monkeypatch.
- Public Contracts schützen: HTTP-API, JSON-State-Shape, Campaign-Datei-Format, Setup-Catalog-Struktur, Turn-Record-Shape.

**Refactor-Disziplin**

- Keine großen Refactorings ohne kurzen Plan + Migrationsrisiko-Analyse.
- Konstanten/Schemas/Prompts dürfen nur extrahiert werden, wenn sie **re-exportiert** werden, sodass `state_engine.configure(globals())` weiterhin alle Symbole findet.
- `EXPORTED_SYMBOLS` in `state_engine.py` muss konsistent zur Public Surface bleiben.
- `docs/codex_state_engine_dependency_inventory.md` und `docs/refactor_codex_log.md` nach jedem Extraction-Schritt aktualisieren.
- Save-State-Format nie versehentlich brechen; ein Reload-Roundtrip-Test ist Pflicht vor Extraktionen, die `normalize_campaign` oder Persistenz berühren.

**Tests**

- `python -m pytest tests -q` muss vor und nach jedem Schritt grün sein (aktuell 242 passed).
- Backend-Tests in `tests/unit/` und `tests/integration/`. Keine echten Ollama-Calls in Tests; Fake-Narrator/Stubs/injizierte Deps benutzen.
- `07_runtime/` ist Produktiv-Pfad — **niemals** als Testfixture beschreiben.
- Bei Turn-/Canon-/State-Änderungen prüfen: Phase, Turn-Zähler, Timeline, aktiver Turn-Status, Claims, State vor/nach Reload.

**Spielkern**

- Schutz des Kernloops: Setup → Claim → Character Setup → Play → Turn → Persist/Reload.
- Narrator-Output muss Canon respektieren; sichtbare Story-Änderungen sollen strukturiert im State landen.
- Story-first UX: Spieleraktionen, aktueller Turn, GM-Text, Claims, Setup-Fortschritt zuerst.
- Legacy-UI (`app/static/`) ist eingefroren. Neue Frontend-Arbeit gehört in `ui/`.

**LLM**

- Ollama-Aufrufe nur über `call_ollama_*`-Wrapper. Schema-Validierung erzwingen, wo Schema-Pfad existiert.
- Patch-Manipulation immer durch Sanitizer → Limits → Validator → Apply.
- Canon-Gate nur für `progression` aktiv. Andere Domänen (`items`, `location`, `faction`, `injury`, `spellschool`) sind im Schema, aber nicht hart geprüft.
- Repetition- und Quality-Guards in `response_quality_issues` ernst nehmen.

**Multiplayer/Presence**

- Claims, Host-Rechte, Player-Token sind Kernverträge.
- Presence/SSE ist Live-Sync, nicht persistente Wahrheit.
- Blocking Actions müssen am Ende sauber aufgehoben werden (`clear_blocking_action`).

**Risikoanzeigen**

- Bei jedem Refactor: explizit nennen, welche Dateien betroffen sind, welche Tests betroffen sind, welche Risiken nicht abgedeckt sind, welcher nächste Schritt empfohlen wird.
- Lieber zu kleine Schritte als ein riesiger Schwung.

---

## Wichtige Pfade (Cheat-Sheet)

- Repo-Root: `D:/Aelunor/`.
- Aktiver Code: `D:/Aelunor/01_repo/aelunor-core/`.
- Backend: `01_repo/aelunor-core/app/`.
- Tests: `01_repo/aelunor-core/tests/`.
- v1 UI: `01_repo/aelunor-core/ui/src/`.
- Doku: `01_repo/aelunor-core/docs/` + `02_docs/` Top-Level.
- Prompts/Catalog: `01_repo/aelunor-core/app/prompts.json`, `app/setup_catalog.json`.
- Runtime-Daten: `07_runtime/` (tabu für Tests).

---

## Test-/Check-Kommandos

Aus `01_repo/aelunor-core/`:

```powershell
python -m pytest tests -q
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m py_compile app/main.py
python scripts/check_progression_canon_gate.py
python scripts/check_codex_system.py
python scripts/check_element_system.py
```

Lokaler Backend-Run ohne Docker:

```powershell
cd 01_repo/aelunor-core
$env:DATA_DIR="$PWD\.runtime"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Frontend:

```powershell
cd 01_repo/aelunor-core/ui
npm install
npm run dev
npm run typecheck
npm run test
npm run build
```

---

## Was diese Analyse NICHT verifiziert hat

- SSE-Token-Übertragung (historischer Audit nannte URL-Token; aktueller Code nicht zeilenweise auf Sicherheit geprüft).
- UI-Detail-Logik (nur Verzeichnisstruktur ausgewertet).
- LLM-Antwortqualität bei echtem Ollama (keine echten LLM-Calls).
- Verhalten unter konkurrierenden Multi-Tab-Writes.
- Performance unter Last.
- Browser-Kompatibilität.

---

## TL;DR für ChatGPT in einem Satz

Aelunor ist ein Python/FastAPI-Backend mit Ollama-LLM + React/Vite-UI für ein lokal gespieltes RPG, dessen Kern eine mehrstufige Turn-Pipeline (sanitize → validate → apply → extractor) mit JSON-Persistenz und JSON-Patch-Shape ist; der Code ist zu großen Teilen schon demonolithisiert (`world/*`, `turn/patch_apply_*`), aber `app/services/state_engine.py` (12k LOC) und `app/main.py` (2k LOC) sind weiterhin Hauptlast und über `configure(globals())` global gekoppelt — die nächsten sicheren Schritte sind Konstanten-/Schema-/Prompt-Auslagerung aus `main.py`, dann ein Persistenz-Layer aus `state_engine.py`, alles abgesichert durch einen Reload-Roundtrip-Test und die bestehenden 242 grünen Tests.
