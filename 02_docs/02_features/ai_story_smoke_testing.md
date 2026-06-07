# AI Story Smoke Testing

## Zweck

`scripts/run_ai_story_smoke.py` ist ein manueller Smoke-/Longrun-Test fuer die neuen World-/Character-Systeme. Er prueft mit einem echten LLM-Turn-Flow, ob World Bible, Living Character Profile, Context Injection, Entity Guard Hook, Entity Guard Reporting und World Bible Quality Reporting zusammen wirken.

Der Test ist kein Unit-Test und gehoert nicht in CI.

## Claude nur temporaer

Claude/Anthropic ist hier ein temporaerer Cloud-Provider, bis wieder eine lokale LLM-/Ollama-Instanz fuer Longruns verfuegbar ist. Der bestehende lokale/Ollama-Pfad bleibt unveraendert.

Konfiguration:

```powershell
$env:AELUNOR_LLM_PROVIDER = "anthropic"
$env:ANTHROPIC_API_KEY = "..."
$env:ANTHROPIC_MODEL = "claude-opus-4-8"
$env:ANTHROPIC_TIMEOUT_SEC = "120"
python scripts/run_ai_story_smoke.py --scenario dark-fantasy --turns 3
```

Das Script bildet `AELUNOR_LLM_PROVIDER` intern auf das vorhandene `LLM_PROVIDER`-Wiring ab. Alternativ kann direkt `--provider anthropic` oder `LLM_PROVIDER=anthropic` genutzt werden.

## Beispielaufrufe

```powershell
python scripts/run_ai_story_smoke.py --scenario dark-fantasy --turns 3
python scripts/run_ai_story_smoke.py --scenario superhero-academy --turns 3 --out reports/ai_story_smoke_superhero.md
python scripts/run_ai_story_smoke.py --provider ollama --scenario dark-fantasy --keep-campaign
```

Ohne `ANTHROPIC_API_KEY` oder `ANTHROPIC_AUTH_TOKEN` bricht der Anthropic-Run sauber ab. API-Keys werden nicht in Reports geschrieben.

## Kosten und Secrets

Der Smoke-Test fuehrt echte LLM-Aufrufe aus und kann API-Kosten verursachen. Standard sind maximal 3 Turns, der Hard Cap liegt bei 10 Turns. Das Script schreibt keine kompletten Prompt-Payloads in den Report, sondern nur kompakte Excerpts und Summary-Daten.

Keine API-Keys committen, in Logs kopieren oder als Testfixture verwenden.

## Was Geprueft Wird

Der Runner erzeugt eine neue Test-Campaign, normalisiert World Bible und Living Profile, fuehrt simulierte Spieleraktionen durch und schreibt einen Markdown-Report mit:

- World Bible Quality
- Entity Guard Summary
- Prompt Context Check
- Sample Generated Names
- Potential Problems
- kurzen Turn Samples

Die Presets decken zwei unterschiedliche Naming-Modi ab:

- `dark-fantasy`: invented/dark fantasy mit Roots, Race-Linguistik, Relikten und Kostenmagie
- `superhero-academy`: moderne Hero-Akademie, damit der Guard nicht fantasy-biased bewertet

## Unterschied zu Unit-Tests

Unit-Tests pruefen nur reine Funktionen des Scripts: Presets, Argument-Parsing, Missing-Key-Handling und Report-Rendering. Sie machen keine echten LLM-, Netzwerk- oder Anthropic-Aufrufe.

## Rueckkehr zu Lokal/Ollama

Fuer lokale Tests kann der Provider wieder auf Ollama gesetzt werden:

```powershell
$env:LLM_PROVIDER = "ollama"
python scripts/run_ai_story_smoke.py --provider ollama --scenario dark-fantasy
```

Damit bleibt der Smoke-Runner als manuelles Werkzeug nutzbar, ohne die App dauerhaft auf Claude zu migrieren.
