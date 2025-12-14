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
                if _is_live_mode():
                    ensure_symbol_blockg_ready("NVDA")
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
def marketable_limit(side: str, ref: float, after_hours: bool) -> float:
    """Return a marketable limit price around a reference price.

    Rules (tests):
      - side must be BUY or SELL (case-insensitive) else ValueError
      - ref must be > 0 else ValueError
      - AH True : BUY=ref*1.01, SELL=ref*0.99
      - AH False: BUY=ref*1.001, SELL=ref*0.999
    """
    s = str(side).upper().strip()
    if s not in ("BUY", "SELL"):
        raise ValueError("invalid side")
    try:
        r = float(ref)
    except Exception:
        raise ValueError("invalid ref")
    if r <= 0.0:
        raise ValueError("invalid ref")
    if bool(after_hours):
        return r * (1.01 if s == "BUY" else 0.99)
    return r * (1.001 if s == "BUY" else 0.999)

def account_snapshot(
    account: str | None = None,
    net_liquidation: float | None = None,
    available_funds: float | None = None,
    buying_power: float | None = None,
    daily_pnl: float | None = None,
) -> dict:
    """
    Pure helper used by tests: returns a normalized account snapshot dict.
    """
    def _f(x):
        try:
            return float(x) if x is not None else None
        except Exception:
            return None

    return {
        "account": (account or "").strip(),
        "net_liquidation": _f(net_liquidation),
        "available_funds": _f(available_funds),
        "buying_power": _f(buying_power),
        "daily_pnl": _f(daily_pnl),
    }
def cancel_all_open(broker: object, orders: list | None = None) -> int:
    """
    Cancel open orders in a broker-safe way.

    - broker: object with cancel_order(order_id) OR cancel_order(order_id=...)
    - orders: optional list of orders (dict-like or objects) containing id/order_id fields.

    Returns number of cancel attempts performed.
    Pure/offline-safe: no network calls unless broker does them.
    """
    if broker is None:
        return 0

    # If broker exposes a native cancel_all_open_orders, use it
    fn = getattr(broker, "cancel_all_open_orders", None)
    if callable(fn):
        try:
            fn()
            return 1
        except Exception:
            return 0

    if not orders:
        return 0

    def _oid(o) -> str | None:
        if o is None:
            return None
        # dict-like
        if isinstance(o, dict):
            for k in ("order_id", "id", "permId"):
                v = o.get(k)
                if v is not None:
                    return str(v)
            return None
        # object-like
        for k in ("order_id", "id", "permId"):
            if hasattr(o, k):
                v = getattr(o, k)
                if v is not None:
                    return str(v)
        return None

    cancels = 0
    for o in orders:
        oid = _oid(o)
        if not oid:
            continue
        try:
            cfn = getattr(broker, "cancel_order", None)
            if callable(cfn):
                # Support both cancel_order(order_id) and cancel_order(order_id=...)
                try:
                    cfn(oid)
                except TypeError:
                    cfn(order_id=oid)
                cancels += 1
        except Exception:
            continue

    return cancels
# ============================================================
# === TEST API (locked to test_ib_safe_* expectations) =======
# ============================================================

import time
from functools import wraps


def retry(exc_types, attempts=3, backoff=1.0, jitter=0.0):
    """
    Retry decorator used by tests.
    """
    def deco(fn):
        @wraps(fn)
        def wrapped(*a, **k):
            last = None
            for i in range(attempts):
                try:
                    return fn(*a, **k)
                except exc_types as e:
                    last = e
                    if i < attempts - 1:
                        time.sleep(backoff + jitter)
            raise last
        return wrapped
    return deco


def connect_ib(host, port, client_id, timeout,
               attempts=3, backoff=1.0, ib_factory=None):
    """
    Retry IB connection using injected factory.
    """
    if ib_factory is None:
        raise RuntimeError("ib_factory is required for safe connect")

    ib = ib_factory()
    for i in range(attempts):
        try:
            ib.connect(host, port, client_id, timeout)
            if ib.isConnected():
                return ib
        except Exception:
            if i >= attempts - 1:
                raise
            time.sleep(backoff)
    raise RuntimeError("Unable to connect to IB")


def account_snapshot(ib, account, wait_sec=1.0):
    """
    Return list of (tag,value,currency) from accountValues().
    """
    ib.client.reqAccountUpdates(True, account)
    ib.waitOnUpdate(timeout=wait_sec)

    out = []
    for v in ib.accountValues():
        out.append((v.tag, v.value, v.currency))
    return out


def cancel_all_open(ib, settle_sec=1.0):
    """
    Cancel all active open trades.
    """
    for tr in ib.openTrades():
        if tr.isActive():
            try:
                ib.cancelOrder(tr.order)
            except Exception:
                pass
    ib.waitOnUpdate(timeout=settle_sec)


def force_refresh_positions(ib, settle_sec=1.0):
    """
    Refresh and return positions list.
    """
    ib.client.reqPositions()
    ib.waitOnUpdate(timeout=settle_sec)
    return list(ib.positions())


def marketable_limit(side: str, ref: float, after_hours: bool) -> float:
    """Return a marketable limit price around a reference price (test contract).

    - side must be BUY or SELL (case-insensitive) else ValueError
    - ref must be > 0 else ValueError
    - after_hours True : BUY=ref*1.01, SELL=ref*0.99
    - after_hours False: BUY=ref*1.001, SELL=ref*0.999
    """
    s = str(side).upper().strip()
    if s not in ("BUY", "SELL"):
        raise ValueError("invalid side")
    try:
        r = float(ref)
    except Exception:
        raise ValueError("invalid ref")
    if r <= 0.0:
        raise ValueError("invalid ref")
    if bool(after_hours):
        return r * (1.01 if s == "BUY" else 0.99)
    return r * (1.001 if s == "BUY" else 0.999)

def map_ib_error(err: Exception) -> str:
    """
    Map IB error messages to codes.
    """
    msg = str(err).lower()

    if "connection reset" in msg:
        return "ECONNRESET"
    if "not connected" in msg:
        return "NOT_CONNECTED"
    if "timed out" in msg:
        return "TIMEOUT"
    if "denied" in msg:
        return "ACCESS_DENIED"
    if "rejected" in msg:
        return "ORDER_REJECTED"
    if "unreachable" in msg:
        return "HOST_UNREACHABLE"
    return "UNKNOWN"
