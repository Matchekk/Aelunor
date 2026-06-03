# Aelunor Architecture Problems Map

Stand: 2026-06-03

## Kurzfassung

Die Kernarchitektur ist spielbar und testbar, aber mehrere Bereiche sind schwer wartbar oder fragil. Die groessten Risiken liegen in der doppelten UI-Schicht, der sehr grossen zentralen State-/Generatorlogik, global injizierten Dependencies, lokaler Token-Speicherung und einigen Live-Sync-/Fehlerpfaden. Rot markierte Knoten sind problematische Stellen; gestrichelte rote Kanten zeigen Drift-, Kopplungs- oder Fragilitaetsrisiken.

## Diagramm

```mermaid
flowchart LR
  user["User"] --> browser["Browser"]

  subgraph frontend["Frontend"]
    legacy["Legacy UI\napp/static/app.js\nProblem: zweiter Clientpfad"]
    v1["React/Vite UI v1\nui/src\naktiver UI-Pfad"]
    routeGate["RouteGate + URL-State\napp/routing\nProblem: viel UI-Zustand im Router"]
    workspaces["Workspaces\nHub, Claim, Setup, Play"]
    rq["TanStack Query\nSnapshot Cache"]
    stores["Zustand Stores\nUI-only state"]
    local["Browser Storage\nlocalStorage/sessionStorage\nProblem: Tokens + viele Keys"]
    sseClient["SSE Client\nv1 ticket flow"]
    legacySse["Legacy EventSource\nProblem: Token in URL"]
  end

  browser --> legacy
  browser --> v1
  v1 --> routeGate --> workspaces
  workspaces --> rq
  workspaces --> stores
  workspaces --> local
  workspaces --> sseClient
  legacy --> legacySse

  subgraph api["Backend / API"]
    main["app/main.py\nProblem: Wiring + Constants + Domain Glue"]
    routers["Routers\napp/routers/*.py\nmostly thin adapters"]
    serializer["campaign_view.py\npublic snapshot"]
    legacyStateEndpoint["/api/state\nProblem: returns first campaign state"]
  end

  rq -- "auth headers\nX-Player-Id/Token" --> routers
  workspaces -- "mutations" --> routers
  sseClient -- "ticket -> stream" --> routers
  legacy -- "same API contracts\nparallel implementation" --> routers
  legacySse -. "player_token in query string" .-> routers
  routers --> main
  routers --> serializer
  main --> legacyStateEndpoint

  subgraph services["Services"]
    campaignService["campaign_service.py"]
    setupService["setup_service.py"]
    claimService["claim_service.py"]
    turnService["turn_service.py"]
    boardsService["boards_service.py"]
    contextService["context_service.py"]
    presenceService["presence_service.py"]
  end

  routers --> campaignService
  routers --> setupService
  routers --> claimService
  routers --> turnService
  routers --> boardsService
  routers --> contextService
  routers --> presenceService

  subgraph engines["Central Logic"]
    globalsInjection["configure(globals())\nProblem: hidden dependency injection"]
    stateEngine["state_engine.py\n12396 lines\nProblem: god module"]
    turnEngine["turn_engine.py\n1309 lines\norchestrates turn pipeline"]
    patchModules["Patch appliers\nmany small modules\nbetter direction"]
    liveState["live_state_service.py\nin-memory live registry"]
    streamTickets["presence_service.py\nin-memory stream tickets"]
  end

  main -. "injects full global namespace" .-> globalsInjection
  globalsInjection -. "runtime symbol coupling" .-> stateEngine
  globalsInjection -. "runtime symbol coupling" .-> turnEngine
  turnService --> turnEngine
  turnEngine --> patchModules
  turnEngine --> stateEngine
  campaignService --> stateEngine
  setupService --> stateEngine
  boardsService --> stateEngine
  contextService --> stateEngine
  presenceService --> streamTickets
  presenceService --> liveState

  subgraph storage["Storage"]
    campaignJson["Campaign JSON\nDATA_DIR/campaigns\nsingle persistent truth"]
    browserLocal["localStorage\nsession library, settings,\ndrafts, UI memory"]
    browserSession["sessionStorage\ncontext cache"]
    memory["Process memory\npresence, subscribers,\nblocking action, tickets"]
  end

  stateEngine --> campaignJson
  local --> browserLocal
  local --> browserSession
  liveState --> memory
  streamTickets --> memory

  subgraph external["External"]
    ollama["Ollama\nProblem: many direct generator roles"]
  end

  stateEngine --> ollama
  turnEngine --> ollama

  campaignJson -- "save -> broadcast" --> liveState
  liveState -- "SSE campaign_sync" --> sseClient
  sseClient -- "invalidate query" --> rq

  classDef problem fill:#ffe1e1,stroke:#c02626,stroke-width:2px,color:#7f1d1d;
  classDef warning fill:#fff4d6,stroke:#b45309,stroke-width:2px,color:#78350f;
  classDef ok fill:#e8f7ef,stroke:#15803d,stroke-width:1px,color:#064e3b;

  class legacy,legacySse,local,main,legacyStateEndpoint,globalsInjection,stateEngine,liveState,streamTickets,ollama problem;
  class routeGate,turnEngine,browserLocal,browserSession,memory warning;
  class routers,serializer,patchModules,campaignJson,sseClient,rq,stores ok;
```

