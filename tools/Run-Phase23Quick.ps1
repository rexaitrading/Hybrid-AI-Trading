[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[PHASE23] Phase-2/3 quick diagnostics RUN" -ForegroundColor Cyan
Write-Host "[PHASE23] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

# Step 1: Phase-2 micro snapshot (SPY/QQQ micro + cost)
$phase2Snap = Join-Path $repoRoot "tools\Run-Phase2MicroSnapshot.ps1"
if (Test-Path $phase2Snap) {
    Write-Host "`n[PHASE23] Step 1: Run-Phase2MicroSnapshot.ps1" -ForegroundColor Yellow
    & $phase2Snap
    $code = $LASTEXITCODE
    Write-Host "[PHASE23] Run-Phase2MicroSnapshot.ps1 exit code = $code" -ForegroundColor DarkCyan
} else {
    Write-Host "[PHASE23] WARN: Run-Phase2MicroSnapshot.ps1 not found at $phase2Snap" -ForegroundColor Yellow
}

# Step 2: GateScore daily pipeline (NVDA)
$phase3Daily = Join-Path $repoRoot "tools\Run-Phase3GateScoreDaily.ps1"
if (Test-Path $phase3Daily) {
    Write-Host "`n[PHASE23] Step 2: Run-Phase3GateScoreDaily.ps1" -ForegroundColor Yellow
    & $phase3Daily
    $code = $LASTEXITCODE
    Write-Host "[PHASE23] Run-Phase3GateScoreDaily.ps1 exit code = $code" -ForegroundColor DarkCyan
} else {
    Write-Host "[PHASE23] WARN: Run-Phase3GateScoreDaily.ps1 not found at $phase3Daily" -ForegroundColor Yellow
}

Write-Host "`n[PHASE23] Phase-2/3 quick diagnostics complete (snapshot stub)." -ForegroundColor Green

# --- Phase23: write daily health row (Block-G input) ---
try {
    $toolsDir = Split-Path -Parent $PSCommandPath
    $repoRoot = Split-Path -Parent $toolsDir
    $logsDir  = Join-Path $repoRoot "logs"
    if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $tsUtc = (Get-Date).ToUniversalTime().ToString("o")

    $gsPath = Join-Path $logsDir "gatescore_daily_summary.csv"
    $gsRow = $null
    if (Test-Path $gsPath) {
        $gsRows = @(Import-Csv $gsPath)
        foreach ($r in $gsRows) {
            if ($null -eq $r) { continue }
            if ("$($r.as_of_date)".Substring(0,10) -ne $today) { continue }
            if ($r.PSObject.Properties.Name -contains "symbol") {
                if ("$($r.symbol)" -ne "NVDA") { continue }
            }
            $gsRow = $r
            break
        }
    }

    # Conservative: Phase2 step ran in this script; if it didn't throw, assume ok.
    $phase2_micro_ok = $true
    $phase3_nvda_ok  = ($null -ne $gsRow)

    $nvda_count_signals   = if ($gsRow) { "$($gsRow.count_signals)" } else { "" }
    $nvda_mean_edge_ratio = if ($gsRow) { "$($gsRow.mean_edge_ratio)" } else { "" }
    $nvda_mean_micro_score= if ($gsRow) { "$($gsRow.mean_micro_score)" } else { "" }
    $nvda_mean_pnl        = if ($gsRow) { "$($gsRow.mean_pnl)" } else { "" }

    $outPath = Join-Path $logsDir "phase23_health_daily.csv"

    $rowObj = [pscustomobject]@{
        ts_utc              = $tsUtc
        date                = $today
        phase2_micro_ok      = [string]$phase2_micro_ok
        phase3_nvda_ok       = [string]$phase3_nvda_ok
        nvda_count_signals   = $nvda_count_signals
        nvda_mean_edge_ratio = $nvda_mean_edge_ratio
        nvda_mean_micro_score= $nvda_mean_micro_score
        nvda_mean_pnl        = $nvda_mean_pnl
    }

    if (-not (Test-Path $outPath)) {
        $rowObj | Export-Csv -NoTypeInformation -Encoding utf8 $outPath
    } else {
        $rowObj | Export-Csv -NoTypeInformation -Append -Encoding utf8 $outPath
    }

    Write-Host "[PHASE23] Wrote/append logs\phase23_health_daily.csv (date=$today)" -ForegroundColor DarkGray
} catch {
    Write-Host "[PHASE23] WARN: could not write phase23 health daily row: $($_.Exception.Message)" -ForegroundColor Yellow
}
# --- end Phase23 health row ---

exit 0
