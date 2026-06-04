# Aelunor Ideal Architecture Overview

Stand: 2026-06-03

## Zielbild

Dieses Diagramm zeigt, wie Aelunor idealerweise aussehen sollte, wenn die aktuelle Architektur sauber stabilisiert ist: eine aktive UI, klare API-Contracts, explizite Service-Dependencies, getrennte Persistenz-, Live-Sync- und LLM-Adapterschichten sowie kleine Domain-Module fuer Setup, Claims, Turns, Canon, Boards und Sheets.

Das Ziel ist nicht maximale Abstraktion, sondern ein wartbarer MVP-Kernflow:

`Session -> Setup -> Claim -> Character Setup -> Play -> Turn -> Persist -> Live Sync -> Reload`.

## Diagramm

```mermaid
flowchart LR
  user["User\nHost oder Spieler"] --> browser["Browser"]

  subgraph frontend["Frontend: eine aktive UI"]
    v1["React/Vite UI\nRoute: /v1/*"]
    routes["Route State\nHub / Claim / Setup / Play\nURL als UI-Quelle"]
    features["Feature Workspaces\nSession, Claim, Setup,\nPlay, Boards, Sheets"]
    query["Server State\nTanStack Query\nCampaign Snapshot Cache"]
    uiStores["UI-only Stores\npresence view, drawers,\nsettings, layout"]
    localData["Local Comfort Data\nsettings, drafts,\nrecent sessions\nkeine Roh-Tokens"]
    liveClient["Live Client\nSSE ticket flow\ncampaign + presence events"]
  end

  browser --> v1
  v1 --> routes
  routes --> features
  features --> query
  features --> uiStores
  features --> localData
  features --> liveClient

  subgraph api["Backend API: stabile Contracts"]
    app["FastAPI Composition\nmain.py nur Wiring"]
    auth["Auth / Session Adapter\nplayer token, host,\nclaim checks"]
    apiSchemas["Pydantic API Schemas\nrequest + response contracts"]
    viewSerializer["Campaign View Serializer\npublic snapshot,\nviewer context,\nprivacy filters"]
    routers["Thin Routers\ncampaigns, setup, claims,\nturns, boards, context,\nsheets, presence"]
  end

  query -- "GET snapshot" --> routers
  features -- "POST/PATCH/DELETE commands" --> routers
  liveClient -- "ticket + EventSource" --> routers
  routers --> auth
  routers --> apiSchemas
  routers --> viewSerializer
  app --> routers

  subgraph domain["Domain Services: explizite Fachlogik"]
    sessionSvc["Session Service\ncreate, join, resume,\nmeta, delete"]
    setupSvc["Setup Service\nworld + character setup,\nrandom previews, finalize"]
    claimSvc["Claim Service\nslot ownership,\ntakeover, unclaim"]
    turnSvc["Turn Service\nturn guards,\nsubmit, edit, undo, retry"]
    boardsSvc["Boards Service\nplot, notes, diary,\nstory cards, world info"]
    contextSvc["Context Service\nread-only canon queries"]
    sheetsSvc["Sheets Service\nparty, character,\nNPC views"]
  end

  routers --> sessionSvc
  routers --> setupSvc
  routers --> claimSvc
  routers --> turnSvc
  routers --> boardsSvc
  routers --> contextSvc
  routers --> sheetsSvc

  subgraph core["Core Engines: kleine, testbare Module"]
    campaignRepo["Campaign Repository\nload/save/list/export\natomic JSON writes"]
    stateNormalizer["State Normalizer\nschema migration,\nderived fields,\nreload safety"]
    setupEngine["Setup Engine\nsummaries, world seed,\ncharacter projection"]
    turnEngine["Turn Engine\nprompt build,\nLLM call,\npatch merge"]
    patchEngine["Patch Engine\nsanitize, validate,\napply, limits,\nevent generation"]
    canonEngine["Canon Engine\ncodex, memory,\nprogression, NPC extraction"]
    ruleEngine["World Rule Modules\nelements, combat,\nskills, injuries,\nprogression"]
  end

  sessionSvc --> campaignRepo
  setupSvc --> setupEngine
  claimSvc --> campaignRepo
  turnSvc --> turnEngine
  boardsSvc --> campaignRepo
  contextSvc --> canonEngine
  sheetsSvc --> stateNormalizer

  setupEngine --> stateNormalizer
  turnEngine --> patchEngine
  patchEngine --> canonEngine
  canonEngine --> ruleEngine
  stateNormalizer --> ruleEngine
  campaignRepo --> stateNormalizer

  subgraph adapters["Adapters: austauschbare Infrastruktur"]
    llmAdapter["LLM Adapter\nOllama now,\nFake in tests,\nrole-based timeouts"]
    liveAdapter["Live Sync Adapter\nSSE events,\npresence, blocking actions"]
    tokenStore["Session/Ticket Store\nshort-lived stream tickets,\noptional persistent sessions"]
    fileStorage["File Storage\nDATA_DIR/campaigns\nJSON truth"]
    logs["Observability\ntrace id, phase events,\nstructured errors"]
  end

  setupEngine -- "setup copy,\nrandom answers" --> llmAdapter
  turnEngine -- "narrator,\nrepair, rewrite" --> llmAdapter
  canonEngine -- "extractors,\ncontext answers" --> llmAdapter
  presenceRouter["Presence Router"] --> liveAdapter
  auth --> tokenStore
  campaignRepo --> fileStorage
  turnEngine --> logs
  campaignRepo -- "after commit" --> liveAdapter

  subgraph tests["Validation Layer"]
    serviceTests["Service Tests\nsetup, claim, turn,\nboards, context"]
    contractTests["API Contract Tests\nHTTP smoke,\nauth/host/claim cases"]
    fakeLlm["Fake LLM Fixtures\nno Ollama in tests"]
    uiChecks["UI Type/Test/Build\nv1 scripts"]
  end

  domain --> serviceTests
  routers --> contractTests
  llmAdapter --> fakeLlm
  frontend --> uiChecks

  liveAdapter -- "campaign_sync\npresence_sync" --> liveClient
  liveClient -- "invalidate snapshot\nor update presence only" --> query
  query -- "fresh public state" --> features

  classDef ideal fill:#e8f7ef,stroke:#15803d,stroke-width:1px,color:#064e3b;
  classDef boundary fill:#eef2ff,stroke:#4f46e5,stroke-width:1px,color:#312e81;
  classDef adapter fill:#fff7ed,stroke:#c2410c,stroke-width:1px,color:#7c2d12;

  class v1,routes,features,query,uiStores,localData,liveClient ideal;
  class app,auth,apiSchemas,viewSerializer,routers,sessionSvc,setupSvc,claimSvc,turnSvc,boardsSvc,contextSvc,sheetsSvc,campaignRepo,stateNormalizer,setupEngine,turnEngine,patchEngine,canonEngine,ruleEngine ideal;
  class frontend,api,domain,core,tests boundary;
  class llmAdapter,liveAdapter,tokenStore,fileStorage,logs adapter;
```

