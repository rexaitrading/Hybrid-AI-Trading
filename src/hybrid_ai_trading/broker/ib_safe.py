"""
IB utils (Phase-2, Step-1): hardened & version-proof
- retry/backoff with jitter
- robust connect() normalizing bool/object returns
- low-level account snapshot (works across ib_insync versions)
- cancel-all open orders with bounded settle
- positions force-refresh
- human error mapping (best-effort)
- marketable_limit helper
"""

import random
import time
from typing import Any, Callable, List, Optional, Tuple

try:
    from ib_insync import IB, LimitOrder, Stock  # type: ignore
except Exception:
    IB = object  # type: ignore

    class Stock:  # stubs allow import in test envs
        def __init__(self, *a, **k): ...

    class LimitOrder:
        def __init__(self, *a, **k): ...


# ----------------------------- Retry / Backoff ----------------------------- #
def retry(
    exc_types: Tuple[type, ...] = (Exception,),
    attempts: int = 3,
    backoff: float = 0.5,
    max_backoff: float = 2.0,
    jitter: float = 0.25,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Exponential backoff with jitter for transient failures."""

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last: Optional[Exception] = None
            for i in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except exc_types as e:
                    last = e
                    if i == attempts - 1:
                        raise
                    sleep_s = min(max_backoff, backoff * (2**i)) + (
                        random.random() * jitter
                    )
                    if sleep_s > 0:
                        time.sleep(sleep_s)
            raise last  # not reached

        return wrapper

    return deco


# ----------------------------- Error mapping ------------------------------- #
def map_ib_error(exc: BaseException) -> str:
    """Best-effort map to a friendly code based on message patterns."""
    s = str(exc).lower()
    code = getattr(exc, "code", None)
    if code in (1100, 1101, 1102):
        return "IB_CONNECTION_STATE"
    if "not connected" in s or "connection closed" in s:
        return "NOT_CONNECTED"
    if "timeout" in s or "timed out" in s:
        return "TIMEOUT"
    if "connection reset" in s or "econnreset" in s:
        return "ECONNRESET"
    if "permission" in s or "access is denied" in s:
        return "ACCESS_DENIED"
    if "order" in s and ("reject" in s or "cannot" in s):
        return "ORDER_REJECTED"
    if "host unreachable" in s or "no route" in s:
        return "HOST_UNREACHABLE"
    return "UNKNOWN"


# ------------------------------- Connect ----------------------------------- #
def connect_ib(
    host: str = "127.0.0.1",
    port: int = 4002,
    client_id: int = 3021,
    timeout: int = 30,
    attempts: int = 3,
    backoff: float = 0.5,
    ib_factory: Callable[[], IB] = IB,  # allows stubbing in unit tests
) -> IB:
    """Robust connect that works across ib_insync versions."""
    ib = ib_factory()

    @retry((Exception,), attempts=attempts, backoff=backoff, jitter=0.0)
    def _do_connect() -> None:
        _ = ib.connect(host, port, clientId=client_id, timeout=timeout)
        if hasattr(ib, "isConnected") and not ib.isConnected():
            raise ConnectionError("IB connect returned not connected")

    _do_connect()
    return ib


# ----------------------------- Account snapshot ---------------------------- #
def account_snapshot(
    ib: IB, acct: Optional[str] = None, wait_sec: float = 3.0
) -> List[Tuple[str, str, str]]:
    """Version-proof snapshot via low-level subscribe → accountValues."""
    if acct is None:
        ma = getattr(ib, "managedAccounts", lambda: [])() or []
        acct = ma[0] if ma else ""
    ib.client.reqAccountUpdates(True, acct)  # type: ignore[attr-defined]
    t0 = time.time()
    while time.time() - t0 < wait_sec:
        ib.waitOnUpdate(timeout=1.0)
    vals = getattr(ib, "accountValues", lambda: [])() or []
    ib.client.reqAccountUpdates(False, acct)  # type: ignore[attr-defined]
    wanted = {"NetLiquidation", "TotalCashValue", "BuyingPower", "AvailableFunds"}
    return [
        (v.tag, v.value, v.currency) for v in vals if getattr(v, "tag", "") in wanted
    ]


# ----------------------------- Cancel / Positions -------------------------- #
def cancel_all_open(ib: IB, settle_sec: int = 8) -> None:
    """Cancel all active open trades for this client, then bounded settle wait."""
    opens = getattr(ib, "openTrades", lambda: [])()
    for tr in opens:
        if tr.isActive():
            ib.cancelOrder(tr.order)
    for _ in range(max(0, settle_sec)):
        ib.waitOnUpdate(timeout=1.0)


def force_refresh_positions(ib: IB, settle_sec: int = 3):
    """Request positions to refresh ib.positions() cache across versions."""
    try:
        ib.client.reqPositions()  # type: ignore[attr-defined]
        for _ in range(max(0, settle_sec)):
            ib.waitOnUpdate(timeout=1.0)
        try:
            ib.client.cancelPositions()  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        pass
    return getattr(ib, "positions", lambda: [])() or []


# ----------------------------- Marketable limit ---------------------------- #
def marketable_limit(side: str, ref: float, afterhours: bool) -> float:
    """Compute a marketable limit around a reference price."""
    s = str(side).upper()
    if s not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")
    if ref <= 0:
        raise ValueError("ref must be > 0")
    bump = 1.01 if afterhours else 1.001
    cut = 0.99 if afterhours else 0.999
    return round(ref * (bump if s == "BUY" else cut), 2)


# ----------------------------- High-level flatten -------------------------- #
def flatten_symbol_limit(
    ib: IB,
    symbol: str,
    qty: float,
    side: str,
    afterhours: bool,
    max_wait_sec: int = 15,
    reprice_pct: float = 0.03,
) -> Tuple[str, float, float]:
    """Place a marketable LIMIT, wait bounded, reprice once if still active."""
    sym = str(symbol).upper()
    c = Stock(sym, "SMART", "USD")  # type: ignore[name-defined]
    ib.qualifyContracts(c)
    t = ib.reqMktData(c, "", False, False)
    ib.sleep(1.0)

    s = str(side).upper()
    ref = (
        (getattr(t, "ask", None) if s == "BUY" else getattr(t, "bid", None))
        or getattr(t, "close", None)
        or 200.0
    )
    lmt = marketable_limit(s, ref, afterhours)

    o = LimitOrder(s, qty, lmt)  # type: ignore[name-defined]
    o.outsideRth = True
    o.tif = "DAY"

    tr = ib.placeOrder(c, o)
    deadline = time.time() + max_wait_sec
    while time.time() < deadline and tr.isActive():
        ib.waitOnUpdate(timeout=1.0)

    if tr.isActive():
        new_ref = (
            getattr(t, "ask", None) if s == "BUY" else getattr(t, "bid", None)
        ) or ref
        o.lmtPrice = round(
            new_ref * (1 + reprice_pct) if s == "BUY" else new_ref * (1 - reprice_pct),
            2,
        )
        ib.placeOrder(c, o)
        for _ in range(8):
            ib.waitOnUpdate(timeout=1.0)

    st = tr.orderStatus
    return st.status, st.filled, st.avgFillPrice
