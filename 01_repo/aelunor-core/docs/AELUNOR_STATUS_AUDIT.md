# AELUNOR STATUS AUDIT

Stand: 2026-04-23  
Scope: `Matchekk/Aelunor`, Projektwurzel `01_repo/aelunor-core`  
Ziel: ehrliche repo-basierte Einschätzung ohne Feature-Implementierung.

## Audit-Methode und harte Grenzen

Geprüft wurden echte Repository-Dateien über den GitHub-Connector: Backend-Router, Services, zentrale FastAPI-Datei, API-Schemas, neue React/Vite-UI, Routing, Presence/SSE, Setup, Claim, Play Workspace, Boards, Drawers, Settings, Legacy-UI und dokumentierte Build-/Run-Befehle.

Nicht lokal verifiziert wurden Build, Tests und Docker-Run. Der Versuch, das Repository in der Ausführungsumgebung lokal zu klonen, scheiterte an fehlender DNS-Auflösung für GitHub. Deshalb sind Aussagen zu `npm run build`, `npm run test`, `python -m py_compile` und Docker-Start nur dokumentations- und dateibasiert, nicht aus einem echten lokalen Lauf. Alles, was nicht eindeutig aus Code ableitbar war, ist als `unklar` markiert.

---

## 1. Executive Summary

Aelunor ist kein leerer Prototyp mehr. Backend, Session-Erstellung, Join, Claim, Setup, Turn-Erzeugung, Boards, Character-/NPC-Sheets und SSE-Presence sind technisch sichtbar vorhanden. Gleichzeitig ist das System noch nicht in einem belastbaren MVP-Zustand, weil die Kernlogik stark über große `Dict[str, Any]`-Strukturen, eine sehr große `app/main.py` und viele implizite State-Konventionen läuft. Die neue React-UI unter `/ui` ist strukturiert und unter `/v1` sauber geroutet, wirkt aber produktseitig noch stark wie eine technische Arbeitsoberfläche mit vielen gleich lauten Panels, Cards, Statuschips und Utility-Flächen. Der Story-first-Anspruch ist im Code erkennbar, aber visuell und im Nutzerfluss noch nicht konsequent genug umgesetzt.

Der Hauptflow ist teilweise funktionsfähig: Hub öffnen, Session erstellen oder joinen, lokale Session speichern, Campaign laden, Setup durchführen, Slot claimen, Play Workspace öffnen, Composer nutzen, Turn senden und Timeline aktualisieren. Nicht ausreichend hart belegt ist, dass dieser Flow stabil als End-to-End-MVP funktioniert, weil keine laufenden Tests oder lokalen Builds ausgeführt werden konnten und die Testabdeckung im Repository nicht eindeutig sichtbar ist. Presence ist technisch vorhanden, aber robustheitsseitig schwach: Token liegen in der SSE-URL, Live-State ist in-memory und Reconnect-/Offline-Verhalten ist nur oberflächlich behandelt. Canon/Narrator/Game-Logic ist deutlich weiter als eine UI-Shell, aber stark monolithisch und schwer kontrollierbar.

Wichtigste Erkenntnis: Aelunor hat bereits eine erstaunlich breite technische Foundation, aber die Breite ist dem Produkt vorausgelaufen. Der nächste sinnvolle Schritt ist nicht mehr Features bauen, sondern den spielbaren Kernpfad stabilisieren, Typ-/State-Grenzen härten, Story-first-Hierarchie erzwingen und danach erst Multiplayer/Presence und Canon-Systeme weiter ausbauen.

---

## 2. Reifegrad-Tabelle

| Bereich | Prozent | Begründung | Sicherheit |
|---|---:|---|---|
| Technischer Foundation-Reifegrad | 62% | FastAPI, modulare Router, React/Vite-UI, React Query, Zustand, SSE, Settings und Boards sind vorhanden. Risiko bleibt durch monolithische `main.py`, viele `Dict[str, Any]` und unklare automatisierte Tests. | mittel |
| Backend-Reifegrad | 64% | Campaign-, Claim-, Setup-, Turn-, Presence-, Boards-, Sheets- und Context-Router existieren. Persistenz und Domain-Modelle wirken aber JSON-/Dict-lastig und nicht transaktional abgesichert. | mittel |
| Frontend-Struktur-Reifegrad | 66% | `/v1` Routing, `AppRoot`, `RouteGate`, `PresenceProvider`, Hub, Claim, Setup Overlay, Campaign Workspace, Boards, Drawers, Settings sind vorhanden. Struktur ist besser als Legacy, aber UI-State ist breit verteilt. | hoch |
| UX-/Produkt-Reifegrad | 43% | Flow existiert, aber Play Screen ist noch zu stark Panel-/Card-/Admin-orientiert. Story, Status, Utility, Setup und Meta konkurrieren visuell. | mittel |
| Story-/Narrator-Reifegrad | 55% | Turn-Service, Narrator-/Canon-/Extractor-Schemata, Intro-Retry, Patch-Zusammenfassung und Memory-Ansätze sind vorhanden. Stabilität, Widerspruchsschutz und saubere Trennung sichtbar vs. intern bleiben kritisch. | mittel |
| Multiplayer-/Presence-Reifegrad | 45% | SSE, Presence Activity, Blocking Actions und Live Snapshot existieren. In-memory Live-State, Token in Query-URL, unklare Multi-Tab- und Reconnect-Härtung. | mittel |
| Test-/Stabilitäts-Reifegrad | 22% | Frontend-Skripte für Vitest existieren, README nennt manuelle Checks. Konkrete Testdateien/CI konnten über Suche nicht belegt werden. Lokaler Lauf nicht möglich. | niedrig |
| MVP-Reifegrad insgesamt | 50% | Ein vertikaler spielbarer Kern scheint erreichbar, aber noch nicht belastbar genug. Größte Lücken: E2E-Stabilität, State-Härtung, Story-first UX, Tests, Presence-Sicherheit. | mittel |

