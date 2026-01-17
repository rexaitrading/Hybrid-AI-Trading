[CmdletBinding()]
param(
  [string]$EvidencePath = ".\logs\ev_hard_evidence_raw.json",
  [string]$OutPath = ".\logs\ev_hard_snapshot.json"
)

# A3_EVH_OUTPATH_WIRE_BEGIN
$ld = (($env:HAT_LOGS_DIR + "")).Trim()
if($env:HAT_MARKET -and -not $ld){
  # Market-scoped mode must not bleed into global logs
  throw "[FAIL-CLOSED] HAT_MARKET set but HAT_LOGS_DIR missing (RunContext not wired)"
}
if($ld){
  # Only override defaults when caller did not explicitly pass a different path
  if((($EvidencePath + "") -eq ".\logs\ev_hard_evidence_raw.json") -or (($EvidencePath + "") -eq "logs\ev_hard_evidence_raw.json")){
    $EvidencePath = (Join-Path $ld "ev_hard_evidence_raw.json")
  }
  if((($OutPath + "") -eq ".\logs\ev_hard_snapshot.json") -or (($OutPath + "") -eq "logs\ev_hard_snapshot.json")){
    $OutPath = (Join-Path $ld "ev_hard_snapshot.json")
  }
}
# A3_EVH_OUTPATH_WIRE_END


Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function As-Bool([object]$v) {
  if ($null -eq $v) { return $false }
  if ($v -is [bool]) { return [bool]$v }
  $s = ("" + $v).Trim()
  return ($s -in @("1","true","True","TRUE","yes","YES"))
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $full = $Path
  if (-not [System.IO.Path]::IsPathRooted($full)) {
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    $full = Join-Path $repoRoot $Path
  }
  $dir = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $Text, $enc)
}
# Market-aware TODAY: if HAT_MARKET set, use Resolve-RunContext.as_of_date (fail-closed)
# --- ASOF PRIORITY (A3): env:HAT_ASOF_DATE wins when provided ---
$asofEnv = (($env:HAT_ASOF_DATE + "")).Trim()
if($asofEnv){
  $asofEnv = $asofEnv.Substring(0,[Math]::Min(10,$asofEnv.Length))
  if($asofEnv -match '^\d{4}-\d{2}-\d{2}$'){
    $today = $asofEnv
  }
}
# --- ASOF PRIORITY END ---
$m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
$sym = (($env:HAT_SYMBOL + "")).Trim().ToUpperInvariant()
if(-not $sym){ $sym = "NVDA" }

if($m){
  $rcPath = Join-Path $PSScriptRoot "Resolve-RunContext.ps1"
  if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
  $rcRaw = (& $rcPath -Market $m -Symbol $sym | Out-String)
  $rcRaw = (($rcRaw + "")).Trim()
  if(-not $rcRaw){ throw "[FAIL-CLOSED] Resolve-RunContext empty stdout" }
  $ix0 = $rcRaw.IndexOf("{"); $ix1 = $rcRaw.LastIndexOf("}")
  if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
  $rc = ($rcRaw.Substring($ix0, ($ix1 - $ix0 + 1))) | ConvertFrom-Json
  if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
  $today = ([string]$rc.as_of_date).Trim()
  if($today.Length -ge 10){ $today = $today.Substring(0,10) }
} else {
# A3_EVHARD_NO_LOCAL_TODAY: removed local clock override (RunContext is single truth)
}
# EVH_EFFECTIVE_TRADING_DAY_BEGIN
$effectiveTradingDay = $today
try {
  if($m){
    # Use the SAME market-aware $today as base for weekend adjustment (no local clock leakage)
    $effectiveTradingDay = (powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Get-EffectiveTradingDay.ps1" -TodayOverride $today).Trim()
  } else {
    $effectiveTradingDay = (powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Get-EffectiveTradingDay.ps1").Trim()
  }
  if(-not $effectiveTradingDay){ $effectiveTradingDay = $today }
} catch { $effectiveTradingDay = $today }
# EVH_EFFECTIVE_TRADING_DAY_END
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")


# EVH_SNAPSHOT_DATES_BEGIN
# Clarity fields (backward-compatible): distinguish snapshot run date vs evidence as-of date.
$evidenceAsOfDate = $null
# EVH_SNAPSHOT_DATES_END
$ok = $false
$reason = "evidence_missing_failclosed"

if (Test-Path $EvidencePath) {
  $raw = Get-Content $EvidencePath -Raw
  $j = $null
  try { $j = $raw | ConvertFrom-Json } catch { $j = $null }

  if ($null -eq $j) {
    $ok = $false
    $reason = "evidence_parse_error_failclosed"
  } else {
    # require evidence to be for today
    $asOf = (($j.as_of_date) + "").Trim()
    $evidenceAsOfDate = $asOf
    if ($asOf -ne $effectiveTradingDay) {
      $ok = $false
      $reason = ("evidence_stale_failclosed as_of_date={0} effective_trading_day={1} snapshot_date={2}" -f $asOf,$effectiveTradingDay,$today)
    } else {
      # if evidence itself declares ok=true, accept; otherwise fail
      $ok = As-Bool $j.ok
      $reason = if($ok){"computed_from_evidence_ok"}else{"computed_from_evidence_not_ok"}
    }
  }
} else {
  $ok = $false
  $reason = ("evidence_missing_failclosed path={0}" -f $EvidencePath)
}

$out = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  snapshot_date = $today
  evidence_as_of_date = $evidenceAsOfDate
  ok = $ok
  reason = $reason
} | ConvertTo-Json -Depth 6

Write-Utf8NoBom -Path $OutPath -Text ($out + "`n")
Write-Host ("[EV-HARD-SNAPSHOT] wrote {0} ok={1} reason={2}" -f $OutPath,$ok,$reason) -ForegroundColor Cyan
exit 0
