# -*- coding: utf-8 -*-
from __future__ import annotations

from hybrid_ai_trading.runtime.run_context import RunContext
from hybrid_ai_trading.execution.blockg_contract import ensure_symbol_blockg_ready
import os
import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live
from hybrid_ai_trading.execution.live_ready_stamp import require_nvda_live_stamp


# -----------------------------
# Live/paper detection + symbol
# -----------------------------
def _is_live() -> bool:
    return str(os.environ.get("HAT_IS_PAPER", "")).strip() == "0"


def _infer_symbol(contract: Any) -> Optional[str]:
    # Best-effort: supports ib_insync Contract-like objects + stubs used in tests.
    for attr in ("symbol", "localSymbol"):
        try:
            v = getattr(contract, attr, None)
            if v:
                return str(v).upper()
        except Exception:
            pass
    return None


def ib_place_order_chokepoint(ib: Any, *args: Any, ctx: RunContext | None = None, meta: Dict[str, Any] | None = None) -> Any:
    """
    Single chokepoint for raw IB placeOrder.

    Supported call styles:
      - ib_place_order_chokepoint(ib, contract, order)                   # order_id defaults to 0
      - ib_place_order_chokepoint(ib, order_id, contract, order)         # explicit order_id

    Institutional safety:
      - If live (HAT_IS_PAPER=0) and symbol is NVDA/SPY/QQQ, enforce Block-G readiness (fail-closed).
    """
    # Parse args once
    if len(args) == 2:
        contract, order = args
        order_id = 0
    elif len(args) >= 3:
        order_id, contract, order = args[0], args[1], args[2]
    else:
        raise TypeError(f"ib_place_order_chokepoint expected 2 or 3 args after ib, got {len(args)}")

    # Infer symbol once
    sym = None
    try:
        sym = str(getattr(contract, "symbol", "") or "").upper().strip()
    except Exception:
        sym = None
    if (not sym) and isinstance(meta, dict):
        try:
            sym = str(meta.get("symbol", "") or "").upper().strip()
        except Exception:
            sym = None

    # Enforce Block-G (single gate)
    if _is_live():
        if sym in ("NVDA", "SPY", "QQQ"):
            require_nvda_live_stamp(sym)
            require_blockg_ready_for_live(sym)

    # Place order
    try:
        return ib.placeOrder(order_id, contract, order)
    except TypeError:
        return ib.placeOrder(contract, order)
def retry(
    exc_types: Union[Type[BaseException], Tuple[Type[BaseException], ...]],
    attempts: int = 3,
    backoff: float = 0.25,
    jitter: float = 0.05,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator: retry function call on specified exceptions.
    Deterministic enough for tests when backoff/jitter are set to 0.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(*a: Any, **k: Any) -> Any:
            for i in range(attempts):
                try:
                    return fn(*a, **k)
                except exc_types:  # type: ignore[misc]
                    if i == attempts - 1:
                        raise
                    delay = float(backoff) * (2**i)
                    if jitter:
                        delay += random.random() * float(jitter)
                    if delay > 0:
                        time.sleep(delay)
            raise RuntimeError("unreachable")

        return wrapped

    return deco


# -----------------------------
# IB connection (injectable)
# -----------------------------
def connect_ib(
    host: str,
    port: int,
    client_id: int,
    timeout: float,
    *,
    attempts: int = 3,
    backoff: float = 0.25,
    jitter: float = 0.0,
    ib_factory: Optional[Callable[[], Any]] = None,
) -> Any:
    """
    Connect to IB using an injected factory in tests.
    IMPORTANT: reuse the SAME ib instance across retries (stubs track calls on self).
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    if ib_factory is None:
        from ib_insync import IB  # type: ignore
        ib_factory = IB

    ib = ib_factory()
    last: Optional[BaseException] = None

    for i in range(attempts):
        try:
            ib.connect(host, port, clientId=client_id, timeout=timeout)
            if not getattr(ib, "isConnected", lambda: True)():
                raise ConnectionError("IB not connected after connect()")
            return ib
        except Exception as e:
            last = e
            if i == attempts - 1:
                raise
            delay = float(backoff) * (2 ** i)
            if jitter:
                delay += random.random() * float(jitter)
            if delay > 0:
                time.sleep(delay)

    assert last is not None
    raise last


def account_snapshot(ib: Any, account: str, *, wait_sec: float = 0.25) -> List[AccountTag]:
    # ask IB to publish account values (stub-safe)
    if hasattr(ib, "client") and hasattr(ib.client, "reqAccountUpdates"):
        try:
            ib.client.reqAccountUpdates(True, account)
        except Exception:
            pass

    if hasattr(ib, "waitOnUpdate"):
        try:
            ib.waitOnUpdate(timeout=wait_sec)
        except Exception:
            pass

    wanted = {"NetLiquidation", "TotalCashValue", "BuyingPower", "AvailableFunds"}
    out: List[AccountTag] = []
    for v in getattr(ib, "accountValues", lambda: [])():
        try:
            tag = str(v.tag)
            if tag in wanted:
                out.append((tag, str(v.value), str(v.currency)))
        except Exception:
            continue
    return out


def force_refresh_positions(ib: Any, *, settle_sec: float = 0.25) -> List[Any]:
    if hasattr(ib, "client") and hasattr(ib.client, "reqPositions"):
        try:
            ib.client.reqPositions()
        except Exception:
            pass

    if hasattr(ib, "waitOnUpdate"):
        try:
            ib.waitOnUpdate(timeout=settle_sec)
        except Exception:
            pass

    return list(getattr(ib, "positions", lambda: [])())


# -----------------------------
# Cancel open orders (bounded)
# -----------------------------
def cancel_all_open(ib: Any, *, settle_sec: float = 1.0) -> None:
    opens = list(getattr(ib, "openTrades", lambda: [])())
    for tr in opens:
        try:
            if getattr(tr, "isActive", lambda: False)():
                ib.cancelOrder(tr.order)
        except Exception:
            continue
    if settle_sec and settle_sec > 0:
        time.sleep(0)


# -----------------------------
# Marketable limit helper
# -----------------------------
def marketable_limit(side: str, ref_price: float, after_hours: bool) -> float:
    if ref_price <= 0:
        raise ValueError("ref_price must be > 0")
    s = side.strip().upper()
    if s not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    bump = 1.0 if after_hours else 0.1
    return float(ref_price + bump) if s == "BUY" else float(ref_price - bump)


# -----------------------------
# Error mapping (string-based)
# -----------------------------
def map_ib_error(err: BaseException) -> str:
    msg = str(err).lower()

    if "connection reset" in msg:
        return "ECONNRESET"
    if "not connected" in msg:
        return "NOT_CONNECTED"
    if "timed out" in msg or "timeout" in msg:
        return "TIMEOUT"
    if "access is denied" in msg or "permission" in msg:
        return "ACCESS_DENIED"
    if "rejected" in msg:
        return "ORDER_REJECTED"
    if "unreachable" in msg:
        return "HOST_UNREACHABLE"
    return "UNKNOWN"

