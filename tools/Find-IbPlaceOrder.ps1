[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path ".").Path
$src = Join-Path $repoRoot "src\hybrid_ai_trading"

Write-Host "Scanning for ib.placeOrder(" -ForegroundColor Cyan
Write-Host "Root=$src" -ForegroundColor Cyan

$hits = Select-String -Path (Join-Path $src "**\*.py") -Pattern 'ib\.placeOrder\(' -AllMatches -ErrorAction SilentlyContinue |
  ForEach-Object {
    $rel = $_.Path.Replace($repoRoot + "\", "").Replace("\","/")
    [PSCustomObject]@{ File=$rel; Line=$_.LineNumber }
  } | Sort-Object File, Line

if(-not $hits){
  Write-Host "No hits." -ForegroundColor Green
  exit 0
}

$hits | Format-Table -Auto | Out-Host
exit 0
