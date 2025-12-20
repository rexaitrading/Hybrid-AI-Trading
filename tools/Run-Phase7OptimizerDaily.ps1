[CmdletBinding()]
param(
  [string]$StatePath = ".\logs\phase6_portfolio_state.json",
  [string]$OutPath = ".\logs\phase7_optimizer_output.json",
  [switch]$Enable
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $full = $Path
  if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $Path }
  $dir = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $Text, $enc)
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc  = (Get-Date).ToUniversalTime().ToString("o")

if (-not $Enable) {
  $out = [ordered]@{
    ts_utc=$tsUtc; as_of_date=$today; ok=$false; reason="optimizer_disabled_failclosed"
    weights=@{}
  } | ConvertTo-Json -Depth 8
  Write-Utf8NoBom -Path $OutPath -Text ($out + "`n")
  Write-Host "[PHASE7] disabled -> wrote fail-closed output" -ForegroundColor Yellow
  exit 2
}

if (-not (Test-Path $StatePath)) {
  $out = [ordered]@{
    ts_utc=$tsUtc; as_of_date=$today; ok=$false; reason="phase6_state_missing_failclosed"
    weights=@{}
  } | ConvertTo-Json -Depth 8
  Write-Utf8NoBom -Path $OutPath -Text ($out + "`n")
  Write-Host "[PHASE7] missing phase6 state -> fail-closed" -ForegroundColor Yellow
  exit 2
}

# Placeholder weights (must be replaced with real optimizer logic)
$weights = [ordered]@{ "NVDA"=0.5; "SPY"=0.3; "QQQ"=0.2 }

$out2 = [ordered]@{
  ts_utc=$tsUtc; as_of_date=$today; ok=$true; reason="optimizer_stub_weights"
  weights=$weights
} | ConvertTo-Json -Depth 8

Write-Utf8NoBom -Path $OutPath -Text ($out2 + "`n")
Write-Host "[PHASE7] wrote optimizer output (stub weights)" -ForegroundColor Cyan
exit 0
