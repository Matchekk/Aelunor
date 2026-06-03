# AELUNOR – CODE OVERVIEW

> Stand der Analyse: 2026-05-27
> Erstellt aus dem tatsächlichen Repo-Stand unter `D:/Aelunor/`.
> Analyse-Modus: rein lesend, keine Source-Änderungen.

---

## 1. Executive Summary

Aelunor ist ein lokales, browserbasiertes Multiplayer-Story-RPG mit KI-Game-Master. Der aktive Code-Stack liegt unter `01_repo/aelunor-core/` und besteht aus:

- **FastAPI-Backend** (Python) mit JSON-Persistenz, optionalem Ollama-LLM und SSE-Presence.
- **React/Vite-v1-UI** unter `ui/`, gemountet auf `/v1`.
- **Legacy-UI** unter `app/static/` auf `/`, eingefroren.
- **Service-Layer** in `app/services/` mit zunehmend granularer World-/Turn-Aufteilung.

Die Demonolithisierung läuft aktiv: `world/codex.py`, `world/progression.py`, `world/injury_state.py`, `world/state_defaults.py`, `world/appearance.py`, `world/element_*` und ein Cluster aus `turn/patch_apply_*`-Modulen wurden bereits aus dem ursprünglichen Monolithen extrahiert. Trotzdem bleiben zwei riesige Module: `app/services/state_engine.py` (≈12.4k Zeilen) und `app/main.py` (≈2k Zeilen). Beide arbeiten weiter über das `configure(globals())`-Pattern und damit über versteckte globale Injektion.

**Testlage:** `python -m pytest tests -q` ergibt **242 passed in 1.34s** (139 davon `test_state_engine.py`, 46 `test_turn_engine.py`, plus Service- und Codex-Tests, plus 3 Integration-Smoke-Tests). Solide Charakterisierungsbasis, aber Coverage konzentriert sich auf State-/Turn-Engine; UI- und Mehr-Spieler-Flows sind im Backend nur per Smoke-Test abgedeckt.

**Wichtigste Risiken:**

1. `state_engine.py` ist God-Modul mit globaler Injektion.
2. `app/main.py` hält Schemas, Prompts, Konstanten, Filesystem-Wiring und Service-Dependency-Factories in einer Datei.
3. Patch-Pipeline (Sanitize → Validate → Apply → Extractor) ist mehrstufig, aber rein über Dataclass-Dependencies entkoppelt; Migrations- und Save-State-Verträge sind noch implizit `Dict[str, Any]`.
4. `07_runtime/` ist Produktivdaten-Pfad; viele Tests benutzen Dependency-Injection statt Monkeypatching, aber die Pfad-/Persistenz-Logik liegt teilweise weiter in `state_engine.py`.
5. SSE-Token wird laut historischen Audits noch via Query-URL übertragen; im Code nicht abschließend verifiziert in dieser Analyse.

---

## 2. Projektzweck

Aus `AGENTS.md` und `README.md`:

- Spielbarer Kernflow: Kampagne erstellen oder beitreten → Welt-/Charakter-Setup → Slots claimen → spielen → Story-Turns mit KI-GM → Canon/Patch-State persistieren → Presence/SSE.
- Story-first UX hat Priorität vor Admin-/Analyse-Dashboards.
- MVP-Stabilität vor Feature-Ausbau.
- Persistenz ist JSON-Dateien unter `07_runtime/campaigns/`.
- KI: Ollama-kompatible HTTP-API, in Tests immer gefaket/gestubbt.

Aktive Charakter-Domänen, die der Code modelliert: Welt-Setup, Charaktere mit Klasse/Skills/Inventory/Equipment/Injuries/Scars/Appearance, Elemente, Codex (Races + Beasts + NPCs), Progression mit XP/Level/Manifestationen, Combat-Meta, Attribute-Influence, Pacing, Memory/Recent-Story.

---

## 3. Architekturübersicht

### Top-Level

```
D:/Aelunor/
├── 01_repo/aelunor-core/      # aktiver Stack
│   ├── app/                   # FastAPI + Services
│   ├── ui/                    # React/Vite v1 UI
│   ├── tests/                 # pytest (unit + integration)
│   ├── scripts/               # check_*, longrun, dev-start
│   ├── docs/                  # historische Audits + Refactor-Logs
│   └── README.md
├── 02_docs/                   # Produkt-/Architektur-Docs (extern zur Repo)
├── 03_brand/                  # Assets
├── 05_prompts/                # Prompt-Bibliothek
├── 07_runtime/                # Lokale Runtime-Daten (TABU für Tests)
├── 99_archive/
├── AGENTS.md                  # Top-Level-Agentenregeln
├── README.md
└── prompt.md
```

