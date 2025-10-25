from __future__ import annotations

import os
from typing import Dict, Any, Optional

from ib_insync import Stock, LimitOrder
from hybrid_ai_trading.utils.ib_conn import ib_session

def _norm_side(side: str) -> Optional[str]:
    try:
        s = str(side).upper()
        if s in ("BUY", "SELL"):
            return s
    except Exception:
        pass
    return None

def place_limit(symbol: str, side: str, qty: int, limit_price: float) -> Dict[str, Any]:
    """
    IBKR primary limit order route (OE-grade, DRY_RUN-aware).

    Returns:
      {
        "broker": "IB",
        "status": "Submitted" | "PreSubmitted" | "Cancelled" | "dry_run" | "skip" | "error",
        "orderId": int | None,
        "symbol": str,
        "side": "BUY"/"SELL",
        "qty": int,
        "limit": float,
        "resp": {...}     # minimal status snapshot
        "reason": str     # for dry_run / skip / error
      }
    """
    side_u = _norm_side(side)
    try:
        q = int(qty)
        px = float(limit_price)
    except Exception:
        return {"broker": "IB", "status": "skip", "reason": "bad_qty_or_price", "symbol": symbol, "side": str(side), "qty": qty, "limit": limit_price}

    if side_u is None or q <= 0 or px <= 0.0:
        return {"broker": "IB", "status": "skip", "reason": "bad_inputs", "symbol": symbol, "side": str(side), "qty": qty, "limit": limit_price}

    # DRY_RUN guard (fast, no IB session)
    if os.environ.get("DRY_RUN", "0") == "1":
        return {
            "broker": "IB",
            "status": "dry_run",
            "symbol": symbol,
            "side": side_u,
            "qty": q,
            "limit": px,
            "resp": {},
            "reason": "DRY_RUN=1"
        }

    # Real route via ib_session
    try:
        with ib_session() as ib:
            contract = Stock(symbol, "SMART", "USD")
            order = LimitOrder(side_u, q, px)
            trade = ib.placeOrder(contract, order)

            # Small wait to populate orderStatus (tune if needed)
            ib.sleep(0.25)

            st = getattr(trade.orderStatus, "status", None)
            oid = getattr(trade.order, "orderId", None)
            filled = getattr(trade.orderStatus, "filled", None)
            remaining = getattr(trade.orderStatus, "remaining", None)

            return {
                "broker": "IB",
                "status": str(st or "Submitted"),
                "orderId": int(oid) if oid is not None else None,
                "symbol": symbol,
                "side": side_u,
                "qty": q,
                "limit": px,
                "resp": {"filled": filled, "remaining": remaining},
            }
    except Exception as e:
        return {
            "broker": "IB",
            "status": "error",
            "reason": f"{type(e).__name__}:{e}",
            "symbol": symbol,
            "side": side_u,
            "qty": q,
            "limit": px,
        }