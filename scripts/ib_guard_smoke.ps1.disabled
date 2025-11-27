param(
  [string]$ApiHost = '::1',
  [int]$Port = 7497,
  [int]$ClientId = 3021,
  [int]$Timeout = 12,
  [int]$MaxWaitSec = 600,
  [ValidateSet('auto','gateway','tws')]
  [string]$Mode = 'auto'
)
$ErrorActionPreference = 'Stop'

function Test-Listen([int]$Port){
  (Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | ? LocalPort -eq $Port | Measure-Object).Count
}

function Find-ExeSafe([string]$name){
  $candidates = @()
  if (Test-Path "C:\Jts") {
    $candidates += Get-ChildItem "C:\Jts" -Recurse -Filter $name -ErrorAction SilentlyContinue | % FullName
  }
  foreach ($root in @(${env:ProgramFiles}, ${env:ProgramFiles(x86)})) {
    if ($root) { $candidates += Get-ChildItem $root -Recurse -Filter $name -ErrorAction SilentlyContinue | % FullName }
  }
  if (-not $candidates) { return $null }
  # Drop backups/disabled
  $candidates = $candidates | ? { $_ -notmatch '(?i)\.bak|backup|disabled' }
  if (-not $candidates) { return $null }
  # Build sortable objects (prefer ibgateway over tws; then newest time)
  $objs = foreach ($p in $candidates) {
    $pp = $p.ToLower()
    $prio = 0
    if ($pp -like '*\ibgateway\*') { $prio = 2 }
    elseif ($pp -like '*\tws\*')   { $prio = 1 }
    [pscustomobject]@{ Path = $p; Priority = $prio; Time = (Get-Item $p).LastWriteTimeUtc }
  }
  $pick = $objs | Sort-Object @{Expression="Priority";Descending=$true}, @{Expression="Time";Descending=$true} | Select-Object -First 1
  if ($pick) { return $pick.Path } else { return $null }
}

function Ensure-Listener {
  param([string]$Mode)
  if ((Test-Listen -Port $Port) -gt 0) { Write-Host "Listener already present on $Port."; return }
  $gw  = Find-ExeSafe 'ibgateway.exe'
  $tws = Find-ExeSafe 'tws.exe'
  $exe = $null
  if ($Mode -eq 'gateway') {
    if ($gw) { $exe = $gw } else { $exe = $tws }
  } elseif ($Mode -eq 'tws') {
    if ($tws) { $exe = $tws } else { $exe = $gw }
  } else {
    if ($gw) { $exe = $gw } else { $exe = $tws }
  }
  if (-not $exe) { throw "Could not find ibgateway.exe or tws.exe (filtered backups/disabled). Start IB manually, then re-run." }
  Write-Host "Starting IB app: $exe"
  Start-Process -FilePath $exe -WindowStyle Minimized
  $deadline = (Get-Date).AddSeconds($MaxWaitSec)
  while ((Test-Listen -Port $Port) -eq 0) {
    if ((Get-Date) -gt $deadline) { throw "Timeout waiting for $Port to listen. Login to IB window and ensure API port=$Port." }
    Start-Sleep -Seconds 2
  }
  Write-Host "Socket listening on $Port."
}

function Probe-Handshake {
  $py = ".\.venv\Scripts\python.exe"
  $code = "from ib_insync import IB; ib=IB(); ok=ib.connect('$ApiHost',$Port,clientId=$ClientId,timeout=$Timeout); print('ok',bool(ok)); print('t', ib.reqCurrentTime() if ok else None); ib.disconnect(); import sys as _s; _s.exit(0 if ok else 2)"
  $deadline = (Get-Date).AddSeconds($MaxWaitSec)
  do {
    & $py -c $code 2>&1
    if ($LASTEXITCODE -eq 0) { return $true }
    if ((Get-Date) -gt $deadline) { return $false }
    Start-Sleep -Seconds 3
  } while ($true)
}

# 1) Start if needed
Ensure-Listener -Mode $Mode
# 2) Handshake now
$ok = Probe-Handshake
if (-not $ok) { Write-Warning "Handshake still blocked after $MaxWaitSec sec. Check IB window for modals / Allow API."; exit 2 }
Write-Host "Handshake OK -> running strict smoke..."
.\.venv\Scripts\python.exe -m pytest -q tests\smoke\test_ib_connect_smoke.py