### Backend (`01_repo/aelunor-core/app/`)

```
app/
├── main.py                    # 2004 LOC – Wiring, Konstanten, Schemas, Prompts, Service-Dep-Factories
├── helpers/setup_helpers.py
├── routers/                   # dünne HTTP-Adapter (campaigns, claim, setup, turns, boards, presence, sheets, context)
├── schemas/api.py             # Pydantic-Eingabemodelle
├── serializers/campaign_view.py
├── services/
│   ├── state_engine.py        # 12396 LOC – Monolith: World, Codex, Character, Patch-Apply-Helfer, Persistenz, LLM
│   ├── turn_engine.py         # 1309 LOC – Turn-Pipeline-Orchestrator
│   ├── patch_payloads.py      # 136 LOC – Patch-Shape, merge, semantics
│   ├── state_basics.py        # slot id helpers, join code, blank patch
│   ├── campaign_service.py    # Kampagnen-CRUD, Intro-Retry, Zeit-/Klassen-/Faction-Updates
│   ├── turn_service.py        # create_turn/edit/undo/retry HTTP-Handler-Layer
│   ├── setup_service.py       # Welt-/Charakter-Setup-Logik (Question Stream)
│   ├── claim_service.py
│   ├── boards_service.py
│   ├── context_service.py     # In-Game-Kontext-Frage (LLM-gestützt)
│   ├── live_state_service.py  # SSE + Presence + Blocking Actions
│   ├── presence_service.py
│   ├── sheets_service.py
│   ├── turn/                  # patch-pipeline-cluster (sanitizer, validator, apply_*, records, prompts)
│   └── world/                 # codex, progression, elements, combat, npc, appearance, injury, ...
└── prompts.json, setup_catalog.json
```

### Services/World-Aufteilung (Stand der Demonolithisierung)

Bereits ausgelagerte World-Module (alle reine Funktionen / kleine Helpers; viele werden aus `state_engine.py` weiter re-exportiert für Backwärts-Kompatibilität):

| Datei | Inhalt |
| --- | --- |
| `world/codex.py` (741) | Codex-Normalisierung, Alias-Index, Welt-/NPC-Codex, Race/Beast-Block-Facts |
| `world/progression.py` (126) | `default_class_current`, `normalize_class_current`, `next_character_xp_for_level`, `normalize_resource_name` |
| `world/injury_state.py` (63) | Injury/Scar Defaults + Normalisierung |
| `world/appearance.py` (80) | Appearance Default, Event-ID, Format, Record Change, active faction ids |
| `world/state_defaults.py` (32) | `default_world_time`, `default_intro_state`, `default_character_modifiers` |
| `world/element_*` (8 Dateien) | Element-System: IDs, Profile, Relations, Class Paths, Skills, Generation, Entities |
| `world/combat.py` (381) | Combat-Meta, Scaling, Element-Matchup, Score |
| `world/attribute_influence.py` (289) | Attribute-Bias |
| `world/skill_*` (4 Dateien) | Skill Ranks, Costs, State |
| `world/world_settings.py` (220) | Pacing, Campaign-Length-Defaults, Turn-Budget |
| `world/npc.py` (28) | `npc_id_from_name`, `normalize_npc_alias` |
| `world/species_profiles.py` (127) | Race-/Beast-Profile |
| `world/math_utils.py` (5), `world/collections.py` (12), `world/text_normalization.py` (7), `world/naming.py` (9) | reine Utilities |

### Turn-Pipeline-Cluster (`app/services/turn/`)

Granular pro Patch-Domäne:

