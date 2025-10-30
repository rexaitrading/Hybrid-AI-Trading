from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


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


# ---------------- IBKR ----------------
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
        c = self._contract(symbol)
        side = side.upper()
        o = (
            MarketOrder(side, abs(qty))
            if order_type.upper() == "MARKET"
            else LimitOrder(side, abs(qty), limit_px)
        )
        t = self.ib.placeOrder(c, o)
        self.ib.sleep(0.5)
        order_id = str(t.order.orderId)
        fills = [
            {"px": f.execution.avgPrice, "qty": f.execution.shares}
            for f in (t.fills() or [])
        ]
        return order_id, {"status": t.orderStatus.status, "fills": fills}

    def disconnect(self):
        try:
            self.ib.disconnect()
        except Exception:
            pass


# ---------------- Binance (ccxt) ----------------
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


# ---------------- Kraken (ccxt) ----------------
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
        # Kraken has a sandbox environment; ccxt exposes set_sandbox_mode on some exchanges.
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
