[CmdletBinding()]
param(
  [int]$Port=4002,
  [int]$CheckSec=10,
  [int]$StartTimeoutSec=120,
  [int]$MinUptimeSec=180,
  [int]$BackoffSec=60
)

# --- SINGLE-INSTANCE LOCKFILE (cross-user safe) ---
$global:HAT_LOCK_PATH = "C:\IBC\watch_ibg_paper.lock"
try {
  $global:HAT_LOCK_FS = [System.IO.File]::Open($global:HAT_LOCK_PATH, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
  try { $global:HAT_LOCK_FS.Flush() } catch {}
  try { [System.GC]::KeepAlive($global:HAT_LOCK_FS) } catch {}
  try { $null = $global:HAT_LOCK_FS.SafeFileHandle } catch {}
  try { if(Get-Command _log -ErrorAction SilentlyContinue){ _log "LOCK_HELD=1 path=$global:HAT_LOCK_PATH" } } catch {}
} catch {
  exit 0
}
# --------------------------------------------------


# --- SINGLE-INSTANCE LOCK (prevents overlap) ---
$mutexName = "Global\HAT_WATCH_IBG_PAPER"
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)
if(-not $createdNew){ exit 0 }
# ---------------------------------------------


$ErrorActionPreference='Stop'

# --- Log init (always create log) ---
$global:IBG_WATCH_LOG = "C:\IBC\ibg_watch_paper.log"
try {
  $enc = New-Object System.Text.UTF8Encoding($false)
  if(-not (Test-Path $global:IBG_WATCH_LOG)){
    [System.IO.File]::WriteAllText($global:IBG_WATCH_LOG, "", $enc)
  }
  [System.IO.File]::AppendAllText($global:IBG_WATCH_LOG, ("{0} START watcher port={1}`n" -f (Get-Date -Format o), $Port), $enc)
} catch {
  try { Add-Content -LiteralPath "C:\IBC\ibg_watch_paper_fallback.log" -Encoding utf8 -Value (("{0} LOG_INIT_FAIL {1}" -f (Get-Date -Format o), $_.Exception.Message)) } catch {}
}

function _log([string]$msg){
  try {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::AppendAllText($global:IBG_WATCH_LOG, ("{0} {1}`n" -f (Get-Date -Format o), $msg), $enc)
  } catch {
    try { Add-Content -LiteralPath "C:\IBC\ibg_watch_paper_fallback.log" -Encoding utf8 -Value (("{0} LOG_FAIL {1}" -f (Get-Date -Format o), $_.Exception.Message)) } catch {}
  }
}

# Try to load shared heartbeat/status helpers if available
$fn = "C:\IBC\Watch-IBG.Functions.ps1"
if(Test-Path $fn){
  try { . $fn; _log "DOTSOURCED Functions=1" } catch { _log ("DOTSOURCED_FAIL " + $_.Exception.Message) }
} else {
  _log "DOTSOURCED Functions=0 (missing)"
}

function _listen {
  @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) | Select-Object -First 1
}

function _ownerPid {
  $ls = _listen
  if($ls){ return [int]$ls.OwningProcess }
  return $null
}

function _procUptimeSec([int]$pid){
  try{
    $p = Get-Process -Id $pid -ErrorAction Stop
    return [int]((New-TimeSpan -Start $p.StartTime -End (Get-Date)).TotalSeconds)
  } catch { return $null }
}

function _start {
  $pid = _ownerPid
  if($pid){
    _log "START_SKIPPED port=$Port already_listening pid=$pid"
    return
  }

  $p = Get-Process -Name ibgateway,ibgateway1 -ErrorAction SilentlyContinue | Select-Object -First 1
  if($p){
    $u = _procUptimeSec -pid $p.Id
    if($u -ne $null -and $u -lt $MinUptimeSec){
      _log "RESTART_BLOCKED reason=uptime_lt_min pid=$($p.Id) uptimeSec=$u min=$MinUptimeSec"
      return
    }
    _log "NO_KILL policy=observe_only reason=port_not_listening pid=$($p.Id) name=$($p.ProcessName)"
    return
  }

  _log "START_PROC exe=C:\Jts\ibgateway\1040\ibgateway1.exe"
  Start-Process 'C:\Jts\ibgateway\1040\ibgateway1.exe' -WorkingDirectory 'C:\Jts\ibgateway\1040'

  $t0=Get-Date
  while(-not (_listen) -and ((Get-Date)-$t0).TotalSeconds -lt $StartTimeoutSec){
    Start-Sleep -Milliseconds 300
  }

  if(_listen){
    _log "START_OK port=$Port"
  } else {
    _log "START_FAIL port=$Port timeoutSec=$StartTimeoutSec backoffSec=$BackoffSec"
    Start-Sleep -Seconds $BackoffSec
  }
}

while($true){
  if(-not (_listen)){
  $ibg = @(Get-Process -Name ibgateway,ibgateway1 -ErrorAction SilentlyContinue)
  if($ibg.Count -gt 0){
    $p0 = $ibg | Sort-Object StartTime | Select-Object -First 1
    $upt = $null; try { $upt = [int]((New-TimeSpan -Start $p0.StartTime -End (Get-Date)).TotalSeconds) } catch {}
    _log ("PORT_DOWN port=$Port action=start ibg_procs=" + ($ibg.Count) + " pids=" + (($ibg.Id -join ",")) + " uptimeSec=" + $upt)
  } else {
    _log ("PORT_DOWN port=$Port action=start ibg_procs=0")
  }
    _start
  }

  # Heartbeat file if Functions.ps1 provided Write-Heartbeat + Get-IBGStatus
  if(Get-Command Get-IBGStatus -ErrorAction SilentlyContinue){
    try {
      $s = Get-IBGStatus -Port $Port
      if(Get-Command Write-Heartbeat -ErrorAction SilentlyContinue){
        Write-Heartbeat -Port $Port -PortUp $s.PortUp -GwPid $s.GW_PID -Uptime $s.Uptime -CPU $s.CPU -RSS ([double]($s.RSS -as [double])) -GwInfo $s.Info -GwPath ($s.Path + "")
      }
    } catch {}
  }

  Start-Sleep -Seconds $CheckSec
}