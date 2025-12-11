[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

Set-Location $repoRoot

Write-Host "`n[PHASE5-AUDIT] Phase-5 Safety Audit RUN" -ForegroundColor Cyan
Write-Host "[PHASE5-AUDIT] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

# 0) Core Phase-5 safety snapshot
$runSnapshot = Join-Path $repoRoot "tools\Run-Phase5SafetySnapshot.ps1"
if (-not (Test-Path $runSnapshot)) {
    Write-Host "[PHASE5-AUDIT] ERROR: Run-Phase5SafetySnapshot.ps1 not found at $runSnapshot" -ForegroundColor Red
    exit 1
}

Write-Host "`n[PHASE5-AUDIT] Step 0: Run-Phase5SafetySnapshot.ps1" -ForegroundColor Yellow
& $runSnapshot
$exitSnapshot = $LASTEXITCODE

if ($exitSnapshot -ne 0) {
    Write-Host "[PHASE5-AUDIT] ERROR: Phase-5 SafetySnapshot failed (exit=$exitSnapshot). Aborting audit." -ForegroundColor Red
    exit $exitSnapshot
}

# Helper to run a tool and report result without aborting whole audit (except snapshot)
function Invoke-SafetyTool {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $fullPath = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path $fullPath)) {
        Write-Host "[PHASE5-AUDIT] WARN: $Label script not found at $fullPath" -ForegroundColor Yellow
        return $null
    }

    Write-Host "`n[PHASE5-AUDIT] Running $Label ..." -ForegroundColor Yellow
    & $fullPath
    $code = $LASTEXITCODE
    Write-Host "[PHASE5-AUDIT] $Label exit code = $code" -ForegroundColor DarkCyan
    return $code
}

# 1) NVDA gated pre-market
$nvdaCode = Invoke-SafetyTool -Label "NVDA gated pre-market (Run-PreMarketOneTapGatedNvda.ps1)" -RelativePath "tools\Run-PreMarketOneTapGatedNvda.ps1"

# 2) SPY gated pre-market
$spyCode  = Invoke-SafetyTool -Label "SPY Phase-5 gated pre-market (Run-SpyPhase5GatedPreMarket.ps1)" -RelativePath "tools\Run-SpyPhase5GatedPreMarket.ps1"

# 3) QQQ gated pre-market
$qqqCode  = Invoke-SafetyTool -Label "QQQ Phase-5 gated pre-market (Run-QqqPhase5GatedPreMarket.ps1)" -RelativePath "tools\Run-QqqPhase5GatedPreMarket.ps1"

Write-Host "`n[PHASE5-AUDIT] Summary:" -ForegroundColor Cyan
Write-Host ("  NVDA gated pre-market exit = {0}" -f $nvdaCode)
Write-Host ("  SPY  gated pre-market exit = {0}" -f $spyCode)
Write-Host ("  QQQ  gated pre-market exit = {0}" -f $qqqCode)

Write-Host "`n[PHASE5-AUDIT] Phase-5 Safety Audit RUN complete." -ForegroundColor Cyan
exit 0