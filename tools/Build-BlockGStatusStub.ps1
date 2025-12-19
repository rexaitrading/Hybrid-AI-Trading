[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# Optional config override: configs/blockg_thresholds.json
$cfgPath = Join-Path $repoRoot "configs\blockg_thresholds.json"
$cfg = @{}
if (Test-Path $cfgPath) {
    try { $cfg = (Get-Content $cfgPath -Raw -Encoding UTF8) | ConvertFrom-Json } catch { $cfg = @{} }
}
function _CfgDouble([string]$name, [double]$fallback) {
    if ($cfg -and ($cfg.PSObject.Properties.Name -contains $name)) {
        $d = $fallback
        if ([double]::TryParse([string]$cfg.$name, [ref]$d)) { return $d }
    }
    return $fallback
}
function _CfgInt([string]$name, [int]$fallback) {
    if ($cfg -and ($cfg.PSObject.Properties.Name -contains $name)) {
        $x = $fallback
        if ([int]::TryParse([string]$cfg.$name, [ref]$x)) { return $x }
    }
    return $fallback
}
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
$phase4Ok = $false
$phase4Path = Join-Path $logsDir "phase4_validation_passed.json"
if (Test-Path $phase4Path) {
    try {
        $j = Get-Content $phase4Path -Raw -Encoding UTF8 | ConvertFrom-Json
        $phase4Ok = ((Slice-Date ([string]$j.as_of_date)) -eq $today) -and (To-Bool $j.phase4_ok_today)
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

# ---- Phase23 health (presence = ok unless explicit false) ----
$phase23Ok = $false
$phase23Path = Join-Path $logsDir "phase23_health_daily.csv"
if (Test-Path $phase23Path) {
    $rows = @(Import-Csv $phase23Path)
    foreach ($r in $rows) {
        $d = ""
        if ($r.PSObject.Properties.Name -contains "as_of_date") { $d = Slice-Date ([string]$r.as_of_date) }
        elseif ($r.PSObject.Properties.Name -contains "date") { $d = Slice-Date ([string]$r.date) }
        if ($d -eq $today) {
            if ($r.PSObject.Properties.Name -contains "phase23_health_ok_today" -and $r.phase23_health_ok_today) {
                $phase23Ok = To-Bool $r.phase23_health_ok_today
            } else {
                $phase23Ok = $true
            }
        }
    }
}

# ---- GateScore thresholds ----
$thrPath = Join-Path $repoRoot "docs\thresholds\gatescore_thresholds.json"
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
            $minEdge = _CfgDouble "min_edge_ratio" ([double]$obj.min_edge_ratio)
            $minMicro = _CfgDouble "min_micro_score" ([double]$obj.min_micro_score)
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
        [void][int]::TryParse([string]$r.pnl_samples, [ref]$gsPnl)
        [void][double]::TryParse([string]$r.mean_edge_ratio, [ref]$gsEdge)
        [void][double]::TryParse([string]$r.mean_micro_score, [ref]$gsMicro)
    }
}
$gsSamplesOk = ($gsCount -ge $minSignals -and $gsPnl -ge $minPnl)

# Split threshold checks (explicit reasons)
$edgeOk  = ($gsEdge -ge $minEdge)
$microOk = ($gsMicro -ge $minMicro)

# Optional paper micro override (NEVER affects live readiness)
$minMicroPaper = $minMicro
if ($cfg -and ($cfg.PSObject.Properties.Name -contains "min_micro_score_paper")) {
    $minMicroPaper = _CfgDouble "min_micro_score_paper" $minMicro
}
$microOkPaper = ($gsMicro -ge $minMicroPaper)

$gsThreshOk = ($edgeOk -and $microOk)
$gsOkToday   = ($gsFresh -and $gsSamplesOk -and $gsThreshOk)

# Paper readiness indicator (NON-LIVE): ignore micro if you want pipeline flow; live remains strict.
$nvdaReadyPaper = ($phase4Ok -and $gsFresh -and $gsSamplesOk -and $edgeOk)


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
if (-not $edgeOk)  { $reasons.Add("gatescore_edge_below_threshold") }
if (-not $microOk) { $reasons.Add("gatescore_micro_below_threshold") }

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

    nvda_blockg_ready       = $nvdaReady
    nvda_blockg_ready_paper = $nvdaReadyPaper
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
