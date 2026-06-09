# AGENTS.md

## Zweck

Verbindliche Arbeitsregeln fuer Coding-Agents im Aelunor-Repository. Ziel: zielgerichtet arbeiten, State-/UI-Regressions vermeiden, Aenderungen reviewbar halten. Diese Datei haelt nur globale, repositoryweite Regeln; pfadnahe `AGENTS.md`/`README.md` ergaenzen sie und gewinnen bei bereichsspezifischen Details.

## Projektueberblick

Aelunor ist ein lokales, UI-getriebenes Fantasy-/Storytelling-RPG mit FastAPI-Backend, React/Vite-v1-UI, JSON-basierter Kampagnenpersistenz, optionaler Ollama-Narrator-Logik und Windows-App-Packaging. Fokus: stabile App-Architektur, saubere Campaign-/Claim-/Turn-/Canon-/Presence-State-Flows, modulare Story-first-UI und langfristig wartbare Narrator-Logik.

## Wichtige Pfade

- `01_repo/aelunor-core/`: aktiver Code-Stack.
- `01_repo/aelunor-core/app/`: FastAPI-Backend und Service-Layer.
- `01_repo/aelunor-core/ui/`: React/Vite-v1-UI. Neue UI-Arbeit bevorzugt hier.
- `01_repo/aelunor-core/tests/`: Python-Tests.
- `01_repo/aelunor-core/scripts/`: Repo-Checks und Wartungsskripte.
- `02_docs/`: Produkt- und Architektur-Doku. `05_prompts/`: Prompt-Bibliothek.
- Runtime-Daten (`.runtime/`, `.runtime-verify/`, `07_runtime/`): nie fuer Tests oder Experimente beschreiben.

## Pfadnahe Regeln und Kontext-READMEs

Vor groesserer Arbeit in einem Bereich die naechstliegende Regel-/Kontextdatei lesen:

- Backend: `app/AGENTS.md`, `app/services/AGENTS.md`, `app/README.md`, `app/services/README.md`, `app/routers/README.md`.
- UI: `ui/AGENTS.md`, `ui/src/shared/design/AGENTS.md`.
- Tests: `tests/AGENTS.md`, `tests/README.md`.
- Scripts: `scripts/README.md`. Core-Setup: `01_repo/aelunor-core/README.md`.

## Token-Effizienz und Output-Schutz

Pflicht fuer alle Agent-Sessions. Ziel: ohne Full-Repo-Neuerkundung arbeiten.

- Zuerst `AELUNOR_HANDOFF.md` lesen (kompakter Fortsetzungskontext); bei groesseren Aenderungen am Ende aktualisieren.
- Nur task-relevante Dateien oeffnen. Keine Full-Repo-Scans ohne Grund. Repo-Map statt Datei-fuer-Datei: `python .agent_scripts/repo_map.py`.
- Grosse/unbekannte Befehlsausgaben nie ungecappt ausgeben: `<cmd> > .agent_tmp/out.txt 2>&1`, dann nur Ausschnitte (`head -c 6000`, `Get-Content -TotalCount 120`).
  - Fehlerlogs: `python .agent_scripts/scan_errors.py .agent_tmp/out.txt`. Tests: `python .agent_scripts/compact_test_output.py .agent_tmp/pytest.txt`.
- Keine vollstaendigen grossen/generierten Dateien in Antworten kopieren; nur Snippets oder Zeilen-Ranges.
- Nicht ungeprueft oeffnen: `node_modules/`, `.venv/`, `dist/`, `build/`, `.runtime*/`, Caches, Logs, Binaries, Schwester-Worktree `Aelunor-push-worktree/`.
- Grosse Zwischenergebnisse nach `.agent_tmp/` (git-ignored). Bevorzugt sichere Kommandos: `rg`/Grep, `git status --porcelain`, `git diff --name-only`, `git diff --stat`.
- Geaenderte Dateien mit ungefaehrer Zeilendifferenz berichten, z.B. `app/main.py (+12/-3)`.

## Arbeitsweise

- Erst verstehen, dann aendern. Relevante Dateien, Tests und lokale Konventionen vorher lesen.
- Kleine, reviewbare Aenderungen; nicht blind grossflaechig refactoren.
- UI, Domain-Logik, Persistenz, API/IO und Tests sauber trennen. Bestehende Patterns, Ordnergrenzen und Public Contracts respektieren.
- Keine kosmetischen Massenaenderungen neben Feature-/Bugfix-Arbeit.
- Public Contracts bewahren: HTTP-API, JSON-State-Shape, Campaign-Dateien, Setup-Catalog, Turn-Records, UI-Snapshot.

## Codegroessen und Modularitaet

