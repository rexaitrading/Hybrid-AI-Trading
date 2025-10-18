from typing import Any, Dict
try:
    from hybrid_ai_trading.risk.risk_manager import RiskManager  # type: ignore
except Exception:
    class RiskManager:  # type: ignore
        def __init__(self, *args, **kwargs): ...
        def approve_trade(self, *args, **kwargs): return {"approved": True, "reason": "stub"}

from hybrid_ai_trading.risk.price_gate import latest_price

class LivePriceRiskManager(RiskManager):
    def _get_symbol(self, trade: Any) -> str:
        if isinstance(trade, dict):
            return str(trade.get("symbol") or trade.get("ticker") or trade.get("sym") or "")
        return str(getattr(trade, "symbol", getattr(trade, "ticker", "")) or "")

    def _get_price(self, trade: Any) -> float | None:
        if isinstance(trade, dict):
            return trade.get("price")  # type: ignore
        return getattr(trade, "price", None)

    def _set_price(self, trade: Any, px: float) -> None:
        if isinstance(trade, dict):
            trade["price"] = px  # type: ignore
            return
        setattr(trade, "price", px)

    def approve_trade(self, trade: Any, *args, **kwargs) -> Dict[str, Any]:
        sym = self._get_symbol(trade)
        px  = self._get_price(trade)
        if (px is None or (isinstance(px, (int, float)) and px <= 0.0)) and sym:
            q = latest_price(sym)
            if isinstance(q, dict) and isinstance(q.get("price"), (int, float)):
                self._set_price(trade, float(q["price"]))
        return super().approve_trade(trade, *args, **kwargs)