## Rote Markierungen

### Kritische Risiken

1. `app/static/app.js:711` und `app/static/app.js:744`
   - Problem: Die Legacy-UI oeffnet SSE mit `player_token` als URL-Query.
   - Warum problematisch: Tokens in URLs koennen in Logs, Browser-History, Proxies oder Fehlerreports landen. Die v1-UI hat dafuer bereits den besseren Ticket-Flow.
   - Bessere Loesung: Legacy-SSE auf `/events/ticket` umstellen oder Legacy-UI deaktivieren, sobald v1 produktiv genug ist.

2. `ui/src/app/bootstrap/sessionStorage.ts`, `ui/src/features/session/sessionLibrary.ts`, `app/static/app.js`
   - Problem: Player-Tokens liegen dauerhaft in `localStorage` und zusaetzlich in einer Session-Library.
   - Warum problematisch: XSS oder fremde lokale Browserprofile koennen Tokens auslesen. Fuer ein lokales MVP ist das verstaendlich, aber es bleibt ein Auth-Risiko.
   - Bessere Loesung: Kurzlebige Session-Tickets, optional HttpOnly-Cookie fuer Webbetrieb, Library ohne Roh-Token oder mit explizitem Export/Import-Modell.

### Architekturprobleme

3. `app/services/state_engine.py`
   - Problem: Sehr grosses Modul mit Persistenz, Normalisierung, Setup, Kontext, Generatoren, Canon, World, Sheets und Kompatibilitaet in einem Laufzeitraum.
   - Warum problematisch: Aenderungen haben hohe Seiteneffekte; Review und Tests muessen viel Kontext halten.
   - Bessere Loesung: Weiter entlang bestehender Subsysteme extrahieren: Persistence, Setup Finalization, Context Index, Sheet Views, Generator Clients.

4. `app/main.py:1214-1260`, `app/main.py:1784-1992`, `app/services/state_engine.py:configure`, `app/services/turn_engine.py:configure`
   - Problem: `configure(globals())` injiziert implizit fast den gesamten `main.py`-Namespace in Engines.
   - Warum problematisch: Dependencies sind schwer sichtbar; fehlende Symbole fallen erst zur Laufzeit auf.
   - Bessere Loesung: Schrittweise echte Dependency-Dataclasses auch fuer State-/Turn-Engine-Cluster verwenden.

5. `app/main.py`
   - Problem: App-Wiring, Runtime-Konstanten, Prompt-/Schema-Erweiterung und Glue-Funktionen leben zusammen.
   - Warum problematisch: `main.py` ist kein reines Composition-Modul mehr und wird zum Engpass fuer Backend-Aenderungen.
   - Bessere Loesung: Konfiguration, LLM-Client und schema/prompt bootstrap in kleine Module auslagern; Router-Wiring in `main.py` belassen.

6. `app/static/app.js` neben `ui/src`
   - Problem: Zwei UIs implementieren denselben Kernflow und dieselben API-Vertraege.
   - Warum problematisch: Drift-Risiko bei Setup-, Claim-, Turn-, Presence- und Boards-Flows. Einige Security-Verbesserungen existieren nur in v1.
   - Bessere Loesung: Legacy als read-only fallback markieren, kritische Fixes portieren oder per Feature-Flag aus dem normalen Startpfad entfernen.

### Moegliche Bugs

7. `app/static/app.js:3257-3258`
   - Problem: `setupEndpointBase()` baut `/setup/world` bzw. `/setup`, waehrend die aktuellen Router `/next`, `/answer`, `/random`, `/random/apply` erwarten.
   - Warum problematisch: Legacy-Setup kann bei neuen Backend-Routen brechen oder braucht Sonderlogik an anderer Stelle.
   - Bessere Loesung: Legacy-Endpunkte zentral auf die aktuellen Router-Pfade synchronisieren oder Legacy-Setup ausblenden.

