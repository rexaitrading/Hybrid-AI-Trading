param(
  [string]$Pattern = "",
  [string[]]$Paths = @(),
  [string]$ExtraOpts = ""
)
$ErrorActionPreference='Stop'
$stamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
$logDir = Join-Path (Resolve-Path ".\logs") $stamp
New-Item -ItemType Directory -Force $logDir | Out-Null
$out = Join-Path $logDir "pytest.out.txt"
$env:PYTEST_ADDOPTS = "--maxfail=1"

# Build pytest command: prefer paths; fall back to -k pattern
$cmd = if ($Paths -and $Paths.Count -gt 0) {
  "powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Pytest-Chokepoint.ps1 -q {0} {1}" -f (($Paths -join ' '), $ExtraOpts)
} elseif ($Pattern) {
  "powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Pytest-Chokepoint.ps1 -q -k `"$Pattern`" $ExtraOpts"
} else {
  "powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Pytest-Chokepoint.ps1 -q $ExtraOpts"
}

Write-Host ">> $cmd" -ForegroundColor Cyan
Invoke-Expression $cmd | Tee-Object -FilePath $out
"`n==== tail (last 30 lines) ====" | Out-File -FilePath $out -Append
Get-Content $out -Tail 30
Write-Host ("Logs: {0}" -f $logDir) -ForegroundColor Green
