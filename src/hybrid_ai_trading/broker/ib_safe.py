# -*- coding: utf-8 -*-
from __future__ import annotations

from hybrid_ai_trading.runtime.run_context import RunContext
import os
import json
import subprocess
import random
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from pathlib import Path

from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live
from hybrid_ai_trading.execution.blockg_ps_checker import require_blockg_ready_via_powershell
from hybrid_ai_trading.execution.portfolio_enforce import require_portfolio_gate_for_live
from hybrid_ai_trading.execution.live_ready_stamp import require_nvda_live_stamp
from hybrid_ai_trading.execution.live_arm import require_live_arm


# -----------------------------
# Live/paper detection + symbol
# -----------------------------
# A1_PAPERLIVE_LIVELIKE_V3_BEGIN
def _is_live_like_mode(mode: str) -> bool:
    m = (mode or "").upper().strip()
    return m in ("LIVE", "PAPERLIVE")
# A1_PAPERLIVE_LIVELIKE_V3_END
def _is_live(ctx: RunContext | None = None) -> bool:
    # A3: ctx is authoritative; env is fallback.
    try:
        if ctx is not None and hasattr(ctx, "is_paper"):
            return (not bool(getattr(ctx, "is_paper")))
    except Exception:
        pass
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


def _infer_mode(ctx: RunContext | None = None) -> str:
    try:
        if ctx is not None and hasattr(ctx, "mode"):
            m = str(getattr(ctx, "mode") or "").upper().strip()
            if m:
                return m
    except Exception:
        pass
    return str(os.environ.get("HAT_MODE", "")).upper().strip() or ("LIVE" if _is_live(ctx) else "PAPER")


