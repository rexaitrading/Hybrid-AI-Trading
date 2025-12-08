param(
    [int]$Days = 4,
    [double]$RiskPerTrade = 0.02
)

$ErrorActionPreference = "Stop"

# This script lives in repoRoot\tools; repoRoot is parent of $PSScriptRoot
$scriptDir = $PSScriptRoot
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location $repoRoot

Write-Host "`n[EV-SUITE] Phase-5 Daily EV Suite (last $Days days)" -ForegroundColor Cyan

# 1) Soft/Hard EV summary
if (Test-Path ".\tools\Build-EvHardVetoSummary.ps1") {
    .\tools\Build-EvHardVetoSummary.ps1
} else {
    Write-Host "[EV-SUITE] WARN: Build-EvHardVetoSummary.ps1 not found at .\tools\Build-EvHardVetoSummary.ps1." -ForegroundColor Yellow
}

# 2) R-multiple stats via Python helper
$python    = ".\.venv\Scripts\python.exe"
$hasPython = Test-Path $python
$hasRStats = Test-Path ".\tools\compute_r_stats_from_jsonl.py"

if ($hasPython -and $hasRStats) {
    Write-Host "`n[EV-SUITE] R-multiple stats (NVDA/SPY/QQQ)" -ForegroundColor Cyan
    & $python .\tools\compute_r_stats_from_jsonl.py --days $Days --risk-per-trade $RiskPerTrade
} else {
    Write-Host "[EV-SUITE] WARN: Python or compute_r_stats_from_jsonl.py missing." -ForegroundColor Yellow
}

# 3) ROI vs notional
Write-Host "`n[EV-SUITE] ROI vs notional (NVDA/SPY/QQQ, last $Days days)" -ForegroundColor Cyan

$cutoff = (Get-Date).AddDays(-$Days)

function Read-JsonlSafe {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path $Path)) { return @() }
    $items = @()
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        try { $items += ($line | ConvertFrom-Json) } catch { }
    }
    return $items
}

$targets = @(
    @{ Symbol = 'NVDA'; Path = 'logs\nvda_phase5_paperlive_results.jsonl' },
    @{ Symbol = 'SPY' ; Path = 'logs\spy_phase5_paperlive_results.jsonl'  },
    @{ Symbol = 'QQQ' ; Path = 'logs\qqq_phase5_paperlive_results.jsonl'  }
)

$totalNotional = 0.0
$totalPnl      = 0.0
$totalTrades   = 0

foreach ($t in $targets) {
    $sym  = $t.Symbol
    $path = Join-Path (Get-Location) $t.Path
    $rows = Read-JsonlSafe -Path $path
    if (-not $rows) { continue }

    foreach ($r in $rows) {
        $tsStr = $null
        if ($r.PSObject.Properties.Name -contains 'ts')       { $tsStr = $r.ts }
        elseif ($r.PSObject.Properties.Name -contains 'ts_trade') { $tsStr = $r.ts_trade }
        if (-not $tsStr) { continue }

        $dt = $null
        try { $dt = [datetime]$tsStr } catch { continue }
        if ($dt -lt $cutoff) { continue }

        $regime = $null
        if ($r.PSObject.Properties.Name -contains 'regime') {
            $regime = $r.regime
        } elseif ($r.PSObject.Properties.Name -contains 'phase5_result') {
            $regime = $r.phase5_result.regime
        }
        if (-not $regime -or ($regime -notlike '*_LIVE')) { continue }

        $rpnl = 0.0
        if ($r.PSObject.Properties.Name -contains 'realized_pnl_paper') {
            $rpnl = [double]($r.realized_pnl_paper -as [double])
        } elseif ($r.PSObject.Properties.Name -contains 'realized_pnl') {
            $rpnl = [double]($r.realized_pnl -as [double])
        }

        $notional = 0.0
        if ($r.PSObject.Properties.Name -contains 'order_result') {
            $ord = $r.order_result
            if ($ord -and $ord.notional -ne $null) {
                $notional = [double]($ord.notional -as [double])
            }
        }
        if ($notional -eq 0.0) {
            $price = 0.0
            $qty   = 0.0
            if ($r.PSObject.Properties.Name -contains 'price') { $price = [double]($r.price -as [double]) }
            if ($r.PSObject.Properties.Name -contains 'qty')   { $qty   = [double]($r.qty   -as [double]) }
            $notional = [math]::Abs($price * $qty)
        }

        $totalTrades   += 1
        $totalNotional += $notional
        $totalPnl      += $rpnl
    }
}

if ($totalTrades -eq 0 -or $totalNotional -le 0) {
    Write-Host "  [INFO] No LIVE trades for ROI-notional calc." -ForegroundColor Yellow
} else {
    $roiFraction = $totalPnl / $totalNotional
    $roiPercent  = $roiFraction * 100.0

    Write-Host ("  Trades        : {0}"    -f $totalTrades)
    Write-Host ("  Total notional: {0:N4}" -f $totalNotional)
    Write-Host ("  Total PnL     : {0:N4}" -f $totalPnl)
    Write-Host ("  ROI vs notional: {0:N4}% " -f $roiPercent) -ForegroundColor Green
}