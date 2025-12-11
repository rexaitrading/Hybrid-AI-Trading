[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[PHASE3] GateScore daily suite RUN" -ForegroundColor Cyan
Write-Host "[PHASE3] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

$smoke = Join-Path $repoRoot "tools\Run-GateScoreSmoke.ps1"
if (-not (Test-Path $smoke)) {
    Write-Host "[PHASE3] WARN: Run-GateScoreSmoke.ps1 not found at $smoke; nothing to run." -ForegroundColor Yellow
    exit 0
}

Write-Host "[PHASE3] Delegating to Run-GateScoreSmoke.ps1..." -ForegroundColor Yellow
& $smoke
$code = $LASTEXITCODE
Write-Host "[PHASE3] Run-GateScoreSmoke.ps1 exit code = $code" -ForegroundColor DarkCyan
exit $code