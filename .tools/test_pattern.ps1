param(
  [Parameter(Mandatory=$true)][string]$Pattern,
  [string]$ExtraOpts = ""
)
$ErrorActionPreference='Stop'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logDir = Join-Path (Resolve-Path ".\logs") $stamp
New-Item -ItemType Directory -Force $logDir | Out-Null
$out    = Join-Path $logDir "pytest.out.txt"
$env:PYTEST_ADDOPTS = "--maxfail=1"
$cmd = "python -m pytest -q -k `"$Pattern`" $ExtraOpts"
Write-Host ">> $cmd" -ForegroundColor Cyan
Invoke-Expression $cmd | Tee-Object -FilePath $out
"`n==== tail ====" | Out-File -FilePath $out -Append
Get-Content $out -Tail 30
Write-Host "Logs: $logDir" -ForegroundColor Green
