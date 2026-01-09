[CmdletBinding()]
param()

Set-StrictMode -Version Latest
# --- secrets (canonical) ---
# --- repo root bootstrap (canonical) ---
$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
if(-not $repoRoot){ throw "[INTEL] FAIL-CLOSED: Go-RepoRoot returned empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)

. (Join-Path $PSScriptRoot "Load-HatSecrets.ps1") -RepoRoot $repoRoot
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[INTEL-FULL] start" -ForegroundColor Cyan

# Always run minimal pulse first (guaranteed artifacts)
$min = Join-Path $toolsDir "Run-IntelPipeline-Minimal.ps1"
if(Test-Path -LiteralPath $min){
  & $min *>&1 | Out-Host
} else {
  throw "[INTEL-FULL] Missing minimal pipeline: $min"
}

# Optional: run additional collectors if they exist (safe SKIP)
$optional = @(
  (Join-Path $toolsDir "Run-IntelNews.ps1"),
  (Join-Path $toolsDir "Run-IntelYouTube.ps1"),
  (Join-Path $toolsDir "Run-IntelEarnings.ps1")
)

foreach($p in $optional){
  if(Test-Path -LiteralPath $p){
    Write-Host "[INTEL-FULL] run => $p" -ForegroundColor Yellow
    & $p *>&1 | Out-Host
  } else {
    Write-Host "[INTEL-FULL] SKIP missing => $p" -ForegroundColor DarkYellow
  }
}

Write-Host "[INTEL-FULL] ok" -ForegroundColor Green
exit 0