---

## 3. Feature-Matrix

| Bereich | Feature | Status | Evidenz aus Dateien | Risiko | Nächster sinnvoller Schritt | Aufwand |
|---|---|---|---|---|---|---|
| Session Hub | Hub als Campaign Gateway | teilweise | `ui/src/features/session/SessionHubWorkspace.tsx`, `HubContinuationPanel`, `CreateCampaignCard`, `JoinCampaignCard` | Wirkt funktional, aber noch stark wie Session-Verwaltung plus Diagnosebereich. | Hub-Happy-Path visuell und textlich auf „Kampagne betreten“ zuschneiden. | M |
| Session Hub | Session erstellen | vorhanden | `app/routers/campaigns.py`, `campaign_service.create_campaign`, `session/mutations.ts` | Ohne E2E-Test nicht belastbar validiert. | API- und UI-Test für Create-Flow. | M |
| Session Hub | Session joinen | vorhanden | `POST /api/campaigns/join`, `campaign_service.join_campaign`, `useJoinCampaignMutation` | Join-Code-Fehler und bereits existierende Identitäten unklar UX-seitig. | Fehlerzustände im Hub testen und klarer machen. | S |
| Session Hub | Session fortsetzen | teilweise | `SessionHubWorkspace.bootstrapSession`, `campaignQueryOptions`, lokale Session Library | Kein eigener Resume-Endpunkt; Resume hängt an localStorage-Credentials und GET Campaign. | Resume-Validierung und kaputte lokale Daten als eigene Testfälle. | M |
| Session Hub | Local Active Session | vorhanden | `app/bootstrap/sessionStorage`, `SessionHubWorkspace`, `readSessionLibrary` | localStorage ist fragil, Migration/Schema-Version für Sessions nur begrenzt belegt. | Session Storage Validator mit Reparatur-/Reset-Pfad. | M |
| Routing | Route Gate | vorhanden | `AppRoot.tsx`, `RouteGate.tsx`, `routing/selectors.ts`, `routes.ts` | Gate-Logik ist gut, aber komplexe Redirects können Edge Cases erzeugen. | Router-Selector-Tests für root/hub/campaign/setup/claim/play. | M |
| Presence | Presence Provider | vorhanden | `PresenceProvider.tsx`, `entities/presence/store.ts` | Store ist sauber, aber UI-Verhalten bei dauerhafter SSE-Störung wirkt dünn. | Offline-/Reconnect-Banner und Tests ergänzen. | M |
| Presence | SSE | technisch vorhanden, produktseitig unvollständig | `app/routers/presence.py`, `live_state_service.py`, `sseClient.ts` | Player-Token wird als Query-Parameter in EventSource-URL übertragen. In-memory State geht bei Neustart verloren. | SSE-Auth entschärfen und Reconnect-/Offline-Verhalten produktisieren. | L |
| Setup | Setup Wizard Overlay | vorhanden | `SetupWizardOverlay.tsx`, `setup_service.py`, `app/routers/setup.py` | Sehr mächtig, aber komplex. Turbo-Random kann schlechte Setups erzeugen und sollte nicht prominent bleiben. | Setup-Happy-Path testen, Turbo verstecken/kennzeichnen. | M |
| Setup | Campaign Setup | vorhanden | World next/answer/random/apply/finalize in `setup.py` und `setup_service.py` | Host-Abhängigkeit klar, aber Wartezustände und Halbzustände brauchen Tests. | Tests für halb abgeschlossenes World Setup. | M |
| Setup | Character Setup | vorhanden | Slot-basierte Character-Setup-Endpunkte und `finalize_character_setup` | Abhängigkeit Claim/World/Character ist korrekt, aber komplex. | Flow-Test: world complete -> claim -> character complete -> play. | L |
| Claim | Party/Slot Claim State | vorhanden | `claim_service.py`, `ClaimWorkspace.tsx`, `claim/selectors.ts` | Takeover erlaubt auch belegte Slots; produktseitig muss klar sein, wann das okay ist. | Takeover-Regeln und Texte schärfen. | S |
| Party | Party State | teilweise | `CampaignSnapshot.party_overview`, `RightRail.tsx`, `sheets.py` | Anzeige vorhanden, aber Party-Logik und Konflikte bei Multi-User unklar. | Party-Zustände als Domain-View definieren und testen. | M |
| Story | Story Timeline | vorhanden | `StoryTimeline.tsx`, `play/selectors.ts` | Card-Liste funktioniert, ist aber noch nicht stark genug als Story-Bühne. | Timeline visuell als Hauptlesefläche priorisieren. | M |
| Story | Composer | vorhanden | `Composer.tsx`, `useSubmitTurnMutation`, `deriveComposerAccessState` | Drafts sind nur lokaler React-State; Refresh/Tab-Wechsel verlieren Eingaben. | Draft-Persistenz pro Campaign/Mode mit Recovery. | M |
| Story | Narrator Response Flow | teilweise | `turn_service.py`, `create_turn_record` über Dependencies, `main.py` Narrator-/Schema-Konstanten | Echte Logik ist vorhanden, aber stark in `main.py`/Dependencies versteckt. | Turn Engine Boundary dokumentieren und mit Integrationstest sichern. | L |
| Canon | Canon State | teilweise | `main.py` Canon Extractor Schema/Prompt, `CANON_GATE_ACTIVE_DOMAINS={"progression"}` | Nur Progression-Gate aktiv; Widerspruchsschutz für Orte/Items/Factions nicht ausreichend belegt. | Canon-Gate-Domänen priorisieren und Testmatrix bauen. | L |
| Codex/Lore | Codex/Lore | teilweise | Codex-Konstanten in `main.py`, `RightRail.tsx`, `DrawerHost.tsx`, `drawers/selectors.ts` | Race/Beast sichtbar, breiter Lore-/World-Codex noch nicht klar als stabiles Produktmodell. | Codex Entry Domain Contract stabilisieren. | M |
| Scene/Location | Scene/Location State | teilweise | `play/selectors.ts`, `scenes/selectors`, Route Query `scene` | Szenen werden aus State/Patches abgeleitet; Datenmodell wirkt implizit. | Scene Domain Model + Migration/Validation einführen. | M |
| Inventory/Progression | Inventory/Progression | teilweise | Character sheet contracts, `DrawerHost`, `main.py` progression/element constants | UI zeigt Inventar/Skills; echte Regeln sind vorhanden, aber schwer prüfbar. | Progression-Regeln isoliert testen. | L |
| Boards | Boards | vorhanden | `BoardsModal.tsx`, `boards.py`, `boards_service.py` | Produktseitig wertvoll, aber Boards können Story-Surface überladen, wenn zu prominent. | Boards als sekundäre Surface klarer abgrenzen. | S |
| Drawers | Drawers | vorhanden | `DrawerHost.tsx`, `drawerStore.ts`, sheet endpoints | Gute Surface-Logik, aber Store plus URL-State kann auseinanderlaufen. | Drawer-Route-State-Tests. | M |
| Settings | Settings Popup | vorhanden | `SettingsDialog.tsx`, `TopBar.tsx`, `entities/settings/store.ts` | Settings sind breit und solide, aber einige Optionen sind vorbereitet statt vollständig produktiv. | Settings in „global comfort“ vs. „game rules“ trennen. | S |
| Loading/Waiting | Waiting Framework | vorhanden | `WaitingFullStage`, `WaitingSurface`, `WaitingInline`, `useWaitingSignal` in Setup/Composer/RouteGate/DrawerHost | Gute technische Grundlage. Produkttexte teils generisch. | Waiting-Klassen pro Scope auditieren und vereinheitlichen. | M |
| Error Handling | Error States | teilweise | RouteGate Failure UI, Composer/Boards/Drawer errors, `turn_service` Trace/Error-Code | Backend hat Error-Codes, UI nutzt teils generische Meldungen. | Fehlerkatalog Frontend/Backend mappen. | M |
| Empty States | Empty States | teilweise | Timeline empty, Claim empty, Setup no-question, RightRail empty | Vorhanden, aber noch nicht überall story-/produktgeführt. | Empty-State Copy story-first überarbeiten. | S |
| Responsive Layout | Responsive Verhalten | unklar | CSS nicht vollständig auditiert; Komponenten nutzen Grids/Panels | Ohne visuellen Lauf nicht belegbar. | Responsive Smoke-Test für Hub/Setup/Play/Drawer. | M |
| Tests | Frontend Tests | unklar bis fehlt | `package.json` hat `vitest run`; Suche fand keine eindeutigen Testdateien | Testskript ohne Tests ist falsche Sicherheit. | Minimaler Selector-/Route-/Flow-Test-Satz. | M |
| Tests | Backend Tests | unklar bis fehlt | README nennt manuelle Checks/Skripte, keine klare pytest-Struktur gefunden | Kernlogik ohne Regression-Schutz. | Backend-Service-Tests für Campaign/Setup/Turn. | L |
| Dokumentation | README/Runbook | teilweise | `README.md` dokumentiert Docker/Ollama/Checks | Neue `/v1` UI und Migration nicht ausreichend als Produkt-/Dev-Guide sichtbar. | `docs/DEV_RUNBOOK.md` und `docs/MVP_FLOW.md`. | S |
| Legacy | Legacy UI aktiv | vorhanden | `app/static/index.html`, README nennt Frontend in `app/static/`; neue UI zusätzlich unter `/ui` | Zwei UIs können UX, State und Wartung auseinanderziehen. | Legacy Freeze Plan und Removal Criteria definieren. | M |
| Legacy | Legacy-Migration | teilweise | Neue UI unter `/v1`, Legacy unter `/` laut Kontext/README | Alte und neue Patterns existieren parallel. | Migration-Checkliste und Feature-Parität definieren. | M |

