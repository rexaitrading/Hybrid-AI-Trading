param(
    [Parameter(Mandatory = $true)][string]$CsvPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path $CsvPath)) {
    throw "CSV not found: $CsvPath"
}

Write-Host "[HybridAITrading] Risk calibration from CSV..." -ForegroundColor Cyan
Write-Host "  CSV = $CsvPath" -ForegroundColor DarkGray

$rows = Import-Csv -Path $CsvPath
if (-not $rows) {
    throw "CSV has no rows"
}

# Try to detect column name for returns
$retCol = @("R","r","return","Return","ret") | Where-Object { $_ -in $rows[0].PsObject.Properties.Name } | Select-Object -First 1
if (-not $retCol) {
    throw "Could not find return column (R/return/ret) in CSV header"
}

$vals = @()
foreach ($r in $rows) {
    $v = $null
    if ([double]::TryParse($r.$retCol, [ref]$v)) {
        $vals += [double]$v
    }
}

if (-not $vals) {
    throw "No numeric values found in column $retCol"
}

$n      = $vals.Count
$wins   = $vals | Where-Object { $_ -gt 0 }
$losses = $vals | Where-Object { $_ -lt 0 }

$winRate = if ($n -gt 0) { [math]::Round(($wins.Count / $n) * 100, 2) } else { 0 }
$avgR    = [math]::Round(($vals | Measure-Object -Average).Average, 4)
$stdR    = [math]::Round(($vals | Measure-Object -Property { $_ } -StandardDeviation).StandardDeviation, 4)

Write-Host "Samples:  $n" -ForegroundColor Green
Write-Host "WinRate:  $winRate % " -ForegroundColor Green
Write-Host "Mean R:   $avgR" -ForegroundColor Green
Write-Host "Std R:    $stdR" -ForegroundColor Green

if ($wins.Count -gt 0 -and $losses.Count -gt 0) {
    $avgWin = ($wins | Measure-Object -Average).Average
    $avgLoss = ($losses | Measure-Object -Average).Average
    $b = 0.0
    if ($avgLoss -ne 0) {
        $b = [math]::Abs($avgWin / $avgLoss)
    }
    $p = $wins.Count / $n
    if ($b -gt 0) {
        $kellyF = $p - ((1 - $p) / $b)
        $kellyF = [math]::Max(0.0, [math]::Min(1.0, $kellyF))
        $kellyF = [math]::Round($kellyF, 4)
        Write-Host ("Raw Kelly fraction (theoretical): {0}" -f $kellyF) -ForegroundColor Yellow
        Write-Host ("Suggested Kelly clamp for config.risk.kelly.fraction: {0}" -f ([math]::Round($kellyF / 4,4))) -ForegroundColor Yellow
    }
}

Write-Host "[HybridAITrading] Use these stats to tune risk_manager / kelly_sizer / sharpe/sortino guards." -ForegroundColor DarkGray