| Datei | Verantwortung |
| --- | --- |
| `patch_pipeline.py` (181) | Wrapper `call_canon_extractor_with_events`, `sanitize_patch_with_events`, `validate_patch_with_events`, `apply_patch_with_events` mit Trace-Logging |
| `patch_sanitizer.py` (201) | Patch-Sanitisierung mit `PatchSanitizerDependencies` |
| `patch_validator.py` (185) | Schema-/Semantik-Validierung mit `PatchValidatorDependencies` |
| `patch_limits.py` (113) | Non-Milestone-Limits, Progression-Set-Mode-Limits |
| `patch_apply_*.py` (18 Dateien) | je eine Sub-Domäne: abilities, bio, class, conditions, events, injuries, inventory, items, journal_factions, map, meta, normalization, plotpoints, progression, resources, skills, time |
| `prompt_payloads.py` (117) | Turn-Prompt-Aufbau (System+User) |
| `records.py` (72) | `build_turn_record_payload` |
| `setup_context.py` (23) | `prepare_turn_working_state` (deep-copy + Pacing) |
| `attribute_context.py` (36) | Attribute-Profile/-Bias/-Prompt-Hints im Turn-Kontext |
| `flow_errors.py` (25) | Narrator-Turn-Fehler-Helper |
| `story_length_guard.py` (77) | LLM-Rewrite bei zu kurzer/zu langer Story |

### Frontend (`01_repo/aelunor-core/ui/src/`)

```
ui/src/
├── app/                      # AppRoot, RouteGate, bootstrap, sessionStorage
├── entities/
│   ├── campaign/             # Campaign-Snapshot, store, query options
│   ├── presence/             # Presence Store + SSE client
│   ├── settings/             # User Settings
│   └── theme/
├── features/
│   ├── session/              # Hub, Library, Create/Join/Resume
│   ├── claim/                # Slot Claim
│   ├── setup/                # SetupWizardOverlay + Selectors
│   ├── play/                 # CampaignWorkspace, StoryTimeline, Composer, RightRail
│   ├── scenes/, boards/, drawers/, context/
└── shared/                   # api, errors, formatting, rules, sse, styles, types, ui, waiting
```

UI hält Backend-State als Quelle der Wahrheit, nutzt React Query, Zustand, SSE-Client und Surface-Layer.

---

## 4. Wichtigste Datenflüsse

### Initialisierung beim Backend-Start

1. `app/main.py` importiert FastAPI, Router-Module, Service-Module.
2. Konstanten, JSON-Schemas (TURN_RESPONSE, CANON_EXTRACTOR, PROGRESSION_EXTRACTOR, NPC_EXTRACTOR, …), Prompts und Setup-Catalog laden.
3. `turn_engine.configure(globals())` wird **zweimal** aufgerufen: einmal früh (für Setup-Finalize), einmal nach allen Konstanten.
4. `state_engine.configure(globals())` injiziert main-Globals in `state_engine` und re-exportiert ~400 Symbole nach `app.main`.
5. `state_engine.configure` ruft intern `world.codex.configure`, `world.progression.configure`, `world.npc.configure` mit denselben Globals.
6. FastAPI-Router werden über Builder-Funktionen mit Pydantic-Modellen + Service-Dependency-Factories gewired.

### Typischer Spielzug (`POST /api/campaigns/{cid}/turns`)

1. **HTTP-Adapter** `routers/turns.py::create_turn` → ruft `turn_service.create_turn(...)`.
2. **Auth/Phase-Check** in `turn_service`: `authenticate_player`, Slot vorhanden, Phase = `active`, Intro vorhanden, `require_claim`.
3. Trace-Context: `new_turn_trace_context(...)`, Event `input_accepted`.
4. Blocking Action setzen (`submit_turn` / `continue_turn`).
5. `turn_engine.create_turn_record(...)`:
   - `prepare_turn_working_state` → `state_before` + `working_state` deep copy, Pacing-Block, Milestone-Info, Story-Char-Range.
   - `infer_combat_context` + `build_combat_scaling_context`.
   - `build_turn_attribute_context` (Profile, Bias, Prompt-Hints).
   - `build_context_packet` (JSON-Bundle aus campaign + working_state).
   - `build_turn_user_prompt` + `build_turn_system_prompt`.
   - Falls `action_type == "canon"`: nur Canon-Extractor laufen lassen, Patch sanitizen/validieren/applizieren.
   - Sonst: bis zu `MAX_TURN_MODEL_ATTEMPTS=3` Versuche `call_ollama_json(...)` mit Retries bei Format-, Repetition-, Inactive-Char-, Quality-Issues. Anschließend:
     - `rewrite_story_length_guard` (Story Min/Max LLM-Rewrite).
     - `sanitize_patch_with_events` (Narrator-Patch).
     - `apply_attribute_bias_to_patch`, `infer_skill_cost_deltas_from_text` → `apply_skill_cost_deltas_to_patch`, `apply_combat_scaling_to_patch`.
     - `enforce_non_milestone_patch_limits`, `enforce_progression_set_mode_limits`.
     - `validate_patch_with_events`, `apply_patch_with_events` (Narrator).
     - Für `player` + `narrator` source-Texte: `call_canon_extractor_with_events`, sanitize/limit/validate/apply.