---

## 4. Nutzerflow-Prüfung

| Schritt | Bewertung | Begründung |
|---|---|---|
| 1. Nutzer öffnet Aelunor | funktioniert | `AppRoot` redirectet unbekannte Pfade auf `/v1`; Legacy bleibt separat über statische App erreichbar. |
| 2. Nutzer sieht Hub | funktioniert | `RouteGate` rendert `SessionHubWorkspace` bei `/v1/hub`. |
| 3. Nutzer erstellt oder resumed Session | teilweise | Create/Join/Resume sind implementiert. Resume hängt an localStorage und GET Campaign. Kaputte lokale Daten werden teilweise behandelt, aber nicht ausreichend testbelegt. |
| 4. Nutzer macht Setup | teilweise | Setup Overlay und Backend-Endpunkte sind vorhanden. Komplexe Halbzustände, Host-Warten und Turbo-Random brauchen E2E-Absicherung. |
| 5. Nutzer landet im Campaign Workspace | funktioniert | RouteGate leitet anhand Claim/Setup-State in Claim oder Play. |
| 6. Nutzer schreibt in Composer | funktioniert | Composer kann Modi, Drafts, Submit, Context Query und Presence Typing. Draft-Persistenz fehlt. |
| 7. Narrator antwortet | teilweise | Turn-Service und Narrator-/Canon-Infrastruktur existieren. Ob Ollama/Schema/Retry im realen Lauf stabil genug ist, wurde nicht lokal validiert. |
| 8. Story Timeline aktualisiert sich | teilweise | Mutation invalidiert Campaign Query; SSE `campaign_sync` invalidiert ebenfalls. Kein realer Run geprüft. |
| 9. Party/Presence/State bleiben konsistent | teilweise | Party Overview und Presence existieren. Multi-Tab, Race Conditions und Prozessneustart sind nicht ausreichend gehärtet. |
| 10. Nutzer kann später zurückkehren | teilweise | Local Session Library und Resume existieren. LocalStorage-Schäden, gelöschte Backend-Session und Token-Rotation sind noch riskant. |

