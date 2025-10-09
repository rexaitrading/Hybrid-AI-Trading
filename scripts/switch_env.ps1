param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('paper-gateway','paper-tws','live-gateway','live-tws')]
  [string]$target
)

$map = @{
  'paper-gateway' = '.env.paper.ibg'   # 127.0.0.1:4002 (IB Gateway Paper)
  'paper-tws'     = '.env.paper'       # 127.0.0.1:7497 (TWS Paper)
  'live-gateway'  = '.env.live.ibg'    # 127.0.0.1:4001 (IB Gateway Live) - create later
  'live-tws'      = '.env.live'        # 127.0.0.1:7496 (TWS Live) - create later
}

if (-not $map.ContainsKey($target)) { Write-Error "Unknown target: $target"; exit 1 }
if (-not (Test-Path $map[$target])) { Write-Error "Config $($map[$target]) not found."; exit 1 }

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
if (Test-Path '.env') { Copy-Item -Force '.env' ".env.backup_$stamp" }
Copy-Item -Force $map[$target] '.env'

Write-Host "✅ Switched to $target"
Write-Host '---'
Get-Content '.env' | ForEach-Object { "  $_" }
