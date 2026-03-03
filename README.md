# Isekai GM MVP (Local, deterministic boards)

## What this is
A minimal web app that:
- lets 3 players (Matchek/Abo/Beni) send actions
- calls a local Ollama model with **Structured Outputs (JSON Schema)**
- stores a canonical world-state in `./data/state.json`
- shows a dashboard (Character Cards / Plot / Map) in the browser (phone-friendly)

## Prereqs
1) Install Docker Desktop
2) Install Ollama on your host OS and start it (Windows recommended)
3) Pull a model:
   - `ollama pull gemma3:12b`

Then run this app:

```bash
docker compose up --build
```

Open:
- PC: http://localhost:8080
- Phone (same WiFi): http://<PC-IP>:8080

If you need the PC-IP:
- Windows: `ipconfig` → IPv4 Address

## Gemma defaults and comparison
- `docker-compose.yml` now defaults to `gemma3:12b`.
- Override the model for a run with an environment variable:

```powershell
$env:OLLAMA_MODEL = "gemma3:8b"
docker compose up -d --build
```

- Runtime status is available at `GET /api/llm/status`.
- A reproducible smoke benchmark for the app flow is included:

```powershell
python scripts/benchmark_models.py gemma3:12b gemma3:8b
```

The benchmark restarts the app per model, runs world setup, character setup, intro generation and one story turn, then prints timings and a short excerpt.

## If you want Ollama in Docker (CPU only)
Ollama’s official Docker image exists (CPU only unless you have NVIDIA Container Toolkit on Linux).
Add this service to docker-compose.yml and change OLLAMA_URL to `http://ollama:11434`:

```yaml
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama

volumes:
  ollama:
```

## Notes
- For more deterministic behavior, keep the seed fixed and temperature lower.
- The model output is enforced with JSON schema (Structured Outputs).
