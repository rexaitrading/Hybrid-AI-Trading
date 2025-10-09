from __future__ import annotations

import time
from typing import Any, Dict, Literal

from ib_insync import IB, MarketOrder, Stock


def twap_market(
    symbol: str,
    total_qty: int,
    slices: int = 3,
    gap_sec: float = 0.5,
    side: Literal["BUY", "SELL"] = "BUY",
    host="127.0.0.1",
    port=7497,
    client_id=2001,
    exchange="SMART",
    currency="USD",
    primary="NASDAQ",
) -> Dict[str, Any]:
    total_qty = int(total_qty)
    slices = max(1, int(slices))
    per = max(1, total_qty // slices)
    left = total_qty

    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=30)
    c = Stock(symbol, exchange, currency, primaryExchange=primary)
    ib.qualifyContracts(c)

    fills = []
    for i in range(slices):
        qty = per if i < slices - 1 else left
        if qty <= 0:
            break
        t = ib.placeOrder(c, MarketOrder(side, qty))
        ib.sleep(0.8)
        fills.append(
            {
                "i": i,
                "qty": qty,
                "status": t.orderStatus.status,
                "filled": t.orderStatus.filled,
                "avgPrice": t.orderStatus.avgFillPrice,
            }
        )
        left -= qty
        time.sleep(max(0.0, gap_sec))
    ib.disconnect()
    return {
        "symbol": symbol,
        "side": side,
        "total_qty": total_qty,
        "slices": slices,
        "gap_sec": gap_sec,
        "fills": fills,
    }