---

## 5. Architekturdiagnose

### Backend

**Was gut ist**
- Es gibt echte Router-Trennung für Campaigns, Claim, Setup, Turns, Presence, Boards, Sheets und Context.
- Campaign Create/Join/Get, Turn Create/Edit/Undo/Retry, Setup World/Character, Boards und Sheets sind echte API-Flächen.
- Turn-Service hat brauchbare Guardrails: Actor muss existieren, Content darf nicht leer sein, Phase muss `active` sein, Intro muss existieren, Claim wird geprüft.
- Fehler im Turn-Flow werden mit Trace-ID und Error-Code klassifiziert.
- Setup-Service erzwingt Host-Rechte für Welt-Setup und Claim-Besitz für Character Setup.

**Was kritisch ist**
- `app/main.py` ist zu groß und enthält zu viele Konstanten, Schemata, Prompt-/Canon-/Progression-Definitionen und vermutlich Kernfunktionen. Das ist ein Wartungs- und Regression-Risiko.
- Backend-State ist überwiegend `Dict[str, Any]`. Das macht schnelle Iteration leicht, aber mittel- bis langfristig gefährlich, weil Domain-Änderungen nicht sauber typisiert brechen.
- Lokale JSON-Persistenz ist für MVP okay, aber ohne klar belegte Locking-/Transaktionsstrategie riskant bei mehreren Tabs/Spielern.
- Presence ist in-memory und nicht persistent. Nach Restart ist Live-State weg, was für Presence okay ist, aber für Blocking Actions und laufende Aktionen gefährlich wirken kann.
- `OLLAMA_URL`/Modelle sind konfigurierbar, aber echte LLM-Verfügbarkeit ist optional/extern und nicht im Audit ausführbar.

### Frontend

**Was gut ist**
- `/v1` ist sauber über `AppRoot` und `RouteGate` gekapselt.
- React Query, Zustand Stores, Surface Layer, Waiting Components, Settings und Route-State ergeben eine moderne Frontend-Basis.
- Hub, Claim, Setup, Play, Boards, Drawers und Settings sind keine reinen Dummies.
- Composer und Timeline haben echte Produktlogik für Modes, Disabled Reasons, Intro-Status, Patch Summary, Edit/Undo/Retry/Continue.

**Was kritisch ist**
- Der Play Screen hat weiterhin ein hohes Risiko, wie Admin-Software statt Story-Oberfläche zu wirken. Viele Chips, Cards, Panels, Tabs und Utility-Flächen konkurrieren.
- URL-State, Zustand Store und lokale UI-Memory laufen parallel. Das ist mächtig, aber fragil.
- Drafts im Composer sind nur React-State. Ein Refresh verliert Eingaben.
- RightRail behauptet, Tagebuchzeilen mit `//` blieben lokal privat, sendet aber den gesamten Tagebuchinhalt über `patch_player_diary`. Das ist ein Produkt-/Vertrauensproblem und muss geklärt werden.

