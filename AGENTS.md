# AGENTS.md

## Zweck

Diese Datei enthaelt verbindliche Arbeitsregeln fuer Coding-Agents im Aelunor-Repository. Sie soll helfen, zielgerichtet zu arbeiten, State-/UI-Regressions zu vermeiden und Aenderungen reviewbar zu halten.

## Projektueberblick

Aelunor ist ein lokales, UI-getriebenes Fantasy-/Storytelling-RPG mit FastAPI-Backend, React/Vite-v1-UI, JSON-basierter Kampagnenpersistenz, optionaler Ollama-Narrator-Logik und Windows-App-Packaging.

Fokus:

- stabile App-Architektur und lokale Start-/Build-Flows
- saubere Campaign-, Claim-, Turn-, Canon- und Presence-State-Flows
- modulare UI mit Story-first UX
- langfristig wartbare Story-/Canon-/Narrator-Logik

Wichtige Pfade:

- `01_repo/aelunor-core/`: aktiver Code-Stack.
- `01_repo/aelunor-core/app/`: FastAPI-Backend, statische Runtime-Assets und Service-Layer.
- `01_repo/aelunor-core/app/main.py`: App-Wiring, Runtime-Konfiguration, Router-Composition und zentrale Glue-Funktionen.
- `01_repo/aelunor-core/app/services/`: Backend-Domainlogik fuer Campaigns, Setup, Claims, Turns, State, Boards, Context, Presence und Sheets.
- `01_repo/aelunor-core/app/routers/`: HTTP-Router um die Service-Layer.
- `01_repo/aelunor-core/app/static/`: statische Brand-/Icon-Assets; keine aktive Legacy-UI.
- `01_repo/aelunor-core/ui/`: React/Vite-v1-UI. Neue UI-Arbeit bevorzugt hier.
- `01_repo/aelunor-core/tests/`: Python-Tests.
- `01_repo/aelunor-core/scripts/`: technische Repo-Checks und Wartungsskripte.
- `02_docs/`: Produkt- und Architektur-Dokumentation.
- `05_prompts/`: Prompt-Bibliothek.
- `01_repo/aelunor-core/.runtime/` und `.runtime-verify/`: lokale Runtime-/Verifikationsdaten (Default-`DATA_DIR`). `07_runtime/` (Repo-Root) ist das Docker-Bind-Mount-Datenverzeichnis aus `docker-compose.yml`. Beide nicht fuer Tests oder Experimente beschreiben, ausser der Nutzer fordert es explizit.

Kontext-READMEs fuer Agents:

- `01_repo/aelunor-core/README.md`: Core-Setup, Checks und Architekturregeln.
- `01_repo/aelunor-core/app/README.md`: Backend-Schichten, Runtime-Wiring, State-Engine-Grenzen.
- `01_repo/aelunor-core/app/services/README.md`: Service-Landkarte und aktuelle Refactoring-Grenzen.
- `01_repo/aelunor-core/app/routers/README.md`: Router-Konventionen und Dependency-Factories.
- `01_repo/aelunor-core/tests/README.md`: Teststruktur, Offline-Regeln, relevante Smoke-Checks.
- `01_repo/aelunor-core/scripts/README.md`: technische Check-Scripts und wann sie laufen sollen.

## Token-Effizienz und Agent-Infrastruktur

Pflicht fuer alle Agent-Sessions. Ziel: ohne Full-Repo-Neuerkundung arbeiten.

- Zuerst `AELUNOR_HANDOFF.md` lesen (kompakter Fortsetzungskontext). Bei groesseren Aenderungen am Ende aktualisieren (Goal, Architektur, Tests, Next Steps).
- Nur Dateien oeffnen, die fuer die konkrete Aufgabe noetig sind. Keine Full-Repo-Scans ohne Grund.
- Repo-Map statt Datei-fuer-Datei-Exploration: `python .agent_scripts/repo_map.py`.
- Grosse oder unbekannte Befehlsausgaben NIE ungecappt in Antwort oder Chat kippen.
  - Muster: `<cmd> > .agent_tmp/out.txt 2>&1`, dann nur begrenzten Ausschnitt ansehen (`head -c 6000`, `Get-Content -TotalCount 120`, `Select-Object -First N`).
  - Fehlerlogs kompakt: `python .agent_scripts/scan_errors.py .agent_tmp/out.txt`.
  - Testausgaben kompakt: `... > .agent_tmp/pytest.txt 2>&1`, dann `python .agent_scripts/compact_test_output.py .agent_tmp/pytest.txt`.
- Keine vollstaendigen grossen Dateien, Logs oder generierten Dateien in Antworten kopieren. Nur relevante Snippets oder Zeilen-Ranges.
- Nicht ungeprueft oeffnen: `node_modules/`, `.venv/`, `dist/`, `build/`, `.runtime*/`, `.pytest_cache/`, Caches, Logs, Binary-/Asset-Dateien, sowie der Schwester-Worktree `Aelunor-push-worktree/`.
- Grosse Zwischenergebnisse nach `.agent_tmp/` schreiben (git-ignored) und nur Ausschnitte inspizieren.
- Bevorzugte sichere Kommandos: `rg`/Grep, `git status --porcelain`, `git diff --name-only`, `git diff --stat`, gezielte Datei-Ranges (`sed -n`/`Get-Content`).
- Geaenderte Dateien immer mit ungefaehrer Zeilendifferenz berichten, z.B. `app/main.py (+12/-3)`.

## Arbeitsweise fuer Agents

- Erst verstehen, dann aendern.
- Vor Aenderungen relevante Dateien, Tests und lokale Konventionen lesen.
- Nicht blind grossflaechig refactoren.
- Kleine, nachvollziehbare Aenderungen bevorzugen.
- Bestehende Patterns, Ordnergrenzen und Public Contracts respektieren.
- Bei unklarer Architektur zuerst vorhandene Konventionen suchen.
- Vor groesseren Backend-Aenderungen zuerst die naechstliegende Kontext-README lesen.
- Aenderungen so umsetzen, dass sie reviewbar bleiben.
- Keine kosmetischen Massenaenderungen neben Feature-/Bugfix-Arbeit.
- Keine Legacy-UI-Arbeit mehr in `app/static/`; aktive UI-Arbeit gehoert nach `ui/`.

## Codegroessen und Modularitaet

- Keine neue oder geaenderte Code-Datei ueber 300 Zeilen ohne sachlichen Grund.
- Wenn eine Datei ueber 300 Zeilen waechst, pruefen, ob Komponenten, Hooks, Services, Utilities, Types oder Tests ausgelagert werden sollten.
- Keine Funktionen ueber ca. 80 Zeilen ohne Begruendung.
- Keine Komponenten mit mehreren Verantwortlichkeiten.
- Keine God-Objects, riesigen Manager-Dateien oder zentralen Dump-Dateien fuer alles.
- Duplikation vermeiden, aber nicht durch zu fruehe Abstraktion verschlimmern.
- Bestehende grosse Dateien nicht zwanghaft in einem Task zerreissen; bei Bearbeitung aber keine weitere Unordnung hinzufuegen.
- Jede Ausnahme kurz im Abschlussbericht begruenden.

## Architekturregeln

- UI, Domain-Logik, Persistenz, API/IO und Tests sauber trennen.
- Service-Logik gehoert in `app/services/`; Router bleiben duenne Adapter.
- `app/main.py` ist Wiring/Composition, kein Ablageort fuer neue Fachlogik.
- `state_engine.EXPORTED_SYMBOLS` bleibt klein. Alte private/domain Helper nicht wieder als breite Fassade exportieren.
- `state_engine.runtime_symbols()` ist nur eine begrenzte interne Uebergangsbruecke fuer Runtime-Factories und Turn-Wiring.
- Der normale `main.py`-Pfad nutzt `configure_dependencies(StateEngineDependencies(...))`; `state_engine.configure(globals())` nicht wieder als App-Hauptmechanismus einfuehren.
- State-Aenderungen zentral, nachvollziehbar, reload-sicher und typisiert halten.
- Keine versteckten Side Effects in UI-Komponenten.
- Story-/Canon-/Narrator-Logik nicht direkt in zufaellige UI-Komponenten schreiben.
- Wiederverwendbare Logik in passende Module auslagern.
- Dateinamen und Ordnerstruktur sollen Zweck und Verantwortlichkeit klar zeigen.
- Bestehende Architektur nicht umgehen, nur weil es schneller geht.
- Public Contracts bewahren: HTTP-API, JSON-State-Shape, Campaign-Dateien, Setup-Catalog, Turn-Records, UI-Erwartungen.

## UI/UX-Regeln

- Neue UI-Arbeit bevorzugt unter `01_repo/aelunor-core/ui/`.
- Keine Legacy-UI-Arbeit mehr in `app/static/`; aktive UI-Arbeit gehoert nach `ui/`.
- Story-first UX: Spieleraktionen, aktueller Turn, GM-Text, Claims, Setup-Fortschritt und spielbare Lage haben Vorrang.
- Keine Admin-Dashboard-Expansion, solange der Spielkern nicht direkt davon profitiert.
- UI-State muss Backend-State respektieren; keine eigene parallele Wahrheit fuer Campaign-, Claim-, Turn- oder Canon-Daten einfuehren.
- Bei UX-Aenderungen mobile und Desktop-Layouts bedenken.
- Keine Dummy-UI bauen, die nicht an echten State oder echte Datenfluesse anschliessbar ist.
- Keine harten Pixel-Fixes ohne responsives Denken.
- Keine neuen Designsysteme neben dem bestehenden Design erfinden.
- Bestehende Theme-, Style-, Wallpaper-, Asset- und Layout-Patterns respektieren.
- Fuer UI-Assets zusaetzlich `01_repo/aelunor-core/ui/AGENTS.md` und relevante `src/shared/design/*` Regeln beachten.
- Background-Art, UI-Layer und interaktive Elemente gedanklich trennen.
- UI-Aenderungen muessen visuell pruefbar sein.
- Bei UI-Aenderungen Screenshots, Browser-Smoke oder klare manuelle Pruefpfade im Abschluss nennen.

## Story-, Canon- und Game-Logic-Regeln

- Canon-State darf nicht willkuerlich ueberschrieben werden.
- Schutz des Kernloops: Setup -> Claim -> Character Setup -> Play -> Turn -> Persist/Reload.
- Story-Progression muss nachvollziehbar, reproduzierbar und testbar bleiben.
- Narrator-/LLM-Ausgaben duerfen nicht ungeprueft strukturellen Spielstatus zerstoeren.
- Game-State, Session-State, Presence-State und persistierte Daten klar unterscheiden.
- Presence/SSE ist Live-Sync, nicht persistente Wahrheit.
- Keine Magic Strings fuer zentrale Story-/State-Schluessel, wenn Konstanten oder Types sinnvoll sind.
- Neue Regeln muessen Edge Cases beruecksichtigen: leere Party, fehlender Save, kaputte Daten, Migration alter Daten, abgebrochene LLM-Antworten.
- Keine echten Ollama-/LLM-Calls in automatisierten Tests; Fake Narrator, Stubs oder Dependency Injection nutzen.

## Tests und Verifikation

- Nach Codeaenderungen passende Tests, Typechecks, Lints oder Builds ausfuehren.
- Wenn nicht alle Tests sinnvoll sind, gezielt relevante Tests ausfuehren und begruenden.
- Keine Erfolgsmeldung ohne echte Verifikation.
- Bei nicht ausfuehrbaren Tests ehrlich sagen, warum sie nicht liefen.
- Neue Logik nach Moeglichkeit mit Tests absichern.
- Bugfixes sollen Regressionstests bekommen, wenn der Aufwand vertretbar ist.
- Tests duerfen nur temporaere Datenpfade oder In-Memory-/Temp-Stores nutzen; `01_repo/aelunor-core/.runtime/` und `07_runtime/` bleiben unberuehrt.

## 8. Testing-Regeln

- Vor Testarbeit vorhandene Teststruktur pruefen.
- Backend-Tests liegen unter `01_repo/aelunor-core/tests/`.
- Kein Docker-Start fuer normale Tests.
- Kein echter Ollama-Call in Tests. Verwende Fake Narrator, Stub-Funktionen oder injizierte Service-Dependencies.
- Tests duerfen nur temporaere Daten schreiben. `.runtime/` und `07_runtime/` bleiben unberuehrt.
- Bei Turn-/Canon-/State-Aenderungen pruefen: Phase, Turn-Zaehler, Timeline, aktiver Turn-Status, Claims, State vor/nach Reload.
- Bei Frontend-Aenderungen passende Node-/Type-/Build-Checks ausfuehren, soweit verfuegbar.
- Wenn ein Check nicht laeuft, dokumentiere Befehl, Fehler, wahrscheinliche Ursache und naechsten Fix.

## 9. Doku-Regeln

