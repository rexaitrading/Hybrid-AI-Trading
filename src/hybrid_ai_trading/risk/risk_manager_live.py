def _kelly_clamp(kelly_raw: float,
                 kelly_min: float,
                 kelly_max: float) -> float:
    k = float(kelly_raw)
    return max(kelly_min, min(k, kelly_max))

def _drawdown_scale(equity_peak: float,
                    equity_now: float,
                    dd_max: float = 0.20,
                    gamma: float = 1.0) -> float:
    """Return [0,1] scale that shrinks risk as drawdown deepens.
    dd = (peak - now)/peak. When dd>=dd_max => 0.  Smooth with gamma."""
    if equity_peak <= 0 or equity_now <= 0:
        return 0.0
    dd = max(0.0, (equity_peak - equity_now) / equity_peak)
    if dd_max <= 0:
        return 0.0
    x = max(0.0, 1.0 - dd / dd_max)
    return x ** max(0.0, gamma)
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

def size_for_signal(signal_strength: float,
                    price: float,
                    equity_now: float,
                    equity_peak: float,
                    risk_per_trade: float = 0.005,
                    kelly_min: float = 0.00,
                    kelly_max: float = 0.20,
                    dd_max: float = 0.20,
                    gamma: float = 1.5,
                    notional_cap: float | None = None) -> dict:
    """Return clamped Kelly fraction and resulting size.

    signal_strength: base Kelly fraction suggestion (0..1 typical).
    risk_per_trade: additional cap vs account (fallback if signal missing).
    notional_cap: optional hard cap on dollars per position.
    """
    k_base = max(0.0, float(signal_strength)) if signal_strength is not None else float(risk_per_trade)
    k = _kelly_clamp(k_base, kelly_min, kelly_max)
    s = _drawdown_scale(equity_peak=equity_peak, equity_now=equity_now, dd_max=dd_max, gamma=gamma)
    k_eff = k * s

    if price <= 0 or equity_now <= 0:
      return {"fraction": 0.0, "qty": 0.0, "notional": 0.0}

    notional = k_eff * equity_now
    if notional_cap is not None and notional_cap > 0:
      notional = min(notional, float(notional_cap))

    qty = max(0.0, notional / price)

    return {
        "fraction": float(k_eff),
        "qty": float(qty),
        "notional": float(notional),
        "meta": {
            "kelly_raw": float(k_base),
            "kelly_clamped": float(k),
            "dd_scale": float(s),
            "kelly_min": kelly_min,
            "kelly_max": kelly_max,
            "dd_max": dd_max,
            "gamma": gamma,
            "risk_per_trade": risk_per_trade,
        }
    }