6. Post-Apply:
   - `update_turn_timing_ema`, `compute_turn_budget_estimates`, `milestone_state_for_turn`.
   - `merge_patch_payloads(narrator_patch, extractor_patch)` → `patch`.
   - `run_canon_gate(...)` (aktuell nur Domain `progression` aktiv per `CANON_GATE_ACTIVE_DOMAINS={"progression"}`).
   - `apply_progression_events`, `apply_skill_events`.
   - `call_npc_extractor` + `apply_npc_upserts`.
   - `collect_codex_triggers` + `apply_codex_triggers`.
   - `build_skill_system_requests`.
   - `build_turn_record_payload(...)` (record mit `state_before`, `state_after`, Patches, Prompt-Payload, Combat, Progression, Codex, NPC).
   - `normalize_npc_codex_state(campaign)`, `remember_recent_story`, `rebuild_memory_summary`.
7. `save_campaign(...)` (JSON in `DATA_DIR/campaigns/<id>.json`).
8. Response: `{turn_id, trace_id, campaign: build_campaign_view(...)}` – Campaign-View filtert private Diary-Inhalte je Viewer.

### Patch-Lifecycle (vereinfacht)

```
LLM JSON-Output
  → normalize_model_output_payload
  → sanitize_patch (Items cleanen, Equipment validieren, Skills/Class normalisieren, Plotpoints/Scenes prüfen, Resources clampen, Progression-Events normieren)
  → enforce_non_milestone_patch_limits + enforce_progression_set_mode_limits
  → validate_patch (Schema + Domain-Invariants: bekannte Slots, Skill-Element konsistent, Skill-Kosten = Welt-Resource, Items/Equipment-Slots bekannt, Injury/Scar valide, keine negativen Resources)
  → apply_patch (Items → Plotpoints → Map → Time → pro Character: bio/resources/attributes/skills/conditions/inventory/equipment/abilities/progression/journal-faction/class/injury+appearance/late-normalization → meta → events)
  → run_canon_gate (Domain-Filter Progression)
  → apply_progression_events + apply_skill_events
```

### Setup-Flow

`POST /api/campaigns/{cid}/setup/world/next` → `setup_service.next_world_setup_question` → liefert nächste Welt-Frage. `/setup/world/answer` schreibt Antwort, `/setup/world/random` (optional Turbo), `/setup/world/random/apply`, am Ende `finalize_world_setup` → `apply_world_summary_to_boards`. Charakter-Setup analog pro Slot.

### Presence/SSE

`live_state_service` hält **In-Memory** `LIVE_STATE_REGISTRY` mit Activities + Blocking Action pro Campaign. Subscribers werden über Python `queue.Queue` notifiziert. SSE-Stream-Endpoint im Presence-Router. **Hinweis (historischer Audit):** Token-Übertragung via Query-URL ist ein bekanntes Robustheits-/Sicherheitsrisiko.

---

## 5. Wichtigste Module (Tabellenkurz, Details in `AELUNOR_MODULE_INVENTORY.md`)

| Modul | LOC | Rolle |
| --- | ---: | --- |
| `app/main.py` | 2004 | App-Wiring, Konstanten, Schemas, Prompts, Service-Dep-Factories |
| `app/services/state_engine.py` | 12396 | God-Modul: Persistenz, Normalisierung, Patch-Apply-Helfer, LLM-Aufrufe, World-/Character-Helper |
| `app/services/turn_engine.py` | 1309 | Turn-Pipeline-Orchestrator, Repetition-Guard, Quality-Issues, `apply_patch`, `create_turn_record` |
| `app/services/setup_service.py` | 407 | Welt-/Char-Setup |
| `app/services/world/codex.py` | 741 | Codex-Subsystem |
| `app/services/world/combat.py` | 381 | Combat-Meta + Scaling |
| `app/services/turn/patch_*` | ~700 zusammen | Sanitizer, Validator, Apply-Subdomains, Limits, Pipeline-Events |

---

## 6. Aktueller technischer Zustand

