function Get-BgTodayString {
    (Get-Date -Format 'yyyy-MM-dd')
}

function Get-BgLogsPath {
    $toolsDir = Split-Path -Parent $PSCommandPath
    $repoRoot = Split-Path -Parent $toolsDir
    Join-Path $repoRoot 'logs'
}

function Get-Phase23HealthOkToday {
    $logsPath = Get-BgLogsPath
    $path = Join-Path $logsPath 'phase23_health_daily.csv'
    if (-not (Test-Path $path)) { return $false }

    $rows = Import-Csv $path
    if (-not $rows) { return $false }

    $last = $rows[-1]
    $today = Get-BgTodayString

    $dateProp = @('as_of_date','date','day_id') | Where-Object {
        $last.PSObject.Properties.Name -contains $_
    } | Select-Object -First 1

    if (-not $dateProp) { return $false }

    $rowDate = ($last.$dateProp).Split(' ')[0]
    if ($rowDate -ne $today) { return $false }

    # Optional stricter flag if present
    if ($last.PSObject.Properties.Name -contains 'phase23_ok') {
        $val = [string]$last.phase23_ok
        if ($val -eq '') { return $false }
        return ($val -eq 'True' -or $val -eq 'true' -or $val -eq '1')
    }

    return $true
}

function Get-EvHardDailyOkToday {
    $logsPath = Get-BgLogsPath
    $path = Join-Path $logsPath 'phase5_ev_hard_veto_daily.csv'
    if (-not (Test-Path $path)) { return $false }

    $rows = Import-Csv $path
    if (-not $rows) { return $false }

    $today = Get-BgTodayString

    foreach ($row in $rows) {
        $dateProp = @('date','as_of_date','day_id') | Where-Object {
            $row.PSObject.Properties.Name -contains $_
        } | Select-Object -First 1

        if (-not $dateProp) { continue }

        $rowDate = ($row.$dateProp).Split(' ')[0]
        if ($rowDate -eq $today) {
            return $true
        }
    }

    return $false
}

function Get-GateScoreFreshToday {
    $logsPath = Get-BgLogsPath
    $path = Join-Path $logsPath 'gatescore_daily_summary.csv'
    if (-not (Test-Path $path)) { return $false }

    $rows = Import-Csv $path
    if (-not $rows) { return $false }

    $today = Get-BgTodayString

    # Look for NVDA row for today with basic sample counts
    $candidate = $rows | Where-Object {
        ($_.symbol -eq 'NVDA') -and
        ($_.as_of_date -like "$today*")
    } | Select-Object -First 1

    if (-not $candidate) { return $false }

    $countSignals = 0
    $pnlSamples = 0
    [void][int]::TryParse([string]$candidate.count_signals, [ref]$countSignals)
    [void][int]::TryParse([string]$candidate.pnl_samples, [ref]$pnlSamples)

    if ($countSignals -lt 1) { return $false }
    if ($pnlSamples -lt 1) { return $false }

    return $true
}

function Get-NvdaBlockGReadyToday {
    $p23 = Get-Phase23HealthOkToday
    $evHard = Get-EvHardDailyOkToday
    $gsFresh = Get-GateScoreFreshToday

    return ($p23 -and $evHard -and $gsFresh)
}
[CmdletBinding()]
param()

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

function Get-TodayRow {
    param(
        [Parameter(Mandatory = $true)][string]$CsvPath
    )

    if (-not (Test-Path $CsvPath)) {
        return $null
    }

    $rows = Import-Csv -Path $CsvPath
    $rowArray = @($rows)
    if ($rowArray.Count -eq 0) {
        return $null
    }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $candidateRows = @()

    foreach ($row in $rowArray) {
        $props = $row.PSObject.Properties
        $dateVal = $null

        foreach ($name in @("as_of_date","date","trading_day")) {
            $prop = $props[$name]
            if ($prop -ne $null -and $prop.Value -ne $null -and $prop.Value -ne "") {
                $dateVal = [string]$prop.Value
                break
            }
        }

        if ($dateVal) {
            if ($dateVal.Length -ge 10) {
                $dateVal = $dateVal.Substring(0,10)
            }

            if ($dateVal -eq $today) {
                $candidateRows += $row
            }
        }
    }

    if ($candidateRows.Count -gt 0) {
        return $candidateRows[-1]
    }

    return $null
}

