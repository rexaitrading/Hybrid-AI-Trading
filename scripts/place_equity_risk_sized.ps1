param(
  [string]$Symbol = "AAPL",
  [ValidateSet("BUY","SELL")][string]$Side = "BUY",
  [double]$RiskCash = 50,
  [double]$TpPct = 0.8,
  [double]$SlPct = 0.5,
  [int]$TicksClamp = 20,

  # Precautionary clamps (match TWS Presets)
  [int]$MaxQty = 10,                 # IB "Size Limit"
  [double]$MaxOrderValueCAD = 1000,  # IB "Total Value Limit" (CAD)

  # Runner behavior
  [int]$CooldownMin = 10,
  [int]$EarlyOpenBlockMin = 2,
  [int]$SpreadRTHbps = 8,
  [int]$SpreadPremktbps = 12,
  [switch]$OutsideRTH,               # set for pre/after-market
  [ValidateSet("patient","normal")][string]$Adaptive = "patient",
  [switch]$BypassCooldown            # removes symbol from cooldowns.json
)

$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = "src"

# --- Compute protective limit (0.1% over ask, tick-clamped) ---
$lmt = @"
from ib_insync import *
ib=IB(); ib.connect("127.0.0.1", 7497, clientId=2001, timeout=30)
c = Stock("$Symbol","SMART","USD"); ib.qualifyContracts(c)
cd = ib.reqContractDetails(c)[0]; tick = cd.minTick or 0.01
t = ib.reqMktData(c, "", False, False); ib.sleep(1.3)
bid, ask, last, close = t.bid, t.ask, t.last, t.close
base = (ask if (ask and ask>0) else (last or close or 10.0))
desired = base * 1.001
px = min(desired, (ask + $TicksClamp*tick)) if (ask and ask>0) else base + max(1,1)*tick
px = round(round(px / tick) * tick, 10)
print(px)
ib.disconnect()
"@ | python -
if (-not $lmt) { throw "Failed to compute protective limit." }
$lmt = [double]$lmt

# --- Get USDCAD (CAD per USD); fallback 1.35 ---
$usdcad = @"
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
if (-not $usdcad) { $usdcad = 1.35 }
$usdcad = [double]$usdcad

# --- Risk sizing, then clamp by size & CAD notional (sequential Min) ---
$stopDistance = $lmt * ($SlPct/100.0)
if ($stopDistance -le 0) { throw "Invalid stop distance from SL%." }
$qtyRisk = [int][math]::Floor($RiskCash / $stopDistance)
if ($qtyRisk -lt 1) { $qtyRisk = 1 }

# Value clamp: allowed USD = CAD cap / USDCAD
$allowedUSD = $MaxOrderValueCAD / $usdcad
$qtyValue = [int][math]::Floor($allowedUSD / $lmt)
if ($qtyValue -lt 0) { $qtyValue = 0 }

# Sequential Min (2-arg each call)
$qtySize = [Math]::Min($qtyRisk, $MaxQty)
$qty     = [Math]::Min($qtySize, $qtyValue)

if ($qty -lt 1) {
  Write-Host ("Order exceeds CAD value cap at this price. " +
              "MaxOrderValueCAD={0}, USDCAD={1:N4}, lmt={2:N2} → qtyValue={3}" -f $MaxOrderValueCAD,$usdcad,$lmt,$qtyValue)
  Write-Host "Tip: lower -RiskCash OR raise -MaxOrderValueCAD in script OR TWS Presets."
  exit 0
}
if ($qtyRisk -gt $MaxQty)   { Write-Host "Clamped by Size Limit: $qtyRisk → $qtySize (max $MaxQty)"; }
if ($qtySize -gt $qty)      { Write-Host "Clamped by Value Limit: $qtySize → $qty (max CAD $MaxOrderValueCAD)"; }

# --- Optional: bypass module cooldown for this symbol ---
if ($BypassCooldown.IsPresent) {
@"
import json, os
p = r".\state\cooldowns.json"
if os.path.exists(p):
    j = json.load(open(p,"r",encoding="utf-8")) or {}
    j.pop("$Symbol", None)
    open(p,"w",encoding="utf-8").write(json.dumps(j))
    print("Bypassed cooldown for $Symbol")
else:
    print("No cooldown file")
"@ | python -
}

# --- Call the module with explicit --qty ---
$hostArg = @('--host','127.0.0.1','--port','7497','--client-id','2001')
$base = @('python','-m','hybrid_ai_trading.execution.paper_order') + $hostArg + @(
  '--symbol', $Symbol, '--side', $Side, '--qty', "$qty",
  '--tp-pct', "$TpPct", '--sl-pct', "$SlPct",
  '--ticks-clamp', "$TicksClamp",
  '--cooldown-min', "$CooldownMin"
)

if ($OutsideRTH.IsPresent) {
  # Adaptive & what-if OFF outside RTH
  $args = $base + @('--outside-rth','1','--early-open-block-min','0','--spread-bps-cap',"$SpreadPremktbps",'--autoreprice-sec','60','--whatif','0')
} else {
  $args = $base + @('--outside-rth','0','--early-open-block-min',"$EarlyOpenBlockMin",'--spread-bps-cap',"$SpreadRTHbps",'--adaptive',"$Adaptive",'--autoreprice-sec','90','--whatif','1')
}

& $args[0] $args[1..($args.Count-1)]
