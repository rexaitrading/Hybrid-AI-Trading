param(
  [switch]$Ci  # CI mode: exits with code; otherwise prompts at end
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 7) { $PSStyle.OutputRendering = 'PlainText' }

# --- Paths & logging ---
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $ScriptDir
$LogsRoot = Join-Path $ScriptDir "..\..\.logs"
New-Item -ItemType Directory -Force -Path $LogsRoot -ErrorAction SilentlyContinue | Out-Null
$Stamp   = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogPath = Join-Path $LogsRoot "ib_order_smoke.$Stamp.log"

# --- Env defaults (PS5.1 style) ---
if (-not $env:IB_HOST)       { $env:IB_HOST       = "127.0.0.1" }
if (-not $env:IB_PORT)       { $env:IB_PORT       = "4002" }
if (-not $env:IB_SMOKE_SSL)  { $env:IB_SMOKE_SSL  = "0" }
if (-not $env:IB_TIMEOUT)    { $env:IB_TIMEOUT    = "20" }
if (-not $env:REQUIRE_PAPER) { $env:REQUIRE_PAPER = "1" }

# --- Guardrail: ensure 4002 owned by expected exe ---
$GoodExe = 'C:\Jts\ibgateway\1039\ibgateway.exe'
$lis = Get-NetTCPConnection -State Listen -LocalPort 4002 -ErrorAction SilentlyContinue
if (-not $lis) { throw "Port 4002 not listening. Is IB Gateway (Paper, IB API) logged in?" }
$proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($lis.OwningProcess)"
if ($proc.ExecutablePath -ne (Get-Item $GoodExe).FullName) {
  "âš ï¸  4002 owned by: $($proc.ExecutablePath)`n    Expected: $GoodExe" | Tee-Object -FilePath $LogPath -Append
  throw "Mismatched IBG version on 4002"
}

# --- Python runner + temp script ---
$PyExe     = Resolve-Path (Join-Path $ScriptDir "..\..\.venv\Scripts\python.exe")
$TmpScript = Join-Path $env:TEMP "ib_order_smoke_rthsafe.py"
$EncNoBom  = [Text.UTF8Encoding]::new($false)

$PyCode = @"
import os
from ib_insync import Stock, LimitOrder
from hybrid_ai_trading.utils.ib_conn import ib_session

HOST=os.getenv("IB_HOST","127.0.0.1")
PORT=int(os.getenv("IB_PORT","4002"))
SSL =os.getenv("IB_SMOKE_SSL","0")=="1"
print(f"connect_to host={HOST} port={PORT} ssl={int(SSL)}")

with ib_session(market_data_type=3) as ib:
    aapl = Stock("AAPL","SMART","USD")
    t    = ib.reqMktData(aapl, "", False, False)
    ib.sleep(1.8)
    last = t.last or t.close or 250.0

    # Far from market to avoid fills; allow outside RTH to suppress warning 399
    px = round(max(1.0, 0.10*float(last)), 2)
    o  = LimitOrder("BUY", 1, px)
    o.outsideRth = True
    o.tif        = "DAY"

    tr = ib.placeOrder(aapl, o)
    print("order_submitted", {"symbol":"AAPL","side":"BUY","qty":1,"limit":px,"outsideRth":o.outsideRth,"tif":o.tif})
    ib.sleep(2.5)
    ib.cancelOrder(o)
    ib.sleep(2.0)
    st = tr.orderStatus.status if tr.orderStatus else None
    print("final_status", st)
"@
[IO.File]::WriteAllText($TmpScript, $PyCode, $EncNoBom)

# --- Verify and preview ---
if (-not (Test-Path $PyExe))    { throw "Python not found at: $PyExe" }
if (-not (Test-Path $TmpScript)){ throw "Script not found at: $TmpScript" }
"Python:  $PyExe"            | Tee-Object -FilePath $LogPath -Append
"Script:  $TmpScript"        | Tee-Object -FilePath $LogPath -Append
"Preview:"                   | Tee-Object -FilePath $LogPath -Append
(Get-Content -Path $TmpScript -TotalCount 5) -join [Environment]::NewLine | Tee-Object -FilePath $LogPath -Append

# --- Run with stderr-tolerant EAP (IBKR warnings may go to stderr) ---
$oldEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $PyExe --version         2>&1 | Tee-Object -FilePath $LogPath -Append
$run = & $PyExe $TmpScript 2>&1 | Tee-Object -FilePath $LogPath -Append
$ErrorActionPreference = $oldEAP

$run | Tee-Object -FilePath $LogPath -Append

# --- Assert final status and finish ---
$passed = $run -match 'final_status\s+Cancelled'
if ($passed) {
  "âœ… Paper order open/cancel smoke passed (RTH-safe)." | Tee-Object -FilePath $LogPath -Append
  if ($Ci) { exit 0 } else { Read-Host "`nPress <Enter> to close"; return }
} else {
  "âš ï¸  Did not see final_status Cancelled in output." | Tee-Object -FilePath $LogPath -Append
  if ($Ci) { exit 2 } else { Read-Host "`nPress <Enter> to close"; return }
}
