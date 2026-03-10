$ErrorActionPreference = "Stop"

$coreDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeDir = Join-Path $coreDir ".runtime"
$pidFile = Join-Path $runtimeDir "dev_v1_pids.json"

function Stop-ProcessSafe([int]$PidToStop) {
  try {
    $proc = Get-Process -Id $PidToStop -ErrorAction Stop
    Stop-Process -Id $proc.Id -Force -ErrorAction Stop
    Write-Host "[dev-v1] stopped $($proc.ProcessName) (PID $($proc.Id))"
  } catch {
    Write-Host "[dev-v1] process $PidToStop not running"
  }
}

if (-not (Test-Path $pidFile)) {
  Write-Host "[dev-v1] no pid file found ($pidFile)"
  exit 0
}

$raw = Get-Content $pidFile -Raw
if (-not $raw) {
  Remove-Item $pidFile -ErrorAction SilentlyContinue
  Write-Host "[dev-v1] empty pid file removed"
  exit 0
}

$state = $raw | ConvertFrom-Json

if ($state.ui_build_watch_pid) {
  Stop-ProcessSafe -PidToStop ([int]$state.ui_build_watch_pid)
}
if ($state.uvicorn_pid) {
  Stop-ProcessSafe -PidToStop ([int]$state.uvicorn_pid)
}

Remove-Item $pidFile -ErrorAction SilentlyContinue
Write-Host "[dev-v1] stopped"
