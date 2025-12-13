[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$p = Join-Path $repoRoot "logs\nvda_phase5_paperlive_results.jsonl"
if (-not (Test-Path $p)) {
  Write-Host "[BOM] Missing $p -> skip" -ForegroundColor Yellow
  return
}

$bytes = [System.IO.File]::ReadAllBytes($p)
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
  $newBytes = $bytes[3..($bytes.Length-1)]
  [System.IO.File]::WriteAllBytes($p, $newBytes)
  Write-Host "[BOM] Removed UTF-8 BOM from nvda_phase5_paperlive_results.jsonl" -ForegroundColor Green
} else {
  Write-Host "[BOM] No BOM detected" -ForegroundColor Green
}
return