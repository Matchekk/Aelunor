param(
  [switch]$ForcePort8080
)

$ErrorActionPreference = "Stop"

$coreDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$uiDir = Join-Path $coreDir "ui"
$runtimeDir = Join-Path $coreDir ".runtime"
$pidFile = Join-Path $runtimeDir "dev_v1_pids.json"

function Stop-ProcessSafe([int]$PidToStop) {
  try {
    $proc = Get-Process -Id $PidToStop -ErrorAction Stop
    Stop-Process -Id $proc.Id -Force -ErrorAction Stop
    Write-Host "[dev-v1] stopped process $($proc.ProcessName) (PID $($proc.Id))"
  } catch {
    Write-Host "[dev-v1] process $PidToStop not running"
  }
}

function Clear-ExistingDevRun {
  if (-not (Test-Path $pidFile)) {
    return
  }
  try {
    $raw = Get-Content $pidFile -Raw
    if ($raw) {
      $state = $raw | ConvertFrom-Json
      if ($state.ui_build_watch_pid) {
        Stop-ProcessSafe -PidToStop ([int]$state.ui_build_watch_pid)
      }
      if ($state.uvicorn_pid) {
        Stop-ProcessSafe -PidToStop ([int]$state.uvicorn_pid)
      }
    }
  } catch {
    Write-Host "[dev-v1] unable to parse previous pid file, continuing"
  }
  Remove-Item $pidFile -ErrorAction SilentlyContinue
}

function Ensure-Port8080Free {
  $listeners = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
  if (-not $listeners) {
    return
  }

  $listenerPids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procPid in $listenerPids) {
    $proc = Get-Process -Id $procPid -ErrorAction SilentlyContinue
    if (-not $proc) {
      continue
    }

    $isSafeToStop = $proc.ProcessName -in @("python", "python3", "uvicorn")
    if ($isSafeToStop -or $ForcePort8080) {
      Stop-Process -Id $procPid -Force -ErrorAction Stop
      Write-Host "[dev-v1] freed :8080 by stopping $($proc.ProcessName) (PID $procPid)"
      continue
    }

    throw "Port 8080 is used by $($proc.ProcessName) (PID $procPid). Re-run with -ForcePort8080 to terminate it."
  }
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
Clear-ExistingDevRun
Ensure-Port8080Free

Push-Location $coreDir
try {
  Write-Host "[dev-v1] starting UI build watch"
  $uiWatch = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "build", "--", "--watch") -WorkingDirectory $uiDir -PassThru

  Write-Host "[dev-v1] starting uvicorn on 127.0.0.1:8080"
  $api = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8080") -WorkingDirectory $coreDir -PassThru

  $state = @{
    ui_build_watch_pid = $uiWatch.Id
    uvicorn_pid = $api.Id
    started_at = (Get-Date).ToString("o")
  }
  $state | ConvertTo-Json | Set-Content -Path $pidFile -Encoding UTF8

  Start-Sleep -Seconds 2
  Start-Process "http://127.0.0.1:8080/v1/hub" | Out-Null

  Write-Host "[dev-v1] ready"
  Write-Host "[dev-v1] ui watch pid: $($uiWatch.Id)"
  Write-Host "[dev-v1] uvicorn pid: $($api.Id)"
  Write-Host "[dev-v1] stop with: powershell -ExecutionPolicy Bypass -File scripts/stop_v1_dev.ps1"
}
finally {
  Pop-Location
}
