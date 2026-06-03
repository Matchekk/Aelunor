param(
  [switch]$SkipInstall,
  [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$coreDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$uiDir = Join-Path $coreDir "ui"
$releaseDir = Join-Path $coreDir "release\windows"
$buildDir = Join-Path $coreDir "build\pyinstaller"

function Invoke-Step([string]$Name, [scriptblock]$Action) {
  Write-Host ""
  Write-Host "[aelunor-build] $Name"
  & $Action
}

Invoke-Step "checking Python" {
  python --version
}

Invoke-Step "checking Node" {
  node --version
  npm --version
}

if (-not $SkipInstall) {
  Invoke-Step "installing Python app dependencies" {
    Push-Location $coreDir
    try {
      python -m pip install -r requirements-app.txt
    }
    finally {
      Pop-Location
    }
  }
}

Invoke-Step "installing UI dependencies" {
  Push-Location $uiDir
  try {
    if (Test-Path "package-lock.json") {
      npm ci
    } else {
      npm install
    }
  }
  finally {
    Pop-Location
  }
}

if (-not $SkipTests) {
  Invoke-Step "running backend smoke checks" {
    Push-Location $coreDir
    try {
      python -m py_compile app/main.py app/desktop_launcher.py app/runtime_config.py
    }
    finally {
      Pop-Location
    }
  }

  Invoke-Step "running UI typecheck" {
    Push-Location $uiDir
    try {
      npm run typecheck
    }
    finally {
      Pop-Location
    }
  }
}

Invoke-Step "building UI" {
  Push-Location $uiDir
  try {
    npm run build
  }
  finally {
    Pop-Location
  }
}

$uiIndex = Join-Path $uiDir "dist\index.html"
if (-not (Test-Path $uiIndex)) {
  throw "UI build did not create $uiIndex"
}

Invoke-Step "cleaning previous Windows release" {
  if (Test-Path $releaseDir) {
    Remove-Item -LiteralPath $releaseDir -Recurse -Force
  }
  New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
  New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
}

$addData = @(
  "$(Join-Path $coreDir 'app\static');app\static",
  "$(Join-Path $coreDir 'app\prompts.json');app",
  "$(Join-Path $coreDir 'app\setup_catalog.json');app",
  "$(Join-Path $coreDir 'ui\dist');ui\dist"
)

$pyinstallerArgs = @(
  "-m", "PyInstaller",
  "--noconfirm",
  "--clean",
  "--windowed",
  "--name", "Aelunor",
  "--distpath", $releaseDir,
  "--workpath", $buildDir,
  "--specpath", $buildDir,
  "--paths", $coreDir
)

foreach ($entry in $addData) {
  $pyinstallerArgs += @("--add-data", $entry)
}

$pyinstallerArgs += @(
  "--collect-submodules", "app",
  "--collect-submodules", "uvicorn",
  "--collect-submodules", "webview",
  "app\desktop_launcher.py"
)

Invoke-Step "packaging Aelunor.exe" {
  Push-Location $coreDir
  try {
    python @pyinstallerArgs
  }
  finally {
    Pop-Location
  }
}

$exePath = Join-Path $releaseDir "Aelunor\Aelunor.exe"
if (-not (Test-Path $exePath)) {
  throw "PyInstaller did not create $exePath"
}

$startCmd = Join-Path $releaseDir "Aelunor starten.cmd"
@"
@echo off
cd /d "%~dp0Aelunor"
start "" "Aelunor.exe"
"@ | Set-Content -Path $startCmd -Encoding ASCII

Write-Host ""
Write-Host "[aelunor-build] done"
Write-Host "[aelunor-build] exe: $exePath"
Write-Host "[aelunor-build] launcher: $startCmd"
