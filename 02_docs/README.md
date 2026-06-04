# Aelunor Documentation

Diese Dokumentation beschreibt den aktuellen Stand des lokalen Aelunor-Projekts. Sie ersetzt die frueheren Platzhalter-Notizen nicht als vollstaendige Spezifikation, sondern als wartbare, code-backed Orientierung.

## Doku-Struktur

| Bereich | Inhalt |
| --- | --- |
| `00_product/` | Produktziel, Scope, Roadmap und Spielpfeiler |
| `01_architecture/` | Systemaufbau, Turn-Flow, Persistence, Canon/Progression |
| `02_features/` | Feature-Notizen fuer Klassen, Skills, Races, World Generation, HUD |
| `03_ux/` | UI-Prinzipien, States, Screens, Design Tokens |
| `04_prompts/` | Prompt- und Evaluator-Notizen |
| `05_decisions/` | Architekturentscheidungen (ADR) |

## Aktive Wahrheit

- Code: `../01_repo/aelunor-core/`
- Root-Setup: `../README.md`
- Core-Setup und Checks: `../01_repo/aelunor-core/README.md`
- Projektregeln fuer Codex: `../AGENTS.md`
- Backend-Kontext fuer Agents: `../01_repo/aelunor-core/app/README.md`
- Service-Kontext: `../01_repo/aelunor-core/app/services/README.md`
- Test- und Script-Kontext: `../01_repo/aelunor-core/tests/README.md`, `../01_repo/aelunor-core/scripts/README.md`

## Pflege-Regeln

- Dokumentiere nur belegbare Architektur und tatsaechliche Kommandos.
- Roadmap-Eintraege als Planung kennzeichnen, nicht als existierende Features.
- Historische Audits in `01_repo/aelunor-core/docs/` nicht loeschen, sondern bei Bedarf mit aktuellem Status referenzieren.
- Zeitdokumente und externe Analyseordner nicht still umschreiben; bei aktiven Architekturthemen lieber aktuelle Kontext-READMEs und `02_docs/01_architecture/` pflegen.
- Runtime-Daten aus `07_runtime/` nie als Doku-Quelle fuer Tests oder Beispiele verwenden.
