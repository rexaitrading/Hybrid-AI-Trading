[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")]
  [string]$Market = "",
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

# Market-aware TODAY + per-market logs (fail-closed)
$m = (($Market + "")).Trim().ToUpperInvariant()
if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant() }
if(-not $m){ $m = "US" }
$Market = $m
$sym = (($Symbol + "")).Trim().ToUpperInvariant()
if(-not $sym){ $sym = (($env:HAT_SYMBOL + "")).Trim().ToUpperInvariant() }
if(-not $sym){ $sym = "NVDA" }
$Symbol = $sym

$rcPath = Join-Path $root "tools\Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
$rcRaw = (& $rcPath -Market $Market -Symbol $Symbol | Out-String).Trim()
$ix0 = $rcRaw.IndexOf("{"); $ix1 = $rcRaw.LastIndexOf("}")
if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
$rc = ($rcRaw.Substring($ix0, ($ix1-$ix0+1))) | ConvertFrom-Json
if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
$today = ([string]$rc.as_of_date).Trim()
if($today.Length -ge 10){ $today = $today.Substring(0,10) }

$gm = Join-Path $root "tools\Get-MarketLogRoot.ps1"
if(-not (Test-Path -LiteralPath $gm)){ throw "[FAIL-CLOSED] Missing Get-MarketLogRoot.ps1: $gm" }
$logDir = (& "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gm -Market $Market | Out-String).Trim()
if(-not $logDir){ $logDir = Join-Path (Join-Path $root "logs") $Market }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$outCsv = Join-Path $logDir "phase5_ev_hard_veto_daily.csv"

function Safe-Bool([bool]$b){ if($b){ "true" } else { "false" } }

# FAIL-CLOSED: real EV-hard veto snapshot must supply ok_today=true
$ok = $false
$reason = "snapshot_missing"

# PREFER_EV_HARD_SNAPSHOT_BEGIN
# Prefer per-market unified EV-hard snapshot; fallback to legacy veto snapshot; then root.
$snap = Join-Path $logDir "ev_hard_snapshot.json"
if (-not (Test-Path $snap)) { $snap = Join-Path $logDir "phase5_ev_hard_veto_snapshot.json" }
if (-not (Test-Path $snap)) { $snap = Join-Path (Join-Path $root "logs") "ev_hard_snapshot.json" }
if (-not (Test-Path $snap)) { $snap = Join-Path (Join-Path $root "logs") "phase5_ev_hard_veto_snapshot.json" }
# PREFER_EV_HARD_SNAPSHOT_END
# A2 evidence path for deterministic contract reasons
$snapshotPathUsed = $snap

if (Test-Path $snap) {
  try {
    $j = Get-Content $snap -Raw -Encoding utf8 | ConvertFrom-Json
function _SliceDate([string]$d){
  if(-not $d){ return "" }
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}
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
$header = "date,ok,reason,as_of_date,snapshot_path"
if (-not (Test-Path $outCsv)) { Set-Content -LiteralPath $outCsv -Encoding utf8 -Value $header }

# Remove existing today rows (idempotent)
$rows = @(Get-Content $outCsv -Encoding utf8)
$kept = @($rows[0])
for ($i=1; $i -lt $rows.Count; $i++){
  if ($rows[$i] -notmatch "^$today,"){ $kept += $rows[$i] }
}

$line = "$today,$(Safe-Bool $ok),$reason,$today,$snapshotPathUsed"
$kept += $line

[System.IO.File]::WriteAllLines($outCsv, $kept, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[EV-HARD] wrote $outCsv ok=$ok today=$today reason=$reason" -ForegroundColor Green
exit 0
