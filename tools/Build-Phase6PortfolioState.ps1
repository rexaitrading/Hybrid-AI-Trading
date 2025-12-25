[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\phase6_portfolio_state.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$toolsDir = Join-Path $repoRoot "tools"
$checker  = Join-Path $toolsDir "Check-BlockGReady.ps1"

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


# ---- IB positions snapshot (read-only; best-effort) ----
$positions = @()
$positions_count = 0
try {
  $py = Join-Path $repoRoot ".venv\Scripts\python.exe"
  if(-not (Test-Path $py)){ $py = "python" }
  $out = & $py -c "from ib_insync import IB; ib=IB(); ib.connect(\"127.0.0.1\",4002,clientId=26,timeout=10); pos=ib.positions(); print(len(pos)); [print(getattr(p.contract,\"symbol\",None), float(p.position or 0), float(getattr(p,\"avgCost\",0) or 0)) for p in pos]; ib.disconnect()"
  if($out -and $out.Count -ge 1){
    $positions_count = [int]($out[0])
    for($i=1; $i -lt $out.Count; $i++){
      $parts = @([regex]::Split(($out[$i]+""), "\s+") | Where-Object { $_ -ne "" })
      if($parts.Count -ge 3){
        $positions += [pscustomobject]@{ symbol=$parts[0]; qty=[double]$parts[1]; avgCost=[double]$parts[2] }
      }
    }
  }
} catch {
  $positions = @(); $positions_count = 0
}

$payload = [ordered]@{
  ts_utc    = $tsUtc
  as_of_date= $today
  ok        = $ok
  reason    = $reason
  ready_symbols = @($ready)
  symbols   = @($syms)
  positions_count = $positions_count
  positions = @($positions)
  version   = "phase6.1"
} | ConvertTo-Json -Depth 8

$enc = New-Object System.Text.UTF8Encoding($false)
$full = Join-Path $repoRoot $OutPath
$dir = Split-Path -Parent $full
if($dir -and -not (Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }
[System.IO.File]::WriteAllText($full, ($payload -replace "`r`n","`n") + "`n", $enc)

Write-Host "[PHASE6] wrote $full ok=$ok ready=$($ready -join ',')" -ForegroundColor Green
exit (0)
