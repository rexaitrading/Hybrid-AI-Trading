from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple

class FakeIB:
    def __init__(self):
        self._connected = False
        self._orders: List[Dict[str, Any]] = []
        self._positions: Dict[str, float] = {}

    # Broker-like surface
    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def server_time(self) -> Optional[str]:
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str="MARKET",
        limit_price: Optional[float]=None,
        meta: Optional[Dict[str, Any]]=None,
    ) -> Tuple[int, Dict[str, Any]]:
        oid = len(self._orders) + 1
        status = "Filled" if order_type.upper() == "MARKET" else "Submitted"
        self._orders.append({
            "orderId": oid, "symbol": symbol, "side": side.upper(),
            "qty": float(qty), "type": order_type.upper(), "status": status
        })
        delta = qty if side.upper() == "BUY" else -qty
        self._positions[symbol] = self._positions.get(symbol, 0.0) + float(delta)
        return oid, {"status": status, "filled": float(qty if status == "Filled" else 0), "avgPrice": 0.0, "meta": meta or {}}

    def open_orders(self) -> List[Dict[str, Any]]:
        return list(self._orders)

    def positions(self) -> List[Dict[str, Any]]:
        return [{"symbol": s, "position": q} for s, q in self._positions.items()]