- Keine neue/geaenderte Code-Datei ueber 300 Zeilen ohne sachlichen Grund; ggf. Komponenten, Hooks, Services, Utilities, Types oder Tests auslagern.
- Keine Funktionen ueber ca. 80 Zeilen ohne Begruendung. Keine God-Objects oder zentralen Dump-Dateien.
- Duplikation vermeiden, aber nicht durch zu fruehe Abstraktion verschlimmern.
- Bestehende grosse Dateien nicht zwanghaft in einem Task zerreissen; aber keine weitere Unordnung hinzufuegen. Ausnahmen kurz im Abschlussbericht begruenden.

## UI/UX-Leitlinien

- Neue UI-Arbeit bevorzugt unter `ui/`; keine Legacy-UI-Arbeit in `app/static/`.
- Story-first UX: Spieleraktionen, aktueller Turn, GM-Text, Claims und Setup-Fortschritt haben Vorrang vor Admin-/Analytics-Oberflaechen.
- UI-State respektiert Backend-State; keine parallele Wahrheit fuer Campaign-, Claim-, Turn- oder Canon-Daten.
- Responsiv denken (mobile und Desktop), kein neues Designsystem neben dem bestehenden. Asset-Details: `ui/AGENTS.md`, `ui/src/shared/design/AGENTS.md`.
- UI-Aenderungen muessen visuell pruefbar sein; Screenshots oder Smoke-Pfade im Abschluss nennen.

## Tests und Verifikation

- Nach Codeaenderungen passende Tests/Typechecks/Lints/Builds ausfuehren; sonst gezielt relevante Checks und begruenden.
- Keine Erfolgsmeldung ohne echte Verifikation; nicht ausfuehrbare Checks ehrlich erklaeren.
- Backend-Tests laufen aus `01_repo/aelunor-core/`. Struktur, Offline-Regeln und Smoke-Checks: `tests/AGENTS.md`, `tests/README.md`. Check-Scripts: `scripts/README.md`.
- Tests schreiben nur in temporaere Datenpfade; `.runtime/`, `.runtime-verify/`, `07_runtime/` bleiben unberuehrt.

## Sicherheit und Daten

- Keine Secrets, API-Keys, Tokens oder privaten Daten committen. Keine `.env`-Inhalte lesen oder ausgeben.
- Keine echten Nutzer-/Kundendaten in Tests oder Fixtures. Keine produktiven Runtime-Daten als Fixture missbrauchen.
- Keine gefaehrlichen Shell-Kommandos; Loesch-/Migrations-/Formatieraktionen nur nach Pruefung.
- Externe API-Calls, Kosten, Netzwerk- oder Modellaufrufe explizit dokumentieren.

## Git- und Aenderungsverhalten

- Vor Beginn Arbeitsbaum pruefen; vorhandene Nutzeraenderungen nicht ueberschreiben.
- Nur task-relevante Dateien aendern. Keine unrelated formatting changes.
- Keine neue Dependency ohne Begruendung; Installationsdateien bei Bedarf aktualisieren.
- Keine Build-Artefakte, Logs, Caches oder generierte Dateien committen.
- Keine Co-authored-by-Zeilen in Commits.

## Absolute No-Gos

- Keine Secrets/`.env`-Inhalte lesen, ausgeben oder committen.
- Keine produktiven Runtime-Daten (`.runtime*/`, `07_runtime/`) fuer Tests anfassen oder als Fixture verwenden.
- Keine echten Ollama-/LLM-Calls in automatisierten Tests; Fake Narrator, Stubs oder Dependency Injection.
- `app/main.py` ist Wiring/Composition, kein Ablageort fuer Fachlogik.
- Keine Wiederbelebung der entfernten Legacy-UI in `app/static/` ohne expliziten Auftrag.
- Keine grossen Architekturumbauten, kein Feature-Bloating, keine Admin-/Analytics-Oberflaechen ohne Nutzen fuer den Story-Spielkern.
- Keine Co-authored-by-Zeilen.

## Agent-Kommunikation und Definition of Done

- Kurz, konkret, keine uebertriebenen Erfolgsaussagen; Unsicherheiten markieren; Ursachen benennen statt still drumherum bauen.
- Abschlussbericht bei Codeaenderungen: geaenderte Dateien mit Zeilendifferenz, was geaendert wurde, gelaufene Tests/Checks, offene Risiken.
- Done, wenn: Aenderung passt fachlich, Code modular/lesbar, relevante Checks liefen oder Nichtausfuehrung begruendet, keine offensichtlichen Regressionen, Bericht nachvollziehbar.

## Lokale Ergaenzungen

- Unterordner duerfen eigene `AGENTS.md`/`AGENTS.override.md` haben, wenn dort andere Regeln gelten.
- Root bleibt bewusst knapp; ausfuehrliche Spezial- und Architekturregeln gehoeren in pfadnahe `AGENTS.md`/`README.md` und `02_docs/`.
