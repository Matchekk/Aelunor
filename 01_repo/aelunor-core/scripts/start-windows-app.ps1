param(
  [switch]$BuildUiIfMissing
)

$ErrorActionPreference = "Stop"

$coreDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$uiDir = Join-Path $coreDir "ui"
$uiIndex = Join-Path $uiDir "dist\index.html"

if ($BuildUiIfMissing -and -not (Test-Path $uiIndex)) {
  Write-Host "[aelunor-app] UI build missing; running npm install/build first"
  Push-Location $uiDir
  try {
    if (Test-Path "package-lock.json") {
      npm ci
    } else {
      npm install
    }
    npm run build
  }
  finally {
    Pop-Location
  }
}

Push-Location $coreDir
try {
  $env:AELUNOR_APP_MODE = "desktop"
  python -m app.desktop_launcher
}
finally {
  Pop-Location
}
