param(
  [string]$UserProfile = 'paper',
  [int]   $Port        = 4002,
  [string]$IbRoot      = 'C:\Jts\ibgateway\1039',
  [string]$IbcPath     = 'C:\IBC',
  [int]   $StartupWait = 35,
  [switch]$KeepAlive
)
$ErrorActionPreference = 'Stop'
$logDir = 'C:\Jts\logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$Log = Join-Path $logDir ("ibg_auto_{0}.log" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
Start-Transcript -Path $Log

Write-Host "[IBG] IbRoot     : $IbRoot"
Write-Host "[IBG] IbcPath    : $IbcPath"
Write-Host "[IBG] UserProfile: $UserProfile"
Write-Host "[IBG] Port       : $Port"

$cfg = Join-Path $IbRoot 'jts.ini'
if (-not (Test-Path $IbRoot)) { throw "IB root not found: $IbRoot" }
if (-not (Test-Path $cfg))    { Write-Warning "jts.ini not found at $cfg (continuing)"; }

$starterCandidates = @('ibcstart.bat','StartGateway.bat','startgateway.bat','gatewaystart.bat')
$starter = Get-ChildItem -Path $IbcPath -Recurse -Include $starterCandidates -File -ErrorAction SilentlyContinue |
          Select-Object -First 1
if (-not $starter) { throw "No IBC starter .bat found under $IbcPath (looked for: $($starterCandidates -join ', '))" }
Write-Host "[IBG] Using starter: $($starter.FullName)"

$env:IBC_PATH = $IbcPath
$env:IBC_INI  = Join-Path $IbcPath 'config.ini'
$env:JAVA_TOOL_OPTIONS = "-Dsun.java2d.noddraw=true"
if (-not (Test-Path $env:IBC_INI)) { Write-Warning "IBC config.ini missing at $($env:IBC_INI). Ensure profiles exist." }

function Test-PortReady([int]$p,[int]$timeoutSec=60) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  do {
    Start-Sleep -Milliseconds 800
    if (Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue) { return $true }
  } until ((Get-Date) -ge $deadline)
  $false
}

Write-Host "[IBG] Launching gateway..."
$wd = Split-Path -Parent $starter.FullName
$argSets = @("gw $UserProfile", "$UserProfile")

$launched = $false
foreach ($args in $argSets) {
  Write-Host "[IBG] Start-Process $($starter.Name) args: $args"
  try {
    Start-Process -FilePath $starter.FullName -WorkingDirectory $wd -ArgumentList $args -WindowStyle Hidden
  } catch {
    Write-Warning "[IBG] Start-Process failed with '$args': $($_.Exception.Message)"; continue
  }
  if (Test-PortReady -p $Port -timeoutSec $StartupWait) {
    $launched = $true; Write-Host "[IBG] Port $Port is listening. Launch OK using args '$args'."; break
  } else {
    Write-Warning "[IBG] Port $Port not listening after $StartupWait s with '$args'. Trying next..."
  }
}
if (-not $launched) { throw "IBG failed to open port $Port with known IBC starter patterns." }

if ($KeepAlive) {
  Write-Host "[IBG] Keep-alive ON (monitoring port $Port)..."
  while ($true) {
    Start-Sleep -Seconds 30
    if (-not (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)) {
      Write-Warning "[IBG] Port $Port dropped. Restarting gateway..."
      Get-Process ibgateway, javaw -ErrorAction SilentlyContinue | ForEach-Object {
        try { Stop-Process -Id $_.Id -Force -ErrorAction Stop } catch {}
      }
      try {
        Start-Process -FilePath $starter.FullName -WorkingDirectory $wd -ArgumentList $args -WindowStyle Hidden
        if (-not (Test-PortReady -p $Port -timeoutSec $StartupWait)) { Write-Error "[IBG] Restart failed: port $Port not up." }
        else { Write-Host "[IBG] Restart OK; port $Port listening." }
      } catch { Write-Error "[IBG] Restart exception: $($_.Exception.Message)" }
    }
  }
}
Stop-Transcript
