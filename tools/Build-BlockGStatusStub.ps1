[CmdletBinding()]
param(
    # NVDA|SPY|QQQ|ALL ; default ALL for builder
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$logsDir  = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

$statusPath = Join-Path $logsDir "blockg_status_stub.json"

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

function _ToBool {
    param([object]$v)
    if ($null -eq $v) { return $false }
    $s = ([string]$v).Trim().ToLowerInvariant()
    return $s -in @("1","true","yes","y","ok","pass","passed")
}

function Get-TodayRow {
    param([Parameter(Mandatory = $true)][string]$CsvPath)

    if (-not (Test-Path $CsvPath)) { return $null }

    $rows = Import-Csv -Path $CsvPath
    $rowArray = @($rows)
    if (@($1).Count -eq 0) { return $null }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $candidateRows = @()

    foreach ($row in $rowArray) {
        $props = $row.PSObject.Properties
        $dateVal = $null

        foreach ($name in @("as_of_date","date","trading_day")) {
            $prop = $props[$name]
            if ($prop -ne $null -and $prop.Value) { $dateVal = [string]$prop.Value; break }
        }

        if ($dateVal) {
            if ($dateVal.Length -ge 10) { $dateVal = $dateVal.Substring(0,10) }
            if ($dateVal -eq $today) { $candidateRows += $row }
        }
    }

    if (@($1).Count -gt 0) { return $candidateRows[-1] }
    return $null
}

function Get-Phase4OkToday {
    param([string]$LogsDir)

    # Prefer common filenames; fail-closed if none.
    $candidates = @( @(
        (Join-Path $LogsDir "phase4_validation_passed.json"),
        (Join-Path $LogsDir "phase4_passed.json"),
        (Join-Path $LogsDir "phase4_validation.json")
    ) | Where-Object { Test-Path [CmdletBinding()]
param(
    # NVDA|SPY|QQQ|ALL ; default ALL for builder
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$logsDir  = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

$statusPath = Join-Path $logsDir "blockg_status_stub.json"

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

function _ToBool {
    param([object]$v)
    if ($null -eq $v) { return $false }
    $s = ([string]$v).Trim().ToLowerInvariant()
    return $s -in @("1","true","yes","y","ok","pass","passed")
}

function Get-TodayRow {
    param([Parameter(Mandatory = $true)][string]$CsvPath)

    if (-not (Test-Path $CsvPath)) { return $null }

    $rows = Import-Csv -Path $CsvPath
    $rowArray = @($rows)
    if (@($1).Count -eq 0) { return $null }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $candidateRows = @()

    foreach ($row in $rowArray) {
        $props = $row.PSObject.Properties
        $dateVal = $null

        foreach ($name in @("as_of_date","date","trading_day")) {
            $prop = $props[$name]
            if ($prop -ne $null -and $prop.Value) { $dateVal = [string]$prop.Value; break }
        }

        if ($dateVal) {
            if ($dateVal.Length -ge 10) { $dateVal = $dateVal.Substring(0,10) }
            if ($dateVal -eq $today) { $candidateRows += $row }
        }
    }

    if (@($1).Count -gt 0) { return $candidateRows[-1] }
    return $null
}

function Get-Phase4OkToday {
    param([string]$LogsDir)

    # Prefer common filenames; fail-closed if none.
    $candidates = @(
        (Join-Path $LogsDir "phase4_validation_passed.json"),
        (Join-Path $LogsDir "phase4_passed.json"),
        (Join-Path $LogsDir "phase4_validation.json")
    ) | Where-Object { Test-Path $_ }

    if (@($1).Count -eq 0) { return $false }

    foreach ($p in $candidates) {
        try {
            $raw = Get-Content $p -Raw -Encoding UTF8
            $j = $raw | ConvertFrom-Json

            # Try common keys; fallback: if as_of_date == today AND ok-ish flag exists
            $asOf = $null
            foreach ($k in @("as_of_date","date","trading_day")) {
                if ($j.PSObject.Properties.Name -contains $k) {
                    $asOf = [string]$j.$k
                    if ($asOf.Length -ge 10) { $asOf = $asOf.Substring(0,10) }
                    break
                }
            }

            $ok = $false
            foreach ($k in @("phase4_ok_today","ok_today","passed","phase4_passed","phase4_ok")) {
                if ($j.PSObject.Properties.Name -contains $k) {
                    $ok = _ToBool $j.$k
                    break
                }
            }

            if ($asOf -eq $today -and $ok) { return $true }
        } catch {
            # ignore and try next
        }
    }

    return $false
}

function Get-GateScoreQualityForSymbol {
    param(
        [Parameter(Mandatory = $true)][string]$CsvPath,
        [Parameter(Mandatory = $true)][string]$Symbol,
        [int]$MinSignals = 3,
        [int]$MinPnlSamples = 1,
        [double]$MinScore = 0.0
    )

    $out = [ordered]@{
        fresh_today = $false
        samples_ok  = $false
        score_ok    = $false
        score_value = 0.0
        count_signals = 0
        pnl_samples = 0
    }

    if (-not (Test-Path $CsvPath)) { return $out }

    $rows = @(Import-Csv -Path $CsvPath)
    if (@($1).Count -eq 0) { return $out }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $target = $null

    foreach ($row in $rows) {
        $props = $row.PSObject.Properties
        $sym = $props["symbol"]
        if ($sym -eq $null -or -not $sym.Value) { continue }
        if ([string]$sym.Value -ne $Symbol) { continue }

        $asOf = $props["as_of_date"]
        if ($asOf -eq $null -or -not $asOf.Value) { continue }
        $d = [string]$asOf.Value
        if ($d.Length -ge 10) { $d = $d.Substring(0,10) }
        if ($d -ne $today) { continue }

        $target = $row
        break
    }

    if ($null -eq $target) { return $out }

    $out.fresh_today = $true

    $cs = 0
    $ps = 0
    $sv = 0.0

    $p = $target.PSObject.Properties

    if ($p["count_signals"] -and $p["count_signals"].Value) {
        [void][int]::TryParse([string]$p["count_signals"].Value, [ref]$cs)
    }
    if ($p["pnl_samples"] -and $p["pnl_samples"].Value) {
        [void][int]::TryParse([string]$p["pnl_samples"].Value, [ref]$ps)
    }

    foreach ($k in @("gatescore","gate_score","score","value")) {
        if ($p[$k] -and $p[$k].Value) {
            [void][double]::TryParse([string]$p[$k].Value, [ref]$sv)
            break
        }
    }

    @($1).Count_signals = $cs
    $out.pnl_samples   = $ps
    $out.score_value   = $sv

    $out.samples_ok = ($cs -ge $MinSignals -and $ps -ge $MinPnlSamples)
    $out.score_ok   = ($sv -ge $MinScore)

    return $out
}

# === Inputs ===
$phase23Csv = Join-Path $logsDir "phase23_health_daily.csv"
$evCsv      = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"
$gsCsv      = Join-Path $logsDir "gatescore_daily_summary.csv"

# === Core daily requirements ===
$phase23Row = Get-TodayRow -CsvPath $phase23Csv
$phase23Ok  = $false
if ($phase23Row -ne $null) {
    $prop = $phase23Row.PSObject.Properties["phase23_health_ok_today"]
    $phase23Ok = if ($prop -and $prop.Value) { _ToBool $prop.Value } else { $true }
}

$evRow    = Get-TodayRow -CsvPath $evCsv
$evHardOk = $false
if ($evRow -ne $null) {
    $prop = $evRow.PSObject.Properties["ev_hard_daily_ok_today"]
    $evHardOk = if ($prop -and $prop.Value) { _ToBool $prop.Value } else { $true }
}

$phase4Ok = Get-Phase4OkToday -LogsDir $logsDir

# === GateScore quality (tunable thresholds) ===
# defaults: minimal, but still explicit
$minSignals = 3
$minPnlSamples = 1
$minScore = 0.0

$gsNvda = Get-GateScoreQualityForSymbol -CsvPath $gsCsv -Symbol "NVDA" -MinSignals $minSignals -MinPnlSamples $minPnlSamples -MinScore $minScore
$gsSpy  = Get-GateScoreQualityForSymbol -CsvPath $gsCsv -Symbol "SPY"  -MinSignals $minSignals -MinPnlSamples $minPnlSamples -MinScore $minScore
$gsQqq  = Get-GateScoreQualityForSymbol -CsvPath $gsCsv -Symbol "QQQ"  -MinSignals $minSignals -MinPnlSamples $minPnlSamples -MinScore $minScore

# For backward compatibility, keep these as NVDA’s
$gsFresh = [bool]$gsNvda.fresh_today
$gsSamplesOk = [bool]$gsNvda.samples_ok
$gsValue = [double]$gsNvda.score_value

# === Per-symbol readiness (institutional: include Phase4) ===
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and [bool]$gsNvda.fresh_today -and [bool]$gsNvda.samples_ok -and [bool]$gsNvda.score_ok
$spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and [bool]$gsSpy.fresh_today  -and [bool]$gsSpy.samples_ok  -and [bool]$gsSpy.score_ok
$qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and [bool]$gsQqq.fresh_today  -and [bool]$gsQqq.samples_ok  -and [bool]$gsQqq.score_ok

# === reasons_not_ready ===
$reasons = New-Object System.Collections.Generic.List[string]
if (-not $phase23Ok) { $reasons.Add("phase23_health_ok_today=false") }
if (-not $evHardOk)  { $reasons.Add("ev_hard_daily_ok_today=false") }
if (-not $phase4Ok)  { $reasons.Add("phase4_ok_today=false") }

# NVDA-focused diagnostic fields (compat with Python helper)
if (-not $gsFresh) { $reasons.Add("gatescore_fresh_today=false") }
if (-not $gsSamplesOk) { $reasons.Add("gatescore_samples_not_ok") }
if (-not [bool]$gsNvda.score_ok) { $reasons.Add("gatescore_below_threshold") }

# === Build JSON payload ===
$payload = [ordered]@{
    ts_utc                   = $tsUtc
    as_of_date               = $today

    # Core daily requirements
    phase23_health_ok_today  = $phase23Ok
    ev_hard_daily_ok_today   = $evHardOk
    phase4_ok_today          = $phase4Ok

    # GateScore (NVDA-compatible legacy fields)
    gatescore_fresh_today    = $gsFresh
    gatescore_samples_ok     = $gsSamplesOk
    gatescore_value          = $gsValue
    gatescore_min_required   = $minScore
    gatescore_samples        = [int]@($1).Count_signals
    gatescore_min_samples    = [int]$minSignals

    # Per-symbol readiness
    nvda_blockg_ready        = $nvdaReady
    spy_blockg_ready         = $spyReady
    qqq_blockg_ready         = $qqqReady

    reasons_not_ready        = @($reasons)
}

$payloadJson = $payload | ConvertTo-Json -Depth 6

Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan

# UTF-8 no BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize } )

    if (@($1).Count -eq 0) { return $false }

    foreach ($p in $candidates) {
        try {
            $raw = Get-Content $p -Raw -Encoding UTF8
            $j = $raw | ConvertFrom-Json

            # Try common keys; fallback: if as_of_date == today AND ok-ish flag exists
            $asOf = $null
            foreach ($k in @("as_of_date","date","trading_day")) {
                if ($j.PSObject.Properties.Name -contains $k) {
                    $asOf = [string]$j.$k
                    if ($asOf.Length -ge 10) { $asOf = $asOf.Substring(0,10) }
                    break
                }
            }

            $ok = $false
            foreach ($k in @("phase4_ok_today","ok_today","passed","phase4_passed","phase4_ok")) {
                if ($j.PSObject.Properties.Name -contains $k) {
                    $ok = _ToBool $j.$k
                    break
                }
            }

            if ($asOf -eq $today -and $ok) { return $true }
        } catch {
            # ignore and try next
        }
    }

    return $false
}

function Get-GateScoreQualityForSymbol {
    param(
        [Parameter(Mandatory = $true)][string]$CsvPath,
        [Parameter(Mandatory = $true)][string]$Symbol,
        [int]$MinSignals = 3,
        [int]$MinPnlSamples = 1,
        [double]$MinScore = 0.0
    )

    $out = [ordered]@{
        fresh_today = $false
        samples_ok  = $false
        score_ok    = $false
        score_value = 0.0
        count_signals = 0
        pnl_samples = 0
    }

    if (-not (Test-Path $CsvPath)) { return $out }

    $rows = @(Import-Csv -Path $CsvPath)
    if (@($1).Count -eq 0) { return $out }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $target = $null

    foreach ($row in $rows) {
        $props = $row.PSObject.Properties
        $sym = $props["symbol"]
        if ($sym -eq $null -or -not $sym.Value) { continue }
        if ([string]$sym.Value -ne $Symbol) { continue }

        $asOf = $props["as_of_date"]
        if ($asOf -eq $null -or -not $asOf.Value) { continue }
        $d = [string]$asOf.Value
        if ($d.Length -ge 10) { $d = $d.Substring(0,10) }
        if ($d -ne $today) { continue }

        $target = $row
        break
    }

    if ($null -eq $target) { return $out }

    $out.fresh_today = $true

    $cs = 0
    $ps = 0
    $sv = 0.0

    $p = $target.PSObject.Properties

    if ($p["count_signals"] -and $p["count_signals"].Value) {
        [void][int]::TryParse([string]$p["count_signals"].Value, [ref]$cs)
    }
    if ($p["pnl_samples"] -and $p["pnl_samples"].Value) {
        [void][int]::TryParse([string]$p["pnl_samples"].Value, [ref]$ps)
    }

    foreach ($k in @("gatescore","gate_score","score","value")) {
        if ($p[$k] -and $p[$k].Value) {
            [void][double]::TryParse([string]$p[$k].Value, [ref]$sv)
            break
        }
    }

    @($1).Count_signals = $cs
    $out.pnl_samples   = $ps
    $out.score_value   = $sv

    $out.samples_ok = ($cs -ge $MinSignals -and $ps -ge $MinPnlSamples)
    $out.score_ok   = ($sv -ge $MinScore)

    return $out
}

# === Inputs ===
$phase23Csv = Join-Path $logsDir "phase23_health_daily.csv"
$evCsv      = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"
$gsCsv      = Join-Path $logsDir "gatescore_daily_summary.csv"

# === Core daily requirements ===
$phase23Row = Get-TodayRow -CsvPath $phase23Csv
$phase23Ok  = $false
if ($phase23Row -ne $null) {
    $prop = $phase23Row.PSObject.Properties["phase23_health_ok_today"]
    $phase23Ok = if ($prop -and $prop.Value) { _ToBool $prop.Value } else { $true }
}

$evRow    = Get-TodayRow -CsvPath $evCsv
$evHardOk = $false
if ($evRow -ne $null) {
    $prop = $evRow.PSObject.Properties["ev_hard_daily_ok_today"]
    $evHardOk = if ($prop -and $prop.Value) { _ToBool $prop.Value } else { $true }
}

$phase4Ok = Get-Phase4OkToday -LogsDir $logsDir

# === GateScore quality (tunable thresholds) ===
# defaults: minimal, but still explicit
$minSignals = 3
$minPnlSamples = 1
$minScore = 0.0

$gsNvda = Get-GateScoreQualityForSymbol -CsvPath $gsCsv -Symbol "NVDA" -MinSignals $minSignals -MinPnlSamples $minPnlSamples -MinScore $minScore
$gsSpy  = Get-GateScoreQualityForSymbol -CsvPath $gsCsv -Symbol "SPY"  -MinSignals $minSignals -MinPnlSamples $minPnlSamples -MinScore $minScore
$gsQqq  = Get-GateScoreQualityForSymbol -CsvPath $gsCsv -Symbol "QQQ"  -MinSignals $minSignals -MinPnlSamples $minPnlSamples -MinScore $minScore

# For backward compatibility, keep these as NVDA’s
$gsFresh = [bool]$gsNvda.fresh_today
$gsSamplesOk = [bool]$gsNvda.samples_ok
$gsValue = [double]$gsNvda.score_value

# === Per-symbol readiness (institutional: include Phase4) ===
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and [bool]$gsNvda.fresh_today -and [bool]$gsNvda.samples_ok -and [bool]$gsNvda.score_ok
$spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and [bool]$gsSpy.fresh_today  -and [bool]$gsSpy.samples_ok  -and [bool]$gsSpy.score_ok
$qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and [bool]$gsQqq.fresh_today  -and [bool]$gsQqq.samples_ok  -and [bool]$gsQqq.score_ok

# === reasons_not_ready ===
$reasons = New-Object System.Collections.Generic.List[string]
if (-not $phase23Ok) { $reasons.Add("phase23_health_ok_today=false") }
if (-not $evHardOk)  { $reasons.Add("ev_hard_daily_ok_today=false") }
if (-not $phase4Ok)  { $reasons.Add("phase4_ok_today=false") }

# NVDA-focused diagnostic fields (compat with Python helper)
if (-not $gsFresh) { $reasons.Add("gatescore_fresh_today=false") }
if (-not $gsSamplesOk) { $reasons.Add("gatescore_samples_not_ok") }
if (-not [bool]$gsNvda.score_ok) { $reasons.Add("gatescore_below_threshold") }

# === Build JSON payload ===
$payload = [ordered]@{
    ts_utc                   = $tsUtc
    as_of_date               = $today

    # Core daily requirements
    phase23_health_ok_today  = $phase23Ok
    ev_hard_daily_ok_today   = $evHardOk
    phase4_ok_today          = $phase4Ok

    # GateScore (NVDA-compatible legacy fields)
    gatescore_fresh_today    = $gsFresh
    gatescore_samples_ok     = $gsSamplesOk
    gatescore_value          = $gsValue
    gatescore_min_required   = $minScore
    gatescore_samples        = [int]@($1).Count_signals
    gatescore_min_samples    = [int]$minSignals

    # Per-symbol readiness
    nvda_blockg_ready        = $nvdaReady
    spy_blockg_ready         = $spyReady
    qqq_blockg_ready         = $qqqReady

    reasons_not_ready        = @($reasons)
}

$payloadJson = $payload | ConvertTo-Json -Depth 6

Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan

# UTF-8 no BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize