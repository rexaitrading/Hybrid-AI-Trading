param(
  [int]$DaysWindow = 21,
  [int]$TargetSessions = 10,
  [switch]$PostSlack,
  [string]$SlackChannel = "C09J0KVQLJY",
  [switch]$ForceHeartbeatOK,
  [int]$HeartbeatGraceHours = 24
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# -------------------------------
# Heartbeat signals
# -------------------------------
$fileCandidates = @(
  "C:\ProgramData\ibg_status.json",
  "C:\ProgramData\ibg_live_status.json",
  "C:\IBC\state\ibg_status.json",
  "C:\IBC\state\ibg_live_status.json",
  (Join-Path $PWD "state\ibg_status.json"),
  (Join-Path $PWD "state\ibg_live_status.json")
)
$hbFiles = @()
foreach ($p in $fileCandidates) { if (Test-Path $p) { $hbFiles += $p } }

$hbInfo = @()
foreach ($f in $hbFiles) {
  try {
    $j = Get-Content $f -Raw | ConvertFrom-Json
    $hbInfo += [pscustomobject]@{ kind="file"; path=$f; ok=$true; last=(Get-Item $f).LastWriteTime; port=$j.port; pid=$j.pid }
  } catch {
    $hbInfo += [pscustomobject]@{ kind="file"; path=$f; ok=$false; last=(Get-Item $f).LastWriteTime; port=$null; pid=$null }
  }
}

try {
  $net = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 4001,4002 }
  foreach ($n in $net) {
    $hbInfo += [pscustomobject]@{ kind="port"; path=("tcp:{0}" -f $n.LocalPort); ok=$true; last=Get-Date; port=$n.LocalPort; pid=$n.OwningProcess }
  }
} catch {}

try {
  $p = Get-Process -Name "ibgateway" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($p) { $hbInfo += [pscustomobject]@{ kind="process"; path="ibgateway.exe"; ok=$true; last=$p.StartTime; port=$null; pid=$p.Id } }
} catch {}

$logCandidates = @("C:\ProgramData\IBG_Paper_Watchdog.log", (Join-Path $PWD "logs\IBG_Paper_Watchdog.log"))
foreach ($l in $logCandidates) { if (Test-Path $l) { $hbInfo += [pscustomobject]@{ kind="log"; path=$l; ok=$true; last=(Get-Item $l).LastWriteTime; port=$null; pid=$null } } }

$hbRecent = @($hbInfo | Where-Object { $_.ok -and $_.last -ge (Get-Date).AddHours(-$HeartbeatGraceHours) })
if ($ForceHeartbeatOK) { $hbRecent = @("forced") }

# -------------------------------
# Telemetry discovery
# -------------------------------
$telemetryDirs = @(
  (Join-Path $PWD "logs"),
  (Join-Path $PWD "runlogs"),
  (Join-Path $PWD "telemetry"),
  (Join-Path $PWD "data\logs")
) | Where-Object { Test-Path $_ }

$telemetryFiles = foreach ($d in $telemetryDirs) { Get-ChildItem $d -Recurse -File -Include *.jsonl -ErrorAction SilentlyContinue }

# Parse JSONL (sample tail)
$sampleCount = 200
$goodLines = 0; $badLines = 0
$lastDates  = New-Object System.Collections.Generic.List[datetime]
foreach ($f in $telemetryFiles) {
  $lines = Get-Content $f -Tail $sampleCount -ErrorAction SilentlyContinue
  foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
      $obj = $line | ConvertFrom-Json
      $goodLines++
      $ts = $null
      foreach ($k in @("ts","timestamp","time","created_at")) {
        if ($obj.PSObject.Properties.Name -contains $k) { $ts = [datetime]$obj.$k; break }
      }
      if ($ts) { [void]$lastDates.Add($ts.Date) }
    } catch { $badLines++ }
  }
}

# -------------------------------
# Sessions window (prefer markers)
# -------------------------------
$markerDir  = Join-Path $PWD "state\sessions"
$markerDays = @()
if (Test-Path $markerDir) {
  $markerDays = Get-ChildItem $markerDir -File -Filter "*.marker" -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty BaseName |
                Where-Object { $_ -match '^\d{4}-\d{2}-\d{2}$' } |
                ForEach-Object { [datetime]::ParseExact($_,'yyyy-MM-dd',$null) }
}

if ($markerDays.Count -gt 0) {
  $recent = $markerDays | Where-Object { $_ -ge (Get-Date).Date.AddDays(-$DaysWindow) }
  $uniqueSessions = @($recent | Select-Object -Unique).Count
} else {
  $recent = ($lastDates | Where-Object { $_ -ge (Get-Date).Date.AddDays(-$DaysWindow) })
  $uniqueSessions = @($recent | Select-Object -Unique).Count
}

# -------------------------------
# Summary & Slack
# -------------------------------
$readiness = if ( ($hbRecent.Count -ge 1) -and ($telemetryFiles.Count -ge 1) -and ($goodLines -gt 0) -and ($badLines -eq 0) -and ($uniqueSessions -ge $TargetSessions) ) { "SOAK-GREEN" } else { "SOAK-TODO" }

$result = [pscustomobject]@{
  phase          = "Phase8-PaperSoak"
  when           = (Get-Date).ToString("s")
  heartbeatsSeen = $hbInfo.Count
  heartbeatsOK   = $hbRecent.Count
  telemetryFiles = $telemetryFiles.Count
  jsonlGoodLines = $goodLines
  jsonlBadLines  = $badLines
  sessionsWindow = $DaysWindow
  sessions       = $uniqueSessions
  target         = $TargetSessions
  readiness      = $readiness
}
$result

if ($PostSlack) {
  try {
    Import-Module (Join-Path $PSScriptRoot "Slack-Alerts.psm1") -Force
    $msg = if ($readiness -eq "SOAK-GREEN") {
      " Phase8 SOAK GREEN | sessions=$uniqueSessions/$TargetSessions files=$($telemetryFiles.Count) hbOK=$($hbRecent.Count) | $(Get-Date -Format s)"
    } else {
      " Phase8 SOAK TODO | sessions=$uniqueSessions/$TargetSessions good=$goodLines bad=$badLines hbOK=$($hbRecent.Count) | $(Get-Date -Format s)"
    }
    Send-SlackAlert -Channel $SlackChannel -Text $msg | Out-Null
  } catch {
    Write-Warning ("Slack post skipped: " + $_.Exception.Message)
  }
}

$global:LASTEXITCODE = if ($readiness -eq "SOAK-GREEN") { 0 } else { 1 }
