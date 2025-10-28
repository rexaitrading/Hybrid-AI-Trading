from __future__ import annotations

from typing import Any, Dict, Optional

from .brokers.factory import make_broker


class OrderManager:
    def __init__(self) -> None:
        self.broker = make_broker()

    def start(self) -> None:
        ok = self.broker.connect()
        if not ok:
            raise RuntimeError("Broker connect failed")

    def stop(self) -> None:
        self.broker.disconnect()

    def buy_market(
        self, symbol: str, qty: float, meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        oid, info = self.broker.place_order(symbol, "BUY", qty, "MARKET", meta=meta)
        out: Dict[str, Any] = {"orderId": oid}
        out.update(info)
        return out

    # NEW: sell market
    def sell_market(
        self, symbol: str, qty: float, meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        oid, info = self.broker.place_order(symbol, "SELL", qty, "MARKET", meta=meta)
        out: Dict[str, Any] = {"orderId": oid}
        out.update(info)
        return out

    # NEW: buy limit
    def buy_limit(
        self, symbol: str, qty: float, limit_price: float, meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        oid, info = self.broker.place_order(
            symbol, "BUY", qty, "LIMIT", limit_price=limit_price, meta=meta
        )
        out: Dict[str, Any] = {"orderId": oid}
        out.update(info)
        return out

    # NEW: sell limit
    def sell_limit(
        self, symbol: str, qty: float, limit_price: float, meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        oid, info = self.broker.place_order(
            symbol, "SELL", qty, "LIMIT", limit_price=limit_price, meta=meta
        )
        out: Dict[str, Any] = {"orderId": oid}
        out.update(info)
        return out

    def positions(self):
        return self.broker.positions()
