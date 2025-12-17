from hybrid_ai_trading.runtime.context_loader import load_run_context_from_env
from hybrid_ai_trading.runtime.context_loader import is_live_env
from hybrid_ai_trading.blockg_contract import require_blockg_ready
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

        self.run_context = load_run_context_from_env()
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
                    d = require_blockg_ready("NVDA")
                    if not d.ready:
                        raise RuntimeError(f"BLOCK-G FAIL: {d.reason} as_of_date={d.as_of_date}")
        except Exception as _exc:
            raise
        
        from hybrid_ai_trading.runtime.live_boundary import forbid_direct_ib_live
        forbid_direct_ib_live("broker/ib_safe.py:direct_send")
        # --- Block-G LIVE no-bypass (last-mile) ---
        # If this is a live boundary, we must fail-closed unless RunContext says OK.
        ctx = kwargs.get("run_context", None)
        if ctx is None:
            ctx = getattr(self, "run_context", None)

        # Heuristic: treat meta/regime hint as live if present; otherwise trust ctx if it exists.
        regime = ""
        try:
            meta = kwargs.get("meta", None) or {}
            regime = str(meta.get("regime", "") or "")
        except Exception:
            regime = ""

        is_live_hint = ("LIVE" in regime.upper())

        if ctx is not None:
            # Canonical: RunContext is the single authority
            if is_live_hint:
                try:
                    ctx.require_live_safe(symbol=symbol)
                except TypeError:
                    ctx.require_live_safe()
        else:
            # No RunContext available: fail-closed if caller hints LIVE
            if is_live_hint:
                raise RuntimeError("BLOCK-G: missing RunContext on LIVE order path (fail-closed)")
        # --- end Block-G LIVE no-bypass ---
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
from typing import Any, Dict, List, Optional, Tuple

from .base import Broker

try:
    from ib_insync import IB, LimitOrder, MarketOrder, Stock
except Exception as e:  # pragma: no cover
    IB = None
    _import_error = e
else:
    _import_error = None



def account_snapshot(ib, account: str, wait_sec: float = 0.25):
    """
    Minimal, test-driven helper: returns list[(tag, value, currency)] from ib.accountValues().
    Works with ib_insync-like objects and the test stubs.
    """
    # Best-effort request to populate values (stubs provide .client)
    try:
        client = getattr(ib, "client", None)
        if client is not None and hasattr(client, "reqAccountUpdates"):
            client.reqAccountUpdates(True, account)
    except Exception:
        pass

    # give IB time to update (stubs implement waitOnUpdate)
    try:
        if hasattr(ib, "waitOnUpdate"):
            ib.waitOnUpdate(timeout=float(wait_sec))
    except Exception:
        pass

    wanted = {"NetLiquidation", "TotalCashValue", "BuyingPower", "AvailableFunds"}
    out = []
    for v in (ib.accountValues() if hasattr(ib, "accountValues") else []):
        try:
            tag = getattr(v, "tag", None)
            if tag in wanted:
                out.append((tag, getattr(v, "value", None), getattr(v, "currency", None)))
        except Exception:
            continue
    return out

def marketable_limit(side: str, ref: float, ah: bool) -> float:
    """
    Test-driven marketable limit:
      - ref must be > 0
      - side must be BUY or SELL
      - if ah (after-hours) : +/- 1.0
      - else: +/- 0.1
    """
    ref = float(ref)
    if ref <= 0.0:
        raise ValueError("ref must be > 0")

    side_u = str(side or "").strip().upper()
    if side_u not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    bump = 1.0 if bool(ah) else 0.1
    return (ref + bump) if side_u == "BUY" else (ref - bump)

