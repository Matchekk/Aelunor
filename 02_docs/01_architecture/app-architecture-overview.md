# Aelunor Webapp Architecture Overview

Stand: 2026-06-04

## Kurzfassung

Aelunor besteht aus einer FastAPI-App mit einer aktiven React/Vite-v1-UI unter `/v1`; `/` leitet auf `/v1` weiter. Die v1-UI nutzt React Router, TanStack Query fuer Campaign-Snapshots und Mutationen, Zustand fuer lokale UI-Stores sowie SSE fuer Live-Sync. Das Backend gruppiert HTTP-Endpunkte in duenne Router und delegiert Fachlogik an Services. Persistente Wahrheit ist JSON-Dateispeicherung unter `DATA_DIR/campaigns`; Live-Presence ist nur transient im Speicher. Ollama ist optionaler externer Generator fuer Setup-Texte, Story-Turns, Canon-Extractor, NPC-Extractor und Kontextantworten; Tests und Check-Scripts muessen ihn faken oder stubs/fallbacks nutzen.

## Erkannte Hauptbereiche

- Frontend v1: `ui/src/app`, `ui/src/features`, `ui/src/entities`, `ui/src/shared`
- Statische Assets: `app/static/`; keine aktive Legacy-UI
- API-Wiring: `app/main.py`
- Router: `app/routers/*.py`
- Services: `app/services/*.py`, `app/services/turn/*.py`, `app/services/world/*.py`, plus extrahierte Zielmodule in `items/`, `characters/`, `setup/`, `llm/`, `state/`
- API-Schemas und View-Serializer: `app/schemas/api.py`, `app/serializers/campaign_view.py`
- Persistenz: JSON-Campaign-Dateien in `DATA_DIR/campaigns`; lokale Browserdaten in `localStorage` und `sessionStorage`
- Extern: Ollama `/api/chat` und `/api/tags`

## Diagramm

