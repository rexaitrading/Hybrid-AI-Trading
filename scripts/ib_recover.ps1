param(
  [ValidateSet('gateway','tws')]
  [string]$Mode      = 'gateway',
  [string]$ApiHost   = '::1',
  [int]   $ApiPort   = 7497,
  [int]   $ClientId  = 3021,
  [int]   $Timeout   = 8,
  [int]   $MaxWaitSec= 180
)
$ErrorActionPreference = 'Stop'
$Py = ".\.venv\Scripts\python.exe"

function Stop-IB {
  Get-Process ibgateway,tws,javaw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
}

function Clear-IBLocks {
  $roots = @("C:\Jts", "$env:USERPROFILE\Jts", "$env:LOCALAPPDATA\Jts") | ForEach-Object { if (Test-Path $_) { $_ } }
  foreach ($r in $roots) {
    Get-ChildItem -Path $r -Recurse -Force -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match '(^|\.)(lock|lck|pid)$' -or $_.Name -match '^jts.*\.lck$' } |
      ForEach-Object { try { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue } catch {} }
  }
}

function Start-IB {
  $gw = 'C:\Jts\ibgateway\ibgateway.exe'
  $tw = 'C:\Jts\TWS\tws.exe'
  if ($Mode -eq 'gateway') {
    if (Test-Path $gw) { Start-Process -FilePath $gw -WindowStyle Minimized }
    elseif (Test-Path $tw) { Start-Process -FilePath $tw -WindowStyle Minimized }
    else { throw "IB Gateway/TWS not found under C:\Jts" }
  } else {
    if (Test-Path $tw) { Start-Process -FilePath $tw -WindowStyle Minimized }
    elseif (Test-Path $gw) { Start-Process -FilePath $gw -WindowStyle Minimized }
    else { throw "IB Gateway/TWS not found under C:\Jts" }
  }
}

function Test-Listen([int]$Port){
  $lis = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -eq $Port
  return [bool]$lis
}

# one-line Python probe (no newlines so -c works on PS 5.1)
$pyOneLiner = 'from ib_insync import IB; import sys; h=sys.argv[1]; p=int(sys.argv[2]); cid=int(sys.argv[3]); t=int(sys.argv[4]); ib=IB(); ok=ib.connect(h,p,clientId=cid,timeout=t); print(f"{h}:{p} connected="+str(bool(ok))); (print("currentTime", ib.reqCurrentTime()) if ok else None); ib.disconnect(); import sys as _s; _s.exit(0 if ok else 2)'

Write-Host "Stopping any existing IB processes..."
Stop-IB
Write-Host "Clearing potential lock files..."
Clear-IBLocks
Write-Host "Starting IB ($Mode)..."
Start-IB

# Wait for the socket to start listening
$deadline = (Get-Date).AddSeconds($MaxWaitSec)
while (-not (Test-Listen -Port $ApiPort)) {
  if ((Get-Date) -gt $deadline) { throw "Timed out waiting for port $ApiPort to listen. Please login to IB UI." }
  Start-Sleep -Seconds 2
}
Write-Host "Socket is listening on $ApiPort. Waiting for API handshake..."

# Retry handshake until success or timeout
$deadline = (Get-Date).AddSeconds($MaxWaitSec)
$ok = $false
do {
  try {
    $out = & $Py -c $pyOneLiner $ApiHost $ApiPort $ClientId $Timeout 2>&1
    if ($LASTEXITCODE -eq 0) { $ok = $true; $out; break }
  } catch { }
  if ((Get-Date) -gt $deadline) { break }
  Start-Sleep -Seconds 3
} while (-not $ok)

if (-not $ok) {
  Write-Warning "Handshake still blocked after $MaxWaitSec sec."
  Write-Host "ðŸ‘‰ Check IB UI for login/modals or the 'Allow incoming API connection?' prompt."
  exit 2
}
Write-Host "IB API handshake OK."
exit 0
