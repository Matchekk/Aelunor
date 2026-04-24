# Aelunor IST-Analyse: Codezustand + Rehaul v1

Stand: 11.03.2026  
Repo: `01_repo/aelunor-core`  
Analysemodus: technischer Audit (IST, nicht Soll)

## Before Coding

### Analyse-Strategie
- Evidenz zuerst: zentrale Laufzeit-Entry-Points, Router, Service-Wiring, State-Kern, Frontend-Routing, Feature-Module, Styleschichten, Persistenz und Tests wurden direkt im Code geprüft.
- Rehaul v1 wurde nicht über Dateinamen vermutet, sondern über aktive Laufzeitpfade (`/v1`, `ui/dist`, React-Routing), Provider-/Feature-Struktur und tatsächlich verwendete CSS-/State-Schichten abgegrenzt.
- Legacy wurde als "aktiv" gewertet, wenn Laufzeit-Routen, Imports, Migrationen oder Kompatibilitätspfade real ausgeführt werden.
- Bewertungen sind markiert als:
  - `[GESICHERT]` direkt im Code gefunden
  - `[ABGELEITET]` aus mehreren Codefakten plausibel abgeleitet
  - `[UNKLAR]` aktuell nicht belastbar belegbar

### Abgrenzung Rehaul v1 vs. Restbestand
- Rehaul-v1-Kern: `ui/src/*` (React + Vite + Query + Zustand, `/v1`-Routing).
- Parallel aktiver Altbestand: `app/static/*` (Vanilla SPA), weiterhin auf Root (`/`) ausgeliefert.
- Übergangszonen: globale Legacy-CSS-Imports in v1 und Hybrid-Character-Drawer.

### Doku-Ablage
- Eine zentrale Audit-Datei: `docs/IST_ANALYSE_REHAUL_V1_2026-03-11.md`.

---

## 1) Struktur- und Laufzeit-Istbild

### 1.1 Entry Points und Runtime-Grenzen
- `[GESICHERT]` `app/main.py` mountet gleichzeitig Legacy und v1:
  - `/static` -> `app/static`
  - `/` -> `app/static/index.html`
  - `/v1/assets` -> `ui/dist/assets`
  - `/v1`, `/v1/*` -> `ui/dist/index.html`
- `[GESICHERT]` Vite-Basis ist `/v1/` (`ui/vite.config.ts`), passt zur Backend-Auslieferung.
- `[ABGELEITET]` Ergebnis: v1 ist produktiv nutzbar, aber Legacy-Root bleibt first-class und erhöht Drift-Risiko.

### 1.2 Backend-Makrostruktur
- `[GESICHERT]` Router-Schicht in `app/routers/*` ist klar nach Domänen getrennt (campaigns, setup, claim, turns, presence, boards, context, sheets).
- `[GESICHERT]` Service-Schicht in `app/services/*` spiegelt diese Domänen.
- `[GESICHERT]` Kernlogik bleibt stark zentralisiert:
  - `app/main.py`: 2004 Zeilen
  - `app/services/state_engine.py`: 14141 Zeilen
  - `app/services/turn_engine.py`: 2076 Zeilen
- `[GESICHERT]` `state_engine.configure(globals())` und `turn_engine.configure(globals())` koppeln extrahierte Module an `main.py`-Globals; Reconfigure passiert mehrfach.
- `[ABGELEITET]` Das ist funktional, aber architektonisch fragil für weitere Entflechtung.

### 1.3 Frontend-Makrostruktur (v1)
- `[GESICHERT]` App-Root: `ui/src/app/AppRoot.tsx` mit `QueryProvider`, `ThemeProvider`, `RouteGate`.
- `[GESICHERT]` Feature-Cluster sind modular: `session`, `claim`, `setup`, `play`, `boards`, `context`, `drawers`, `scenes`.
- `[GESICHERT]` State-Layer ist hybrid:
  - Serverzustand: TanStack Query (`campaignQueryKeys.by_id`)
  - UI-Surface-State: Zustand-Stores (`drawerStore`, `contextStore`, `layoutStore`, `presenceStore`, `waitingStore`, settings)