```mermaid
flowchart LR
  user["User\nspielt, richtet ein, claimt Slots"] --> browser["Browser"]

  subgraph frontend["Frontend"]
    rootRedirect["Root Redirect\n/ -> /v1"]
    v1["React/Vite UI v1\nui/src\nRoute: /v1/*"]
    router["React Router Gate\nhub / claim / setup / play\napp/routing"]
    workspaces["Feature Workspaces\nSessionHub, Claim,\nSetupWizard, Play"]
    rq["TanStack Query\nCampaign Snapshot Cache"]
    stores["Zustand UI Stores\npresence, drawer, context,\nlayout, settings"]
    local["Browser Storage\nsession credentials,\nsettings, drafts, UI memory"]
    sseClient["SSE Client\ncampaign_sync + presence_sync"]
  end

  browser --> rootRedirect --> v1
  browser --> v1
  v1 --> router
  router --> workspaces
  workspaces --> rq
  workspaces --> stores
  workspaces --> local
  workspaces --> sseClient

  subgraph api["Backend / API"]
    fastapi["FastAPI App Wiring\napp/main.py"]
    campaignsRouter["Campaigns Router\ncreate, join, get,\nintro, meta, export, delete"]
    setupRouter["Setup Router\nworld + character questions,\nanswers, random, finalize"]
    claimRouter["Claim Router\nclaim, takeover, unclaim"]
    turnsRouter["Turns Router\ncreate, edit, undo, retry"]
    boardsRouter["Boards Router\nplot, note, diary,\nstory cards, world info"]
    contextRouter["Context Router\ncanon/context query"]
    sheetsRouter["Sheets Router\nparty, character, npc sheets"]
    presenceRouter["Presence Router\nSSE ticket, stream,\nactivity, clear"]
  end

  rq -- "GET /api/campaigns/:id\nloads public snapshot" --> campaignsRouter
  workspaces -- "POST/PATCH/DELETE\nmutations invalidate cache" --> campaignsRouter
  workspaces --> setupRouter
  workspaces --> claimRouter
  workspaces --> turnsRouter
  workspaces --> boardsRouter
  workspaces --> contextRouter
  workspaces --> sheetsRouter
  sseClient -- "POST ticket then EventSource\nno player token in v1 URL" --> presenceRouter

  fastapi --> campaignsRouter
  fastapi --> setupRouter
  fastapi --> claimRouter
  fastapi --> turnsRouter
  fastapi --> boardsRouter
  fastapi --> contextRouter
  fastapi --> sheetsRouter
  fastapi --> presenceRouter

  subgraph services["Service Layer / Domain Logic"]
    campaignService["campaign_service.py\nsessions, host actions,\nintro retry, meta"]
    setupService["setup_service.py\nsetup flow and access rules"]
    claimService["claim_service.py\nslot ownership rules"]
    turnService["turn_service.py\nturn guards and error mapping"]
    boardsService["boards_service.py\nboards + revision log"]
    contextService["context_service.py\nread-only canon answers"]
    sheetsService["sheets_service.py\nsheet view builders"]
    presenceService["presence_service.py\nstream tickets + validation"]
    serializer["campaign_view.py\npublic snapshot + viewer context"]
  end

  campaignsRouter --> campaignService
  setupRouter --> setupService
  claimRouter --> claimService
  turnsRouter --> turnService
  boardsRouter --> boardsService
  contextRouter --> contextService
  sheetsRouter --> sheetsService
  presenceRouter --> presenceService
  campaignsRouter --> serializer
  setupRouter --> serializer
  claimRouter --> serializer
  turnsRouter --> serializer
  boardsRouter --> serializer

  subgraph engines["Central Logic / Generators"]
    mainGlue["Dependency Wiring + Constants\napp/main.py"]
    stateEngine["state_engine.py\nnormalization, persistence,\nsetup finalization,\nworld/canon helpers\nsmall public facade"]
    turnEngine["turn_engine.py\nturn pipeline orchestration"]
    patchPipeline["turn patch pipeline\nsanitize, validate,\napply, limits"]
    worldModules["world modules\ncodex, progression,\nelements, combat, NPCs"]
    liveState["live_state_service.py\nin-memory presence,\nblocking action, SSE broadcast"]
  end

  campaignService --> mainGlue
  setupService --> mainGlue
  claimService --> mainGlue
  turnService --> turnEngine
  boardsService --> mainGlue
  contextService --> mainGlue
  sheetsService --> mainGlue
  presenceService --> liveState
  mainGlue --> stateEngine
  turnEngine --> patchPipeline
  stateEngine --> worldModules
  turnEngine --> stateEngine

  subgraph storage["Storage"]
    campaignJson["Campaign JSON files\nDATA_DIR/campaigns/*.json\npersistent truth"]
    legacyState["Legacy state fallback\nDATA_DIR/state.json\ncompatibility"]
    transient["Process memory\nlive state registry,\nSSE subscribers,\nstream tickets"]
  end

  stateEngine -- "load_campaign / save_campaign\nnormalize before save" --> campaignJson
  stateEngine -. "old shape compatibility" .-> legacyState
  liveState --> transient
  presenceService --> transient

  subgraph external["External Services"]
    ollama["Ollama\n/api/chat + /api/tags"]
  end

  stateEngine -- "setup copy, random setup,\nextractors, context, intro" --> ollama
  turnEngine -- "narrator call,\nstory rewrite guard,\ncanon/NPC extraction" --> ollama

  campaignJson -- "campaign_sync after save" --> liveState
  liveState -- "SSE event\ninvalidate query / update presence" --> sseClient
  rq -- "fresh snapshot renders UI" --> workspaces
```

## Haupt-Workflows

- Kampagne erstellen/joinen: `SessionHubWorkspace` -> `/api/campaigns` oder `/api/campaigns/join` -> `campaign_service` -> JSON-Campaign -> lokale Sessiondaten.
- Setup: `SetupWizardOverlay` -> setup API -> `setup_service` -> explicit dependencies -> `state_engine`/setup modules fuer AI-Copy, Random Answers, Finalisierung, World/Character Summary -> JSON save -> SSE.
- Claim: `ClaimWorkspace` -> claim API -> `claim_service` -> Claims im Campaign JSON -> SSE.
- Spielen: `Composer`/`CampaignWorkspace` -> turns API -> `turn_service` -> `turn_engine` -> Ollama Narrator/Extractors -> Patch-Pipeline -> State save -> SSE -> React Query reload.
- Live-Sync: Presence-Aktivitaeten gehen in `live_state_service`; persistente Campaign-Aenderungen senden `campaign_sync`; die v1-UI invalidiert danach den Campaign-Snapshot.
- Context und Sheets: UI fragt read-only Views ab; `context_service` prueft per State-Signature, dass Context Queries keinen State veraendern.
