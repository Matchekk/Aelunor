# Aelunor CAR Missions

Use these as small, reviewable CAR missions. Do not combine them into one large task.

## Mission 1: Turn Pipeline Fake LLM Test

```text
Mission:
Ergaenze einen deterministischen Test fuer die echte turn_engine-Pipeline mit Fake-LLM. Ziel ist, nicht mehr create_turn_record komplett zu stubben, sondern die echte Patch-/Narrator-/Turn-Pipeline so weit wie moeglich durchlaufen zu lassen.

Kontext:
D:\Aelunor\01_repo\aelunor-core

Subagents:
- Architect Agent: prueft Testnaht, State-/Patch-Vertraege und Refactor-Risiken.
- QA/Test Agent: definiert Assertions, Temp-DATA_DIR und No-Network-Guards.
- Reviewer Agent: prueft finalen Diff und gibt GO/NO-GO.

Guardrails:
- Keine echten Ollama-/LLM-/requests.post-Aufrufe.
- Keine Nutzung von D:\Aelunor\07_runtime.
- Keine API-Vertraege aendern.
- Keine grossen Refactorings.
- ui/vite.config.ts ist user-owned und darf nicht committet werden.

Checks:
cd D:\Aelunor\01_repo\aelunor-core
python -m pytest tests -q
python -m py_compile app/main.py
python scripts/check_progression_canon_gate.py
python scripts/check_codex_system.py
python scripts/check_element_system.py

Deliverables:
- Geaenderte Testdateien.
- Beschreibung der Fake-LLM-Naht.
- Checks.
- Commit nur bei Reviewer-GO.
```

## Mission 2: API Contract Documentation

```text
Mission:
Dokumentiere die wichtigsten Aelunor-API- und JSON-State-Contracts fuer Campaign, Setup, Claim, Turn, Canon/Patch und Reload. Nur dokumentieren, keine Produktlogik aendern.

Kontext:
D:\Aelunor\01_repo\aelunor-core
D:\Aelunor\02_docs

Subagents:
- Architect Agent: liest Router, Schemas und Services.
- QA/Test Agent: gleicht dokumentierte Contracts mit vorhandenen Tests ab.
- Reviewer Agent: prueft auf Widersprueche und veraltete Aussagen.

Guardrails:
- Keine Backend-/API-Aenderungen.
- Keine Runtime-Daten lesen oder beschreiben.
- Keine grossen README-Umbauten.

Checks:
cd D:\Aelunor\01_repo\aelunor-core
python -m pytest tests -q

Deliverables:
- Kurze Contract-Doku unter D:\Aelunor\02_docs\technical.
- Liste offener Testluecken.
```

## Mission 3: Asset Mirror Check Script

```text
Mission:
Erstelle oder erweitere einen kleinen Check, der UI-Asset-Mirror-Risiken erkennt: fehlende Spiegelungen, zu grosse Dateien, ungewollte Source-Sheets in app/static und broken brand/ui-kit references.

Kontext:
D:\Aelunor\01_repo\aelunor-core
D:\Aelunor\03_brand
D:\Aelunor\02_docs\technical\PERFORMANCE_AND_STORAGE_NOTES.md
D:\Aelunor\02_docs\technical\UI_ASSET_KIT_NOTES.md

Subagents:
- Asset/Performance Agent: definiert Regeln und Pfade.
- QA/Test Agent: prueft Script-Determinismus.
- Reviewer Agent: verhindert Loesch-/Asset-Chaos.

Guardrails:
- Keine Assets loeschen.
- Keine Assets generieren.
- Keine grossen Bilddateien kopieren.
- Nur Check/Report, kein automatisches Reparieren.

Checks:
cd D:\Aelunor\01_repo\aelunor-core
python -m pytest tests -q
python scripts/check_element_system.py

Deliverables:
- Check-Script oder Test.
- Klare Fehlermeldungen.
- Doku, wie der Check ausgefuehrt wird.
```

## Mission 4: HubTopBar and SessionLibrary Polish

```text
Mission:
Polishe gezielt HubTopBar und SessionLibraryPanel in der React/Vite-v1-UI, damit sie weniger generisch-webartig und naeher am Aelunor RPG-HUD wirken. Keine neuen Assets generieren.

Kontext:
D:\Aelunor\01_repo\aelunor-core\ui
D:\Aelunor\03_brand\wallpapers\Hub_referenz.png
D:\Aelunor\02_docs\technical\UI_ASSET_KIT_NOTES.md

Subagents:
- UI/HUD Agent: prueft Referenzbildnaehe, Hierarchie und Responsive.
- Asset/Performance Agent: prueft, dass keine Asset-Abhaengigkeit eskaliert.
- Reviewer Agent: prueft Diff und UI-Risiken.

Guardrails:
- Keine Backend-/API-Aenderungen.
- Keine neuen PNG/WebP-Assets.
- Keine Legacy-UI-Arbeit in app/static/app.js.
- Keine Landingpage- oder Marketing-Layouts.

Checks:
cd D:\Aelunor\01_repo\aelunor-core\ui
npm run typecheck
npm run test
npm run build

Deliverables:
- Kleine UI/CSS-Aenderung.
- Responsive-Risiken notieren.
- Screenshot-Test empfohlen, falls Dev-Server laeuft.
```

## Mission 5: State Engine Refactor Plan

```text
Mission:
Erstelle einen Refactor-Plan fuer state_engine.py und angrenzende Turn-/Canon-Logik. Nicht umsetzen. Ziel ist ein sicherer Zerlegeplan nach bestehenden Tests und verbleibenden Testluecken.

Kontext:
D:\Aelunor\01_repo\aelunor-core

Subagents:
- Architect Agent: analysiert Modulgrenzen und Contract-Risiken.
- QA/Test Agent: mappt vorhandene Tests und benoetigte Regression Guards.
- Reviewer Agent: prueft, ob der Plan klein und migrationsfaehig ist.

Guardrails:
- Keine Produktlogik aendern.
- Keine Dateien loeschen.
- Keine API-Vertraege aendern.

Checks:
cd D:\Aelunor\01_repo\aelunor-core
python -m pytest tests -q

Deliverables:
- Refactor-Plan mit Reihenfolge.
- Risiko-/Test-Matrix.
- NO-GO-Bereiche fuer den ersten Refactor-Schritt.
```