- `[ABGELEITET]` Frontend-Struktur ist deutlich moderner als Legacy, aber noch kein strikt durchtypisiertes Domain-Frontend.

---

## 2) Rehaul-v1-Grenzen und Parallelität

## 2.1 Was klar rehaulig ist
- `[GESICHERT]` v1-Routing über `/v1/hub`, `/v1/campaign/:id/(claim|setup|play)`.
- `[GESICHERT]` Gate-Logik für Session/Claim/Setup/Play in `RouteGate` + `routing/selectors`.
- `[GESICHERT]` Modale/Drawer/Context/Boards als Surface-System mit URL-gekoppeltem Zustand (`routes.ts`, `with*RouteState`).
- `[GESICHERT]` Theme-/Token-Ansatz (`shared/styles/tokens/*`, `ThemeProvider`, Settings-Store).

### 2.2 Was klar Legacy bleibt
- `[GESICHERT]` Vollständige Legacy-SPA in `app/static/index.html`, `app/static/app.js`, `app/static/style.css`.
- `[GESICHERT]` Root-Auslieferung (`/`) zeigt weiterhin Legacy-App.
- `[GESICHERT]` README beschreibt Frontend primär als `app/static/` und ist damit hinter dem Istzustand zurück.

### 2.3 Mischzustände
- `[GESICHERT]` v1 lädt global Legacy-CSS (`legacy-vars.css`, `legacy-shell.css`, `legacy-play.css`) zusätzlich zu `globals.css`.
- `[GESICHERT]` Character-Drawer in v1 ist Hybrid:
  - `legacy-character-*` Klassen in `DrawerHost`
  - `legacyCharacterSheet.css`
  - eigener Inline-Tab-Mechanismus in `CharacterDrawer`.
- `[ABGELEITET]` Rehaul v1 ist aktuell eine Teilmigration mit modernem Shell/Routing plus Legacy-Darstellungsinseln.

---

## 3) Produktflächen / Screens / Flows (IST)

### 3.1 Hub / Einstieg
- Technisch: `SessionHubWorkspace`, `session/*`, `sessionLibrary.ts`.
- Funktion: Campaign create/join/resume, lokale Session-Bibliothek, LLM-Status.
- Reifegrad: **funktional, aber inkonsistent**.
- Befunde:
  - `[GESICHERT]` robustes Local-Session-Handling inkl. Legacy-Key-Normalisierung.
  - `[GESICHERT]` mehrere UI-Texte in Englisch in ansonsten deutscher Oberfläche.

### 3.2 Claim-Workspace
- Technisch: `ClaimWorkspace`, `claim/selectors.ts`, `claim/mutations.ts`.
- Funktion: Slot claim/takeover/unclaim mit Presence-Integration.
- Reifegrad: **funktional, aber inkonsistent**.
- Befunde:
  - `[GESICHERT]` sauberer Gate-State (`needs_world_setup`, `needs_claim`, `needs_character_setup`, `can_enter_play`).
  - `[GESICHERT]` Texte/Statuslabels teils Englisch.

### 3.3 Setup-Overlay (World + Character)
- Technisch: `SetupWizardOverlay`, `setup/selectors.ts`, `setup/mutations.ts`, Backend `setup_service.py`, `setup_helpers.py`, `setup_catalog.json`.
- Funktion: Host-gesteuertes World-Setup + slotbezogenes Character-Setup, Random-Preview, Review, Turbo.
- Reifegrad: **halb migriert / Übergangszustand**.
- Befunde:
  - `[GESICHERT]` starker Runtime-Stack mit chapter/progress/review und Presence-Heartbeat.
  - `[GESICHERT]` Katalogversion `v1`, 18 World-Fragen, 17 Character-Fragen.
  - `[GESICHERT]` UI-Texte im Setup sind mehrsprachig gemischt (EN/DE).