## Was daran besser ist

- Nur eine aktive UI: Die React/Vite-v1-UI ist der produktive Pfad; Legacy wird entfernt oder klar als Read-only-Fallback markiert.
- Keine versteckten Globals: Engines erhalten explizite Dependencies statt `configure(globals())`.
- Kleine Kernmodule: Persistenz, Normalisierung, Turn-Pipeline, Canon und LLM sind getrennt testbar.
- Klare State-Regel: Campaign JSON ist persistente Wahrheit; Presence/SSE bleibt Live-Signal, nicht State-Quelle.
- Sicherere Sessions: Stream-Tickets und Sessions sind kurzlebig oder bewusst gespeichert; Roh-Tokens liegen nicht breit in lokalen Komfortdaten.
- Einheitlicher LLM-Zugang: Ollama ist nur ein Adapter; Tests nutzen Fake-LLMs.
- Sauberer Live-Sync: Erst nach erfolgreichem Persist-Commit wird `campaign_sync` gesendet; Presence bleibt separat.
- Reviewbare Entwicklung: Neue Fachlogik landet in Services/Core-Modulen, Router und `main.py` bleiben duenn.

## Migrationspfad aus dem Ist-Zustand

1. Aktiven UI-Pfad konsolidieren: `/` -> `/v1` beibehalten und keine neue Arbeit in `app/static/` starten.
2. LLM-Adapter einfuehren: bestehende Ollama-Funktionen hinter einen kleinen Rollen-Client legen.
3. `state_engine.py` schrittweise teilen: zuerst Repository/Persistence, danach Setup- und Sheet-Views.
4. Runtime-Bruecken reduzieren: pro extrahiertem Modul eine Dependency-Dataclass und `runtime_symbols()` weiter verkleinern.
5. Save/Broadcast entkoppeln: Persistenz als Commit, Broadcast als nachgelagerter Live-Event mit Recovery-Fallback.
6. v1-UI-State vereinheitlichen: URL fuer offene Oberflaechen, Stores fuer abgeleitete Renderdaten.
