from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from pathlib import Path

from hybrid_ai_trading.runtime.context_loader import load_run_context_from_env
from hybrid_ai_trading.blockg_contract import require_blockg_ready
class BrokerError(Exception):
    pass


try:
    from ib_insync import IB, Crypto, Forex, LimitOrder, MarketOrder, Stock
except Exception:
    IB = Stock = Forex = Crypto = MarketOrder = LimitOrder = None  # type: ignore

try:
    import ccxt
except Exception:
    ccxt = None


class BrokerClient:
    name: str

    def submit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        limit_px: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        raise NotImplementedError


# ================= IBKR =================
class IBKRClient(BrokerClient):
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 7,
        asset_class: str = "STK",
        currency: str = "USD",
    ):
        if IB is None:
            raise BrokerError("ib_insync not installed")

        self.name = "ibkr"
        self.ib = IB()
        self.ib.connect(host, port, clientId=client_id)

        self.asset_class = asset_class
        self.currency = currency

    def _contract(self, symbol: str):
        if self.asset_class.upper() == "STK":
            return Stock(symbol, "SMART", self.currency)
        if self.asset_class.upper() == "CRYPTO":
            return Crypto(symbol, "PAXOS", self.currency)
        if self.asset_class.upper() == "FX":
            return Forex(symbol)
        raise BrokerError(f"Unsupported IBKR asset_class={self.asset_class}")

    def submit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        limit_px: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        # ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ B4: HARD LIVE SAFETY GATE
        ctx = load_run_context_from_env()
        # attach for traceability / unified context
        try:
            self.run_context = ctx
        except Exception:
            pass

        # fail-closed: prefer symbol-aware gate when available
        try:
            ctx.require_live_safe(symbol=symbol)
        except TypeError:
            ctx.require_live_safe()

        c = self._contract(symbol)
        side = side.upper()

        o = (
            MarketOrder(side, abs(qty))
            if order_type.upper() == "MARKET"
            else LimitOrder(side, abs(qty), limit_px)
        )

        # ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Block-G NVDA enforcement
        sym = getattr(c, "symbol", None)
        if sym and str(sym).upper() == "NVDA" and ctx.is_live:
            d = require_blockg_ready("NVDA")
            if not d.ready:
                raise RuntimeError(f"BLOCK-G FAIL: {d.reason} as_of_date={d.as_of_date}")
        t = self.ib.placeOrder(c, o)
        self.ib.sleep(0.5)

        order_id = str(t.order.orderId)
                _fills_obj = None
        try:
            _fills_attr = getattr(t, "fills", None)
            _fills_obj = _fills_attr() if callable(_fills_attr) else _fills_attr
        except Exception:
            _fills_obj = None

        fills = [
            {"px": f.execution.avgPrice, "qty": f.execution.shares}
            for f in (_fills_obj or [])
        ]return order_id, {"status": t.orderStatus.status, "fills": fills}

    def disconnect(self):
        try:
            self.ib.disconnect()
        except Exception:
            pass


# ================= Binance =================
class BinanceClient(BrokerClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        sandbox: bool = False,
    ):
        if ccxt is None:
            raise BrokerError("ccxt not installed")
        self.name = "binance"
        self.ex = ccxt.binance()
        if hasattr(self.ex, "set_sandbox_mode") and sandbox:
            self.ex.set_sandbox_mode(True)
        if api_key and secret:
            self.ex.apiKey = api_key
            self.ex.secret = secret

    def submit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        limit_px: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        side = side.upper()
        params = meta or {}
        if order_type.upper() == "MARKET":
            resp = self.ex.create_order(
                symbol, "market", side.lower(), qty, params=params
            )
        else:
            resp = self.ex.create_order(
                symbol, "limit", side.lower(), qty, price=limit_px, params=params
            )
        oid = str(
            resp.get("id")
            or resp.get("orderId")
            or resp.get("clientOrderId")
            or "unknown"
        )
        return oid, {"raw": resp}


# ================= Kraken =================
class KrakenClient(BrokerClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        sandbox: bool = False,
    ):
        if ccxt is None:
            raise BrokerError("ccxt not installed")
        self.name = "kraken"
        self.ex = ccxt.kraken()
        if hasattr(self.ex, "set_sandbox_mode") and sandbox:
            self.ex.set_sandbox_mode(True)
        if api_key and secret:
            self.ex.apiKey = api_key
            self.ex.secret = secret

    def submit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        limit_px: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        side = side.upper()
        params = meta or {}
        if order_type.upper() == "MARKET":
            resp = self.ex.create_order(
                symbol, "market", side.lower(), qty, params=params
            )
        else:
            resp = self.ex.create_order(
                symbol, "limit", side.lower(), qty, price=limit_px, params=params
            )
        oid = str(
            resp.get("id") or resp.get("txid") or resp.get("clientOrderId") or "unknown"
        )
        return oid, {"raw": resp}




