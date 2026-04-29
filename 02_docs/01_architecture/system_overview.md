# System Overview

Aelunor ist derzeit ein einzelner lokaler App-Stack mit FastAPI-Backend, React/Vite-v1-Frontend und JSON-Persistenz.

## Runtime-Topologie

```text
Browser
  /v1 React/Vite UI
  / Legacy static UI
    |
FastAPI app.main
    |
Routers in app/routers
    |
Services in app/services
    |
Campaign JSON in DATA_DIR/campaigns
    |
Optional Ollama HTTP API
```

## Backend-Schichten

- `app/main.py`: App-Wiring, globale Runtime-Konfiguration, Pydantic-Modelle, Router-Registrierung, Static Mounts, Kompatibilitaets-Exports aus `state_engine`.
- `app/routers/`: HTTP-Adapter. Sie lesen Header/Payloads, rufen Services auf und serialisieren Responses.
- `app/services/`: Domainlogik fuer Campaigns, Claims, Setup, Turns, Boards, Context, Presence, Sheets und State.
- `app/helpers/`: Setup-/Serializer-Hilfslogik.
- `app/static/`: Legacy-UI und statische Assets.

## Frontend-Schichten

- `ui/src/app/`: Bootstrapping, Provider, Routing, Route-Gates.
- `ui/src/entities/`: langlebige Domain-Stores und Queries.
- `ui/src/features/`: Feature-Surfaces fuer Session Hub, Claim, Setup, Play, Boards, Drawers, Context.
- `ui/src/shared/`: API-Contracts, HTTP-Client, Fehlerformatierung, Styles, UI-Primitives, SSE.
- `ui/src/state/`: cross-feature UI-State.

## Datenfluss

1. Frontend speichert lokale Session-Credentials in `localStorage`.
2. API-Calls senden `X-Player-Id` und `X-Player-Token`.
3. Backend laedt Campaign JSON aus `DATA_DIR/campaigns`.
4. Services validieren Claims, Phase, Setup, Turn- und Canon-Regeln.
5. Mutationen persistieren Campaign JSON und liefern einen neuen Snapshot.
6. Presence/SSE liefert Live-Sync, bleibt aber nicht die persistente Wahrheit.

## Public Contracts

- HTTP-Routen unter `/api/campaigns/...`
- Campaign JSON Shape
- Turn-Record-Format
- Setup-Catalog-Struktur
- Frontend `CampaignSnapshot` in `ui/src/shared/api/contracts.ts`
- Player-Token-/Claim-Regeln

Diese Contracts nur mit Migration und Tests aendern.

## Haupt-Schulden

- `app/services/state_engine.py` ist zu gross und enthaelt mehrere Domains.
- `app/services/turn_engine.py` sollte weiter in Narrator-Orchestration, Canon-Gate und LLM-Adapter zerlegt werden.
- Legacy-UI `app/static/app.js` bleibt gross und sollte nicht aktiv ausgebaut werden.
- Globale CSS-Regeln sind noch umfangreich; neue Designsysteme sollten in eigene Token-/Layout-Dateien.
