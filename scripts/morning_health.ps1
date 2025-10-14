param([ValidateSet("paper","live")][string]$Mode="paper")
$ErrorActionPreference='Stop'

# --- resolve script and repo paths robustly ---
$scriptFile = $MyInvocation.MyCommand.Path
if (-not $scriptFile) { $scriptFile = $PSCommandPath }  # fallback
$scriptDir  = Split-Path -Parent $scriptFile
$repoRoot   = Split-Path -Parent $scriptDir

$stPath     = Join-Path $scriptDir 'self_test_ibg.ps1'
$pyPath     = Join-Path $scriptDir 'selftest_ib_insync.py'
$logDir     = Join-Path $repoRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$statusPath = Join-Path $logDir 'morning_health_last.json'

# 1) TCP self-test (JSON)
$st = powershell -NoProfile -File $stPath -Mode $Mode 2>$null
try { $status = $st | ConvertFrom-Json } catch { $status = $null }

# 2) init result
$result = [ordered]@{
  ts                   = (Get-Date).ToString('s')
  mode                 = $Mode
  time_service         = $false
  tcp_listening        = $false
  handshake_connected  = $false
  serverTime           = $null
  exit                 = 2
}

# 3) merge self-test and optionally handshake
if ($status) {
  $result.time_service  = [bool]$status.time_service
  $result.tcp_listening = [bool]$status.tcp_listening

  if ($status.tcp_listening -eq $true) {
    if (Test-Path $pyPath) {
      $h = python $pyPath $Mode 2>$null
      try {
        $j = $h | ConvertFrom-Json
        $result.handshake_connected = [bool]$j.connected
        if ($null -ne $j.serverTime) { $result.serverTime = $j.serverTime }
        if ($result.handshake_connected) { $result.exit = 0 } else { $result.exit = 3 }
      } catch {
        $result.exit = 3
      }
    } else {
      $result.exit = 0
    }
  } else {
    $result.exit = 2
  }
} else {
  $result.exit = 3
}

# 4) emit JSON and persist to file
$result | ConvertTo-Json -Depth 4 | Out-Host
try { $result | ConvertTo-Json -Depth 4 | [System.IO.File]::WriteAllText($Path, $Value, (New-Object System.Text.UTF8Encoding($false))) $statusPath } catch {}

# --- append a one-line task log as well (path-robust) ---
try {
  \logs\morning_health_task.log = Join-Path \logs 'morning_health_task.log'
  \ mode= tcp= handshake= exit= = "\ mode=\ tcp=\ handshake=\ exit=\"
  Add-Content -Encoding UTF8 -Path \logs\morning_health_task.log -Value \ mode= tcp= handshake= exit=
} catch {}
exit $result.exit
