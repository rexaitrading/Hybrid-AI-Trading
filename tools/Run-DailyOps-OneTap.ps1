[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null
. (Join-Path (Split-Path -Parent $PSCommandPath) "RepoRoot.ps1")
if(-not (Get-Command Get-RepoRoot -ErrorAction SilentlyContinue)){
  throw "RepoRoot.ps1 did not load Get-RepoRoot (fail-closed)"
}
$repoRoot = Get-RepoRoot
# -----------------------------
# Run-once-per-day stamp (avoid duplicate spam)
# -----------------------------
$stamp = Join-Path $repoRoot "logs\daily_ops_onetap_last_ok.json"
$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")  # boot value; later replaced by Phase6 as_of_date
try{
  if(Test-Path -LiteralPath $stamp){
    $j = Get-Content -LiteralPath $stamp -Raw -Encoding utf8 | ConvertFrom-Json
    $last = ([string]$j.as_of_date).Trim()
    if($last -eq $today){
      Write-Host "[DAILY-OPS] already ran today ($today). Skipping." -ForegroundColor Yellow
$global:LASTEXITCODE = 0; return
    }
  }
}catch{ }
# -----------------------------
# HARD SAFETY: paper-only lock
# -----------------------------
$env:HAT_IS_PAPER="1"
$env:HAT_LIVE_DISABLED="1"

# Ensure key envs are visible in this process (fail-closed if missing)
if([string]::IsNullOrWhiteSpace($env:HAT_IBG_STATUS_PATH)){
  $u = [Environment]::GetEnvironmentVariable("HAT_IBG_STATUS_PATH","User")
  if(-not [string]::IsNullOrWhiteSpace($u)){ $env:HAT_IBG_STATUS_PATH = $u }
}

# -------- Phase-5 / Block-G checks (single source of truth: Check-BlockGReady) --------
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Check-BlockGReady.ps1") -Symbol NVDA

# -------- Intel pipeline (your configured entrypoint via HAT_INTEL_ENTRYPOINT) --------
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelPipeline.ps1")

# -------- Phase-6 state + CSV + Notion upsert --------
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-Phase6OneTap-Notion.ps1")
# Derive "today" from Phase6 output (single source of truth)
try{
  $p6 = Get-Content -LiteralPath (Join-Path $repoRoot "logs\phase6_portfolio_state.json") -Raw -Encoding utf8 | ConvertFrom-Json
  if($p6 -and $p6.PSObject.Properties.Name -contains "as_of_date"){
    $today = ([string]$p6.as_of_date).Trim()
  }
}catch{ }
# Write stamp (only after success)
try{
  $stampObj = [ordered]@{
  as_of_date = $today
  ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
  symbol     = "NVDA"
  mode       = "paper_locked"
} | ConvertTo-Json -Depth 5
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($stamp, (($stampObj -replace "`r`n","`n") + "`n"), $enc)
}catch{ }

Write-Host "[DAILY-OPS] DONE (paper-locked)" -ForegroundColor Green
$global:LASTEXITCODE = 0; return
