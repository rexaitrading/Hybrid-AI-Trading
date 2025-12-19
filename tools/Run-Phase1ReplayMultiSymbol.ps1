[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$env:PYTHONPATH = Join-Path $repoRoot "src"
$python = ".\.venv\Scripts\python.exe"

function Get-JsonProp {
    param(
        [Parameter(Mandatory = $true)][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )
    if ($null -eq $Object) { return $null }
    $prop = $Object.PSObject.Properties[$Name]
    if ($prop) { return $prop.Value }
    return $null
}

Write-Host "[PHASE1] Multi-symbol replay stats" -ForegroundColor Cyan
Write-Host "RepoRoot  = $repoRoot" -ForegroundColor DarkGray
Write-Host "PythonExe = $python"   -ForegroundColor DarkGray

$symbols = @(
    @{ Name = "NVDA"; Csv = "data\nvda_1min_sample.csv" },
    @{ Name = "SPY";  Csv = "data\spy_1min_sample.csv"  },
    @{ Name = "QQQ";  Csv = "data\qqq_1min_sample.csv"  }
)

foreach ($s in $symbols) {
    $sym  = $s.Name
    $csv  = Join-Path $repoRoot $s.Csv

    if (-not (Test-Path $csv)) {
        Write-Host "[PHASE1] SKIP $sym – sample CSV not found at $csv" -ForegroundColor Yellow
        continue
    }

    $session = "${sym}_PHASE1_MULTI"
    $summary = Join-Path $repoRoot ("replay_summary_{0}_{1}.json" -f $sym, $session)

    if (Test-Path $summary) {
        Remove-Item $summary -Force
    }

    Write-Host "`n[PHASE1] Running replay for $sym" -ForegroundColor Cyan

    $script = Join-Path $toolsDir "run_bar_replay_to_json.py"
    if (-not (Test-Path $script)) {
        Write-Host "[PHASE1] ERROR: run_bar_replay_to_json.py not found at $script" -ForegroundColor Red
        break
    }

    $args = @(
        $script,
        "--symbol", $sym,
        "--csv", $csv,
        "--session", $session
    )

    & $python @args

    if (-not (Test-Path $summary)) {
        Write-Host "[PHASE1] WARN: No summary JSON written for $sym at $summary" -ForegroundColor Yellow
        continue
    }

    $json = Get-Content $summary -Raw | ConvertFrom-Json

    $edge    = Get-JsonProp $json 'mean_edge_ratio'
    $ev      = Get-JsonProp $json 'mean_ev'
    $maxDD   = Get-JsonProp $json 'max_drawdown_pct'
    $winRate = Get-JsonProp $json 'win_rate'
    $avgWin  = Get-JsonProp $json 'avg_win'
    $avgLoss = Get-JsonProp $json 'avg_loss'

    Write-Host ("[PHASE1] Stats for {0}:" -f $sym) -ForegroundColor Green
    Write-Host ("  mean_edge_ratio : {0}" -f $edge)
    Write-Host ("  mean_ev         : {0}" -f $ev)
    Write-Host ("  max_drawdown_pct: {0}" -f $maxDD)
    Write-Host ("  win_rate        : {0}" -f $winRate)
    Write-Host ("  avg_win         : {0}" -f $avgWin)
    Write-Host ("  avg_loss        : {0}" -f $avgLoss)
}