- **Tests:** 242 grün (1.34 s lokal). Backend-Determinismus dadurch hoch. Charakterisierungstests für `state_engine`, `turn_engine`, `world/codex`, `world/progression`, Services und Setup-Helpers vorhanden. 3 Integration-Smoke-Tests (`test_core_flow_smoke.py`, `test_core_flow_http_smoke.py`, `test_turn_pipeline_fake_llm.py`).
- **Compile:** `py_compile` für `app/main.py` und Kern-Services grün.
- **Demonolithisierung läuft:** Codex/Progression/Element-Schicht ist sauber getrennt; viele World-Helper sind reine Funktionen mit expliziten Ports (`CodexRuntimeDependencies`). Patch-Apply pro Subdomain (`turn/patch_apply_*`) ist sehr klein und gut testbar.
- **Globale Injektion bleibt:** `state_engine.configure(globals())` ist die zentrale Hürde. Solange `app/main.py` Symbole hostet, sind viele World-Module weiter implizit gekoppelt.
- **Daten-Verträge:** Campaign-JSON-Shape, Patch-Shape (`blank_patch()`), Turn-Record-Shape, Setup-Catalog-Shape sind Public Contracts. Schema-Versionierung fehlt.
- **LLM:** Optional, aber überall im Turn-Flow eingebaut. Tests verwenden Fake-Narrator / Stubs. `MAX_TURN_MODEL_ATTEMPTS = 3`, mit Retry-Eskalation und Story-Length-Guard.
- **Persistenz:** JSON-Dateien in `DATA_DIR/campaigns/`. Kein Locking sichtbar; Konfliktbehandlung wäre relevant bei Multiplayer + Mehrtab. `live_state_service` hält In-Memory-Presence.

---

## 7. Testsituation

| Bereich | Tests | Befund |
| --- | --- | --- |
| `state_engine` | 139 | Sehr gut abgedeckt: Appearance, Attribute-Influence, Codex, Combat, Progression, Patch-Helfer, Element-System, Scenes, Items, Skills, Resources. |
| `turn_engine` | 46 | Patch-Apply, sanitize/validate-Wrapper, Quality-Issues, Repetition-Guard. Fake-LLM-Pfad existiert (`test_turn_pipeline_fake_llm.py`). |
| `world/codex` | 15 | Alias-Index, Codex-Entry-Clamp, NPC-Defaults, NPC-Alias-Index, Story-Card-Seeding. |
| `world/progression` | 4 | Class Current Normalisierung. |
| Service-Tests | 25 | boards, campaign, claim, context, live-state, presence, setup, sheets, turn_service. |
| Serializer/View | 3 | `campaign_view`. |
| Setup-Helpers | 4 | Random Preview, World/Character Summary, Validate Answer. |
| `main_state_engine_config` | 6 | Garantiert, dass nach Import die Globals/Injection sitzen. |
| Integration | 3 | Core-Flow, HTTP-Smoke, Turn-Pipeline mit Fake-LLM. |

**Lücken:** Multiplayer-Race-Conditions (Multi-Tab, gleichzeitige Claims, gleichzeitige Turns), Reload-Konsistenz von In-Flight-Turns, SSE-Reconnect, Save-State-Migrationen, Canon-Gate für andere Domänen als Progression, fehlerhafte Codex-Migration.

**Empfohlene nächste Charakterisierungstests** (vor weiterer Demonolithisierung):

- Vollständiger Smoke-Test des Patch-Apply-Pfads für jeden `turn/patch_apply_*`-Subdomain einzeln (viele sind klein und gut isolierbar).
- `normalize_campaign` Reload-Roundtrip (Save → Load → Save → keine Diffs).
- Canon-Gate-Verhalten bei deaktiviertem Domain.
- Story-Length-Guard mit Fake-LLM.
- NPC-Extractor + Codex-Trigger-Cycle.

---

## 8. Wichtigste Risiken

