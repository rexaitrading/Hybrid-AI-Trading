[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# Optional override: a path RELATIVE to repoRoot (ps1 or py)
$override = [System.Environment]::GetEnvironmentVariable("HAT_INTEL_ENTRYPOINT","User")
if ([string]::IsNullOrWhiteSpace($override)) {
  $override = [System.Environment]::GetEnvironmentVariable("HAT_INTEL_ENTRYPOINT","Process")
}

function Find-IntelEntrypoint {
  param([string]$Root)

  # Heuristic: locate python files that reference intel artifacts
  $paths = @(
    (Join-Path $Root "src\hybrid_ai_trading\**\*.py"),
    (Join-Path $Root "tools\**\*.py"),
    (Join-Path $Root "scripts\**\*.py")
  )

  $hits = Select-String -Path $paths 
    -Pattern "\.intel","risk_pulse","news_feed","notion_intel","intel_report" 
    -AllMatches -ErrorAction SilentlyContinue |
    Select-Object -Unique Path

  if ($hits -and $hits.Count -gt 0) { return ($hits | Select-Object -First 1).Path }
  return $null
}

$entry = $null
if (-not [string]::IsNullOrWhiteSpace($override)) {
  $entry = Join-Path $repoRoot $override
  if (-not (Test-Path -LiteralPath $entry)) { throw "HAT_INTEL_ENTRYPOINT set but not found: $entry" }
} else {
  $entry = Find-IntelEntrypoint -Root $repoRoot
}

if (-not $entry -or -not (Test-Path -LiteralPath $entry)) {
  Write-Host "[INTEL] NOT READY: No intel entrypoint found. Set env HAT_INTEL_ENTRYPOINT to a .ps1 or .py path relative to repoRoot." -ForegroundColor Yellow
  exit 2
}

if ($entry.ToLowerInvariant().EndsWith(".ps1")) {
  Write-Host "[INTEL] Running PS1: $entry" -ForegroundColor Cyan
  & powershell -NoProfile -ExecutionPolicy Bypass -File $entry
  exit $LASTEXITCODE
}

if ($entry.ToLowerInvariant().EndsWith(".py")) {
  $py = Join-Path $repoRoot ".venv\Scripts\python.exe"
  if (-not (Test-Path -LiteralPath $py)) { throw "Python venv missing: $py" }
  Write-Host "[INTEL] Running PY: $entry" -ForegroundColor Cyan
  & $py $entry
  exit $LASTEXITCODE
}

throw "Unsupported intel entrypoint type: $entry"