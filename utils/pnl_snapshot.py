from __future__ import annotations
from typing import Dict, Any, List
from ib_insync import IB

def snapshot(host="127.0.0.1", port=7497, client_id=2001) -> Dict[str, Any]:
    ib = IB(); ib.connect(host, port, clientId=client_id, timeout=30)
    ib.reqMarketDataType(3)
    net = 0.0
    rows: List[Dict[str,Any]] = []
    for p in ib.positions():
        c = p.contract; qty = float(p.position or 0); avg = float(p.avgCost or 0.0)
        if qty == 0 or getattr(c,"secType","") != "STK": continue
        t = ib.reqMktData(c, "", False, False); ib.sleep(0.7)
        last = float(getattr(t,"last", 0.0) or 0.0)
        upl = (last - avg) * qty
        rows.append({"symbol": c.symbol, "qty": qty, "avgCost": avg, "last": last, "UPL": upl})
        net += upl
    # NetLiq
    ewl = None
    try:
        # piggyback earlier helper
        from utils.ib_preview import whatif_preview
        ewl = (whatif_preview(rows[0]["symbol"], qty=1)["equityWithLoan"] if rows else None)
    except Exception:
        pass
    ib.disconnect()
    return {"positions": rows, "UPL_total": net, "equityWithLoan": ewl}