# Grok2API (G2A) launcher — prefers 8010, falls back to 8012 if stale process occupies 8010
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File .\start_g2a.ps1
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Granian = Join-Path $Root '.venv\Scripts\granian.exe'
if (-not (Test-Path $Granian)) { throw "granian not found: $Granian" }

function Test-G2ANewBridge([int]$Port) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/openapi.json" -UseBasicParsing -TimeoutSec 2
    return ($r.Content -match 'sub2_base_url')
  } catch { return $false }
}

function Test-PortFree([int]$Port) {
  try {
    $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return -not $c
  } catch { return $true }
}

# If already new bridge on 8010, keep it
if (Test-G2ANewBridge 8010) {
  Write-Host "G2A already running with direct SUB2 bridge on http://127.0.0.1:8010"
  exit 0
}
if (Test-G2ANewBridge 8012) {
  Write-Host "G2A already running with direct SUB2 bridge on http://127.0.0.1:8012"
  Write-Host "NOTE: port 8010 may still be a stale process without sub2_base_url — use 8012 for SUB2导入."
  exit 0
}

# Stop our known granian processes for this tree
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match [regex]::Escape($Root) -and $_.CommandLine -match 'granian|app\.main:app')
} | ForEach-Object {
  Write-Host "Stopping PID $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

$port = 8010
if (-not (Test-PortFree 8010)) {
  Write-Host "Port 8010 is occupied by a non-killable/stale listener — starting on 8012 instead."
  $port = 8012
}

$log = Join-Path $env:TEMP "g2a_granian_$port.log"
$err = Join-Path $env:TEMP "g2a_granian_$port.err"
$p = Start-Process -FilePath $Granian -ArgumentList @(
  '--interface','asgi','--host','0.0.0.0','--port',"$port",'--workers','1','app.main:app'
) -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $log -RedirectStandardError $err

Start-Sleep -Seconds 3
if (Test-G2ANewBridge $port) {
  Write-Host "G2A started OK: http://127.0.0.1:$port  (PID $($p.Id))"
  Write-Host "Open admin: http://127.0.0.1:$port/admin/account"
  Write-Host "SUB2导入 uses Sub2 URL + Admin JWT; G2A Admin Key is app_key (not api_key)."
  exit 0
}

Write-Host "Failed to verify new bridge on port $port. Logs:"
if (Test-Path $err) { Get-Content $err -Tail 30 }
if (Test-Path $log) { Get-Content $log -Tail 30 }
exit 1

