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
* In-Memory Campaign-Memory-Index-Service ergaenzt (`memory_index.py`):
  verbindet Mapper -> Chunking -> Retrieval -> Context Builder. Public Surface:
  `CampaignMemoryIndex`, `build_campaign_memory_index`,
  `retrieve_campaign_memory`, `build_campaign_memory_context`. Deterministisch,
  in-memory, keine Persistenz/Cache, keine globale Registry, mutiert State
  nicht; Retrieval immer ueber `index.campaign_id` (kein Cross-Campaign-Leak).
* Read-only Context Preview Service/API ergaenzt (`context_preview.py`):
  zeigt fuer Campaign + hypothetische Aktion Index/Results und bounded
  `<RAG_MEMORY>`-Block. Public Surface: `RagContextPreviewDependencies`,
  `preview_campaign_rag_context`. Mutiert keinen State, persistiert nichts,
  keine LLM-/HTTP-Aufrufe; Limits geclamped, Response bounded. Endpoint
  `POST /api/campaigns/{id}/context/rag-preview` (duenner Router, Wiring ueber
  `factories.build_rag_context_preview_dependencies` + `main.py`).
* Noch nicht produktiv integriert: keine Vector-DB, keine Embeddings, keine
  Turn-Pipeline-Integration; Preview injiziert nichts in echte Turns.
* RAG ist unterstuetzende Erinnerung; strukturierter Campaign-/World-/Turn-State
  gewinnt bei Konflikt (Hinweis steht im erzeugten Context-Block).

## UI-State-HUD-Status

* PR #57: Draft, nicht gemerged; Branch `fix/ui-campaign-state-hud`,
  Head `2c47331`. Checks gruen: typecheck, `npm test` 64/64, build,
  Browser-Smoke (Hub + Kampagne erstellen, kein UI-v1-Error).
* Play-HUD rendert Campaign-State ueber Adapter statt Roh-Zugriffe:
  `ui/src/features/play/partyHudModel.ts` (UiCharacterSummary/UiSceneSummary/
  UiPartyHudState) + `actorDockModel.ts` (Karma-/Szene-Label, Bond-Fix).
* Sichtbar pro Charakter (rechtes Dock, `PartyStatusPanel` im `ActorDock`):
  Name, Klasse/Rang/Level, Leben, Ausdauer, Ressource (Mana/Aether-Name aus
  Backend), Ruf/Karma (aus `journal.reputation`), Conditions, Verletzungen,
  Szene/Ort, Kampf-Flag; global Party-Anzahl, Phase, aktive Szene.
* Kontrollierte Fallbacks statt kaputter Anzeige: `Unbenannte Figur`,
  `Unbekannte Klasse`, `Unbekannter Ort`, `Neutral`, `—`; Werte geclamped
  (0..max); kein `undefined`/`[object Object]` (Tests decken das ab:
  `partyHudModel.test.ts`).
* `WorldRail` zeigt keinen erfundenen HP-Balken mehr, wenn HP-Daten fehlen.
* Adapter/Komponenten lesen Snapshot-Arrays/-Records nur noch defensiv
  (`partyOverview`, `displayParty`, `activeTurns`, `characterSheetSlots`,
  `viewerContext`, `plotEssentials`, `worldTime` in `partyHudModel.ts`);
  frisch erstellte/minimal normalisierte Snapshots crashen die UI nicht mehr.
* Hub-Crash "Cannot read properties of undefined (reading 'length')" kam aus
  `LlmStatusPanel`: `/api/llm/status` liefert seit den Local-LLM-PRs eine
  verschachtelte Shape (`{provider, primary, fallback}`) statt flach; Panel
  liest jetzt beide Shapes defensiv. UI-Contract `LlmStatusResponse` in
  `contracts.ts` ist veraltet (bewusst nicht migriert, eigener Slice).
* `ui/src/features/play/components/RightRail.tsx` ist toter Code (nirgends
  importiert); der echte HUD ist WorldRail (links) + ActorDock (rechts).
