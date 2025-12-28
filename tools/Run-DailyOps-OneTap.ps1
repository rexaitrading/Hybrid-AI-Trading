[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)


# -----------------------------
# Run-once-per-day stamp (avoid duplicate spam)
# -----------------------------
$stamp = Join-Path $repoRoot "logs\daily_ops_onetap_last_ok.json"
$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
try{
  if(Test-Path -LiteralPath $stamp){
    $j = Get-Content -LiteralPath $stamp -Raw -Encoding utf8 | ConvertFrom-Json
    $last = ([string]$j.as_of_date).Trim()
    if($last -eq $today){
      Write-Host "[DAILY-OPS] already ran today ($today). Skipping." -ForegroundColor Yellow
      exit 0
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
# Write stamp (only after success)
try{
  $stampObj = [ordered]@{
    as_of_date = $today
    ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
  } | ConvertTo-Json -Depth 5
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($stamp, (($stampObj -replace "`r`n","`n") + "`n"), $enc)
}catch{ }

Write-Host "[DAILY-OPS] DONE (paper-locked)" -ForegroundColor Green
exit 0



