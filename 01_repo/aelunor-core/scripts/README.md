# Scripts Context

`scripts/` enthaelt technische Checks, lokale Start-/Stop-Skripte und
Longrun-/Benchmark-Hilfen. Normale Tests brauchen keinen Docker-Start.

## Standard-Checks

Aus `01_repo/aelunor-core/`:

```powershell
python scripts/check_progression_canon_gate.py
python scripts/check_element_system.py
python scripts/check_codex_system.py
```

Diese Checks muessen offline bleiben. Wenn ein Check World-/Codex-/Setup-Pfade
beruehrt, muessen LLM-Funktionen lokal gestubbt oder auf Fallbacks gelenkt
werden.

## Weitere Checks

| Script | Zweck |
| --- | --- |
| `check_progression_system.py` | Progression-System-Smoke |
| `check_extraction_quarantine.py` | Extractor-/Quarantine-Pfade |
| `check_turn_error_classification.py` | Turn-Fehlerklassifikation |
| `check_legacy_state_consolidation.py` | Legacy-State-Migration/Consolidation |
| `check_normalize_passive.py` | Normalisierungs-Smoke |
| `check_narrative_manifestation.py` | Narrative Manifestation/Progression |
| `check_ui_asset_usage.py` | UI-Asset-Referenzen |

## Start-/Build-Skripte

- `start_v1_dev.ps1`, `stop_v1_dev.ps1`: lokale Dev-Helfer.
- `build-windows.ps1`, `start-windows-app.ps1`, `rebuild_gm_app.ps1`: Windows-App/Packaging.

## Agent-Regeln

- Keine dauerhaften Debug-Prints in Produktcode fuer Script-Diagnosen.
- Haenger mit `faulthandler` oder gezielten Stubs diagnostizieren.
- Externe API-/LLM-Aufrufe im Abschlussbericht nennen, falls sie bewusst liefen.
