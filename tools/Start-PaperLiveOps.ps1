[CmdletBinding()]
param(
  [ValidateSet("NVDA")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Fail([string]$m){ throw ("[PAPERLIVE-OPS] FAIL-CLOSED: " + $m) }

# --- repo root (canonical, deterministic) ---
$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
if(-not $repoRoot){ Fail "Go-RepoRoot returned empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

Write-Host ("[PAPERLIVE-OPS] start Symbol=" + $Symbol) -ForegroundColor Cyan

# Load canonical secrets into THIS process (no args; canonical loader)
. (Join-Path $repoRoot "tools\Load-HatSecrets.ps1")

# Intel refresh (non-breaking)
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelNews.ps1") *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail ("Run-IntelNews failed exit=" + $LASTEXITCODE) }

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelYouTube.ps1") *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail ("Run-IntelYouTube failed exit=" + $LASTEXITCODE) }

# NVDA paper ops pipeline (stream->events->summaries->evhard->blockg)
$pOps = Join-Path $repoRoot "tools\Run-NvdaPaperOps.ps1"
if(-not (Test-Path -LiteralPath $pOps)){ Fail "Missing required tool: tools\Run-NvdaPaperOps.ps1" }
powershell -NoProfile -ExecutionPolicy Bypass -File $pOps *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail ("Run-NvdaPaperOps failed exit=" + $LASTEXITCODE) }

# ContractPack rebuild + check
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-Premarket-ContractPack.ps1") -Symbol $Symbol *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail ("Run-Premarket-ContractPack failed exit=" + $LASTEXITCODE) }

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Check-BlockGReady.ps1") -Symbol $Symbol *>&1 | Out-Host
Write-Host ("[PAPERLIVE-OPS] EXIT_BLOCKG=" + $LASTEXITCODE) -ForegroundColor Yellow

exit $LASTEXITCODE