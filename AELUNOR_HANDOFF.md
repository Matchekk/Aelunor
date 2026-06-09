# Aelunor Agent Handoff

## Zweck

* Diese Datei ist der kompakte aktuelle Projektzustand fuer Coding-Agenten.
* `AGENTS.md` bleibt massgeblich fuer Regeln.
* README-Dateien bleiben massgeblich fuer Architekturdetails.
* Code gewinnt bei Widerspruch.
* Kein Tagebuch: nur langlebiger Stand, offene Risiken, naechste Schritte.

## Aktiver Arbeitsbereich

* Sauberer Workspace: `D:\Projekte\Aelunor-main-clean`
* Nicht verwenden: `D:\Projekte\Aelunor-main`
* Keine alten kaputten lokalen Workspaces, kein `D:\Aelunor\07_runtime`.
* Repository: `Matchekk/Aelunor`
* Aktiver Code: `01_repo/aelunor-core/`

## Architektur-Kurzbild

* FastAPI-Backend unter `app/` (Python 3.13, Uvicorn, HTTP + SSE).
* React/Vite-UI unter `ui/` (TS strict, Base `/v1`). Neue UI-Arbeit hier.
* Domain-/Workflow-Logik unter `app/services/`.
* Router (`app/routers/`) sind duenne HTTP-Adapter ohne Fachlogik.
* `app/main.py` ist Wiring/Composition, kein Ablageort fuer Fachlogik.
* `state_engine.py` ist kleine Public-Fassade (`EXPORTED_SYMBOLS` =
  `public_turn`, `build_campaign_view`); Kernlogik in `turn_engine.py`,
  `state/runtime_core.py`, `campaigns/`, `turn/`.
* Tests unter `tests/` (`unit/`, `integration/`), Pytest laeuft aus
  `01_repo/aelunor-core/`.
* Persistenz: JSON-Kampagnen unter `DATA_DIR` (Default `.runtime/`,
  Tests = tempdir). Presence/SSE = Live-Sync, nicht persistente Wahrheit.
* Runtime-Daten (`.runtime/`, `.runtime-verify/`, `07_runtime/`) nie als
  Fixtures verwenden oder beschreiben.

## Kern-Game-Flow (kurz)

* Phasen: lobby -> world_setup -> character_setup_open -> ready_to_start ->
  active.
* Loop: Setup -> Claim -> Character Setup -> Play (Turns) -> Persist/Reload.
* Turn: HTTP -> turn_service -> `turn_engine.create_turn_record` -> LLM-Narrator
  -> Patch (sanitize -> validate -> apply) -> mutate -> save JSON -> SSE.
* LLM: `LLM_PROVIDER` = auto|ollama|anthropic (Default Ollama; Claude-Fallback
  braucht `ANTHROPIC_API_KEY`). In Tests nie echte Calls.

## Agent-Kontextdateien

* `AGENTS.md`
* `01_repo/aelunor-core/app/AGENTS.md`
* `01_repo/aelunor-core/app/services/AGENTS.md`
* `01_repo/aelunor-core/app/routers/AGENTS.md`
* `01_repo/aelunor-core/app/services/rag/AGENTS.md`
* `01_repo/aelunor-core/tests/AGENTS.md`
* `01_repo/aelunor-core/ui/AGENTS.md`
* `01_repo/aelunor-core/ui/src/shared/design/AGENTS.md`

## Erledigte Repo-Hygiene

