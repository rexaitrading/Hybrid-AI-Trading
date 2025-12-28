[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string]$AsOfDate = $null
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ $py = "python" }

if([string]::IsNullOrWhiteSpace($AsOfDate)){
  $AsOfDate = (Get-Date).ToString("yyyy-MM-dd")
}

# 1) Readiness snapshot (expects HAT_PORTFOLIO_HALT_CFG_JSON optionally set by caller)
& (Join-Path $repoRoot "tools\Write-Phase6ReadinessSnapshot.ps1")
if($LASTEXITCODE -ne 0){ throw "Phase6 readiness snapshot failed rc=$LASTEXITCODE" }

# 2) Phase6 daily summary
& $py -m hybrid_ai_trading.phase6.daily_summary --as-of-date $AsOfDate
if($LASTEXITCODE -ne 0){ throw "Phase6 daily_summary failed rc=$LASTEXITCODE" }

# 3) Stable CSV name for Notion import/sync
$src = Join-Path $repoRoot "logs\phase6\phase6_daily_summary.csv"
if(-not (Test-Path -LiteralPath $src)){ throw "Missing expected output: $src" }

$dst = Join-Path $repoRoot "logs\phase6\phase6_daily_for_notion.csv"
Copy-Item -LiteralPath $src -Destination $dst -Force

$head = Get-Content -LiteralPath $dst -Encoding utf8 | Select-Object -First 1
Write-Host ("PHASE6_EXPORT_OK as_of_date={0} file={1}" -f $AsOfDate, $dst)
Write-Host ("CSV_HEADER=" + $head)