### 3.4 Play-Workspace (Timeline + Composer + RightRail)
- Technisch: `CampaignWorkspace`, `StoryTimeline`, `Composer`, `RightRail`, `play/selectors.ts`.
- Funktion: Storyturns, Kontextabfragen, Intro-Retry, Szene-Filter, Boards/Drawer/Context-Surfaces.
- Reifegrad: **funktional, aber inkonsistent**.
- Befunde:
  - `[GESICHERT]` klare URL-basierte Surface-Steuerung (Boards, Drawer, Context, Szene).
  - `[GESICHERT]` starke Koppelung vieler concern in `CampaignWorkspace` (große Orchestrierungsdatei).
  - `[GESICHERT]` RightRail mischt taktische Infos, Codex, Tagebuch, Szene, Events in einem Baustein.

### 3.5 Boards / Codex / Meta
- Technisch: `BoardsModal` + `boards/*`, Backend `boards_service.py`.
- Funktion: Plot Essentials, Author's Note, Story Cards, World Info, Memory, Session.
- Reifegrad: **funktional, aber inkonsistent**.
- Befunde:
  - `[GESICHERT]` Host-Gates für zentrale Boards, eigenes Diary pro Spieler.
  - `[GESICHERT]` Labeling und Sprache teils EN-lastig.

### 3.6 Drawers (Character/NPC/Codex)
- Technisch: `DrawerHost`, `CharacterDrawer`, `NpcDrawer`, `CodexDrawer`, `drawers/selectors.ts`.
- Funktion: Sheet- und Codex-Detailansichten.
- Reifegrad: **halb migriert / technisch fragil**.
- Befunde:
  - `[GESICHERT]` Character-Drawer nutzt eigenes Tab-System statt generischer DrawerTabs.
  - `[GESICHERT]` Character-Drawer ist sehr groß und defensiv typisiert (`readRecord`-Muster statt strikter Modelle).

### 3.7 Presence / Waiting / Session-nahe Flächen
- Technisch: `PresenceProvider`, `entities/presence/*`, `shared/waiting/*`, Backend `live_state_service.py` + `presence_service.py`.
- Funktion: SSE-Live-Sync, Activities, Blocking-Action, Waiting-Signale.
- Reifegrad: **stabil-funktional**.
- Befunde:
  - `[GESICHERT]` solide SSE-Pipeline mit TTL-Cleanup und Ping.
  - `[GESICHERT]` `campaign_sync` führt zu kompletter Campaign-Query-Invalidierung (coarse-grained).

---

## 4) Zustands- und Flow-Logik

### 4.1 Produktphasen
- `[GESICHERT]` Primärphase im Backend: `state.meta.phase` mit Kernwerten `lobby`, `world_setup`, `character_setup_open`, `ready_to_start`, `active`.
- `[GESICHERT]` Setup-Services setzen die Phase aktiv; Turn-Service blockt Storyturns solange nicht `active`.

### 4.2 Frontend-Gating
- `[GESICHERT]` `deriveRouteRenderState` kombiniert Claim- und Setup-Gate.
- `[GESICHERT]` `canonical_workspace` kann `setup` sein, während gerenderter Workspace weiter `claim`/`play` bleibt und Setup als Overlay eingeblendet wird.
- `[ABGELEITET]` Verhalten ist funktional, aber konzeptionell doppelt: Route/Workspace/Overlay führen zu mehr mentaler Komplexität.

### 4.3 Disabled/Loading/Error/Empty-State
- `[GESICHERT]` viele dedizierte Wartesignale (`WaitingSurface`, `WaitingInline`, `useWaitingSignal`).
- `[GESICHERT]` Fehlerpfade vorhanden (z. B. RouteGate-Fallbacks, DrawerErrorState).
- `[ABGELEITET]` Qualität variiert je Fläche; nicht alle Flows gleich konsistent übersetzt/erklärt.

### 4.4 UI-State und Fachlogik-Kopplung
- `[GESICHERT]` zahlreiche Selektoren extrahieren Produktlogik aus Snapshot.
- `[GESICHERT]` zugleich häufig defensive `Record<string, unknown>`-Pfadlesung.
- `[ABGELEITET]` Koppelung bleibt hoch, weil UI oft nah an Roh-Snapshot-Feldern arbeitet.

---

## 5) Daten- und State-Landschaft