8. `app/main.py:1741-1747`
   - Problem: `/api/state` gibt ohne Auth den State der ersten gefundenen Kampagne oder den Initial-State zurueck.
   - Warum problematisch: Unklare Legacy-Semantik; kann versehentlich falsche Kampagne anzeigen und passt nicht zum Campaign-Auth-Contract.
   - Bessere Loesung: Endpoint nur fuer Legacy/Debug kennzeichnen, absichern oder entfernen, wenn kein Client ihn mehr braucht.

9. `ui/src/features/play/uiMemory.ts`
   - Problem: `writeState()` schreibt `localStorage` ohne `try/catch`.
   - Warum problematisch: Private mode, Quota oder Storage-Fehler koennen eine Komfortfunktion zur UI-Fehlerquelle machen.
   - Bessere Loesung: Wie bei `composerDraftStorage.ts` und `sessionLibrary.ts` Storage-Fehler still abfangen.

### Unklare Logik

10. `ui/src/app/routing/routes.ts`, `ui/src/features/play/CampaignWorkspace.tsx`
    - Problem: Scene, Boards, Drawer und Context sind im Querystring serialisiert, waehrend Drawer/Context zusaetzlich Zustand Stores nutzen.
    - Warum problematisch: Zwei UI-Wahrheiten muessen synchron bleiben; Back/Forward-Verhalten ist dadurch empfindlich.
    - Bessere Loesung: URL als alleinige Quelle fuer offene Oberflaechen definieren und Stores nur als abgeleitete Render-/Payload-Caches nutzen.

11. `app/services/live_state_service.py`
    - Problem: Presence, Blocking Actions und SSE-Subscriber sind nur pro Prozess im Speicher.
    - Warum problematisch: Reload, mehrere Worker oder Prozessneustart verlieren Live-State; Blocking Actions koennen zwischen Prozessen auseinanderlaufen.
    - Bessere Loesung: Fuer MVP dokumentieren, dass nur ein Prozess supported ist; spaeter Redis/Datei-gestuetzte Live-State-Abstraktion.

### Unnoetige Komplexitaet

12. `state_engine.py` plus `app/services/world/*.py`
    - Problem: World-Subsysteme sind teilweise extrahiert, aber ueber `state_engine.configure()` wieder eng an globale Symbole gekoppelt.
    - Warum problematisch: Die Extraktion reduziert Dateigroesse, aber nicht vollstaendig Laufzeitkopplung.
    - Bessere Loesung: Module mit expliziten Inputs/Outputs stabilisieren und globale Rueckverdrahtung pro Subsystem abbauen.

13. `ui/src/shared/ui/SettingsDialog.tsx`, `ui/src/features/setup/SetupWizardOverlay.tsx`, `ui/src/features/play/CampaignWorkspace.tsx`
    - Problem: Mehrere UI-Dateien liegen bei 500+ Zeilen und mischen Koordination, Persistenz, Modals und Renderstruktur.
    - Warum problematisch: UI-Aenderungen sind schwer zu pruefen und laufen Gefahr, Nebenverhalten zu brechen.
    - Bessere Loesung: Nur bei konkreten Feature-Aenderungen kleine Hooks/Container extrahieren, nicht als Grossrefactor.

### Fehlende oder fragile Fehlerbehandlung

14. `app/services/state_engine.py:9151`, `app/services/state_engine.py:9267`, `app/services/turn_engine.py`
    - Problem: Ollama wird fuer viele Rollen direkt genutzt: Narrator, JSON repair, Setup Copy, Random Answers, Extractors, Context.
    - Warum problematisch: Fehlerklassifikation existiert vor allem im Turn-Flow; Setup/Context koennen anders ausfallen oder unterschiedliche Fallbacks nutzen.
    - Bessere Loesung: Einheitlichen LLM-Client mit Timeouts, Rollen, Telemetrie, Fallback-Kontrakt und testbaren Fake-Adaptern einfuehren.

15. `app/services/presence_service.py`
    - Problem: Stream-Tickets liegen in einem Modul-globalen Dict.
    - Warum problematisch: Tickets verschwinden bei Neustart und funktionieren nicht ueber mehrere Backend-Prozesse.
    - Bessere Loesung: Fuer lokalen MVP okay, aber als Single-Process-Annahme dokumentieren; spaeter gemeinsamer TTL-Store.

16. `app/services/state_engine.py:10313`
    - Problem: `save_campaign()` normalisiert, schreibt JSON und broadcastet SSE in einem Ablauf.
    - Warum problematisch: Wenn Broadcast fehlschlaegt, ist die Datei schon gespeichert; Clients koennen stale bleiben, obwohl Persistenz erfolgreich war.
    - Bessere Loesung: Persistenz-Erfolg und Broadcast-Erfolg getrennt behandeln, Broadcast-Fehler loggen und optional Recovery/Reload-Fallback anbieten.
