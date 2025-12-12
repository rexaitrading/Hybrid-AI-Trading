from __future__ import annotations
from hybrid_ai_trading.execution.blockg_contract_reader import assert_symbol_ready

from typing import Any, Dict, List, Optional, Tuple

from .base import Broker

try:
    from ib_insync import IB, LimitOrder, MarketOrder, Stock
except Exception as e:  # pragma: no cover
    IB = None
    _import_error = e
else:
    _import_error = None


class IBAdapter(Broker):
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4002,
        client_id: int = 201,
        timeout: int = 15,
    ):
        if _import_error:
            raise RuntimeError(f"ib_insync not available: {_import_error!r}")
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self.ib = IB()

    def connect(self) -> bool:
        ok = self.ib.connect(
            self.host, self.port, clientId=self.client_id, timeout=self.timeout
        )
        return bool(ok)

    def disconnect(self) -> None:
        try:
            self.ib.disconnect()
        except Exception:
            pass

    def server_time(self) -> Optional[str]:
        try:
            return str(self.ib.serverTime())
        except Exception:
            return None

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        contract = Stock(symbol, "SMART", "USD")
        if order_type.upper() == "LIMIT":
            if limit_price is None:
                raise ValueError("limit_price required for LIMIT orders")
            order = LimitOrder(side.upper(), qty, limit_price)
        else:
            order = MarketOrder(side.upper(), qty)
        # --- HARD BLOCK-G ENFORCEMENT (last-mile) ---
        # No live NVDA order may reach IBKR unless contract says READY.
        try:
            # 'symbol' may not be in scope; prefer contract symbol if available.
            _sym = (locals().get("symbol") or "").upper()
            _c = locals().get("c", None) or locals().get("contract", None)
            if (getattr(_c, "symbol", None) or "").upper() == "NVDA" or _sym == "NVDA":
                assert_symbol_ready("NVDA")
        except Exception as _exc:
            raise
        
        trade = self.ib.placeOrder(contract, order)
        # Give IB a moment to populate status in async loop
        self.ib.sleep(0.1)
        st = trade.orderStatus
        meta_out = {
            "status": st.status,
            "filled": float(st.filled or 0),
            "avgPrice": float(getattr(st, "avgFillPrice", 0.0) or 0.0),
            "meta": meta or {},
        }
        return trade.order.orderId, meta_out

    def open_orders(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for oo in self.ib.openTrades():
            st = oo.orderStatus
            out.append(
                {
                    "orderId": oo.order.orderId,
                    "symbol": getattr(oo.contract, "symbol", None),
                    "side": oo.order.action,
                    "qty": float(oo.order.totalQuantity or 0),
                    "status": st.status,
                }
            )
        return out

    def positions(self) -> List[Dict[str, Any]]:
        pos = []
        for p in self.ib.positions():
            pos.append(
                {
                    "symbol": getattr(p.contract, "symbol", None),
                    "position": float(p.position or 0),
                    "avgCost": float(p.avgCost or 0.0),
                }
            )
        return pos
