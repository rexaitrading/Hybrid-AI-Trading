from __future__ import annotations
import math

"""
IBClient (Hybrid AI Quant Pro Ã¢â‚¬â€œ minimal, safe wrapper)
- Env-driven connect (defaults to TWS paper: localhost:7497)
- Clean timeouts/retries
- Account summary helper
- Real-time equity entitlement probe (captures 10089)
- What-If order helper (no execution)
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ib_insync import IB, MarketOrder, Stock


# ---------------------------
# Config
# ---------------------------
@dataclass
class IBConfig:
    host: str = os.getenv("IB_GATEWAY_HOST", "localhost")
    port: int = int(os.getenv("IB_GATEWAY_PORT", "7497"))  # TWS paper by default
    client_id: int = int(os.getenv("IB_CLIENT_ID", "301"))
    connect_timeout_s: float = float(os.getenv("IB_CONNECT_TIMEOUT", "15"))
    request_timeout_s: float = float(os.getenv("IB_REQUEST_TIMEOUT", "20"))


class IBClient:
    def __init__(self, cfg: Optional[IBConfig] = None) -> None:
        self.cfg = cfg or IBConfig()
        self.ib = IB()
        # Give handshake calls some breathing room
        self.ib.RequestTimeout = self.cfg.request_timeout_s

    # ---------- Lifecycle ----------
    def connect(self) -> IB:
        self.ib.connect(
            self.cfg.host,
            self.cfg.port,
            clientId=self.cfg.client_id,
            timeout=self.cfg.connect_timeout_s,
        )
        if not self.ib.isConnected():
            raise RuntimeError("IB connect() returned, but isConnected() is False")
        return self.ib

    def disconnect(self) -> None:
        try:
            self.ib.disconnect()
        except Exception:
            pass

    @contextmanager
    def session(self):
        try:
            self.connect()
            yield self
        finally:
            self.disconnect()

    # ---------- Convenience ----------
    def server_info(self) -> Tuple[int, str]:
        return (self.ib.client.serverVersion(), str(self.ib.reqCurrentTime()))

    def account_summary(self) -> Dict[str, Tuple[str, str]]:
        """Returns {tag: (value, currency)} for common tags."""
        wanted = {"TotalCashValue", "BuyingPower", "NetLiquidation"}
        out: Dict[str, Tuple[str, str]] = {}
        for e in self.ib.accountSummary():
            if e.tag in wanted:
                out[e.tag] = (e.value, e.currency)
        return out

    def ensure_realtime_equity_entitlement(
        self, symbol: str = "AAPL"
    ) -> Tuple[bool, List[Tuple[int, str]]]:
        """
        Try a real-time snapshot; capture 10089 (missing subscription) if it fires.
        Returns (ok, errors), where ok=True means snapshot looked good.
        """
        errors: List[Tuple[int, str]] = []

        def on_err(req_id, code, msg, *_):
            errors.append((int(code), str(msg)))

        # Subscribe temporary error hook
        self.ib.errorEvent += on_err  # type: ignore[attr-defined]
        try:
            self.ib.reqMarketDataType(1)  # 1 = real-time
            t = self.ib.reqMktData(Stock(symbol, "SMART", "USD"), "", snapshot=True)
            self.ib.sleep(2.0)  # allow a moment for the snapshot
            ok = (t is not None) and (
                t.bid is not None or t.last is not None or t.ask is not None
            )
            return ok, errors
        finally:
            # Unsubscribe hook
            try:
                self.ib.errorEvent -= on_err  # type: ignore[attr-defined]
            except Exception:
                pass

    def what_if_market_buy(self, symbol: str, quantity: int = 1) -> Dict[str, str]:
        """Safe what-if (no execution)."""
        c = Stock(symbol, "SMART", "USD")
        o = MarketOrder("BUY", quantity)
        st = self.ib.whatIfOrder(c, o)
        return {
            "status": st.status,
            "initBefore": str(st.initMarginBefore),
            "initChange": str(st.initMarginChange),
            "initAfter": str(st.initMarginAfter),
            "commission": str(st.commission),
        }
def get_last_prices(symbols, client_id: int = 3021, host: str = "127.0.0.1", port: int = 4002, wait_sec: float = 2.0):
    """
    Paper-safe snapshot prices using IBKR via ib_insync reqMktData(snapshot=True).
    Returns dict {SYM: float_price}. Fail-closed if any symbol missing.
    """
    # Local import to avoid hard dependency at module import time for non-IB paths
    from ib_insync import IB, Stock  # type: ignore

    ib = IB()
    import time as _time
    # Suppress ib_insync console spam for error 10089 (no subscription)
    _orig_err = getattr(ib.wrapper, "error", None)
    def _err(reqId, errorCode, errorString, contract=None):
        try:
            if int(errorCode) == 10089:
                return
        except Exception:
            pass
        if _orig_err is not None:
            return _orig_err(reqId, errorCode, errorString, contract)
    try:
        ib.wrapper.error = _err
    except Exception:
        pass

    
    # Mute IB market-data subscription spam (10089) for this snapshot helper
    def _on_err(reqId, errorCode, errorString, *_):
        try:
            if int(errorCode) == 10089:
                return
        except Exception:
            pass
        # allow other errors to surface normally
        return
    try:
        ib.errorEvent += _on_err  # type: ignore[attr-defined]
    except Exception:
        pass
    
    import os as _os
    try:
      import os as _os
      # Always use a unique clientId for snapshot helper to avoid collisions
      _cid = 30000 + (_os.getpid() % 10000)
      ib.connect(host, port, clientId=int(_cid))
    except Exception:
      # Fallback to a unique clientId (avoids Error 326 client id already in use)
      _cid = 30000 + (_os.getpid() % 10000)
      ib.connect(host, port, clientId=int(_cid))
    try:
      out = {}
      for sym in symbols:
        c = Stock(str(sym), "SMART", "USD")
        ib.reqMarketDataType(3)  # 3=delayed (reduces 10089 spam)
        t = ib.reqMktData(c, "", snapshot=True)
        _time.sleep(float(wait_sec))
        px = None

        # Prefer last; then close; then marketPrice
        if hasattr(t, "last") and t.last is not None:
          px = t.last
        elif hasattr(t, "close") and t.close is not None:
          px = t.close
        elif hasattr(t, "marketPrice"):
          try:
            mp = t.marketPrice()
            if mp is not None:
              px = mp
          except Exception:
            pass

        if px is None:
          raise RuntimeError(f"ib_snapshot_missing_price: {sym}")
        out[str(sym).upper()] = float(px)
      return out
    finally:
      try:
        if _orig_err is not None:
          ib.wrapper.error = _orig_err
      except Exception:
        pass
      try:
        ib.errorEvent -= _on_err  # type: ignore[attr-defined]
      except Exception:
        pass
      try:
        ib.disconnect()
      except Exception:
        pass