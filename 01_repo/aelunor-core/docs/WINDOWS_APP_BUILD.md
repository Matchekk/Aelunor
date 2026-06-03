# Aelunor Windows App Build

Diese Anleitung beschreibt den lokalen Windows-App-Workflow fuer Aelunor. Die App bleibt technisch ein lokaler FastAPI-Server mit gebauter React/Vite-UI; die Windows-App startet diesen Server automatisch auf `127.0.0.1` und zeigt `/v1/hub` in einem WebView-Fenster.

## Voraussetzungen

Aus `01_repo/aelunor-core/`:

```powershell
python --version
node --version
npm --version
```

Empfohlen:

- Python 3.11 oder 3.12
- Node.js 20+
- Windows WebView2 Runtime. Auf aktuellen Windows-Installationen ist sie normalerweise vorhanden.

App-Abhaengigkeiten installieren:

```powershell
python -m pip install -r requirements-app.txt
```

## Dev-Start

Backend plus Vite-Build-Watch wie bisher:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_v1_dev.ps1
```

Stoppen:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_v1_dev.ps1
```

Der Dev-Start nutzt `01_repo/aelunor-core/.runtime/` als lokalen Datenpfad.

## Windows-App aus dem Source starten

Per Doppelklick:

```text
01_repo/aelunor-core/Aelunor starten.bat
```

Oder per PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-windows-app.ps1 -BuildUiIfMissing
```

Das startet Aelunor im Desktop-Modus, baut die UI bei Bedarf und oeffnet ein App-Fenster. Der Server bindet nur lokal an `127.0.0.1` und verwendet einen freien dynamischen Port.

## Release-Build

Portable Windows-App bauen:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

Schneller Build ohne Install/Test-Schritte, wenn Abhaengigkeiten schon vorhanden sind:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -SkipInstall -SkipTests
```

Ergebnis:

```text
01_repo/aelunor-core/release/windows/Aelunor/Aelunor.exe
01_repo/aelunor-core/release/windows/Aelunor starten.cmd
```

Fuer normale Nutzung den Ordner `release/windows/` weitergeben oder lokal oeffnen und `Aelunor starten.cmd` doppelklicken.

Release-Smoke ohne sichtbares App-Fenster:

```powershell
$env:AELUNOR_DESKTOP_SMOKE="1"
.\release\windows\Aelunor\Aelunor.exe
Remove-Item Env:\AELUNOR_DESKTOP_SMOKE
```

## Speicherorte

Desktop-App:

```text
%APPDATA%\Aelunor\data\campaigns
%APPDATA%\Aelunor\data\state.json
%APPDATA%\Aelunor\logs\aelunor-desktop.log
```

Dev-Modus:

```text
01_repo/aelunor-core/.runtime/
```

Die Release-App schreibt Saves und Logs nicht in den App-Bundle-Ordner. Alte Saves werden nicht automatisch geloescht oder migriert.

## Build-Details

Der Build-Prozess:

1. installiert Python-App-Abhaengigkeiten aus `requirements-app.txt`
2. installiert UI-Abhaengigkeiten mit `npm ci`
3. prueft Python-Entrypoints mit `py_compile`
4. fuehrt `npm run typecheck` aus
5. baut die React-UI mit `npm run build`
6. paketiert `app/desktop_launcher.py` mit PyInstaller
7. bundelt `app/static`, `app/prompts.json`, `app/setup_catalog.json` und `ui/dist`

Build-Artefakte unter `build/`, `dist/` und `release/` sind generiert und werden nicht versioniert.

## Troubleshooting

Wenn die App nicht startet:

```powershell
Get-Content "$env:APPDATA\Aelunor\logs\aelunor-desktop.log" -Tail 80
```

Wenn `pywebview` fehlt:

```powershell
python -m pip install -r requirements-app.txt
```

Wenn die UI fehlt oder alt wirkt:

```powershell
cd ui
npm run build
cd ..
powershell -ExecutionPolicy Bypass -File scripts/start-windows-app.ps1
```

Wenn Windows SmartScreen warnt: Die lokal erzeugte `Aelunor.exe` ist nicht signiert. Das ist bei lokalen PyInstaller-Builds normal; fuer eine echte Distribution waere Code Signing der naechste Schritt.

Wenn Aelunor bereits laeuft: zuerst das vorhandene App-Fenster schliessen. Der Desktop-Launcher verhindert parallele Instanzen, damit dieselben Save-Dateien nicht gleichzeitig beschrieben werden.

## Bekannte Grenzen

- Der Release-Build ist portable, kein Installer.
- Ollama wird nicht gebuendelt. Die App nutzt den konfigurierten lokalen Ollama-Endpunkt, falls Narrator-Funktionen ihn brauchen.
- Die `.exe` ist ohne Code Signing unbekannt fuer SmartScreen.
- Multiplayer bleibt lokal. Der Desktop-Server bindet standardmaessig nur an `127.0.0.1`.
