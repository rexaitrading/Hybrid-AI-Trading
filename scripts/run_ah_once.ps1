param(
  [string]$Symbol    = "AAPL",
  [ValidateSet("BUY","SELL")] [string]$Force = "BUY",
  [string]$Dest      = "SMART",    # SMART|ISLAND|ARCA|NASDAQ
  [ValidateSet("LMT","MKT")] [string]$OrderType = "LMT",
  [double]$LimitOffset = 1.0,
  [switch]$OutsideRth,
  [double]$Qty = 1.0,
  [int]$ClientId = 5007,
  [string]$VenvPy = ".\.venv\Scripts\python.exe"
)

$env:PYTHONPATH = (Resolve-Path ".\src").Path
$py = (Resolve-Path ".\src\hybrid_ai_trading\runners\ah_once.py").Path
$args = @($py, "--symbol", $Symbol, "--force", $Force, "--dest", $Dest, "--order-type", $OrderType, "--limit-offset", ('{0:N2}' -f $LimitOffset), "--qty", $Qty, "--client-id", $ClientId, "--json")
if ($OutsideRth) { $args += "--outside-rth" }

Write-Host ("Running: {0} {1}" -f $VenvPy, ($args -join ' ')) -ForegroundColor Cyan
& $VenvPy @args