### State und Datenfluss

| State-Bereich | Fundort | Bewertung |
|---|---|---|
| Session State | `sessionStorage`/localStorage Bootstrap, Session Library | vorhanden, aber browserfragil |
| Campaign State | Backend Campaign JSON, `CampaignSnapshot` | vorhanden, aber stark `Record/Dict` |
| Setup State | Backend `campaign["setup"]`, `setup_runtime`, Setup Overlay | vorhanden, komplex |
| Story/Narrator State | `active_turns`, campaign state, turn service, main/turn engine | teilweise stabil, schwer isolierbar |
| Presence State | Backend in-memory `LIVE_STATE_REGISTRY`, Frontend Zustand | technisch vorhanden, robustheitsseitig schwach |
| UI Surface State | URL Query, Zustand Stores, `useSurfaceLayer` | technisch gut, aber komplex |
| Canon State | campaign state plus extractor/gate constants | teilweise, Domain-Abdeckung unvollständig |
| Codex/Lore | World races/beasts, drawers, right rail | teilweise |
| Inventory/Progression | Character sheet contracts, progression constants, drawer tabs | teilweise |

### Tests

- Frontend-Testskript existiert: `vitest run`.
- Backend-README nennt manuelle Checks und einzelne Script-Checks.
- Konkrete Testdateien oder CI konnten über Repository-Suche nicht belastbar belegt werden.
- Lokale Ausführung war nicht möglich.
- Konsequenz: Stabilitätsreife bleibt niedrig, egal wie viel Code bereits vorhanden ist.

### Legacy

Legacy ist noch aktiv und umfangreich. `app/static/index.html` enthält eigene Landing-, Claim-, Campaign-, Composer-, Party-, Board-, Drawer-, Setup- und Settings-Flächen. Das ist kurzfristig nützlich als Fallback und Vergleich, langfristig aber gefährlich, weil Produktlogik, UI-Sprache und State-Verhalten doppelt existieren. Neue UI und Legacy müssen jetzt bewusst getrennt werden: Legacy einfrieren, Feature-Parität definieren, danach schrittweise entfernen.

---

## 6. MVP-Gap-Analyse

### Blocker für ein echtes MVP

1. Kein belegter grüner End-to-End-Flow von Create -> Setup -> Claim -> Play -> Turn -> Resume.
2. Keine sichtbar belastbare Testbasis für Routing, Setup, Turn-Service, Canon/Progression und Presence.
3. Zu großer Anteil impliziter `Dict[str, Any]` State ohne Domain-Validierung.
4. Presence/SSE ist sicherheits- und robustheitsseitig nicht hart genug, besonders wegen Token in URL und in-memory Live-State.
5. Play Screen erfüllt Story-first noch nicht konsequent genug. Die Story ist vorhanden, aber nicht dominant genug.
6. LocalStorage-Session-/UI-Zustände sind fragil bei kaputten Daten, mehreren Tabs und gelöschten Backend-Sessions.
7. Narrator/Canon wirkt technisch vorhanden, aber schwer isolierbar und schwer regressionssicher.

### Wichtige, aber nicht blockierende Lücken

- Bessere Empty-State-Texte.
- Polished mobile/responsive Layout.
- Mehr visuelle Motive im Waiting Framework.
- Mehr Story-Codex-Qualität für Lore, Fraktionen, Orte, Items.
- Export/Import als bewusstes Produktfeature statt reiner Utility.
- UI-Sprache vereinheitlichen: Deutsch/Englisch ist aktuell gemischt.

### Technische Schulden

- Massive `main.py` als Systemkern.
- Backend Domain Models sind nicht sauber typisiert.
- Frontend Contracts enthalten große `Record<string, unknown>` Flächen.
- URL-State, Zustand und localStorage sind gleichzeitig aktiv.
- Keine klare Migration/Versionierung für Campaign State sichtbar.
- Legacy und v1 UI existieren parallel.

### UX-Schulden

- Play Screen ist noch zu dashboard-artig.
- Story, Meta, Status, Setup und Utility sind nicht klar genug hierarchisiert.
- RightRail ist nützlich, aber visuell und semantisch zu dominant.
- Settings sind umfangreich, aber teilweise mehr App-Konfiguration als Story-Erlebnis.
- Setup Overlay ist funktional, aber sehr technisch und schwergewichtig.

### Architektur-Risiken

- Race Conditions bei mehreren Nutzern, mehreren Tabs und langsamen LLM-Antworten.
- Blockierende Aktionen können durch Restart oder Fehler inkonsistent wirken.
- Canon-Fakten können widersprüchlich werden, solange nicht alle relevanten Domänen gegatet sind.
- SSE-Token in URL kann in Logs/Browser-Tools landen.
- JSON-State kann ohne Schema-Migration brechen.

### Dinge, die später weh tun, wenn sie jetzt ignoriert werden

