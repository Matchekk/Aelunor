# Persistence Strategy

Aelunor persistiert lokal als JSON. Es gibt aktuell keine Datenbank.

## Pfade

- Docker: `DATA_DIR=/data`, gemountet auf `../../07_runtime`
- Lokal: `DATA_DIR` explizit setzen, fuer Tests immer temporaer
- Campaigns: `DATA_DIR/campaigns/{campaign_id}.json`
- Legacy-State: `DATA_DIR/state.json`

## Regeln

- Persistente Wahrheit ist Campaign JSON.
- Presence/SSE ist nur Live-Sync.
- Tests duerfen `07_runtime/` nicht beschreiben.
- Migrations-/Normalize-Pfade muessen deterministisch sein.
- State-Aenderungen muessen reload-sicher sein.

## Risiken

- JSON-Dateien sind einfach zu debuggen, aber brauchen saubere Normalisierung.
- Concurrent Writes muessen service-seitig kontrolliert bleiben.
- Alte Campaign-Dateien koennen fehlende Felder enthalten; Normalizer muessen tolerant bleiben.
