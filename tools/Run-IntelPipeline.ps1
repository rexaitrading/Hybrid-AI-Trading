[CmdletBinding()]
param()

Set-StrictMode -Version Latest
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# Optional override: a path RELATIVE to repoRoot (ps1 or py)
$override = [System.Environment]::GetEnvironmentVariable("HAT_INTEL_ENTRYPOINT","User")
if ([string]::IsNullOrWhiteSpace($override)) {
  $override = [System.Environment]::GetEnvironmentVariable("HAT_INTEL_ENTRYPOINT","Process")
}

$entry = $null
if (-not [string]::IsNullOrWhiteSpace($override)) {
  $entry = Join-Path $repoRoot $override
  if (-not (Test-Path -LiteralPath $entry)) { Write-Host "[INTEL] NOT READY: HAT_INTEL_ENTRYPOINT set but not found: $entry" -ForegroundColor Yellow; exit 2 }
} else {
  # No override => never run arbitrary discovered .py. Use minimal safe intel pulse.
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelPipeline-Minimal.ps1")
  exit $LASTEXITCODE
}

if (-not $entry -or -not (Test-Path -LiteralPath $entry)) {
  Write-Host "[INTEL] WARN: No intel entrypoint found; running minimal fallback pulse." -ForegroundColor Yellow
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelPipeline-Minimal.ps1")
exit $LASTEXITCODE
}

if ($entry.ToLowerInvariant().EndsWith(".ps1")) {
  Write-Host "[INTEL] Running PS1: $entry" -ForegroundColor Cyan
  & powershell -NoProfile -ExecutionPolicy Bypass -File $entry
  exit $LASTEXITCODE
}

if ($entry.ToLowerInvariant().EndsWith(".py")) {
  $py = Join-Path $repoRoot ".venv\Scripts\python.exe"
  if (-not (Test-Path -LiteralPath $py)) { throw "Python venv missing: $py" }

  # Ensure package imports work when running repo python files
  $env:PYTHONPATH = $repoRoot

  Write-Host "[INTEL] Running PY: $entry" -ForegroundColor Cyan
  & $py $entry
  exit $LASTEXITCODE
}

throw "Unsupported intel entrypoint type: $entry"