* Offene UI-State-Risiken: Karma/Ruf ist nur `journal.reputation`-Text
  (echtes Karma-System = Issue #33); `journal.reputation`-Eintragsform ist
  nicht typisiert (UI liest defensiv); Party-Panel zeigt max. Backend-Daten,
  keine Pagination bei grossen Parties.
* Frische Charaktere starten mit vollen Ressourcen (Fix in
  `app/services/setup/summaries.py`: Currents wurden vor der Attributvergabe
  auf niedrige Maxima geclampt, z.B. 8/18 Leben). Claim-/Setup-UI ist jetzt
  durchgehend deutsch. Umlaut-Mojibake in 8 Backend-Dateien wird durch den
  offenen PR #51 (Heim-PC) gefixt — hier bewusst nicht dupliziert.
* Play-Journal Center poliert (Branch `polish/ui-play-journal-center`):
  Panel ist dunkles Navy statt Beige-Block (`aelunor-main-screen.css`),
  Eintraege als Pergamentkarten mit vertikaler Gold-Chronik-Linie und
  Typ-Badge (Story/System/Spieler via `deriveTurnKindLabel`), Lesespalte
  zentriert (max 58rem), kontrollierter Empty-State
  ("Noch keine Chronik-Einträge."), leerer Spieler-Lead wird ausgeblendet.
  Tests: `journalView.test.ts`. WorldRail/ActorDock/TopBar/Composer-Logik
  unangetastet. Kein LLM-Call im Smoke.
* Play-HUD Premium-Pass (Branch `polish/ui-play-hud-premium-pass`):
  gemeinsame Chrome-Sprache fuer die Play-Shell in `campaignPlayV2.css`
  (dunkle Scrollbars, Gold-Panel-Linien, --ael-Tokens statt Farbduplikate).
  Journal: Karten-Lesespalte repariert — Root Cause war ein Relikt
  `margin-left: 50%` auf `.story-turn-card` in `aelunor-premium-layout.css`
  (altes Split-Layout); Karte jetzt ~76% Center-Breite, Kopfzeile mit
  Hairline, kein doppelter Story/Mode-Badge (`deriveShowModePill`),
  Empty-Text "Noch kein sichtbarer Chroniktext.". Composer: RPG-Action-Tabs,
  Gold-Fokus, integrierter Disabled-Send. ActorDock: gerahmtes Portrait,
  ruhige Pill-Navigation mit aria-labels, Meter mit Track, absichtliche
  Empty-States. WorldRail: Karten-Padding (PARTY nicht mehr abgeschnitten),
  Quest-Line-Clamp (nur visuell), dunklere Fantasy-Map mit Goldpfaden.
  Topbar: Status-Segmente, ruhigere Utilities. Tests 76/76, Build gruen,
  Smoke 1920x1080 ohne Fehler. Keine LLM-Calls.
* Debug-Chrome-Cleanup (auf `polish/ui-play-hud-premium-pass`): Center-
  Status-Pills (Phase/Blickwinkel/Slots) und Member-Chips entfernt (Infos
  leben in Topbar/ActorDock/Composer-Dropdown); Composer-Pills "Modus X"/
  "Akteur slot_x" entfernt (keine rohen Slot-IDs mehr sichtbar);
  `PartyStatusPanel` rechts geloescht (Party bleibt links; Modell
  `partyHudModel` bleibt fuer Adapter/Accessors); Einbuchstaben-Sektions-Nav
  (U R S K F A G B = Anfangsbuchstaben der Sektionen, rein kosmetisch)
  entfernt. ActorRail hat jetzt einen Drawer-Griff an der Leiste
  (`actor-rail-handle`, CSS-Glyph, aria-expanded; Persistenz weiter ueber
  bestehendes uiMemory `right_rail_open`, kein neuer Key); "Akteur"-Button
  aus der Topbar entfernt, Reihenfolge rechts: Claim loesen, Code, Hub,
  Icon-Utilities. ActorRail-Griff ist jetzt ornamental und ueberlappt die
  Panelkante wie ein eingelassener Beschlag: keine separate Grid-Spalte mehr,
  sondern relativer Wrapper `.actor-rail-shell` (3. Grid-Spalte; collapsed
  0px) mit absolut positioniertem Griff (left 0, top 50%,
  translate(-45%,-50%); collapsed translate(-100%,-50%)), 34x132px-Kapsel mit
  `{`/`}`-Glyph, Gold-Border/Glow, Finial-Rauten — reiner CSS-Placeholder,
  spaeter durch `.webp`-Asset ersetzbar; A11y/State/Persistenz (uiMemory
  `right_rail_open`) unveraendert. Play-Topbar nutzt keine SVGs (CSS-Glyphen + PNG-Logo;
  einzige SVG-Nutzung im UI ist das Drawer-Attributradar, unangetastet).
  Composer-Default 340px / min 240 (Gap 0.55rem) — alle Controls ohne
  internen Scroll (scrollHeight<=clientHeight verifiziert), Overflow nur
  als Notfall bei manuell kleiner Hoehe. Tests 88/88, Smoke gruen.
* Responsive-Pass Play-Shell (auf `polish/ui-play-hud-premium-pass`):
  geprueft 1920/1366/1100/960/820/768/390 — kein horizontaler Overflow.
  >1200 3-spaltig, 901-1200 2-spaltig (Actor-Dock + Griff ausgeblendet),
  <=900 gestapelt. Fix: im Stack ist die Center-Spalte (Journal+Composer)
  jetzt story-first vor der WorldRail (`order` in der 900px-Media), Map-
  Platzhalter auf 150px gedeckelt, WorldRail wird simpler Flex-Stack,
  Composer-Basis 300px. Composer-Inhalte sind flex (kein interner Scroll),
  obere Gruppe (Header->Tabs) eng. Journal-Schriftrolle bis 76rem breit.
* Center-Density-/Lesbarkeits-Fix (auf `polish/ui-play-hud-premium-pass`):
  JOURNAL-/DEIN-BEITRAG-Titel ~30% kleiner, Paddings/Gaps im Center
  reduziert (campaignPlayV2.css Abschnitt 2c). Pergament-Lesbarkeit: Text
  auf `.story-turn-card` wird per hoher Spezifitaet auf
  `var(--ael-story-ink)` gezwungen (globals `.timeline-item p` und
  premium-layout `#f4ead9` hatten hellen Text auf heller Karte erzeugt);
  Token-basiert, damit Theme arcane (dunkle Karte, helle Tinte) intakt
  bleibt. Composer-Grenzen neu: min 220 / Default 260 / max 44% der
  Center-Hoehe (Journal-Guard 260); localStorage-Key bleibt
  `aelunor.play.composerHeight.v1`, alte Werte werden nach Mount gegen die
  echte Center-Hoehe geclamped und zurueckgeschrieben (450 -> 422 bei
  1080p). Smoke: Default 258px, Karte vollstaendig sichtbar, Ink
  rgb(32,24,15). Tests 88/88.
* Resizable Composer (auf `polish/ui-play-hud-premium-pass`): vertikaler
  Split Journal/Composer mit Drag-Handle (`composerResize.ts` +
  `composer-resize-handle` in `CampaignWorkspace`), Hoehe via CSS-Variable
  `--play-composer-height`. Persistenz in localStorage-Key
  `aelunor.play.composerHeight.v1` (Pixel, beim Laden geclamped). Regeln:
  min 220px, Default 300px, max 55% der Center-Hoehe bzw. Journal-Guard
  (Journal min 220px). Tastatur: Pfeile (+Shift), Enter/Doppelklick =
  Default; role=separator mit aria-Werten. Pure Clamp-/Storage-Tests
  (`composerResize.test.ts`); kein DOM-Drag-Test (keine Testing-Library im
  Projekt). Smoke: Default 298px, Drag 448px, Reload persistiert. Keine
  LLM-Calls; Backend/Turn/Provider/Runtime/Campaign-State unveraendert.
* LLM-Status-Contract-Drift behoben (Branch `fix/ui-llm-status-contract`,
  gestackt auf `fix/ui-campaign-state-hud`): `LlmStatusResponse` ist jetzt die
  ehrliche Union der drei Backend-Shapes (flat Ollama, flat Anthropic, nested
  auto mit `primary`/`fallback`; Quelle: `app/adapters/llm.py` +
  `anthropic_adapter.py`, read-only verifiziert). Neuer Normalizer
  `normalizeLlmStatusResponse` in `ui/src/features/session/llmStatusModel.ts`;
  `LlmStatusPanel` rendert nur noch normalisierte Daten (inkl. Provider- und
  Fallback-Zeile), keine rohen Shape-Zugriffe. Tests:
  `llmStatusModel.test.ts` (alle Shapes, kaputte Payloads, kein
  `undefined`/`[object Object]`). Keine LLM-Calls, keine Backend-Aenderung.
* Naechste UI-Slices: 1) Right Actor HUD polish, 2) Left WorldRail/Party/Map
  polish, 3) Topbar enttechnisieren, 4) Mojibake/Encoding separat pruefen
  (PR #51 abwarten); ausserdem RightRail.tsx entfernen oder reaktivieren
  (Entscheidung noetig).
* Nicht erneut untersuchen: keine Cloud-LLM-Intro-Flows im Smoke (Setup nie
  bis zum Intro abschliessen), keine Runtime-Daten, keine Backend-/Turn-/
  LLM-Dateien in diesem PR.

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
3. `feat(rag)`: In-Memory Campaign-Memory-Index-Service. (erledigt)
4. `feat(rag)`: Context-Preview-Service/API (nur Service-Aufruf im Router).
   (erledigt)
5. `feat(rag)`: guarded Turn-Context-Integration (klar markierter Block) oder
   LLM Context Contract Alignment (#39). (naechster Slice)
6. `feat(rag)`: optional Hybrid-Retrieval/Embeddings (eigener Slice).

## Handoff-Pflege-Regeln

* Am Ende relevanter Slices aktualisieren.
* Nur langlebige Entscheidungen, offene Risiken und naechste Schritte aufnehmen.
* Keine Logs, keine langen Diffs, keine Testausgaben.
* Bei Widerspruch Handoff vs. Code: Code pruefen, Handoff korrigieren.
* Bei Widerspruch Handoff vs. `AGENTS.md`: `AGENTS.md` gewinnt.