* Inventar-/Cleanup-Plan erstellt (siehe `02_docs/01_architecture/`).
* Falsch getrackte `.runtime-verify`-Campaign-Datei entfernt (PR #43).
* Root-`AGENTS.md` verschlankt (PR #44).
* `app/AGENTS.md`, `app/services/AGENTS.md` ergaenzt (PR #44).
* `app/routers/AGENTS.md` ergaenzt (PR #45).
* Deterministische RAG-Foundation unter `app/services/rag/` ergaenzt (PR #46).
* Unicode-freundliche Keyword-Tokenisierung im RAG-Retrieval ergaenzt.
* `.agent_tmp/` fuer temporaere Agent-Ausgaben (git-ignored).
* `.agent_scripts/` fuer kleine Agent-Hilfsskripte (Repo-Map, Log-Scan,
  kompakte Testausgabe).

## Aktuelle No-Gos

* Keine Secrets/`.env` lesen, ausgeben oder committen.
* Keine Runtime-Daten anfassen oder als Fixture nutzen.
* Keine echten LLM-/Ollama-/Anthropic-Calls in Tests; Fakes/Stubs/Ports.
* Keine Produktlogik in `main.py`.
* Keine Fachlogik in Routern.
* Keine Legacy-UI-Wiederbelebung (`app/static/`) ohne Auftrag.
* Keine Vector-DB-/Embedding-Dependencies ohne eigenen Slice.
* Keine neue externe Dependency ohne Begruendung.
* Keine Datei ueber 300 Zeilen ohne sachlichen Grund.
* Keine Co-authored-by-Zeilen in Commits.

## RAG-Status

* Deterministische Foundation vorhanden unter `app/services/rag/`.
* Enthaelt `models.py`, `chunking.py`, `retrieval.py`, `context_builder.py`,
  `__init__.py`, `README.md`, `AGENTS.md` und Unit-Tests
  (`tests/unit/test_rag_*.py`).
* Public Surface: `RAGDocument`, `RAGChunk`, `RetrievalQuery`,
  `RetrievalResult`, `chunk_document`, `retrieve_chunks`, `build_rag_context`.
* Retrieval ist rein lexical/deterministisch; `campaign_id` ist harter Filter
  (kein Cross-Campaign-Leak); Context Builder haelt `max_items`/`max_chars`
  strikt ein.
* Structured Memory Mapper ergaenzt (`document_mapping.py` +
  `_mapping_utils.py`): mappt strukturierten Campaign-State deterministisch zu
  `RAGDocument` (source_types: campaign_summary, world_summary, lore, location,
  npc, quest, turn_summary). Stdlib-only, offline, mutiert State nicht, liest
  keine Rohlogs/Runtime-Dateien. Public Surface: `build_rag_documents_from_
  campaign_state`, `build_rag_document_id`.
* Noch nicht produktiv integriert: keine Vector-DB, keine Embeddings, keine
  API-Endpunkte, keine Turn-Pipeline-Integration.
* RAG ist unterstuetzende Erinnerung; strukturierter Campaign-/World-/Turn-State
  gewinnt bei Konflikt (Hinweis steht im erzeugten Context-Block).

## Offene GitHub-Issue-Landschaft

Snapshot 2026-06-09; nur Lesezugriff. Details:
`02_docs/01_architecture/GITHUB_ISSUE_TRIAGE.md`.

* Architektur/Struktur-Audits: #35 (Context Map / modularer Monolith),
  #36 (State-Versionierung/Migrationen), #37 (Patch -> Commands/Events),
  #38 (Runtime-Wiring/DI), #42 (Stack Review; FastAPI bleibt).
* RAG-/LLM-nahe Themen: #2 (geplante echte lokale RAG-Schicht),
  #39 (LLM-Contracts/Schemas).
* Test-/Replay-Themen: #40 (replaybare Turn-Pipeline, Golden Tests, Smokes).
* Issue-Hygiene/Duplikate: #41 (Labels, Prioritaeten, Duplikatkontrolle).
* Future Features (RAG-/State-relevant): #34 Map-Rehaul, #33 Karma/Ruf/Standing,
  #32 Split-Party, #23 Waffen/Techniken, #18 Zeit-System, #15
  Persoenlichkeitssystem; zusaetzlich offen #14, #10, #3.

## Empfohlene naechste Slices

1. `chore(docs)`: Issue-Labels/Roadmap-Hygiene (#41), falls explizit erlaubt.
2. `feat(rag)`: strukturierte Campaign-Memory auf `RAGDocument` mappen. (erledigt)
3. `feat(rag)`: In-Memory Campaign-Memory-Index-Service. (naechster Slice)
4. `feat(rag)`: Context-Preview-Service/API (nur Service-Aufruf im Router).
5. `feat(rag)`: guarded Turn-Context-Integration (klar markierter Block).
6. `feat(rag)`: optional Hybrid-Retrieval/Embeddings (eigener Slice).

## Handoff-Pflege-Regeln

* Am Ende relevanter Slices aktualisieren.
* Nur langlebige Entscheidungen, offene Risiken und naechste Schritte aufnehmen.
* Keine Logs, keine langen Diffs, keine Testausgaben.
* Bei Widerspruch Handoff vs. Code: Code pruefen, Handoff korrigieren.
* Bei Widerspruch Handoff vs. `AGENTS.md`: `AGENTS.md` gewinnt.
