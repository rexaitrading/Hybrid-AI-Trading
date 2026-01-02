[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL",
    [switch]$StrictToday
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

$today = (Get-Date).ToString("yyyy-MM-dd")
$outPath = Join-Path $logsDir "gatescore_pnl_summary.csv"

function _SliceDate([string]$d) {
    if (-not $d) { return "" }
    if ($d.Length -ge 10) { return $d.Substring(0,10) }
    return $d
}

function _TryDouble([object]$v) {
    $x = 0.0
    if ($null -eq $v) { return $null }
    if ([double]::TryParse([string]$v, [ref]$x)) { return $x }
    return $null
}

function _TryString([object]$v) {
    if ($null -eq $v) { return "" }
    return [string]$v
}

function Read-Jsonl([string]$Path) {
    if (-not (Test-Path $Path)) { return @() }
    $lines = Get-Content $Path -Encoding UTF8
    $out = @()
    foreach ($ln in $lines) {
        $s = $ln.Trim()
        if (-not $s) { continue }
        try { $out += ($s | ConvertFrom-Json) } catch { }
    }
    return $out
}

function Get-EventDate($e) {
    $props = $e.PSObject.Properties.Name

    foreach ($k in @("as_of_date","date","trading_day")) {
        if ($props -contains $k) {
            $v = _TryString ($e.$k)
            if ($v) { return _SliceDate $v }
        }
    }

    foreach ($k in @("ts_utc","ts","timestamp")) {
        if ($props -contains $k) {
            $t = _TryString ($e.$k)
            if ($t.Length -ge 10) { return $t.Substring(0,10) }
        }
    }

    return ""
}

function Get-Num($e, [string[]]$keys) {
    $props = $e.PSObject.Properties.Name
    foreach ($k in $keys) {
        if ($props -contains $k) {
            $v = _TryDouble ($e.$k)
            if ($null -ne $v) { return $v }
        }
    }
    return $null
}

function Mean($arr) {
    if ($arr.Count -eq 0) { return 0.0 }
    $sum = 0.0
    foreach ($v in $arr) { $sum += [double]$v }
    return $sum / [double]$arr.Count
}
function Get-EventPnlSamples($events) {
    $sum = 0
    foreach ($e in $events) {
        try {
            $v = $e.pnl_samples
            if ($null -eq $v) { $v = $e.pnlSamples }
            if ($null -eq $v) { $v = $e.sample_count }
            if ($null -eq $v) { $v = $e.samples }
            $n = 0
            if ([int]::TryParse([string]$v, [ref]$n)) { $sum += $n }
            elseif ([double]::TryParse([string]$v, [ref]([double]$d = 0.0))) { $sum += [int]$d }
        } catch { }
    }
    return [int]$sum
}

$eventFiles = @(
    @{ sym="NVDA"; path=(Join-Path $logsDir "nvda_gatescore_events.jsonl") },
    @{ sym="SPY";  path=(Join-Path $logsDir "spy_gatescore_events.jsonl")  },
    @{ sym="QQQ";  path=(Join-Path $logsDir "qqq_gatescore_events.jsonl")  }
)

$wanted = @()
switch ($Symbol.ToUpperInvariant()) {
    "NVDA" { $wanted = @("NVDA") }
    "SPY"  { $wanted = @("SPY") }
    "QQQ"  { $wanted = @("QQQ") }
    "ALL"  { $wanted = @("NVDA","SPY","QQQ") }
}

$rowsOut = New-Object System.Collections.Generic.List[object]

foreach ($it in $eventFiles) {
    $sym = [string]$it.sym
    if ($wanted -notcontains $sym) { continue }
    $path = [string]$it.path
    if (-not (Test-Path $path)) { continue }

    $events = Read-Jsonl $path
    if ($events.Count -eq 0) { continue }

    
    # Determine latest event date in this file (fail-closed if none)
    $latest = ""
    foreach ($e in $events) {
        $ed = Get-EventDate $e
        if ($ed) {
            if ($latest -eq "" -or $ed -gt $latest) { $latest = $ed }
        }
    }
    if ($latest -eq "") { continue }

    $targetDate = if($StrictToday){ $today } else { $latest }

    if (-not $StrictToday -and $targetDate -ne $today) {
        Write-Host ("GateScore PnL summary: WARN {0} events are stale (latest={1}, today={2})" -f $sym,$targetDate,$today) -ForegroundColor Yellow
    }
    if ($StrictToday -and $latest -ne $today) {
        Write-Host ("GateScore PnL summary: STRICT-TODAY no events for today={0} (latest={1})" -f $today,$latest) -ForegroundColor Yellow
    }

    $todayEvents = @()
    foreach ($e in $events) {
        if ((Get-EventDate $e) -eq $targetDate) { $todayEvents += $e }
    }
    if ($todayEvents.Count -eq 0) { continue }

    # Drop ineligible events (fail-closed against zero-metric pollution)
    $todayEvents = @($todayEvents | Where-Object {
        -not ($_.PSObject.Properties.Name -contains "eligible") -or [bool]$_.eligible
    })
    if ($todayEvents.Count -eq 0) { continue }


    $edgeVals = @()
    $microVals = @()
    $pnlVals = @()

    foreach ($e in $todayEvents) {
        $edge  = Get-Num $e @("edge_ratio","mean_edge_ratio","edge","ev_edge_ratio")
        $micro = Get-Num $e @("micro_score","mean_micro_score","micro","micro_score_today")
        $pnl   = Get-Num $e @("realized_pnl","pnl","net_pnl","pnl_usd")

        if ($null -ne $edge)  { $edgeVals += $edge }
        if ($null -ne $micro) { $microVals += $micro }
        if ($null -ne $pnl)   { $pnlVals += $pnl }
    }
    # pnl_samples semantics:
    # 1) Prefer numeric pnl samples (realized_pnl count)
    # 2) Else fallback to declared per-event pnl_samples
    # 3) Else fallback to count_signals (wiring-safe)
    $rowPnlSamples = [int]$pnlVals.Count
    if ($rowPnlSamples -le 0) {
        $declSum = Get-EventPnlSamples $todayEvents
        if ($declSum -gt 0) { $rowPnlSamples = $declSum }
    }
    if ($rowPnlSamples -le 0) { $rowPnlSamples = [int]$todayEvents.Count }

    $row = [pscustomobject]@{
        as_of_date       = $targetDate
        symbol           = $sym
        count_signals    = [int]$todayEvents.Count
        pnl_samples      = [int]$rowPnlSamples
        mean_edge_ratio  = [double](Mean $edgeVals)
        mean_micro_score = [double](Mean $microVals)
        mean_pnl         = [double](Mean $pnlVals)
    }

    $rowsOut.Add($row) | Out-Null
}

if ($rowsOut.Count -eq 0) {
    Write-Error "GateScore PnL summary: no usable 'today' events found. Refusing to write $outPath (fail-closed)."
    exit 2
}

$allZero = $true
foreach ($r in $rowsOut) {
    if ($r.count_signals -gt 0 -or $r.pnl_samples -gt 0 -or $r.mean_edge_ratio -ne 0.0 -or $r.mean_micro_score -ne 0.0 -or $r.mean_pnl -ne 0.0) {
        $allZero = $false; break
    }
}
if ($allZero) {
    Write-Error "GateScore PnL summary: computed rows are all zeros. Refusing to write $outPath (fail-closed)."
    exit 3
}

Write-Host "GateScore PnL summary: writing $outPath" -ForegroundColor Cyan
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$csv = $rowsOut | Sort-Object symbol | ConvertTo-Csv -NoTypeInformation
[System.IO.File]::WriteAllLines($outPath, $csv, $utf8NoBom)

Write-Host "GateScore PnL summary: sample rows:" -ForegroundColor Yellow
$rowsOut | Format-Table -AutoSize

exit 0
