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

- `01_repo/aelunor-core/`: aktiver Code-Stack
- `01_repo/aelunor-core/app/`: FastAPI, Router, Services, Legacy-UI, Assets
- `01_repo/aelunor-core/app/services/`: Domain- und State-Logik
- `01_repo/aelunor-core/app/routers/`: duenne HTTP-Adapter
- `01_repo/aelunor-core/ui/`: React/Vite-v1-UI; neue UI-Arbeit bevorzugt hier
- `01_repo/aelunor-core/tests/`: Backend-Tests
- `01_repo/aelunor-core/scripts/`: Checks, Dev-Start, Packaging
- `02_docs/`: Produkt-/Architektur-Dokumentation
- `07_runtime/`: lokale Runtime-Daten; nicht fuer Tests oder Experimente benutzen

## Arbeitsweise fuer Agents

- Erst verstehen, dann aendern.
- Vor Aenderungen relevante Dateien, Tests und lokale Konventionen lesen.
- Nicht blind grossflaechig refactoren.
- Kleine, nachvollziehbare Aenderungen bevorzugen.
- Bestehende Patterns, Ordnergrenzen und Public Contracts respektieren.
- Bei unklarer Architektur zuerst vorhandene Konventionen suchen.
- Aenderungen so umsetzen, dass sie reviewbar bleiben.
- Keine kosmetischen Massenaenderungen neben Feature-/Bugfix-Arbeit.
- Legacy-UI unter `app/static/` nur fuer Bugfixes, Kompatibilitaet oder explizite Aufgaben erweitern.

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
- State-Aenderungen zentral, nachvollziehbar, reload-sicher und typisiert halten.
- Keine versteckten Side Effects in UI-Komponenten.
- Story-/Canon-/Narrator-Logik nicht direkt in zufaellige UI-Komponenten schreiben.
- Wiederverwendbare Logik in passende Module auslagern.
- Dateinamen und Ordnerstruktur sollen Zweck und Verantwortlichkeit klar zeigen.
- Bestehende Architektur nicht umgehen, nur weil es schneller geht.
- Public Contracts bewahren: HTTP-API, JSON-State-Shape, Campaign-Dateien, Setup-Catalog, Turn-Records, UI-Erwartungen.

## UI/UX-Regeln

- Neue UI-Arbeit bevorzugt unter `01_repo/aelunor-core/ui/`.
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
- Tests duerfen nur temporaere Datenpfade oder In-Memory-/Temp-Stores nutzen; `07_runtime/` bleibt unberuehrt.

Empfohlene Checks aus `01_repo/aelunor-core/`:

```powershell
python -m pytest tests -q
python -m py_compile app/main.py
node --check app/static/app.js
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

- geaenderte Dateien
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
