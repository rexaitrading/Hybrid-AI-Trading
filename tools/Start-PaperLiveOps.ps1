[CmdletBinding()]
param(
  [ValidateSet("NVDA")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[PAPERLIVE-OPS] start Symbol=$Symbol" -ForegroundColor Cyan

# Load secrets into this process
. (Join-Path $repoRoot "tools\Load-HatSecrets.ps1") -Profile paper

# Intel refresh (non-breaking)
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelNews.ps1") *>&1 | Out-Host
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelYouTube.ps1") *>&1 | Out-Host

# NVDA paper ops pipeline (stream->events->summaries->evhard->blockg)
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-NvdaPaperOps.ps1") *>&1 | Out-Host

# ContractPack rebuild + check
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-Premarket-ContractPack.ps1") -Symbol $Symbol *>&1 | Out-Host
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Check-BlockGReady.ps1") -Symbol $Symbol *>&1 | Out-Host
Write-Host ("[PAPERLIVE-OPS] EXIT_BLOCKG=" + $LASTEXITCODE) -ForegroundColor Yellow

exit $LASTEXITCODE