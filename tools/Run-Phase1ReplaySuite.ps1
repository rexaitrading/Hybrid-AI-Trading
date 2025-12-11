[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Split-Path -Parent $scriptDir

if (-not (Test-Path $repoRoot)) {
    throw "[PHASE1] Repo root not found from script path: $repoRoot"
}

Push-Location $repoRoot
try {
    Write-Host "`n[PHASE1] Replay suite starting..." -ForegroundColor Cyan
    Write-Host "[PHASE1] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

    $PythonExe = ".\.venv\Scripts\python.exe"
    if (-not (Test-Path $PythonExe)) {
        throw "[PHASE1] Python exe not found at $PythonExe"
    }

    $cases = @(
        @{ Symbol = 'NVDA'; Csv = 'data\NVDA_1m.csv'; Mode = 'nvda_bplus' },
        @{ Symbol = 'SPY';  Csv = 'data\SPY_1m.csv';  Mode = 'spy_orb'    },
        @{ Symbol = 'QQQ';  Csv = 'data\QQQ_1m.csv';  Mode = 'qqq_orb'    },
        @{ Symbol = 'AAPL'; Csv = 'data\AAPL_1m.csv'; Mode = 'aapl_orb'   }
    )

    foreach ($c in $cases) {
        $csvPath = Join-Path $repoRoot $c.Csv
        if (-not (Test-Path $csvPath)) {
            Write-Host "[WARN] CSV not found for $($c.Symbol): $csvPath" -ForegroundColor Yellow
            continue
        }

        Write-Host "`n[PHASE1] Running replay for $($c.Symbol) using $csvPath ..." -ForegroundColor Yellow
                $session = "PHASE1_{0}_{1}" -f $c.Symbol, (Get-Date -Format "yyyyMMdd")
        & $PythonExe .\tools\run_bar_replay_to_json.py `
            --symbol  $($c.Symbol) `
            --session $session `
            --data    $csvPath
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            Write-Host "[ERROR] replay for $($c.Symbol) failed with exit code $exitCode" -ForegroundColor Red
        } else {
            Write-Host "[PHASE1] replay for $($c.Symbol) completed." -ForegroundColor Green
        }
    }

    Write-Host "`n[PHASE1] Replay suite complete." -ForegroundColor Cyan
}
finally {
    Pop-Location
}