1. Keine State-Versionierung und Validatoren.
2. Kein Test-Harness für echten Story-Turn mit Fake Narrator.
3. Kein klares Surface-State-Modell für Boards/Drawers/Context/Setup.
4. Keine klare Legacy-Abbau-Strategie.
5. Kein Produktentscheid, was „privat“, „shared“ und „host-only“ wirklich bedeutet.

---

## 7. Priorisierte Roadmap

### Phase 1: Stabilisieren und echte Spielbarkeit herstellen

**Ziel**  
Ein einzelner Nutzer kann zuverlässig von `/v1/hub` bis zum ersten echten Story-Turn kommen und später wieder einsteigen.

**Tasks**
- Minimalen E2E-Happy-Path definieren und als Test/Script absichern.
- LocalStorage Session Bootstrap validieren, reparieren oder sauber resetten.
- Setup-Halbzustände testen: keine Frage geladen, World Setup halb fertig, Character Setup halb fertig.
- Composer-Drafts lokal persistieren.
- Backend nicht erreichbar, 401/403/404 und kaputte Session UX hart prüfen.
- Legacy bewusst einfrieren: keine neuen Features mehr in Legacy.

**Abhängigkeiten**  
Bestehende API-Routen, React Query Campaign Snapshot, Setup/Claim Selectors.

**Aufwand**  
L bis XL.

**Nutzen**  
Macht aus breitem Prototyp einen wiederholbar spielbaren Kern.

**Risiken**  
Es werden Inkonsistenzen im State sichtbar, die bisher nur verdeckt waren.

### Phase 2: Story-/Narrator-/Canon-System produktfähig machen

**Ziel**  
Story-Turns sind nachvollziehbar, persistent, editierbar, retrybar und Canon-seitig kontrollierbar.

**Tasks**
- Turn Engine Boundary dokumentieren: Input, LLM Call, Response Parse, Patch Apply, Extractor, Save.
- Fake Narrator Test Harness bauen.
- Canon-Gate-Domänen priorisieren: Progression bleibt aktiv, Location/Items/Factions als nächste Kandidaten.
- Storytext und interner Canon State als explizite Contracts trennen.
- Narrator-Fehlerzustände produktseitig lesbar machen.

**Abhängigkeiten**  
`turn_service`, `main.py` turn engine, campaign serializer.

**Aufwand**  
XL.

**Nutzen**  
Reduziert das größte Produktversprechen-Risiko.

**Risiken**  
Refactoring-Druck steigt, obwohl zunächst nur Stabilisierung gewünscht ist.

### Phase 3: UI/UX auf Story-first Qualität bringen

**Ziel**  
Play fühlt sich wie eine Story-Bühne an, nicht wie ein Admin-Dashboard.

**Tasks**
- Play Screen Hierarchie neu festlegen: Story zuerst, Composer zweitens, Party/Status sekundär.
- Statuschips reduzieren oder bündeln.
- RightRail standardmäßig leiser machen.
- Timeline-Turn-Cards in lesbare Story-Abschnitte umbauen.
- Preplay/Setup/Play Übergänge klarer erzählen.
- Deutsche UI-Sprache vereinheitlichen.

**Abhängigkeiten**  
Phase 1 stabiler Flow.

**Aufwand**  
L.

**Nutzen**  
Erhöht sofort die Produktqualität.

**Risiken**  
Zu viel optische Arbeit ohne Flow-Stabilität wäre Verschwendung. Deshalb erst nach Phase 1.

### Phase 4: Multiplayer/Presence/Sync härten

**Ziel**  
Mehrere Spieler und mehrere Tabs führen nicht zu kaputten, verwirrenden oder unsicheren Zuständen.

**Tasks**
- SSE-Token nicht mehr in Query-URL verwenden oder Risiko technisch minimieren.
- Reconnect-/Offline-State als UI-Zustand einführen.
- Multi-Tab-Verhalten definieren: gleicher Player, mehrere Tabs, konkurrierende Actions.
- Blocking Actions backendseitig robuster machen.
- Presence-Fallbacks bei SSE-Abbruch testen.

**Abhängigkeiten**  
Stabiler Campaign Snapshot und Turn Blocking.

**Aufwand**  
L bis XL.

**Nutzen**  
Macht Multiplayer glaubwürdig.

**Risiken**  
Browser EventSource schränkt Header/Auth-Möglichkeiten ein; Designentscheidung nötig.

### Phase 5: Polish, Tests, Legacy-Abbau

**Ziel**  
v1 wird die einzige relevante UI. Legacy wird entfernt oder als klarer Fallback isoliert.

**Tasks**
- Test-Suite ausbauen: selectors, route gate, setup, turn service, presence store.
- Legacy-Feature-Parität prüfen.
- Legacy-Routen/Assets einfrieren, deprecaten, entfernen.
- Dokumentation schreiben: Dev Runbook, MVP Flow, State Model, Troubleshooting.
- Responsive Audit und kleine Screens testen.

**Abhängigkeiten**  
Phasen 1 bis 4.

**Aufwand**  
L.

**Nutzen**  
Senkt langfristige Wartungskosten drastisch.

**Risiken**  
Legacy zu früh entfernen kann Debugging/Fallback erschweren.