def cancel_all_open(ib, settle_sec: float = 1.0) -> int:
    """
    Cancel active open trades (bounded).
    Returns number of cancel attempts.
    Works with ib_insync-like objects and the test stubs.
    """
    n = 0
    trades = []
    try:
        trades = list(ib.openTrades()) if hasattr(ib, "openTrades") else []
    except Exception:
        trades = []

    for t in trades:
        try:
            is_active = t.isActive() if hasattr(t, "isActive") else False
            if not is_active:
                continue
            order = getattr(t, "order", None)
            ib.cancelOrder(order)
            n += 1
        except Exception:
            continue

    # Best-effort settle wait (tests use stub flipping active flag)
    try:
        if hasattr(ib, "waitOnUpdate"):
            ib.waitOnUpdate(timeout=float(settle_sec))
    except Exception:
        pass
    return n

def force_refresh_positions(ib, settle_sec: float = 1.0):
    """
    Best-effort refresh positions and return list.
    Works with ib_insync-like objects and the test stubs.
    """
    try:
        client = getattr(ib, "client", None)
        if client is not None and hasattr(client, "reqPositions"):
            client.reqPositions()
    except Exception:
        pass

    try:
        if hasattr(ib, "waitOnUpdate"):
            ib.waitOnUpdate(timeout=float(settle_sec))
    except Exception:
        pass

    try:
        return list(ib.positions()) if hasattr(ib, "positions") else []
    except Exception:
        return []

def retry(exc_types, attempts: int = 3, backoff: float = 0.5, jitter: float = 0.0):
    """
    Minimal retry decorator used by tests.
    - exc_types: tuple of exception classes
    - attempts: number of tries
    - backoff: seconds sleep between tries (multiplied by attempt index)
    - jitter: optional random extra (0 disables)
    """
    def deco(fn):
        def wrapper(*args, **kwargs):
            import time
            import random

            last = None
            n = int(attempts)
            if n < 1:
                n = 1
            for i in range(n):
                try:
                    return fn(*args, **kwargs)
                except exc_types as e:
                    last = e
                    if i == n - 1:
                        raise
                    delay = float(backoff) * (i + 1)
                    if float(jitter) > 0.0:
                        delay += random.random() * float(jitter)
                    if delay > 0.0:
                        time.sleep(delay)
            raise last  # pragma: no cover
        return wrapper
    return deco

def connect_ib(host: str, port: int, clientId: int, timeout: float,
               attempts: int = 3, backoff: float = 0.5, jitter: float = 0.0,
               ib_factory=None):
    """
    Test-driven IB connect helper with retries.
    IMPORTANT: reuse the same IB instance across retries (tests expect call counter increments).
    """
    if ib_factory is None:
        try:
            from ib_insync import IB  # type: ignore
            ib_factory = IB
        except Exception:
            raise RuntimeError("ib_factory required when ib_insync is not available")

    import time
    import random

    ib = ib_factory()  # <-- reuse across retries

    n = int(attempts)
    if n < 1:
        n = 1

    last = None
    for i in range(n):
        try:
            ib.connect(host, int(port), int(clientId), float(timeout))
            if hasattr(ib, "isConnected") and not ib.isConnected():
                raise ConnectionError("Not connected")
            return ib
        except Exception as e:
            last = e
            if i == n - 1:
                raise
            delay = float(backoff) * (i + 1)
            if float(jitter) > 0.0:
                delay += random.random() * float(jitter)
            if delay > 0.0:
                time.sleep(delay)

    raise last  # pragma: no cover
def map_ib_error(err: Exception) -> str:
    msg = str(err or "")
    m = msg.lower()

    if "connection reset" in m or "reset by peer" in m:
        return "ECONNRESET"
    if "not connected" in m:
        return "NOT_CONNECTED"
    if "timed out" in m or "timeout" in m:
        return "TIMEOUT"
    if "access is denied" in m or "access denied" in m:
        return "ACCESS_DENIED"
    if "order rejected" in m or "rejected" in m:
        return "ORDER_REJECTED"
    if "host unreachable" in m or "unreachable" in m:
        return "HOST_UNREACHABLE"
    return "UNKNOWN"


