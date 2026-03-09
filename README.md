# Aelunor

Lokales, browserbasiertes Multiplayer-Story-RPG mit KI-GM (Ollama), kanonischem Patch-State und Live-Sync.

## Aktueller Kern
- FastAPI-Backend in `backend/main.py`
- Frontend in `backend/static/` (Vanilla JS/HTML/CSS)
- Kampagnenbasiertes State-Modell in `data/campaigns/*.json`
- Setup-Flow (Welt/Charakter) über `setup_catalog.json`
- Story-Turns mit Modi `TUN`, `SAGEN`, `STORY`, `CANON`, `KONTEXT`
- Strukturierte Turn-Observability mit `trace_id` und Phasen-Logs

## Voraussetzungen
1. Docker Desktop
2. Ollama lokal auf dem Host (Windows empfohlen)
3. Modell ziehen, z. B.:
   - `ollama pull gemma3:12b`

## Starten
```powershell
docker compose up -d --build
```

App öffnen:
- Desktop: `http://localhost:8080`
- Handy im selben WLAN: `http://<DEIN-PC-IP>:8080`

PC-IP unter Windows:
```powershell
ipconfig
```

## Rebuild ohne Cache (empfohlen bei größeren Änderungen)
```powershell
docker compose down --remove-orphans
docker compose build --no-cache gm-app
docker compose up -d --force-recreate gm-app
```

Shortcut:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/rebuild_gm_app.ps1
```

## Konfiguration
In `docker-compose.yml`:
- `OLLAMA_URL` (Default: `http://host.docker.internal:11434`)
- `OLLAMA_MODEL` (Default: `gemma3:12b`)
- `OLLAMA_TIMEOUT_SEC`, `OLLAMA_TEMPERATURE`, `OLLAMA_NUM_CTX`, `OLLAMA_SEED`

Zur Laufzeit prüfen:
- `GET /api/llm/status`

## Nützliche Checks
```powershell
python -m py_compile backend/main.py
node --check backend/static/app.js
python scripts/check_progression_canon_gate.py
python scripts/check_codex_system.py
python scripts/check_element_system.py
```

## Daten & Repo-Hygiene
- Laufende Kampagnen liegen lokal in `data/campaigns/`.
- Automations-/Longrun-Artefakte liegen lokal in `data/automation_runs/`.
- Diese Datenpfade sind absichtlich in `.gitignore`, damit das Repo sauber bleibt.
