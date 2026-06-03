Du bist Senior Refactoring-Engineer für Aelunor.

Ziel:
Extrahiere `normalize_injury_state` und `normalize_scar_state` aus `app/services/state_engine.py` in ein neues fokussiertes World-Modul.

Dies ist ein aktiver Refactoring-Auftrag.
Du sollst Code ändern.
Der Scope ist absichtlich klein.

Warum:
Die Monolithen-Analyse hat `app/services/state_engine.py` als kritischstes God Module identifiziert. `normalize_injury_state` und `normalize_scar_state` sind kleine, klar abgrenzbare Bridge-Helfer und deshalb ein sicherer nächster Schritt, um `state_engine.py` weiter zu verkleinern, ohne Verhalten zu ändern.

Strikte Grenzen:
- Keine Turn Pipeline anfassen.
- Keine LLM-/Prompt-Logik anfassen.
- Keine API-Verträge ändern.
- Kein Save-State-Format ändern.
- Keine Features implementieren.
- Keine kosmetischen Massenänderungen.
- Keine Signaturen ändern.
- Keine Default-Werte ändern.
- Keine Commits.
- Keine bestehenden Tests abschwächen.
- Keine Netzwerkaufrufe.
- Keine Ollama Requests.

Zu prüfende Dateien:
- `app/services/state_engine.py`
- `tests/unit/test_state_engine.py`
- `tests/unit/test_turn_engine.py`
- `tests/integration/test_turn_pipeline_fake_llm.py`
- `tests/unit/test_main_state_engine_config.py`
- `docs/refactor_codex_log.md`, falls vorhanden
- `docs/codex_state_engine_dependency_inventory.md`, falls relevant vorhanden

Konkrete Aufgaben:

1. Neues Modul erstellen

Erstelle:

`app/services/world/injury_state.py`

Dieses Modul soll nur enthalten:
- nötige Imports
- `normalize_injury_state`
- `normalize_scar_state`
- kurze Modul-Doku im Stil der bestehenden `world/*`-Module

Keine neue Fachlogik.
Keine neuen Konstanten.
Keine globale `configure(...)`-Logik.

2. Funktionen 1:1 verschieben

Verschiebe aus `app/services/state_engine.py`:
- `normalize_injury_state`
- `normalize_scar_state`

Wichtig:
- Codeverhalten exakt beibehalten.
- Keine Umbenennung.
- Keine inhaltliche Glättung.
- Keine zusätzliche Validierung.
- Keine Typverschärfung.
- Keine neue Logik.

Wenn eine der Funktionen unerwartet auf globale Symbole aus `state_engine.py` zugreift:
- nicht raten
- nicht improvisieren
- Refactoring abbrechen
- im Abschlussbericht exakt nennen, welches Symbol blockiert

3. Rückwärtskompatibilität in `state_engine.py` sichern

In `app/services/state_engine.py`:
- entferne die beiden lokalen Funktionsdefinitionen
- importiere sie stattdessen aus `app.services.world.injury_state`
- bestehende externe Imports müssen weiter funktionieren

Beispiel-Ziel:
`from app.services.world.injury_state import normalize_injury_state, normalize_scar_state`

Falls `normalize_injury_state` oder `normalize_scar_state` in `EXPORTED_SYMBOLS` stehen:
- Einträge beibehalten
- Re-Export-Verhalten muss unverändert bleiben

4. Keine unnötigen Änderungen in `turn_engine.py`

`app/services/turn_engine.py` nicht ändern, außer ein Test zeigt zwingend, dass es nötig ist.

Falls `_PATCH_SANITIZER_DEP_NAMES` oder `_PATCH_VALIDATOR_DEP_NAMES` diese Funktionen weiterhin per globalem Wiring erwarten:
- Verhalten unverändert lassen
- nicht in diesem Schritt umbauen

5. Tests ergänzen nur falls nötig

Falls es noch keine direkte Charakterisierung gibt, ergänze minimale Tests für:
- `normalize_injury_state`
- `normalize_scar_state`

Bevorzugt in:
`tests/unit/test_state_engine.py`

Testfälle:
- valider Injury-State bleibt strukturell stabil
- ungültige/leere Injury-Daten werden wie bisher normalisiert
- valider Scar-State bleibt strukturell stabil
- ungültige/leere Scar-Daten werden wie bisher normalisiert

Wenn bestehende Tests diese Funktionen bereits ausreichend abdecken:
- keine neuen Tests erzwingen
- bestehende Tests laufen lassen

6. Dokumentation aktualisieren

Aktualisiere, falls vorhanden:

`docs/refactor_codex_log.md`

Ergänze unter dem passenden Abschnitt:
- `normalize_injury_state -> app/services/world/injury_state.py`
- `normalize_scar_state -> app/services/world/injury_state.py`

Aktualisiere zusätzlich, falls passend:

`docs/codex_state_engine_dependency_inventory.md`

Ergänze kurz:
- dass Injury-/Scar-Normalisierung aus `state_engine.py` herausgezogen wurde
- dass `state_engine.py` weiter rückwärtskompatibel re-exportiert
- dass die globale Wiring-Struktur dadurch noch nicht vollständig entfernt ist

7. Tests ausführen

Führe aus:

```powershell
cd D:\Aelunor\01_repo\aelunor-core
python -m pytest tests/unit/test_state_engine.py -q
python -m pytest tests/unit/test_turn_engine.py -q
python -m pytest tests/integration/test_turn_pipeline_fake_llm.py -q
python -m pytest tests/unit/test_main_state_engine_config.py -q
python -m pytest tests -x -q