### 5.1 Kampagnen-Snapshot als Primärvertrag
- `[GESICHERT]` `CampaignSnapshot` enthält große Domains (`state`, `setup`, `setup_runtime`, `boards`, `active_turns`, `viewer_context`, `live` ...).
- `[GESICHERT]` zentrale Teile sind nur als `Record<string, unknown>` getypt (`state`, `setup`, `claims`, etliche Untermodelle).
- `[ABGELEITET]` API ist flexibel, aber typing-schwach und fehleranfälliger bei Evolution.

### 5.2 Globale State-Bereiche (Backend)
- `[GESICHERT]` `state_engine.normalize_campaign` ist zentrale Konvergenzstelle für Phasen, Setup, Codex, NPC, Ressourcen, Claims, Slots, Migrationsfelder.
- `[GESICHERT]` `build_campaign_view` serialisiert über `campaign_view.py` inkl. `viewer_context`, `setup_runtime`, `live`.

### 5.3 Kampagnenspezifische Datenquellen
- `[GESICHERT]` Persistenz als JSON je Kampagne: `/data/campaigns/{campaign_id}.json`.
- `[GESICHERT]` automatische Legacy-Importmigration aus `/data/state.json` bei leerem Storage (`ensure_campaign_storage`).
- `[GESICHERT]` Docker mountet `../../07_runtime` auf `/data`.

### 5.4 Viewer-lokale Persistenz (Frontend)
- `[GESICHERT]` LocalStorage/SessionStorage-Keyset:
  - Session: `isekaiCampaignId`, `isekaiPlayerId`, `isekaiPlayerToken`, `isekaiJoinCode`
  - Session Library: `isekaiSessionLibrary`
  - Novelty: `isekaiNoveltyState`
  - Play UI Memory: `aelunorPlayUiMemoryV1`
  - User Settings: `aelunorUserSettingsV1`
  - Context Cache: `aelunorV1ContextCache` (sessionStorage)
- `[GESICHERT]` Settings-Store migriert Legacy-Theme-Keys (`isekaiTheme*`).

### 5.5 Inkonsistente Felder / Übergangsfelder
- `[GESICHERT]` starke Legacy-Kompatibilität im State-Kern:
  - `is_legacy_campaign`, `migrate_campaign_to_dynamic_slots`
  - Legacy-Ressourcen-Shadow-Writeback optional
  - heuristisches Legacy-Backfill optional
- `[GESICHERT]` Context-Typing-Differenz:
  - `ContextServiceDependencies` erwartet teils `Dict`-Signaturen
  - implementierte `state_engine`-Funktionen arbeiten für den Index mit `List[Dict]`
- `[ABGELEITET]` Laufzeit stabil, aber statische Typkohärenz ist unvollständig.

---

## 6) UI- und Komponentenarchitektur

### 6.1 Positive Strukturmerkmale
- `[GESICHERT]` klare Feature-Verzeichnisse und lokalisierte Mutations-/Selector-Layer.
- `[GESICHERT]` Route-Zustand ist URL-serialisierbar und reproduzierbar.
- `[GESICHERT]` Surface-Stack/Focus-Return für Modale/Drawer ist vorhanden.

### 6.2 Überladene / monolithische Bereiche
- `[GESICHERT]` `CampaignWorkspace.tsx` orchestriert sehr viele Verantwortungen (Routing-Surfaces, Novelty, Memory, Modale, Turnaktionen, Persistenz).
- `[GESICHERT]` `CharacterDrawer.tsx` ist groß und vereint Datenmappung, Rendering, Exportlogik, Tabs.
- `[ABGELEITET]` Diese Dateien sind Hotspots für Regressionen.

### 6.3 Duplikate/Parallelkonzepte
- `[GESICHERT]` Character-Tabs existieren sowohl generisch (`DrawerTabs`) als auch separat inline im CharacterDrawer.
- `[GESICHERT]` Legacy- und v1-UI-Konzepte leben parallel (global CSS + Hybrid-Komponenten).

---

## 7) Styling / Theme / Designsystem-Istzustand

### 7.1 Vorhandene Systematik
- `[GESICHERT]` Token- und Theme-Struktur in `shared/styles/tokens/*` + `ThemeProvider` über `data-*`-Attribute.
- `[GESICHERT]` umfangreiche globale Styles in `globals.css`.

