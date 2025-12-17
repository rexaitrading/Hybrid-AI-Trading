[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [ValidateSet("BUY","SELL")][string]$Side = "BUY",
  [double]$Qty = 1,
  [ValidateSet("MARKET","LIMIT")][string]$OrderType = "MARKET",
  [double]$LimitPx = 0.0,
  [string]$IbHost = "127.0.0.1",
  [int]$Port = 7497,
  [int]$ClientId = 7
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot
$env:PYTHONPATH = Join-Path $repoRoot "src"

Write-Host ("[IBKR-SMOKE][DEBUG] IBC_INI={0}" -f ("$env:IBC_INI")) -ForegroundColor Cyan
Write-Host ("[IBKR-SMOKE][DEBUG] HAT_LIVE_ARM={0}" -f ("$env:HAT_LIVE_ARM")) -ForegroundColor Cyan
Write-Host ("[IBKR-SMOKE][DEBUG] Host={0} Port={1} ClientId={2} Symbol={3} Side={4} Qty={5} OrderType={6}" -f $IbHost,$Port,$ClientId,$Symbol,$Side,$Qty,$OrderType) -ForegroundColor Cyan

if (("$env:HAT_LIVE_ARM" -ne "1") -and ("$env:HAT_LIVE_ARM" -ne "true")) {
  Write-Host "[IBKR-SMOKE] FAIL-CLOSED: set HAT_LIVE_ARM=1 to run IBKR smoke" -ForegroundColor Yellow
  Write-Host "RESULT_CODE=90"
  return
}

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-NvdaBlockGPreflight.ps1
if ($LASTEXITCODE -ne 0) {
  Write-Host "[IBKR-SMOKE] NO-GO: preflight failed" -ForegroundColor Yellow
  Write-Host ("RESULT_CODE={0}" -f [int]$LASTEXITCODE)
  return
}

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing python: $py" }

# Build python script as plain lines (no nested here-strings)
$pyLines = @(
  "from hybrid_ai_trading.execution.brokers import IBKRClient",
  "",
  "host = '__HOST__'",
  "port = int('__PORT__')",
  "client_id = int('__CID__')",
  "",
  "sym = '__SYM__'",
  "side = '__SIDE__'",
  "qty = float('__QTY__')",
  "order_type = '__OT__'",
  "limit_px = '__LPX__'",
  "",
  "c = IBKRClient(host=host, port=port, client_id=client_id, asset_class='STK', currency='USD')",
  "",
  "lp = None",
  "if order_type != 'MARKET':",
  "    lp = float(limit_px)",
  "",
  "oid, raw = c.submit_order(sym, side, qty, order_type=order_type, limit_px=lp, meta={'regime':'NVDA_BPLUS_LIVE'})",
  "print('[IBKR-SMOKE] order_id=', oid)",
  "print('[IBKR-SMOKE] raw=', raw)"
)

$pyCode = ($pyLines -join "`n")
$pyCode = $pyCode.Replace("__HOST__", $IbHost).Replace("__PORT__", "$Port").Replace("__CID__", "$ClientId").Replace("__SYM__", $Symbol).Replace("__SIDE__", $Side).Replace("__QTY__", "$Qty").Replace("__OT__", $OrderType).Replace("__LPX__", "$LimitPx")

$tmp = Join-Path $repoRoot "tools\_tmp_ibkr_smoke.py"
$utf8NoBom2 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($tmp, ($pyCode -replace "`r`n","`n") + "`n", $utf8NoBom2)

& $py $tmp
$rc = [int]$LASTEXITCODE
Remove-Item -Force $tmp
Write-Host ("RESULT_CODE={0}" -f $rc)
return

