from __future__ import annotations

def ensure_symbol_blockg_ready(symbol: str) -> None:
    """
    Back-compat shim for tests: canonical Block-G contract-only check.
    """
    from hybrid_ai_trading.execution.blockg_contract_reader import assert_symbol_ready
    assert_symbol_ready(str(symbol))
from hybrid_ai_trading.runtime.context_loader import load_run_context_from_env
from hybrid_ai_trading.runtime.context_loader import is_live_env
from hybrid_ai_trading.execution.blockg_contract import ensure_symbol_blockg_ready

def _is_live_mode() -> bool:
    """
    Unified LIVE-mode check via RunContext (single authority).
    Preserves operator override: IBKR_LIVE=1.
    """
    import os
    if os.getenv("IBKR_LIVE", "0") == "1":
        return True
    return bool(load_run_context_from_env().is_live)

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
                        # --- HARD BLOCK-G ENFORCEMENT (early, fail-closed) ---
        # Rules:
        #   - LIVE mode: enforce NVDA Block-G
        #   - Contract override set (BLOCKG_CONTRACT_PATH): enforce NVDA Block-G (test last-mile)
        import os as _os
        _force_contract = bool((_os.getenv("BLOCKG_CONTRACT_PATH", "") or "").strip())
        if (symbol or "").strip().upper() == "NVDA" and (_is_live_mode() or _force_contract):
            try:
                ensure_symbol_blockg_ready("NVDA")
            except Exception as _exc:
                raise RuntimeError(f"[BLOCK-G] NVDA not ready: {_exc}")

        if order_type.upper() == "LIMIT":
            if limit_price is None:
                raise ValueError("limit_price required for LIMIT orders")
            order = LimitOrder(side.upper(), qty, limit_price)
        else:
            order = MarketOrder(side.upper(), qty)
                        # --- HARD BLOCK-G ENFORCEMENT (last-mile) ---
        import os as _os2
        _force_contract2 = bool((_os2.getenv("BLOCKG_CONTRACT_PATH", "") or "").strip())
        if (symbol or "").strip().upper() == "NVDA" and (_is_live_mode() or _force_contract2):
            try:
                ensure_symbol_blockg_ready("NVDA")
            except Exception as _exc:
                raise RuntimeError(f"[BLOCK-G] NVDA not ready: {_exc}")

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
