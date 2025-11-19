<#
.SYNOPSIS
    Diff Phase5 risk sketches between two ORB/VWAP threshold JSON configs.

.DESCRIPTION
    Loads phase5_risk_sketch from two JSON files (e.g. AAPL vs NVDA) and
    prints a side-by-side comparison of key fields.

.PARAMETER Left
    Path to first thresholds JSON (e.g. config/orb_vwap_aapl_thresholds.json).

.PARAMETER Right
    Path to second thresholds JSON (e.g. config/orb_vwap_nvda_thresholds.json).
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Left  = "config/orb_vwap_aapl_thresholds.json",

    [Parameter(Mandatory = $false)]
    [string]$Right = "config/orb_vwap_nvda_thresholds.json"
)

$ErrorActionPreference = "Stop"

function Load-Phase5Sketch {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        Write-Host "[PHASE5-RISK-DIFF] MISSING config: $Path" -ForegroundColor Red
        return $null
    }

    $raw = Get-Content -Path $Path -Raw
    if (-not $raw) {
        Write-Host "[PHASE5-RISK-DIFF] EMPTY config: $Path" -ForegroundColor Red
        return $null
    }

    try {
        $json = $raw | ConvertFrom-Json
    } catch {
        $errText = $_.ToString()
        Write-Host ("[PHASE5-RISK-DIFF] JSON parse error in {0}: {1}" -f $Path, $errText) -ForegroundColor Red
        return $null
    }

    if (-not $json.PSObject.Properties.Match("phase5_risk_sketch")) {
        Write-Host "[PHASE5-RISK-DIFF] No phase5_risk_sketch in $Path (OK if Phase5 disabled)." -ForegroundColor Yellow
        return $null
    }

    $symbol   = $json.symbol
    $strategy = $json.strategy

    $sketch = $json.phase5_risk_sketch
    if ($null -eq $sketch) {
        Write-Host "[PHASE5-RISK-DIFF] phase5_risk_sketch is null in $Path [$symbol/$strategy]." -ForegroundColor Yellow
        return $null
    }

    return [PSCustomObject]@{
        Path                      = $Path
        Symbol                    = $symbol
        Strategy                  = $strategy
        NoAveragingDown           = $sketch.no_averaging_down
        MinAddCushionBp           = $sketch.min_add_cushion_bp
        DailyLossCapPct           = $sketch.daily_loss_cap_pct
        DailyLossCapNotional      = $sketch.daily_loss_cap_notional
        SymbolDailyLossCapBp      = $sketch.symbol_daily_loss_cap_bp
        SymbolMaxTradesPerDay     = $sketch.symbol_max_trades_per_day
        MaxOpenPositions          = $sketch.max_open_positions
    }
}

Write-Host "[PHASE5-RISK-DIFF] Left:  $Left" -ForegroundColor Cyan
Write-Host "[PHASE5-RISK-DIFF] Right: $Right" -ForegroundColor Cyan

$leftSketch  = Load-Phase5Sketch -Path $Left
$rightSketch = Load-Phase5Sketch -Path $Right

if (-not $leftSketch -or -not $rightSketch) {
    Write-Host "[PHASE5-RISK-DIFF] One or both configs missing sketches; nothing to diff." -ForegroundColor Yellow
    return
}

Write-Host ""
Write-Host "[PHASE5-RISK-DIFF] Comparing Phase5 risk sketches:" -ForegroundColor Cyan
Write-Host "  Left : $($leftSketch.Symbol)/$($leftSketch.Strategy) ($($leftSketch.Path))"
Write-Host "  Right: $($rightSketch.Symbol)/$($rightSketch.Strategy) ($($rightSketch.Path))"
Write-Host ""

$fields = @(
    "NoAveragingDown",
    "MinAddCushionBp",
    "DailyLossCapPct",
    "DailyLossCapNotional",
    "SymbolDailyLossCapBp",
    "SymbolMaxTradesPerDay",
    "MaxOpenPositions"
)

$results = @()

foreach ($field in $fields) {
    $leftVal  = $leftSketch.$field
    $rightVal = $rightSketch.$field

    $isEqual = $false
    if ($null -eq $leftVal -and $null -eq $rightVal) {
        $isEqual = $true
    } elseif ($leftVal -eq $rightVal) {
        $isEqual = $true
    }

    $results += [PSCustomObject]@{
        Field      = $field
        LeftValue  = $leftVal
        RightValue = $rightVal
        Match      = if ($isEqual) { "OK" } else { "DIFF" }
    }
}

$results | Format-Table -AutoSize