- Dokumentation knapp und wartbar halten.
- Root-/Core-README nur fuer Setup, Start, Konfiguration, wichtige Checks und Kontext-Landkarten erweitern.
- Kontext-READMEs in aktiven Ordnern duerfen kurze Architektur- und Zustandskarten enthalten, damit Agents gezielt arbeiten koennen.
- Wenn Code verschoben wird, die naechstliegende Kontext-README im selben Slice aktualisieren.
- Architektur- oder Produktdetails gehoeren bevorzugt nach `02_docs/`.
- Neue Tests oder wichtige Workflows sollen kurz ausfuehrbar beschrieben werden.
- Keine veralteten Docker-, Ollama- oder Datenpfad-Hinweise stehen lassen.

## 10. Guardrails/Non-Goals

- Kein wildes Feature-Bloating.
- Keine grossen Architekturumbauten ohne Plan.
- Keine neue Dependency ohne Begruendung.
- Keine produktiven Runtime-Daten fuer Tests veraendern.
- Keine UI-E2E-Browser-Tests als Ersatz fuer Backend-Smoke-Tests.
- Keine Wiederbelebung der entfernten Legacy-UI, ausser der Nutzer fordert sie explizit.
- Keine Admin-/Analytics-/Tooling-Oberflaechen, wenn der Story-Spielkern nicht direkt davon profitiert.
- Keine Multiplayer-, Economy- oder Progression-Grosssysteme ohne klaren Scope.

## 11. Empfohlene Check-Kommandos

Aus `01_repo/aelunor-core/`:

```powershell
python -m pytest tests -q
python -m py_compile app/main.py
python scripts/check_progression_canon_gate.py
python scripts/check_codex_system.py
python scripts/check_element_system.py
```

Gezielte Backend-Checks:

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration -q
```

UI-v1-Checks aus `01_repo/aelunor-core/ui/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Windows-App/Packaging:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

## Sicherheit und Daten

- Keine Secrets, API-Keys, Tokens oder privaten Daten committen.
- Keine lokalen `.env`-Inhalte ausgeben.
- Keine echten Nutzer-/Kundendaten in Tests oder Fixtures uebernehmen.
- Keine gefaehrlichen Shell-Kommandos ohne klaren Grund.
- Keine Loesch-, Migrations- oder Formatierungsaktionen ohne vorherige Pruefung.
- Keine produktiven Runtime-Daten fuer Tests veraendern oder als Fixture missbrauchen.
- Bei externen API-Calls, Kosten, Netzwerkzugriff oder Modellaufrufen explizit dokumentieren, was ausgefuehrt wurde.

## Git- und Aenderungsverhalten

- Vor Beginn den aktuellen Arbeitsbaum pruefen.
- Bereits vorhandene Nutzeraenderungen nicht ueberschreiben.
- Nur Dateien aendern, die fuer die Aufgabe relevant sind.
- Keine unrelated formatting changes.
- Keine Dependency hinzufuegen ohne klaren Grund.
- Neue Dependencies nur nach Pruefung von Nutzen, Wartbarkeit und Alternativen.
- Relevante Installationsdateien aktualisieren, wenn Dependencies geaendert werden.
- Keine Build-Artefakte, Logs, Cache-Ordner oder generierte Dateien committen, ausser sie sind ausdruecklich Teil des Projekts.

## Agent-Kommunikation

- Kurz und konkret berichten.
- Keine uebertriebenen Erfolgsaussagen.
- Unsicherheiten offen markieren.
- Bei groesseren Aufgaben erst Plan, dann Umsetzung.
- Bei entdeckten Problemen nicht stillschweigend drumherum bauen, sondern Ursache benennen.
- Keine Architekturentscheidungen verstecken.

Abschlussberichte bei Codeaenderungen enthalten:

- geaenderte Dateien mit ungefaehrer Zeilendifferenz pro Datei
- was geaendert wurde
- welche Tests/Checks liefen
- welche Risiken oder offenen Punkte bleiben

## Definition of Done

Eine Aufgabe gilt nur als erledigt, wenn:

- die Aenderung fachlich zur Aufgabe passt
- Code modular und lesbar bleibt
- relevante Tests/Checks gelaufen sind oder Nichtausfuehrung begruendet wurde
- keine offensichtlichen Regressionen entstanden sind
- der Abschlussbericht die Aenderung nachvollziehbar macht

## Lokale Ergaenzungen

- Fuer spezielle Unterordner duerfen zusaetzliche `AGENTS.md` oder `AGENTS.override.md` Dateien angelegt werden, wenn dort andere Regeln gelten.
- Root-`AGENTS.md` bleibt bewusst knapp.
- Ausfuehrliche Spezialregeln gehoeren in separate Docs, auf die verwiesen wird.
