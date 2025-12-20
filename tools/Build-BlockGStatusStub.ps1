[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-Phase4OkToday([string]$RepoRoot, [string]$Today){
  $path = Join-Path $RepoRoot "logs\phase4_validation_passed.json"
  if(-not (Test-Path $path)){ return $false }

  try {
    $raw = Get-Content -LiteralPath $path -Raw -Encoding utf8
    $j = $raw | ConvertFrom-Json
    $asOf = [string]$j.as_of_date
    $ok = [bool]$j.phase4_ok_today
    return (($asOf.Substring(0,10)) -eq $Today) -and $ok
  } catch {
    return $false
  }
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")
$statusPath = Join-Path $logsDir "blockg_status_stub.json"

function To-Bool([object]$v) {
    if ($null -eq $v) { return $false }
    $s = ([string]$v).Trim().ToLowerInvariant()
    return $s -in @("1","true","yes","y","ok","pass","passed")
}
function Slice-Date([string]$d) {
    if (-not $d) { return "" }
    if ($d.Length -ge 10) { return $d.Substring(0,10) }
    return $d
}

# ---- Phase4 ----
    $phase4Ok = Get-Phase4OkToday $repoRoot $today
$phase4Path = Join-Path $logsDir "phase4_validation_passed.json"
if (Test-Path $phase4Path) {
    try {
        $j = Get-Content $phase4Path -Raw -Encoding UTF8 | ConvertFrom-Json
    $phase4Ok = Get-Phase4OkToday $repoRoot $today
    } catch { $phase4Ok = $false }
}

# ---- EV hard veto daily ----
$evHardOk = $false
$evPath = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"
if (Test-Path $evPath) {
    $rows = @(Import-Csv $evPath)
    foreach ($r in $rows) {
        if ((Slice-Date ([string]$r.date)) -eq $today) {
            if ($r.PSObject.Properties.Name -contains "ok") { $evHardOk = To-Bool $r.ok } else { $evHardOk = $true }
        }
    }
}

# ---- Phase23 health (must match today row; fail-closed) ----
$phase23Ok = $false
$phase23Path = Join-Path $logsDir "phase23_health_daily.csv"
$phase23SawToday = $false

if (Test-Path $phase23Path) {
    $rows = @(Import-Csv $phase23Path)
    foreach ($r in $rows) {
        $d = ""
        if ($r.PSObject.Properties.Name -contains "as_of_date") { $d = Slice-Date ([string]$r.as_of_date) }
        elseif ($r.PSObject.Properties.Name -contains "date") { $d = Slice-Date ([string]$r.date) }

        if ($d -ne $today) { continue }

        $phase23SawToday = $true

        if ($r.PSObject.Properties.Name -contains "phase23_ok") {
            $phase23Ok = To-Bool $r.phase23_ok
        }
        elseif ($r.PSObject.Properties.Name -contains "phase23_health_ok_today") {
            $phase23Ok = To-Bool $r.phase23_health_ok_today
        }
        else {
            # Unknown schema => fail-closed
            $phase23Ok = $false
        }
    }
}

if (-not $phase23SawToday) {
    # No today row => fail-closed
    $phase23Ok = $false
}

# ---- GateScore thresholds ----
$thrPath = Join-Path $repoRoot "configs\blockg_thresholds.json"
$thrPathDocs = Join-Path $repoRoot "docs\thresholds\gatescore_thresholds.json"
if (-not (Test-Path $thrPath) -and (Test-Path $thrPathDocs)) { $thrPath = $thrPathDocs }
$minSignals=999999; $minPnl=999999; $minEdge=999.0; $minMicro=999.0
if (Test-Path $thrPath) {
    try {
        $t = Get-Content $thrPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $symKey = "NVDA"
        $obj = $null
        if ($t.PSObject.Properties.Name -contains $symKey) { $obj = $t.$symKey }
        elseif ($t.PSObject.Properties.Name -contains "DEFAULT") { $obj = $t.DEFAULT }
        if ($null -ne $obj) {
            $minSignals = [int]$obj.min_signals
            $minPnl     = [int]$obj.min_pnl_samples
            $minEdge    = [double]$obj.min_edge_ratio
            $minMicro   = [double]$obj.min_micro_score
        }
    } catch { }
}

# ---- GateScore daily summary (NVDA today row) ----
$gsFresh=$false; $gsSamplesOk=$false; $gsThreshOk=$false
$gsCount=0; $gsPnl=0; $gsEdge=0.0; $gsMicro=0.0
$gsPath = Join-Path $logsDir "gatescore_daily_summary.csv"
if (Test-Path $gsPath) {
    $rows = @(Import-Csv $gsPath)
    foreach ($r in $rows) {
        if ($r.symbol -ne "NVDA") { continue }
        if ((Slice-Date ([string]$r.as_of_date)) -ne $today) { continue }
        $gsFresh = $true
        [void][int]::TryParse([string]$r.count_signals, [ref]$gsCount)
        # Producer-missing semantics: a "today row" with 0 signals is NOT fresh.
        if($gsCount -le 0){ $gsFresh = $false }
        [void][int]::TryParse([string]$r.pnl_samples, [ref]$gsPnl)
        [void][double]::TryParse([string]$r.mean_edge_ratio, [ref]$gsEdge)
        [void][double]::TryParse([string]$r.mean_micro_score, [ref]$gsMicro)
    }
}
$gsSamplesOk = ($gsCount -ge $minSignals -and $gsPnl -ge $minPnl)
$gsThreshOk  = (($gsEdge + 1e-9) -ge $minEdge -and ($gsMicro + 1e-9) -ge $minMicro)
$gsOkToday   = ($gsFresh -and $gsSamplesOk -and $gsThreshOk)

# ---- Per-symbol ready (institutional) ----
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsOkToday
$spyReady  = $false
$qqqReady  = $false

$reasons = New-Object System.Collections.Generic.List[string]
if (-not $phase23Ok) { $reasons.Add("phase23_health_ok_today=false") }
if (-not $evHardOk)  { $reasons.Add("ev_hard_daily_ok_today=false") }
if (-not $phase4Ok)  { $reasons.Add("phase4_ok_today=false") }
if (-not $gsFresh)   { $reasons.Add("gatescore_fresh_today=false") }
if (-not $gsSamplesOk) { $reasons.Add("gatescore_samples_not_ok") }
if (-not $gsThreshOk)  { $reasons.Add("gatescore_below_threshold") }

$payload = [ordered]@{
    ts_utc = $tsUtc
    as_of_date = $today

    phase23_health_ok_today = $phase23Ok
    ev_hard_daily_ok_today  = $evHardOk
    phase4_ok_today         = $phase4Ok

    gatescore_fresh_today   = $gsFresh
    gatescore_samples_ok    = $gsSamplesOk
    gatescore_threshold_ok_today = $gsThreshOk
    gatescore_ok_today      = $gsOkToday

    gatescore_samples       = $gsCount
    gatescore_min_samples   = $minSignals
    gatescore_pnl_samples   = $gsPnl
    gatescore_min_pnl_samples = $minPnl

    gatescore_mean_edge_ratio  = $gsEdge
    gatescore_mean_micro_score = $gsMicro
    gatescore_min_edge_ratio   = $minEdge
    gatescore_min_micro_score  = $minMicro

    nvda_blockg_ready = $nvdaReady
    spy_blockg_ready  = $spyReady
    qqq_blockg_ready  = $qqqReady

    reasons_not_ready = @($reasons)
}

$payloadJson = $payload | ConvertTo-Json -Depth 6
Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize

exit 0