### 7.2 Parallel laufende Legacy-Stile
- `[GESICHERT]` `main.tsx` lädt Legacy-CSS global zusätzlich.
- `[GESICHERT]` Character-Drawer nutzt eigene Legacy-Styleschicht mit gesonderten Variablen und Layoutregeln.
- `[ABGELEITET]` Stylesprache ist nicht vollständig konsolidiert; visuelle Kollisionen sind strukturell erwartbar.

### 7.3 Strukturelle UI-Spannungen
- `[GESICHERT]` gemischte Begriffswelten und Labeling (DE/EN) quer durch Hub/Claim/Setup/Boards/RightRail.
- `[ABGELEITET]` Das wirkt nicht nur kosmetisch, sondern erschwert konsistente Produktsemantik.

---

## 8) Multiplayer / Sichtbarkeit / Sync

### 8.1 Presence / Session / Claims
- `[GESICHERT]` Presence-Endpunkte + SSE-Stream (`/events`) mit Query-Auth (`player_id`, `player_token`).
- `[GESICHERT]` Presence-Activities + Blocking-Action haben TTL-basierte Cleanup-Logik.
- `[GESICHERT]` Claim-/Takeover-/Unclaim-Flow ist serverseitig abgesichert (Auth + Phase + Ownership).

### 8.2 Live-Sync-Modell
- `[GESICHERT]` `campaign_sync` invalidiert im Frontend den gesamten Campaign-Snapshot.
- `[ABGELEITET]` robust bei Korrektheit, aber kostenintensiv und potenziell ruckelig bei wachsendem Snapshot.

### 8.3 Viewer-lokal vs synchronisiert
- `[GESICHERT]` lokale Komfortzustände (Theme, UI-Memory, Novelty) sind bewusst clientlokal.
- `[GESICHERT]` kampagnenrelevanter Zustand kommt serverseitig aus Snapshot + SSE.
- `[ABGELEITET]` Trennung ist grundsätzlich sauber, wird aber durch defensive Rohdatenzugriffe weniger transparent.

---

## 9) Canon / Narrator / Game-Logic-Verzahnung

### 9.1 Technische Lage
- `[GESICHERT]` Turn-Orchestrierung liegt in `turn_engine.create_turn_record`.
- `[GESICHERT]` Pipeline umfasst Narrator-Call, Patch-Sanitize/Validate/Apply, Extractor-Pässe, Canon-Gate, Progression-Events, NPC-Extractor, Codex-Trigger, Memory-Rebuild.

### 9.2 Canon-Gate-Istzustand
- `[GESICHERT]` Konstante Domänenliste in `main.py`: `("progression", "items", "location", "faction", "injury", "spellschool")`.
- `[GESICHERT]` aktiv ist derzeit nur `{ "progression" }`.
- `[ABGELEITET]` Canon-Gate ist teilaktiviert und damit funktional vorhanden, aber nicht voll ausgerollt.

### 9.3 UI-Kopplung
- `[GESICHERT]` Turn-Responses enthalten zahlreiche Diagnose-/Meta-Felder (`canon_gate`, `progression_events`, `npc_updates`, `codex_updates`, Patches).
- `[ABGELEITET]` v1 nutzt davon nur Teile explizit; Potenzial und Komplexität liegen bereits im Vertrag.

---

## 10) Legacy-Map (explizit)

### 10.1 Parallel existierende Systeme
- `[GESICHERT]` Legacy-Frontend: `app/static/index.html` + `app/static/app.js` (4428 Zeilen JS) + `style.css`.
- `[GESICHERT]` v1-Frontend: `ui/src/*` + `ui/dist/*`.

### 10.2 Legacy in Backend-State
- `[GESICHERT]` aktive Migrations- und Kompatibilitätspfade in `state_engine` für Slots, Ressourcen, Klassen/Skills, Shadow-Felder.
- `[GESICHERT]` optionales Legacy-Writeback und heuristischer Backfill via Environment-Flags.

### 10.3 Legacy in v1-UI
- `[GESICHERT]` globale Legacy-CSS-Imports in v1.
- `[GESICHERT]` Hybrid-Character-Drawer als prominentester Mischbereich.

---