---

## 8. Top 15 nächste Tasks

1. **MVP-Happy-Path als automatisierten Smoke-Test definieren**: create campaign, setup world, claim, setup character, enter play, fake turn, resume.
2. **Build/Test-Kommandos real laufen lassen und Ergebnis dokumentieren**: `npm run typecheck`, `npm run test`, `npm run build`, Python checks, Docker start.
3. **Session Storage Validator bauen**: ungültige localStorage/sessionStorage Daten erkennen, migrieren, löschen oder Nutzer führen.
4. **Composer Draft Recovery einführen**: pro Campaign, Slot und Mode lokal speichern.
5. **Turn Engine Boundary dokumentieren und testen**: Fake Narrator statt Ollama für stabile Tests.
6. **SSE-Auth-Risiko beheben oder bewusst dokumentieren**: Token in Query-URL ist für ein Multiplayer-System nicht sauber.
7. **RightRail Diary Privacy Bug klären**: `//` lokal privat ist aktuell nicht belegt und wahrscheinlich falsch.
8. **Setup Halbzustände härten**: keine Frage geladen, Host wartet, random/apply unterbrochen, Turbo abgebrochen.
9. **Play Screen visuelle Priorität reduzieren**: Statuschips/RightRail/Boards leiser, Story lauter.
10. **Canon Domain Matrix schreiben**: Progression, Items, Location, Faction, Injury, Spellschool mit Status und Testfällen.
11. **Campaign State Versionierung/Validation vorbereiten**: minimale Schema-Version und Validator beim Load.
12. **Route/Surface Tests bauen**: `/v1`, `/v1/hub`, campaign claim/setup/play, query states.
13. **Presence Offline/Reconnecting UI ergänzen**: nicht nur `sseConnected`, sondern sichtbarer Nutzerzustand.
14. **Legacy Freeze-Dokument erstellen**: was bleibt, was darf nicht mehr erweitert werden, Removal-Kriterien.
15. **UI-Sprache vereinheitlichen**: Deutsch/Englisch-Mix in Hub/Claim/Setup/Boards reduzieren.

---

## 9. Codex-Folgeprompts

### Prompt 1: MVP-Happy-Path Audit-Test ohne echte LLM-Abhängigkeit

Du bist Senior Product Engineer im Aelunor-Repo. Erstelle keinen neuen Produkt-Feature-Code. Ziel ist ein reproduzierbarer MVP-Smoke-Test für den Kernflow: Campaign erstellen, World Setup abschließen, Slot claimen, Character Setup abschließen, Play Workspace erreichen, einen Fake-Turn erzeugen, Campaign erneut laden. Verwende keine externe Ollama-Abhängigkeit, sondern isoliere oder mocke den Narrator minimal. Prüfe vorhandene Teststruktur und ergänze nur die kleinste sinnvolle Test-/Script-Struktur. Dokumentiere im Code oder in `docs/MVP_SMOKE_TEST.md`, wie der Test lokal ausgeführt wird. Guardrails: keine großen Refactorings, keine UI-Umbauten, keine Secrets, keine externen Services. Deliverable: lauffähiger Smoke-Test oder eine präzise Begründung, welche minimale Abstraktion noch fehlt.

### Prompt 2: Session Storage Robustness

Du bist Tech Lead für die neue Aelunor `/v1` UI. Härte den lokalen Session-Bootstrap und die Session Library gegen kaputte localStorage/sessionStorage-Daten. Prüfe `ui/src/app/bootstrap/sessionStorage`, `features/session/sessionLibrary`, `RouteGate` und `SessionHubWorkspace`. Ziel: ungültige JSON-Daten, fehlende `campaign_id`, fehlende Tokens, gelöschte Campaigns und stale credentials führen immer zu einem verständlichen Hub-Zustand mit Reset/Forget-Aktion. Keine neuen Features außer Validierung, Migration und Tests. Ergänze Selector-/Unit-Tests, falls Teststruktur vorhanden ist. Dokumentiere kurz die Edge Cases.

### Prompt 3: Turn Engine Boundary und Fake Narrator

Du bist kritischer Backend-Architekt. Prüfe den aktuellen Turn/Narrator/Canon-Flow in `app/main.py`, `app/services/turn_service.py`, `turn_engine` und zugehörigen Funktionen. Ziel: eine klare Boundary für Turn-Erzeugung definieren, damit Tests ohne Ollama möglich werden. Implementiere nur minimale Abstraktion, falls nötig. Erzeuge einen Fake-Narrator-Pfad für Tests, der eine deterministische GM-Antwort und einen minimalen Patch liefert. Keine produktiven neuen Features, keine großen Refactorings. Deliverables: kurze Doku `docs/TURN_ENGINE_BOUNDARY.md`, Tests oder Check-Script, und klare Liste der verbleibenden Risiken.

### Prompt 4: Story-first Play Screen Hierarchie Audit und kleiner UI-Fix

