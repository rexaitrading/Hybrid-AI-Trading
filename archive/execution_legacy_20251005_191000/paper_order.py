from __future__ import annotations

from typing import Any, Dict, Literal

from ib_insync import IB, MarketOrder, Stock


def place_market(
    symbol: str,
    qty: int,
    side: Literal["BUY", "SELL"] = "BUY",
    host="127.0.0.1",
    port=7497,
    client_id=2001,
    exchange="SMART",
    currency="USD",
    primary="NASDAQ",
    outside_rth: bool = True,
    tif: str = "DAY",
) -> Dict[str, Any]:
    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=30)
    c = Stock(symbol, exchange, currency, primaryExchange=primary)
    ib.qualifyContracts(c)
    o = MarketOrder(side, int(qty))
    o.outsideRth = outside_rth
    o.tif = tif
    t = ib.placeOrder(c, o)
    ib.sleep(1.0)
    status = t.orderStatus.status
    filled = t.orderStatus.filled
    avgpx = t.orderStatus.avgFillPrice
    ib.disconnect()
    return {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "status": status,
        "filled": filled,
        "avgPrice": avgpx,
    }


def place_market_watch(
    symbol: str,
    qty: int,
    side: Literal["BUY", "SELL"] = "BUY",
    host="127.0.0.1",
    port=7497,
    client_id=2001,
    exchange="SMART",
    currency="USD",
    primary="NASDAQ",
    outside_rth: bool = True,
    tif: str = "DAY",
    wait_sec: float = 20.0,
) -> Dict[str, Any]:
    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=30)
    c = Stock(symbol, exchange, currency, primaryExchange=primary)
    ib.qualifyContracts(c)
    o = MarketOrder(side, int(qty))
    o.outsideRth = outside_rth
    o.tif = tif
    t = ib.placeOrder(c, o)
    waited = 0.0
    while waited < wait_sec and t.orderStatus.status in (
        "PendingSubmit",
        "PreSubmitted",
        "PendingCancel",
        "Submitted",
    ):
        ib.waitOnUpdate(0.5)
        waited += 0.5
    out = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "status": t.orderStatus.status,
        "filled": t.orderStatus.filled,
        "avgPrice": t.orderStatus.avgFillPrice,
        "waited_sec": waited,
    }
    ib.disconnect()
    return out