1. **`state_engine.py` Monolith (12.4k LOC)** – Versteckte Kopplung über `globals()`; Refactoring riskiert Save-State-Inkonsistenzen.
2. **`app/main.py` als zentraler Schema-/Konstanten-/Prompt-Container (2k LOC)** – Konstanten sind Public Contracts; jede Auslagerung muss `EXPORTED_SYMBOLS`-Liste anpassen.
3. **Globale Injektion via `configure(main_globals)`** – Erschwert lokales Testen; ohne `app.main`-Import laufen viele Helper nicht.
4. **JSON-Persistenz ohne Locking** – Multi-Player/Tab-Konflikte können State zerstören; keine Schema-Versionierung sichtbar.
5. **LLM-Aufrufe deep im Turn-Engine** – Nur 1 Boundary über `call_ollama_*`. Fake-Pfade existieren, sind aber implizit.
6. **Presence in-memory** – Restart killt Live-State; akzeptabel, aber Blocking Actions können hängen.
7. **`07_runtime/` darf nicht als Testfixture genutzt werden** – Tests respektieren das, aber Devs könnten versehentlich Runtime-Daten beschreiben.
8. **Legacy-UI unter `app/static/`** – Doppelte Wahrheit; offizielle Linie: einfrieren.
9. **Canon-Gate aktiv nur für `progression`** – Andere Domänen (items, location, faction, injury, spellschool) sind im Schema vorgesehen, aber nicht hart geprüft.
10. **`extend_turn_patch_schema`** dynamisches Schema-Manipulieren in `main.py` – fragile Stelle, wenn Patch-Subschema migriert.

---

## 9. Empfohlene nächste Schritte (Highlevel, Details in `AELUNOR_REFACTORING_ROADMAP.md`)

1. **Reload-Roundtrip-Test** für `normalize_campaign` als Schutznetz vor weiteren Extraktionen.
2. **Konstanten aus `app/main.py` in `app/config/*` extrahieren** (rein read-only, keine Logik): Skill-Ranks, Codex-Block-Order, Element-Konstanten, Pacing-Defaults, Progression-Event-Tables. Re-Export via `app.main` für Backwärts-Kompatibilität.
3. **Schema-Bundles in `app/schemas/llm.py` extrahieren**: TURN_RESPONSE, CANON_EXTRACTOR, PROGRESSION_EXTRACTOR, NPC_EXTRACTOR, STORY_REWRITE.
4. **Prompts in `app/prompts/system_prompts.py` extrahieren** und aus JSON laden.
5. **`state_engine.py` Sub-Cluster bestimmen** (Persistenz, LLM, Memory, Character, Element/Codex-Glue) und einen davon (z. B. `state_engine_persistence.py` mit `save_campaign`/`load_campaign`/`campaign_path`/`list_campaign_ids`) testbedingt extrahieren.
6. **Canon-Gate-Erweiterung** für weitere Domains nur mit eigenem Regressionstest pro Domain.
7. **Save-State-Versionierung**: `campaign_meta.schema_version` einführen, Migrationslayer als Function-Pipeline.
8. **Patch-Apply-Cluster konsolidieren**: Die 18 `turn/patch_apply_*`-Module sind gut, aber das `apply_patch`-Aufruf in `turn_engine.py` ist riesig; ein Orchestrator-Modul `turn/patch_apply_orchestrator.py` würde die Aufruf-Sequenz isolieren.
9. **`turn_engine.create_turn_record` aufteilen** in (a) Working-State-Prep, (b) Narrator-Loop, (c) Extractor-Pass, (d) Post-Process, (e) Record-Build. Diese Phasen sind faktisch schon getrennt, aber prozedural verkettet.
10. **Doku-Kohärenz**: `docs/codex_state_engine_dependency_inventory.md` aktiv halten; jeder Extraction-PR aktualisiert den Refactor-Log.

---

## 10. Bekannte/dokumentierte Unsicherheiten

- Die hier zitierten LOC-Zahlen stammen aus `wc -l` und sind nicht semantisch (Leerzeilen + Kommentare zählen mit).
- SSE-Token-Risiko aus historischem Audit `docs/AELUNOR_STATUS_AUDIT.md` (2026-04-23). Eine sicherheitsorientierte Re-Verifizierung im aktuellen Code wurde in dieser Analyse nicht durchgeführt.
- `app/main.py` ändert dynamisch ein JSON-Schema (`extend_turn_patch_schema`). Wenn Tests grün sind, ist das semantisch korrekt; das Pattern bleibt aber fragil.
- Die UI ist in dieser Analyse nur auf Verzeichnisebene erfasst, nicht im Detail.

---

> Weiterführende Dokumente in diesem Bundle:
> - `AELUNOR_MODULE_INVENTORY.md` – tabellarisches Modul-Inventar
> - `AELUNOR_FLOW_MAP.md` – Turn-/Patch-/State-Flows mit Mermaid
> - `AELUNOR_REFACTORING_ROADMAP.md` – nächste sichere Mini-Schritte
> - `AELUNOR_CHATGPT_HANDOFF.md` – verdichtete Übergabe
