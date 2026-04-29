# AGENTS.md

## 1. Projektziel

Aelunor ist ein lokales, browserbasiertes Multiplayer-Story-RPG mit KI-GM. Das Ziel ist ein stabiler, spielbarer Kernflow: Kampagne erstellen, Welt und Charaktere einrichten, Slots claimen, gemeinsam spielen, Story-Turns erzeugen, Canon/Patch-State konsistent halten und Live-Updates per Presence/SSE anzeigen.

Prioritaet: MVP-Stabilitaet vor Feature-Ausbau. Story-first UX hat Vorrang vor Admin- oder Analyse-Dashboards.

## 2. Aktive Projektpfade

- `01_repo/aelunor-core/`: aktiver Code-Stack.
- `01_repo/aelunor-core/app/`: FastAPI-Backend, Legacy-UI, statische Assets und Service-Layer.
- `01_repo/aelunor-core/app/main.py`: App-Wiring, Runtime-Konfiguration, Router-Composition und zentrale Glue-Funktionen.
- `01_repo/aelunor-core/app/services/`: Backend-Domainlogik fuer Campaigns, Setup, Claims, Turns, State, Boards, Context, Presence und Sheets.
- `01_repo/aelunor-core/app/routers/`: HTTP-Router um die Service-Layer.
- `01_repo/aelunor-core/app/static/`: Legacy-UI. Nicht weiter ausbauen, ausser ausdruecklich angefordert.
- `01_repo/aelunor-core/ui/`: React/Vite-v1-UI. Neue UI-Arbeit bevorzugt hier.
- `01_repo/aelunor-core/tests/`: Python-Tests.
- `01_repo/aelunor-core/scripts/`: technische Repo-Checks und Wartungsskripte.
- `02_docs/`: Produkt- und Architektur-Dokumentation.
- `05_prompts/`: Prompt-Bibliothek.
- `07_runtime/`: lokale Runtime-Daten. Nicht fuer Tests oder Experimente beschreiben, ausser der Nutzer fordert es explizit.

## 3. Architekturregeln

- Halte Aenderungen klein, reviewbar und am bestehenden Modulzuschnitt orientiert.
- Keine grossen Refactorings ohne kurzen Plan, betroffene Module, Migrationsrisiken und Validierungsstrategie.
- Bewahre oeffentliche Contracts: HTTP-API, JSON-State-Shape, Campaign-Dateien, Setup-Catalog-Struktur, Turn-Record-Format und UI-Erwartungen.
- Service-Logik gehoert in `app/services/`; Router bleiben duenne HTTP-Adapter.
- `app/main.py` ist Wiring/Composition. Neue Fachlogik dort nur, wenn sie bestehendes Wiring ergaenzt und nicht sinnvoll in Services passt.
- State-Aenderungen muessen deterministisch, validierbar und reload-sicher sein.
- Keine neue Dependency ohne klare Begruendung, vorhandene Alternativen und Update der relevanten Installationsdateien.

## 4. Backend-Regeln

- Bevorzuge Service-Tests fuer Fachlogik und kleine Integrationstests fuer Kernflows.
- Verwende Dependency Injection der bestehenden Service-Dependency-Dataclasses statt globales Monkeypatching, wenn moeglich.
- Persistenz ist JSON-basiert. Tests muessen temporaere Datenpfade oder In-Memory-/Temp-Stores nutzen.
- Bestehende Daten in `07_runtime/` duerfen nicht veraendert, geloescht oder als Testfixture missbraucht werden.
- Fehlerpfade sollen HTTP-konforme `HTTPException`s oder bestehende Error-Modelle nutzen.
- Auth-, Host-, Claim- und Phase-Regeln nicht umgehen, ausser ein Test benennt den Bypass explizit als Harness.
- Ollama/LLM-Aufrufe in Tests immer faken oder stubben.

## 5. Frontend-Regeln

- Neue Frontend-Arbeit bevorzugt in der React/Vite-v1-UI unter `01_repo/aelunor-core/ui/`.
- Legacy-UI in `app/static/` nur fuer Bugfixes, Kompatibilitaet oder ausdruecklich angeforderte Arbeit erweitern.
- Story-first UX: Spieleraktionen, aktueller Turn, GM-Text, Claims, Setup-Fortschritt und spielbare Lage haben Vorrang.
- Keine Admin-Dashboard-Expansion, solange der Spielkern nicht direkt davon profitiert.
- UI-State muss Backend-State respektieren; keine eigene parallele Wahrheit fuer Campaign-, Claim-, Turn- oder Canon-Daten einfuehren.
- Bei UX-Aenderungen mobile und Desktop-Layouts bedenken.

## 6. Game-/Narrator-/Canon-Regeln

