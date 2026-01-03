[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$today = (Get-Date).ToString("yyyy-MM-dd")

# EVHARD_REASON_DETAIL_BEGIN
function _SliceDate([string]$d){
  if(-not $d){ return "" }
  if($d.Length -ge 10){ return $d.Substring(0,10) }
  return $d
}
# EVHARD_REASON_DETAIL_END
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outCsv = Join-Path $logDir "phase5_ev_hard_veto_daily.csv"

function Safe-Bool([bool]$b){ if($b){ "true" } else { "false" } }

# FAIL-CLOSED: real EV-hard veto snapshot must supply ok_today=true
$ok = $false
$reason = "snapshot_missing"

$snap = Join-Path $logDir "phase5_ev_hard_veto_snapshot.json"
if (Test-Path $snap) {
  try {
    $j = Get-Content $snap -Raw -Encoding utf8 | ConvertFrom-Json
    $d = _SliceDate ([string]$j.as_of_date)

    $okFlag = $false
    if ($j.PSObject.Properties.Name -contains "ok_today") { $okFlag = [bool]$j.ok_today }
    elseif ($j.PSObject.Properties.Name -contains "ok") { $okFlag = [bool]$j.ok }

    if ($d -ne $today) {
      $ok = $false
      $reason = ("snapshot_asof_mismatch as_of=" + $d + " today=" + $today)
    } elseif (-not $okFlag) {
      $ok = $false
      $reason = "snapshot_ok_false"
    } else {
      $ok = $true
      $reason = "snapshot_ok_today"
    }
  } catch {
    $ok = $false
    $reason = "snapshot_parse_failed"
  }
}

# Ensure header exists (exact schema expected by builder)
$header = "date,ok,reason"
if (-not (Test-Path $outCsv)) { Set-Content -LiteralPath $outCsv -Encoding utf8 -Value $header }

# Remove existing today rows (idempotent)
$rows = @(Get-Content $outCsv -Encoding utf8)
$kept = @($rows[0])
for ($i=1; $i -lt $rows.Count; $i++){
  if ($rows[$i] -notmatch "^$today,"){ $kept += $rows[$i] }
}

$line = "$today,$(Safe-Bool $ok),$reason"
$kept += $line

[System.IO.File]::WriteAllLines($outCsv, $kept, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[EV-HARD] wrote $outCsv ok=$ok today=$today reason=$reason" -ForegroundColor Green
exit 0
