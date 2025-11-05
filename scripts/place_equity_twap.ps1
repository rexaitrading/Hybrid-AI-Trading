param(
  [string]$Symbol = "AAPL",
  [ValidateSet("BUY","SELL")][string]$Side = "BUY",
  [int]$TotalQty = 6,
  [int]$Slices = 3,
  [int]$SliceGapSec = 60,
  [double]$TpPct = 0.8,
  [double]$SlPct = 0.5,
  [int]$TicksClamp = 20,
  [int]$SpreadRTHbps = 8,
  [int]$SpreadPremktbps = 12,

  # Precautionary clamps (per slice)
  [int]$MaxQtyPerSlice = 10,
  [double]$MaxOrderValueCAD = 1000,

  [switch]$OutsideRTH,
  [ValidateSet("patient","normal")][string]$Adaptive = "patient",
  [switch]$BypassCooldown
)

$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = "src"

function Get-ProtectiveLimit {
@"
from ib_insync import *
ib=IB(); ib.connect("127.0.0.1", 7497, clientId=2001, timeout=30)
c = Stock("$Symbol","SMART","USD"); ib.qualifyContracts(c)
cd = ib.reqContractDetails(c)[0]; tick = cd.minTick or 0.01
t = ib.reqMktData(c, "", False, False); ib.sleep(1.2)
bid, ask, last, close = t.bid, t.ask, t.last, t.close
base = (ask if (ask and ask>0) else (last or close or 10.0))
px = min(base*1.001, (ask + $TicksClamp*tick)) if (ask and ask>0) else base + max(1,1)*tick
px = round(round(px/tick)*tick, 10)
print(px)
ib.disconnect()
"@ | python -
}

function Get-USDCAD {
@"
from ib_insync import *
fx = 1.35
try:
    ib=IB(); ib.connect("127.0.0.1", 7497, clientId=2001, timeout=30)
    try:
        con = Forex("USDCAD")
    except Exception:
        from ib_insync import Contract
        con = Contract(secType='CASH', symbol='USD', currency='CAD', exchange='IDEALPRO')
    ib.qualifyContracts(con)
    t = ib.reqMktData(con, "", False, False); ib.sleep(1.0)
    fxv = t.bid or t.ask or t.close
    if fxv and fxv > 0: fx = fxv
    ib.disconnect()
except Exception:
    pass
print(fx)
"@ | python -
}

function Get-OpenOrderCount {
@"
from ib_insync import *
ib=IB(); ib.connect("127.0.0.1", 7497, clientId=2001, timeout=30)
n=sum(1 for t in ib.reqOpenOrders() if getattr(t.contract,"symbol",None)=="$Symbol" and t.order.action.upper()=="$Side")
print(n); ib.disconnect()
"@ | python -
}

[int]$qBase = [math]::Floor($TotalQty / $Slices)
[int]$remainder = $TotalQty - $qBase * $Slices
$usdcad = [double](Get-USDCAD); if (-not $usdcad) { $usdcad = 1.35 }

for ($i=1; $i -le $Slices; $i++) {
  $qtyPlan = $qBase + ($(if ($i -eq $Slices) { $remainder } else { 0 }))
  if ($qtyPlan -le 0) { continue }

  $lmt = [double](Get-ProtectiveLimit); if (-not $lmt) { throw "Failed to compute limit." }

  # CAD value cap per slice Ã¢â€ â€™ allowed shares by value
  $allowedUSD = $MaxOrderValueCAD / $usdcad
  $allowedByValue = [int][math]::Floor($allowedUSD / $lmt)

  # Sequential Min
  $qtySize  = [Math]::Min($qtyPlan, $MaxQtyPerSlice)
  $qty      = [Math]::Min($qtySize, $allowedByValue)

  if ($qty -le 0) { Write-Host "[$i/$Slices] Skipped (value cap too tight at this price)."; continue }

  if ($BypassCooldown.IsPresent) {
@"
import json, os
p = r".\state\cooldowns.json"
if os.path.exists(p):
    j = json.load(open(p,"r",encoding="utf-8")) or {}
    j.pop("$Symbol", None)
    open(p,"w",encoding="utf-8").write(json.dumps(j))
"@ | python -
  }

  $hostArg = @('--host','127.0.0.1','--port','7497','--client-id','2001')
  $base = @('python','-m','hybrid_ai_trading.execution.paper_order') + $hostArg + @(
    '--symbol',$Symbol,'--side',$Side,'--qty',"$qty",
    '--tp-pct',"$TpPct",'--sl-pct',"$SlPct",
    '--ticks-clamp',"$TicksClamp",
    '--cooldown-min','0',
    '--dedupe-mode','cancel_older'
  )

  if ($OutsideRTH.IsPresent) {
    $args = $base + @('--outside-rth','1','--early-open-block-min','0','--spread-bps-cap',"$SpreadPremktbps",'--autoreprice-sec','60','--whatif','0')
    # Adaptive OFF outside RTH
  } else {
    $args = $base + @('--outside-rth','0','--early-open-block-min','2','--spread-bps-cap',"$SpreadRTHbps",'--adaptive',"$Adaptive",'--autoreprice-sec','75','--whatif','1')
  }

  Write-Host "[$i/$Slices] Placing $Symbol $Side x$qty ..."
  & $args[0] $args[1..($args.Count-1)]

  $tries = 0
  do {
    Start-Sleep -Seconds $SliceGapSec
    $openN = [int](Get-OpenOrderCount)
    $tries++
    Write-Host "  openOrders for $Symbol/$Side = $openN"
  } while ($openN -gt 0 -and $tries -lt 10)
}
Write-Host "TWAP complete for $Symbol ($TotalQty in $Slices slices)."
