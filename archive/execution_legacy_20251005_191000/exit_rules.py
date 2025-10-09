from __future__ import annotations

import time
from typing import Any, Dict, List

from ib_insync import IB, MarketOrder


def _to_f(x):
    try:
        return float(str(x))
    except:
        return None


def _tick_last(ib: IB, contract) -> float | None:
    t = ib.reqMktData(contract, "", False, False)
    ib.sleep(0.8)
    return _to_f(getattr(t, "last", None)) or _to_f(getattr(t, "close", None))


def check_and_exit(
    stop_pct: float = 0.02,
    take_pct: float = 0.03,
    dry_run: bool = True,
    host: str = "127.0.0.1",
    port: int = 7497,
    client_id: int = 2001,
) -> List[Dict[str, Any]]:
    """
    For each LONG stock position, if last <= avgCost*(1-stop_pct) or last >= avgCost*(1+take_pct),
    place a paper SELL (unless dry_run). Returns actions list.
    """
    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=30)
    ib.reqMarketDataType(3)

    actions: List[Dict[str, Any]] = []
    # Positions: [Position(account, contract, position, avgCost)]
    for pos in ib.positions():
        acct = pos.account
        c = pos.contract
        qty = int(pos.position or 0)
        avg = _to_f(pos.avgCost)
        if qty <= 0:  # only long equity
            continue
        if getattr(c, "secType", "") != "STK":
            continue

        last = _tick_last(ib, c)
        if not last or not avg or avg <= 0:
            actions.append(
                {"symbol": getattr(c, "symbol", "?"), "skip": "no price or avgCost"}
            )
            continue

        stop_level = avg * (1.0 - stop_pct)
        take_level = avg * (1.0 + take_pct)

        reason = None
        if last <= stop_level:
            reason = f"STOP {stop_pct:.2%} (last={last:.2f} <= {stop_level:.2f})"
        elif last >= take_level:
            reason = f"TAKE {take_pct:.2%} (last={last:.2f} >= {take_level:.2f})"

        if reason:
            if dry_run:
                actions.append(
                    {
                        "symbol": c.symbol,
                        "qty": qty,
                        "reason": reason,
                        "would_sell": True,
                    }
                )
            else:
                t = ib.placeOrder(c, MarketOrder("SELL", qty))
                ib.sleep(1.0)
                actions.append(
                    {
                        "symbol": c.symbol,
                        "qty": qty,
                        "reason": reason,
                        "status": t.orderStatus.status,
                        "filled": t.orderStatus.filled,
                        "avgPrice": t.orderStatus.avgFillPrice,
                    }
                )
        else:
            actions.append(
                {
                    "symbol": c.symbol,
                    "hold": True,
                    "last": last,
                    "avgCost": avg,
                    "stop": stop_level,
                    "take": take_level,
                }
            )
        time.sleep(0.2)

    ib.disconnect()
    return actions