## 11) Reifegrad-Einschätzung pro Bereich

| Bereich | Einstufung | Begründung (kurz) |
|---|---|---|
| Backend Router/Service-Schnitt | stabil / produktreif | klare Router-Domänen, Tests vorhanden |
| Backend State-/Turn-Kern | funktional, aber technisch fragil | sehr große Kernmodule, starke Global-Kopplung |
| v1 Routing + Session-Gates | funktional, aber inkonsistent | robustes Gating, jedoch Overlay/Canonical-Mehrdeutigkeit |
| Setup-System | halb migriert / Übergang | fachlich stark, UI-/Text-Konsistenz uneinheitlich |
| Claim-/Presence-Flows | funktional, aber inkonsistent | gute Kernlogik, teils gemischte UX-Sprache |
| Play-Workspace | funktional, aber inkonsistent | viel Funktion, zentrale Orchestrierungsmonolithen |
| Drawers | halb migriert / technisch fragil | Character-Drawer-Hybrid + duplizierte Tab-Patterns |
| Styling/Theme | halb migriert / Übergang | modernes Token-System + globale Legacy-Layer parallel |
| Multiplayer Sync | stabil-funktional | SSE + TTL + Blocking solide, Invalidation grob |
| Legacy-Altbestand | Legacy-Rest mit aktiver Rolle | weiterhin Runtime-pflichtig und Migrationsrelevant |

Unsicherheiten:
- `[UNKLAR]` Ob/ab wann Legacy-Root (`/`) offiziell abgeschaltet werden soll, ist im Code nicht als Roadmap markiert.

---

## 12) Priorisierte Hotspots, Schulden, Risiken

### Kritisch
1. **Monolithischer State-/Turn-Kern + Global-Wiring**
- Risiko: hoher Änderungsaufwand, Regressionen, erschwerte Domänenentkopplung.
- Evidenz: `state_engine.py` (14141), `turn_engine.py` (2076), `configure(globals())`-Pattern.

2. **Parallelbetrieb Legacy + v1 auf Runtime-Ebene**
- Risiko: Produktdrift, doppelte Pflege, unklare Support-Grenzen.
- Evidenz: `/` -> Legacy, `/v1/*` -> React.

### Hoch
3. **Hybrid-Character-Drawer**
- Risiko: UI-/CSS-Kollisionen, inkonsistente Weiterentwicklung, schwer testbar.
- Evidenz: `legacyCharacterSheet.css`, `legacy-character-*` Klassen, eigenes Tab-System.

4. **Coarse-grained Sync-Invalidation**
- Risiko: bei größerer Kampagne unnötige Re-Render/Netzlast.
- Evidenz: Mutations + SSE invalidieren jeweils gesamten Campaign-Key.

5. **Typing-Unsicherheit im Snapshot-UI**
- Risiko: stille Feldfehler, späte Laufzeitprobleme.
- Evidenz: breiter Einsatz von `Record<string, unknown>` + defensive Parser.

### Mittel
6. **Sprachliche Inkonsistenz (DE/EN)**
- Risiko: Produktfriktion, uneinheitliche Semantik in Setup/Claim/Hub/Boards.

7. **Dokumentationsdrift**
- Risiko: Onboarding-/Betriebsfehler.
- Evidenz: README fokussiert Legacy-Frontend, v1-Laufzeitpfad nicht gleichwertig dokumentiert.

---

## 13) Rehaul v1 als reale Baseline

### Was v1 aktuell real ist
- `[GESICHERT]` **Kein rein visueller Facelift**: Routing, Session-Gates, Surface-Management, Settings/Theming, Presence-Integration und Feature-Cluster sind modernisiert.
- `[GESICHERT]` **Aber auch kein abgeschlossener Architekturwechsel**: zentrale Game-Logik bleibt monolithisch, Legacy bleibt aktiv, UI enthält Hybrid-Zonen.
- `[ABGELEITET]` Gesamtcharakter: **Mischzustand aus UI-Modernisierung + Teilmigration + selektiver Strukturverbesserung**.