- Schutz des Kernloops: Setup -> Claim -> Character Setup -> Play -> Turn -> Persist/Reload.
- Narrator-Ausgaben muessen Canon/Patch-State respektieren. Sichtbare Story-Aenderungen sollen, wo relevant, strukturiert im State landen.
- Turn-/Canon-Aenderungen brauchen Tests oder mindestens einen konkreten Testplan mit Fake Narrator.
- Keine echten LLM-/Ollama-Calls in automatisierten Tests.
- Balancing- und Tuningwerte nach Moeglichkeit datengetrieben halten. Hartcodierte Werte nur als klar erkennbare Prototype-Konstanten.
- Keine ueberdimensionierten Progression-, Economy- oder Multiplayer-Systeme ohne ausdruecklichen Scope.
- Patch-State, Turn-Record, Timeline, Recent Story, Memory Summary und Campaign Phase muessen nach Reload konsistent bleiben.

## 7. Multiplayer-/Presence-Regeln

- Claims, Host-Rechte und Player-Token sind Kerncontracts. Aenderungen daran besonders vorsichtig testen.
- Presence/SSE ist Live-Sync, nicht persistente Wahrheit. Persistente Wahrheit bleibt Campaign JSON/State.
- Blocking Actions und Live Activity muessen bei Fehlern sauber beendet werden.
- Repeated actions, Retry, Undo, Pause/Resume und Reload duerfen keine ungueltigen Zwischenzustaende erzeugen.
- Bei Multiplayer-Aenderungen mindestens Host, geclaimter Spieler, fremder Spieler und unautorisierter Zugriff als Faelle bedenken.

## 8. Testing-Regeln

- Vor Testarbeit vorhandene Teststruktur pruefen.
- Backend-Tests liegen unter `01_repo/aelunor-core/tests/`.
- Kein Docker-Start fuer normale Tests.
- Kein echter Ollama-Call in Tests. Verwende Fake Narrator, Stub-Funktionen oder injizierte Service-Dependencies.
- Tests duerfen nur temporaere Daten schreiben. `07_runtime/` bleibt unberuehrt.
- Bei Turn-/Canon-/State-Aenderungen pruefen: Phase, Turn-Zaehler, Timeline, aktiver Turn-Status, Claims, State vor/nach Reload.
- Bei Frontend-Aenderungen passende Node-/Type-/Build-Checks ausfuehren, soweit verfuegbar.
- Wenn ein Check nicht laeuft, dokumentiere Befehl, Fehler, wahrscheinliche Ursache und naechsten Fix.

## 9. Doku-Regeln

- Dokumentation knapp und wartbar halten.
- README nur fuer Setup, Start, Konfiguration und wichtige Checks erweitern.
- Architektur- oder Produktdetails gehoeren bevorzugt nach `02_docs/`.
- Neue Tests oder wichtige Workflows sollen kurz ausfuehrbar beschrieben werden.
- Keine veralteten Docker-, Ollama- oder Datenpfad-Hinweise stehen lassen.

## 10. Guardrails/Non-Goals

- Kein wildes Feature-Bloating.
- Keine grossen Architekturumbauten ohne Plan.
- Keine neue Dependency ohne Begruendung.
- Keine produktiven Runtime-Daten fuer Tests veraendern.
- Keine UI-E2E-Browser-Tests als Ersatz fuer Backend-Smoke-Tests.
- Keine Erweiterung der Legacy-UI, ausser der Nutzer fordert sie explizit.
- Keine Admin-/Analytics-/Tooling-Oberflaechen, wenn der Story-Spielkern nicht direkt davon profitiert.
- Keine Multiplayer-, Economy- oder Progression-Grosssysteme ohne klaren Scope.

## 11. Empfohlene Check-Kommandos

Aus `01_repo/aelunor-core/`:

```powershell
python -m pytest tests -q
python -m py_compile app/main.py
node --check app/static/app.js
python scripts/check_progression_canon_gate.py
python scripts/check_codex_system.py
python scripts/check_element_system.py
```

Fuer gezielte Backend-Arbeit:

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration -q
```

Fuer UI-v1-Arbeit zuerst `01_repo/aelunor-core/ui/package.json` lesen und die dort definierten Scripts verwenden.

## 12. Output-Konvention fuer Codex-Antworten

Bei Code-Aenderungen knapp berichten:

- Geaenderte Dateien.
- Zusammenfassung der Verhaltensaenderung.
- Tests und Checks mit exakten Befehlen.
- Bekannte Risiken oder nicht abgedeckte Bereiche.
- Empfohlener naechster Schritt.

Bei fehlgeschlagenen Checks immer angeben:

- Befehl.
- Fehler.
- Wahrscheinliche Ursache.
- Naechster Fix.
