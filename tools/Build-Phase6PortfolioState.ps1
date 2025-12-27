[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\phase6_portfolio_state.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$toolsDir = Join-Path $repoRoot "tools"
$checker  = Join-Path $toolsDir "Check-BlockGReady.ps1"

# --- ENV FALLBACK (fail-closed): ensure current Process sees HAT_IBG_STATUS_PATH if set in User env ---
if([string]::IsNullOrWhiteSpace($env:HAT_IBG_STATUS_PATH)){
  $u = [Environment]::GetEnvironmentVariable('HAT_IBG_STATUS_PATH','User')
  if(-not [string]::IsNullOrWhiteSpace($u)){
    $env:HAT_IBG_STATUS_PATH = $u
  }
}
$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

function CheckSym([string]$sym){
  powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $sym 2>$null | Out-Host
  return $LASTEXITCODE
}

$syms = @("NVDA","SPY","QQQ")
$ready = @()
foreach($s in $syms){
  if((CheckSym $s) -eq 0){ $ready += $s }
}

$ok = ($ready.Count -gt 0)
$reason = if($ok){"phase6_state_ok"}else{"phase6_state_no_symbols_ready"}

$payload = [ordered]@{
  ts_utc    = $tsUtc
  as_of_date= $today
  ok        = $ok
  reason    = $reason
  ready_symbols = @($ready)
  symbols   = @($syms)
  version   = "phase6.1"
} | ConvertTo-Json -Depth 8

$enc = New-Object System.Text.UTF8Encoding($false)
$full = Join-Path $repoRoot $OutPath
$dir = Split-Path -Parent $full
if($dir -and -not (Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }
[System.IO.File]::WriteAllText($full, ($payload -replace "`r`n","`n") + "`n", $enc)

Write-Host "[PHASE6] wrote $full ok=$ok ready=$($ready -join ',')" -ForegroundColor Green
exit (0)

