[CmdletBinding()]
param(
  [switch]$MonitorOnly = $true,     # default SAFE MODE
  [switch]$AllowKill,                # must be explicitly set to permit kill/restart
  [int]$BackoffOnFailSec = 300,      # 5 min backoff on failures
  [int]$BackoffOnSuccessSec = 30,    # normal cadence on success
[string]$IbHost = "127.0.0.1",
  [int]$Port = 4002,
  [int]$ClientId = 3099,

  [int]$IntervalSec = 30,
  [int]$FailStreakToRestart = 2,
  [int]$ProbeTimeoutSec = 15,

  # Optional: if you know exact IBG exe path, set it here; otherwise we just restart process if we can
  [string]$IbGatewayExe = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$log = Join-Path $repoRoot ("logs\ibg_api_watch_" + (Get-Date -Format yyyyMMdd) + ".log")
# --- single instance lock (per machine) ---
$lockDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $lockDir | Out-Null
$lock = Join-Path $lockDir "ibg_api_watchdog.lock"

try {
  $fs = [System.IO.File]::Open($lock, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
} catch {
  # another instance holds the lock
  exit 0
}
function Log([string]$m){
  $line = ("{0} {1}" -f (Get-Date -Format o), $m)
  $line | Out-Host
  $line | Add-Content -LiteralPath $log -Encoding utf8
}

function Probe(){
  $probe = Join-Path $repoRoot "tools\Probe-IbApiReady.ps1"

  # Run probe in a child powershell with non-terminating error behavior.
  # Discard ALL output, trust ONLY exit code.
  & powershell -NoProfile -ExecutionPolicy Bypass -Command `
    "`$ErrorActionPreference='Continue'; & `"$probe`" -IbHost `"$IbHost`" -Port $Port -ClientId $ClientId -TimeoutSec $ProbeTimeoutSec *> `$null; exit `$LASTEXITCODE" `
    *> $null

  return [int]$LASTEXITCODE
}

function KillIbGateway(){
  $k = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^(ibgateway|tws)$' })
  foreach($p in $k){ try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {} }
  # If IBG runs under java in your install, keep java-kill OFF by default (too risky).
  Log ("KILL ibgateway/tws killed=" + $k.Count)
}

function StartIbGateway(){
  if($IbGatewayExe -and (Test-Path -LiteralPath $IbGatewayExe)){
    Log ("START exe=" + $IbGatewayExe)
    Start-Process -FilePath $IbGatewayExe -WindowStyle Minimized | Out-Null
    return
  }
  Log "START skipped (IbGatewayExe not set). If IBG is launched via IBC/task, set -IbGatewayExe to make restart deterministic."
}

# Optional capture hook if you want
function CaptureContext(){
  $cap = Join-Path $repoRoot "tools\Capture-IBGDeathContext.ps1"
  if(Test-Path -LiteralPath $cap){
    try { & powershell -NoProfile -ExecutionPolicy Bypass -File $cap -LookbackMinutes 60 | Out-Host } catch {}
  }
}

Log "WATCH_START host=$IbHost port=$Port clientId=$ClientId interval=$IntervalSec"
$fail = 0

while($true){
  try{
    $rc = Probe
    if($rc -eq 0){
      $fail = 0
      Log "API_OK"`r`n      $fail = 0`r`n} else {
      $fail++
      Log ("API_FAIL rc=$rc failStreak=$fail")
    }

    if((-not $MonitorOnly) -and $AllowKill -and ($fail -ge $FailStreakToRestart) -and ($IbGatewayExe -and (Test-Path -LiteralPath $IbGatewayExe))) {
      Log "RESTART_SEQUENCE_BEGIN"
      CaptureContext
      KillIbGateway
      Start-Sleep -Seconds 2
      StartIbGateway
      Start-Sleep -Seconds 8
      $fail = 0
      Log "RESTART_SEQUENCE_END"
    }

  } catch {
    Log ("WATCH_ERR " + $_.Exception.Message)
  }

      if($rc -eq 0){
      Start-Sleep -Seconds ([Math]::Max(5, $BackoffOnSuccessSec))
    } else {
      Start-Sleep -Seconds ([Math]::Max(30, $BackoffOnFailSec))
    }
}








