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

## Pflege-Regeln

- Dokumentiere nur belegbare Architektur und tatsaechliche Kommandos.
- Roadmap-Eintraege als Planung kennzeichnen, nicht als existierende Features.
- Historische Audits in `01_repo/aelunor-core/docs/` nicht loeschen, sondern bei Bedarf mit aktuellem Status referenzieren.
- Runtime-Daten aus `07_runtime/` nie als Doku-Quelle fuer Tests oder Beispiele verwenden.