Du bist Senior UX/Product Engineer. Prüfe `CampaignWorkspace`, `StoryTimeline`, `Composer`, `RightRail`, `TopBar` und die zugehörigen CSS-Dateien. Ziel: Play Screen weniger dashboard-artig machen, ohne optischen Komplettumbau. Story und Composer müssen visuell wichtiger werden als Meta, Status, Boards und RightRail. Reduziere gleich laute Cards/Chips, bündele Meta-Informationen und mache RightRail sekundärer. Keine neuen Features. Keine Backend-Änderungen. Deliverable: kleine, gezielte UI/CSS-Änderungen plus kurze Begründung in einer Markdown-Notiz.

### Prompt 5: Setup Flow Edge Cases härten

Du bist Product Engineer für Aelunor Setup. Prüfe `SetupWizardOverlay`, `features/setup/selectors`, `features/setup/mutations`, `app/routers/setup.py` und `setup_service.py`. Ziel: robuste Behandlung von Edge Cases: keine aktuelle Frage geladen, World Setup halb abgeschlossen, Character Setup ohne Claim, Spieler wartet auf Host, Random Preview abgebrochen, Backend nicht erreichbar. Keine großen Refactorings. Ergänze Tests für Selector-Logik und API-Fehlerzustände, soweit vorhandene Teststruktur es erlaubt. Dokumentiere offene Fragen.

### Prompt 6: Presence/SSE Security und Reconnect Hardening

Du bist Senior Systemarchitekt. Prüfe `PresenceProvider`, `sseClient`, `presence_service`, `presence.py` und `live_state_service.py`. Ziel: Risiken bei SSE-Verbindung, Token-Transport, Reconnect, Offline-Zustand, mehreren Tabs und Blocking Actions bewerten und mit minimalen Änderungen entschärfen. Keine neue Multiplayer-Featurelogik. Wenn EventSource-Header nicht möglich sind, dokumentiere die beste realistische lokale MVP-Lösung. Deliverables: Code-Fix falls klein, sonst `docs/PRESENCE_SYNC_RISKS.md`, plus Tests/Checks für Store- und Reconnect-Verhalten.

### Prompt 7: Canon Domain Matrix und Progression Regression Tests

Du bist Canon/Game-Logic Engineer. Prüfe die Canon-/Progression-Logik in `app/main.py`, `turn_engine`, `state_engine` und vorhandene Scripts wie `check_progression_canon_gate.py`. Ziel: eine Canon Domain Matrix erstellen für Progression, Items, Location, Faction, Injury und Spellschool. Markiere pro Domain: aktiv, teilweise, nicht aktiv, Risiko, benötigte Tests. Ergänze nur für Progression minimale Regression Tests, keine neuen Canon-Domänen aktivieren. Deliverable: `docs/CANON_DOMAIN_MATRIX.md` und lauffähige Checks.

### Prompt 8: Legacy Freeze und Migration Plan

Du bist Tech Lead für die Aelunor UI-Migration. Vergleiche Legacy `app/static/*` mit neuer UI `ui/src/*`. Ziel: Legacy einfrieren und eine klare Migration-/Removal-Liste erstellen. Keine Feature-Implementierung. Dokumentiere: welche Legacy-Funktionen noch nicht sauber in v1 abgebildet sind, welche v1-Funktionen besser sind, welche Risiken doppelte UI erzeugt und ab wann Legacy entfernt werden kann. Deliverable: `docs/LEGACY_FREEZE_AND_REMOVAL_PLAN.md`.

---

## 10. Offene Fragen

1. Soll Aelunor im MVP wirklich Multiplayer-first sein oder reicht zuerst ein stabiler Single-Player/Host-Happy-Path mit späterer Multiplayer-Härtung?
2. Soll Legacy `/` aktiv nutzbar bleiben oder nur noch als Fallback/Referenz eingefroren werden?
3. Wie privat sollen Player Diaries wirklich sein? Die UI behauptet lokale private `//` Zeilen, der sichtbare Code sendet aber den gesamten Diary-Inhalt.
4. Welche Canon-Domänen sind für MVP zwingend: nur Progression oder auch Location, Items, Factions und Injuries?
5. Soll der Setup Turbo-Random in der normalen UI sichtbar bleiben oder nur als Dev-/Debug-Hilfe existieren?
6. Ist Ollama zwingend für MVP oder soll ein Fake-/Local-Dummy-Narrator als offizieller Offline-Testmodus unterstützt werden?
7. Welche Bildschirmgröße ist MVP-Priorität: Desktop, Laptop, Tablet oder Handy im WLAN?
8. Soll die neue UI nach erfolgreicher Stabilisierung `/` übernehmen und Legacy komplett ablösen?

---

## Knappe Schlussbewertung

Gesamt-MVP-Reifegrad: **50%**.

Aelunor ist technisch breit, aber noch nicht belastbar. Der Code zeigt echte Substanz: Sessions, Setup, Claims, Turns, Boards, Presence und v1 UI existieren. Das Problem ist nicht fehlende Menge, sondern fehlende Stabilisierung, klare Domain-Grenzen, Testschutz und Story-first Produktfokus. Der nächste Entwicklungsschritt sollte deshalb kein neues Feature sein, sondern ein harter vertikaler MVP-Pfad mit Fake Narrator, Tests, Storage-Härtung und einer ruhigeren Play-Hierarchie.
