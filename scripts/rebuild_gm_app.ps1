$ErrorActionPreference = "Stop"

Write-Host "[gm-app] down --remove-orphans"
docker compose down --remove-orphans

Write-Host "[gm-app] build --no-cache gm-app"
docker compose build --no-cache gm-app

Write-Host "[gm-app] up -d --force-recreate gm-app"
docker compose up -d --force-recreate gm-app

Write-Host "[gm-app] done"
