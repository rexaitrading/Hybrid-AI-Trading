from __future__ import annotations
"""
IBKR Client (Hybrid AI Quant Pro v1.0 - Safe & Test-Friendly)
- Connects to TWS/Gateway (defaults to paper: 127.0.0.1:7497, clientId=1)
- Helpers: account, positions, open_orders, cancel_all, place market/limit stock orders
- Uses ib_insync synchronous style for simplicity
"""


import os
from typing import Any, Dict, List, Optional

from ib_insync import IB, Stock, MarketOrder, LimitOrder


def connect_ib(
    host: Optional[str] = None,
    port: Optional[int] = None,
    client_id: Optional[int] = None,
    readonly: bool = True,
    timeout: float = 5.0,
) -> IB:
    """
    Connect to IBKR. Defaults to paper: 127.0.0.1:7497, clientId=1.
    Environment overrides:
      IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID
    """
    h = host or os.getenv("IBKR_HOST", "127.0.0.1")
    p = int(port or os.getenv("IBKR_PORT", "7497"))
    cid = int(client_id or os.getenv("IBKR_CLIENT_ID", "1"))

    ib = IB()
    ib.connect(h, p, clientId=cid, readonly=readonly, timeout=timeout)
    if not ib.isConnected():
        raise RuntimeError(f"Failed to connect to IBKR at {h}:{p} (clientId={cid})")
    return ib


def account_summary(ib: IB) -> Dict[str, Any]:
    # Return summary as a simple dict; ib.accountValues() also exists if needed
    acct = ib.managedAccounts() or []
    return {"accounts": acct}


def positions(ib: IB) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for pos in ib.positions():
        out.append({
            "account": pos.account,
            "symbol": getattr(pos.contract, "symbol", None),
            "currency": getattr(pos.contract, "currency", None),
            "position": float(pos.position),
            "avgCost": float(pos.avgCost or 0.0),
        })
    return out


def open_orders(ib: IB) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for o in ib.openOrders():
        out.append({
            "orderId": o.orderId,
            "action": o.action,
            "totalQuantity": float(o.totalQuantity or 0.0),
            "lmtPrice": float(getattr(o, "lmtPrice", 0.0) or 0.0),
            "orderType": o.orderType,
            "tif": o.tif,
            "transmit": o.transmit,
        })
    return out


def cancel_all(ib: IB, symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    Cancel all open orders; if symbol is provided, filter by that stock.
    """
    canceled = []
    for trade in ib.openTrades():
        cont = trade.contract
        if symbol is not None and getattr(cont, "symbol", None) != symbol:
            continue
        ib.cancelOrder(trade.order)
        canceled.append({"orderId": trade.order.orderId, "symbol": getattr(cont, "symbol", None)})
    return {"canceled": canceled}


def place_market_stock(ib: IB, symbol: str, shares: float, action: str = "BUY") -> Dict[str, Any]:
    contract = Stock(symbol, "SMART", "USD")
    order = MarketOrder(action.upper(), abs(shares))
    trade = ib.placeOrder(contract, order)
    ib.sleep(1.0)
    return {"orderId": trade.order.orderId, "status": trade.orderStatus.status}


def place_limit_stock(ib: IB, symbol: str, shares: float, limit_price: float, action: str = "BUY") -> Dict[str, Any]:
    contract = Stock(symbol, "SMART", "USD")
    order = LimitOrder(action.upper(), abs(shares), float(limit_price))
    trade = ib.placeOrder(contract, order)
    ib.sleep(1.0)
    return {"orderId": trade.order.orderId, "status": trade.orderStatus.status}
