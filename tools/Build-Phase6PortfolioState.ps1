[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\phase6_portfolio_state.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$toolsDir = Join-Path $repoRoot "tools"
$checker  = Join-Path $toolsDir "Check-BlockGReady.ps1"

# Policy A: daily Phase-6 readiness uses market-aware RunContext as_of_date (US lane)
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Resolve-RunContext.ps1") -Market US
$rc = $null
try { $rc = $rcRaw | ConvertFrom-Json -ErrorAction Stop } catch { $rc = $null }
if(-not $rc){ throw "[PHASE6] Resolve-RunContext invalid JSON (fail-closed)" }
$today = ([string]$rc.as_of_date).Trim()
if(-not $today){ throw "[PHASE6] RunContext as_of_date missing (fail-closed)" }
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

function CheckSym([string]$sym){
  powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $checker -Symbol $sym -Market US -Mode BUILD_ONLY 2>$null | Out-Host
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
ready_for_optimizer = @($ready)
ready_for_live = @()
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
