$ErrorActionPreference = "Stop"

$hub = "/mnt/d/Aelunor/10_tools/car-hub"
$command = 'export PATH="$PATH:/root/.local/bin"; cd /mnt/d/Aelunor/10_tools/car-hub; car doctor; car serve --host 0.0.0.0'

Write-Host "Checking WSL Ubuntu-24.04..."
wsl.exe -d Ubuntu-24.04 -- bash -lc "id; python3 --version; car --version; opencode --version"

Write-Host "Starting CAR from $hub ..."
wsl.exe -d Ubuntu-24.04 -- bash -lc $command