def _parse_utc_dt(s: str) -> datetime:
    s = (s or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _cooldown_active(repo_root: str) -> bool:
    p = Path(repo_root) / "logs" / "crisis_cooldown.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    until = _parse_utc_dt(str(obj.get("cooldown_until_utc", "")))
    now = datetime.now(timezone.utc)
    return now < until



# RUNCONTEXT_LIVE_SESSION_GATE_BEGIN
def _repo_root_from_ctx_or_env(ctx: RunContext | None) -> str:
    try:
        if ctx is not None and hasattr(ctx, "repo_root"):
            rr = str(getattr(ctx, "repo_root") or "").strip()
            if rr:
                return rr
    except Exception:
        pass
    rr = str(os.environ.get("HAT_REPO_ROOT", "")).strip()
    return rr or os.getcwd()

def _ps_exe() -> str:
    w = os.environ.get("WINDIR", r"C:\Windows")
    return str(Path(w) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")

def _runctx_from_ps(market: str, symbol: str, as_of_date: str | None = None) -> Dict[str, Any]:
    repo_root = _repo_root_from_ctx_or_env(None)
    rc = Path(repo_root) / "tools" / "Resolve-RunContext.ps1"
    if not rc.exists():
        raise RuntimeError(f"RUNCONTEXT FAIL-CLOSED: missing {rc}")

    args = [
        _ps_exe(),
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(rc),
        "-Market", str(market).upper().strip(),
        "-Symbol", str(symbol).upper().strip(),
    ]
    if as_of_date and str(as_of_date).strip():
        args += ["-AsOfDate", str(as_of_date).strip()]

    cp = subprocess.run(args, cwd=str(Path(repo_root)), capture_output=True, text=True)
    out = (cp.stdout or "").strip()
    if cp.returncode != 0:
        raise RuntimeError(f"RUNCONTEXT FAIL-CLOSED: rc={cp.returncode} stderr={(cp.stderr or '').strip()[:300]}")

    i0 = out.find("{")
    i1 = out.rfind("}")
    if i0 < 0 or i1 <= i0:
        raise RuntimeError(f"RUNCONTEXT FAIL-CLOSED: non-json stdout head={out[:120]!r}")

    return json.loads(out[i0 : i1 + 1])

def _enforce_live_session_gate(ctx: RunContext | None, meta: Dict[str, Any] | None, sym: str | None) -> None:
    # Enforce for LIVE and PAPERLIVE (PAPER remains exempt).
    mode = _infer_mode(ctx)
    if not _is_live_like_mode(mode):
        return

    # Prefer ctx truth if available
    market_closed = None
    session_name = None
    try:
        if ctx is not None:
            if hasattr(ctx, "market_closed_today"):
                market_closed = bool(getattr(ctx, "market_closed_today"))
            if hasattr(ctx, "session_name"):
                session_name = str(getattr(ctx, "session_name") or "").strip().upper()
    except Exception:
        market_closed = None
        session_name = None

    # Hydrate if missing
    if market_closed is None or not session_name:
        mkt = "US"
        as_of = None
        try:
            if ctx is not None and hasattr(ctx, "market"):
                mkt = str(getattr(ctx, "market") or mkt).strip().upper()
        except Exception:
            pass
        try:
            if meta and isinstance(meta, dict):
                mkt = str(meta.get("market") or mkt).strip().upper()
                as_of = meta.get("as_of_date") or meta.get("asOfDate") or None
        except Exception:
            pass
        use_sym = (sym or "")
        try:
            if (not use_sym) and meta and isinstance(meta, dict):
                use_sym = str(meta.get("symbol") or "").strip().upper()
        except Exception:
            pass
        if not use_sym:
            use_sym = "ALL"

        rc = _runctx_from_ps(market=mkt, symbol=use_sym, as_of_date=str(as_of) if as_of else None)
        market_closed = bool(rc.get("market_closed_today", True))
        session_name = str(rc.get("session_name", "CLOSED")).strip().upper()

    # Fail-closed
    if bool(market_closed):
        raise RuntimeError("LIVE BLOCKED: market_closed_today=true (RunContext)")
    if str(session_name).upper() != "RTH":
        raise RuntimeError(f"LIVE BLOCKED: session_name={session_name} (RunContext)")
# RUNCONTEXT_LIVE_SESSION_GATE_END
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
    mode = _infer_mode(ctx)
    _enforce_live_session_gate(ctx, meta, sym)
    # Enforce Block-G + live gates (fail-closed)
    if _is_live_like_mode(mode):
        # CrashMode cooldown deny (defense-in-depth). Fail-closed for LIVE/PAPERLIVE.
        # Allow risk-action callers (flatten/close) to pass a meta flag.
        allow_risk_action = False
        try:
            allow_risk_action = bool(meta.get("allow_risk_action")) if isinstance(meta, dict) else False
        except Exception:
            allow_risk_action = False

        if not allow_risk_action:
            mode = _infer_mode(ctx)
            if mode in ("LIVE", "PAPERLIVE"):
                rr = ""
                try:
                    rr = str(getattr(ctx, "repo_root", "") or "").strip() if ctx is not None else ""
                except Exception:
                    rr = ""
                if not rr:
                    rr = str(os.environ.get("HAT_REPO_ROOT", "")).strip() or os.getcwd()

                try:
                    if _cooldown_active(rr):
                        raise RuntimeError("CRASHMODE_DENY: cooldown active (crisis_cooldown.json)")
                except Exception as e:
                    raise RuntimeError(f"CRASHMODE_DENY: cooldown state unreadable -> fail-closed: {e!r}")
        if sym in ("NVDA", "SPY", "QQQ"):
            # System readiness first (Block-G) so tests can assert correct chokepoint behavior
            mk = None
            try:
                mk = str(getattr(ctx, "market", "")).upper().strip() if ctx is not None else None
            except Exception:
                mk = None
            require_blockg_ready_via_powershell(sym, market=mk, build=False)
            require_nvda_live_stamp(sym)
            # Phase-7 portfolio guard (fail-closed). Applies to NVDA/SPY/QQQ in LIVE mode.
            require_portfolio_gate_for_live(sym)

        # Operator intent last (2-key arm token)
        require_live_arm(sym)# LIVE_2KEY_ARM_AND_BLOCKG_PS_BEGIN
    # PS checker is the single semantic owner for LIVE (fail-closed).
    # LIVE_2KEY_ARM_AND_BLOCKG_PS_END

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
