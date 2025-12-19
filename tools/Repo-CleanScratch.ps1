[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$targets = @(
  ".venv",
  ".pytest_cache",
  "__pycache__",
  "logs",
  ".logs",
  "reports",
  "replay_out",
  "htmlcov",
  ".backup",
  "local_backups"
)

foreach($t in $targets){
  if(Test-Path $t){
    Write-Host "[CLEAN] Removing $t" -ForegroundColor Yellow
    Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction SilentlyContinue
  }
}

Write-Host "[CLEAN] Done." -ForegroundColor Green
exit 0