function Get-GateScoreFreshForSymbol {
    param(
        [Parameter(Mandatory = $true)][string]$CsvPath,
        [Parameter(Mandatory = $true)][string]$Symbol
    )

    if (-not (Test-Path $CsvPath)) {
        return $false
    }

    $rows = Import-Csv -Path $CsvPath
    $rowArray = @($rows)
    if ($rowArray.Count -eq 0) {
        return $false
    }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $targetRow = $null

    foreach ($row in $rowArray) {
        $props = $row.PSObject.Properties

        $symProp = $props["symbol"]
        $symVal  = $null
        if ($symProp -ne $null -and $symProp.Value -ne $null) {
            $symVal = [string]$symProp.Value
        }

        if ($symVal -ne $Symbol) {
            continue
        }

        $asOf = $null
        $propAsOf = $props["as_of_date"]
        if ($propAsOf -ne $null -and $propAsOf.Value -ne $null -and $propAsOf.Value -ne "") {
            $asOf = [string]$propAsOf.Value
            if ($asOf.Length -ge 10) {
                $asOf = $asOf.Substring(0,10)
            }
        }

        if ($asOf -eq $today) {
            $targetRow = $row
            break
        }
    }

    if ($targetRow -eq $null) {
        return $false
    }

    $props = $targetRow.PSObject.Properties
    $countSignals = 0
    $pnlSamples   = 0

    $csProp = $props["count_signals"]
    if ($csProp -ne $null -and $csProp.Value -ne $null -and $csProp.Value -ne "") {
        [void][int]::TryParse([string]$csProp.Value, [ref]$countSignals)
    }

    $psProp = $props["pnl_samples"]
    if ($psProp -ne $null -and $psProp.Value -ne $null -and $psProp.Value -ne "") {
        [void][int]::TryParse([string]$psProp.Value, [ref]$pnlSamples)
    }

    # Simple freshness / sample-count rule (tunable later)
    if ($countSignals -ge 3 -and $pnlSamples -ge 1) {
        return $true
    }

    return $false
}

# 1) Phase-23 health -> phase23_health_ok_today
$phase23Csv = Join-Path $logsDir "phase23_health_daily.csv"
$phase23Row = Get-TodayRow -CsvPath $phase23Csv
$phase23Ok  = $false

if ($phase23Row -ne $null) {
    # If the row has an explicit flag, respect it; otherwise presence => ok
    $prop = $phase23Row.PSObject.Properties["phase23_health_ok_today"]
    if ($prop -ne $null -and $prop.Value -ne $null -and $prop.Value -ne "") {
        $val = [string]$prop.Value
        $phase23Ok = $val.Trim().ToLowerInvariant() -in @("1","true","yes","y")
    } else {
        $phase23Ok = $true
    }
}

# 2) EV-hard veto daily -> ev_hard_daily_ok_today
$evCsv     = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"
$evRow     = Get-TodayRow -CsvPath $evCsv
$evHardOk  = $false

if ($evRow -ne $null) {
    # If the row has a boolean-like "ev_hard_daily_ok_today", use it; else presence => ok
    $prop = $evRow.PSObject.Properties["ev_hard_daily_ok_today"]
    if ($prop -ne $null -and $prop.Value -ne $null -and $prop.Value -ne "") {
        $val = [string]$prop.Value
        $evHardOk = $val.Trim().ToLowerInvariant() -in @("1","true","yes","y")
    } else {
        $evHardOk = $true
    }
}

# 3) GateScore daily summary -> gatescore_fresh_today (NVDA)
$gsCsv = Join-Path $logsDir "gatescore_daily_summary.csv"

$gsFreshNvda = Get-GateScoreFreshForSymbol -CsvPath $gsCsv -Symbol "NVDA"
$gsFreshSpy  = Get-GateScoreFreshForSymbol -CsvPath $gsCsv -Symbol "SPY"
$gsFreshQqq  = Get-GateScoreFreshForSymbol -CsvPath $gsCsv -Symbol "QQQ"

# For backward compatibility, keep gatescore_fresh_today as NVDA's freshness
$gsFresh = $gsFreshNvda

# 4) Per-symbol readiness (require EV-band samples as well)
$nvdaEvOk = Get-EvBandSamplesOkTodayForSymbol -Symbol "NVDA" -MinTrades 3
$spyEvOk  = Get-EvBandSamplesOkTodayForSymbol -Symbol "SPY"  -MinTrades 3
$qqqEvOk  = Get-EvBandSamplesOkTodayForSymbol -Symbol "QQQ"  -MinTrades 3

$nvdaReady = $phase23Ok -and $evHardOk -and $gsFreshNvda -and $nvdaEvOk
$spyReady  = $phase23Ok -and $evHardOk -and $gsFreshSpy  -and $spyEvOk
$qqqReady  = $phase23Ok -and $evHardOk -and $gsFreshQqq -and $qqqEvOk

# 5) Build JSON payload
$payload = [ordered]@{
    ts_utc                   = $tsUtc
    as_of_date               = $today
    phase23_health_ok_today  = $phase23Ok
    ev_hard_daily_ok_today   = $evHardOk
    gatescore_fresh_today    = $gsFresh
    nvda_blockg_ready        = $nvdaReady
    spy_blockg_ready         = $spyReady
    qqq_blockg_ready         = $qqqReady
}

$payloadJson = $payload | ConvertTo-Json -Depth 4

Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan
$payloadJson | Set-Content -Path $statusPath -Encoding UTF8

Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize




