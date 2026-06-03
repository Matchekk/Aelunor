@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start-windows-app.ps1" -BuildUiIfMissing
if errorlevel 1 (
  echo.
  echo Aelunor konnte nicht gestartet werden. Details stehen unter %%APPDATA%%\Aelunor\logs.
  pause
)