### Wie weit v1 in der Praxis ist
- v1 trägt den Haupt-Playflow technisch bereits end-to-end.
- Legacy ist jedoch weiterhin Laufzeitrealität und kein rein historischer Rest.
- Rehaul ist im Frontend deutlich sichtbar, im Domänenkern nur teilweise strukturell angekommen.

### Sinnvolle reale Ausgangsbasis für nächste Arbeit
- Baseline sollte **v1 als primären Produktpfad** nehmen, aber folgende IST-Schulden als harte Randbedingungen akzeptieren:
  - Legacy-Parallelbetrieb
  - monolithischer State-/Turn-Kern
  - Hybrid-Drawer + globale Legacy-CSS
  - Snapshot-Typing-Lücken

---

## 14) Test- und Stabilitätsindikatoren

- `[GESICHERT]` Backend Unit-Tests: `34 passed` (`pytest -q tests/unit`).
- `[GESICHERT]` Frontend Tests: `15 files, 43 tests passed` (`vitest run`).
- `[ABGELEITET]` Gute Basis für Kernservices und Utility-Layer; End-to-End-Integrationstests über Legacy/v1-Parallelbetrieb sind nicht sichtbar.

---

## 15) Unklarheiten / offene Prüfpunkte

- `[UNKLAR]` Offizielle Abschaltstrategie für Legacy-Root und globale Legacy-CSS.
- `[UNKLAR]` Geplantes Zielniveau für Canon-Gate-Domänen (aktuell nur `progression` aktiv).
- `[UNKLAR]` Ob Snapshot-Typing schrittweise verschärft wird oder bewusst flexibel bleiben soll.

---

## After Coding

### Analysierte Dateien / Cluster (Schwerpunkt)
- Runtime/Entry: `app/main.py`, `ui/vite.config.ts`, `ui/dist/*`, `app/static/*`, `docker-compose.yml`, `README.md`.
- Backend Router: `app/routers/*.py`.
- Backend Services: `campaign_service.py`, `setup_service.py`, `claim_service.py`, `turn_service.py`, `presence_service.py`, `context_service.py`, `boards_service.py`, `live_state_service.py`, `sheets_service.py`.
- Backend Kern: `state_engine.py`, `turn_engine.py`, `serializers/campaign_view.py`, `helpers/setup_helpers.py`, `setup_catalog.json`.
- Frontend App/Providers/Routing: `ui/src/app/*`.
- Frontend Features: `ui/src/features/{session,claim,setup,play,boards,drawers,context,scenes}/*`.
- Frontend Shared/State: `ui/src/shared/*`, `ui/src/state/layoutStore.ts`, `ui/src/entities/{presence,settings}/*`.

### Neu angelegte Dateien
- `docs/IST_ANALYSE_REHAUL_V1_2026-03-11.md`

### Struktur der IST-Dokumentation
- Before Coding (Strategie, Rehaul-Abgrenzung, Dokuablage)
- Architektur- und Laufzeitkarte
- Rehaul-v1- und Legacy-Mapping
- Screen-/Flow-Kartierung
- State-/Daten-/Persistenzanalyse
- UI-/Style-/Komponentenbewertung
- Multiplayer/Canon-Verzahnung
- Reifegradmatrix
- Hotspots/Risiken
- Baseline-Fazit
- After Coding (Audit-Trail)

### Wichtigste Erkenntnisse Codezustand
- Services/Router sind gut modularisiert, Kernlogik bleibt aber hochgradig monolithisch.
- Snapshot- und UI-State funktionieren, sind aber typseitig defensiv statt streng.
- Synchronisation ist robust, aber invalidiert grob.

### Wichtigste Erkenntnisse Rehaul-v1-Zustand
- v1 ist funktional tragfähig und deckt den Hauptflow ab.
- Rehaul ist real, aber nicht vollständig konsolidiert: Legacy und Hybridzonen sind aktiv.
- Der größte sichtbare Übergangspunkt ist der Character-Drawer inkl. Legacy-Styleschicht.

### Größte Risiken / Inkonsistenzen / offene Baustellen
- State-/Turn-Kernkomplexität + Global-Wiring.
- Parallelbetrieb Legacy/v1 ohne harte Entkopplungsgrenze.
- Hybrid-UI und sprachliche Inkonsistenz in zentralen Flows.
