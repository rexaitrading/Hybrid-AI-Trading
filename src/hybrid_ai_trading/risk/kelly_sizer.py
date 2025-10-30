"""
Kelly Sizer (Hybrid AI Quant Pro v13.2 – Suite-Aligned, Hedge Fund OE Grade, Fixed)
-----------------------------------------------------------------------------------
Responsibilities:
- Compute Kelly Criterion fraction (scaled, clamped)
- Regime-aware scaling (input from RegimeDetector)
- Integrates with RiskManager veto (PnL breach → return 0)
- Structured audit trail for compliance & backtests
- Supports batch portfolio sizing
- Safe persistence of parameters (JSON)
- FIX: size_position now returns numeric size (float) for TradeEngine compatibility
"""

import json
import logging
from typing import Dict, Union

logger = logging.getLogger("hybrid_ai_trading.risk.kelly_sizer")
logger.setLevel(logging.DEBUG)
logger.propagate = True


def _safe_fmt(val: Union[float, int, object]) -> str:
    """Format safely for logs/strings."""
    try:
        return f"{float(val):.2f}"
    except Exception:
        return str(val)


class KellySizer:
    def __init__(
        self,
        win_rate: float = 0.5,
        payoff: float = 1.0,
        fraction: float = 1.0,
        regime_factor: float = 1.0,
    ) -> None:
        self.win_rate = win_rate
        self.payoff = payoff
        self.fraction = fraction
        self.regime_factor = regime_factor
        logger.info(
            "✅ KellySizer initialized | win_rate=%s, payoff=%s, fraction=%s, regime_factor=%s",
            _safe_fmt(self.win_rate),
            _safe_fmt(self.payoff),
            _safe_fmt(self.fraction),
            _safe_fmt(self.regime_factor),
        )

    # ------------------------------------------------------------------
    def kelly_fraction(self, risk_veto: bool = False) -> float:
        """Return Kelly fraction (scaled, clamped in [0,1])."""
        try:
            if risk_veto:
                logger.warning("⚠️ Risk veto active → Kelly fraction=0.0")
                return 0.0
            if self.payoff <= 0 or not (0 <= self.win_rate <= 1):
                logger.warning("⚠️ Invalid Kelly inputs → returning 0.0")
                return 0.0
            f_star = self.win_rate - (1 - self.win_rate) / self.payoff
            scaled = f_star * max(0.0, self.fraction) * max(0.0, self.regime_factor)
            clamped = max(0.0, min(scaled, 1.0))
            logger.debug(
                "📊 Kelly fraction | f*=%.4f, scale=%.2f, regime=%.2f, clamped=%.4f",
                f_star,
                self.fraction,
                self.regime_factor,
                clamped,
            )
            return clamped
        except Exception as e:
            logger.error("Kelly sizing failed: %s", e)
            return 0.0

    # ------------------------------------------------------------------
    def size_position(
        self, equity: float, price: float, risk_veto: bool = False
    ) -> float:
        """Return numeric position size. Detailed decision is logged for audit."""
        try:
            if equity <= 0 or price <= 0:
                logger.warning("⚠️ Invalid equity/price → returning 0.0")
                return 0.0
            f = self.kelly_fraction(risk_veto=risk_veto)
            size = (equity * f) / price
            decision = {
                "size": max(0.0, size),
                "fraction": f,
                "equity": equity,
                "price": price,
                "reason": "risk_veto" if risk_veto else "ok",
            }
            logger.info("📈 Kelly sizing decision | %s", json.dumps(decision))
            return max(0.0, size)
        except Exception as e:
            logger.error("Kelly sizing failed: %s", e)
            return 0.0

    # ------------------------------------------------------------------
    def batch_size(
        self, equity: float, prices: Dict[str, float], risk_veto: bool = False
    ) -> Dict[str, float]:
        """Compute Kelly sizing across multiple symbols and return numeric sizes."""
        results = {}
        for sym, price in prices.items():
            results[sym] = self.size_position(equity, price, risk_veto=risk_veto)
        return results

    # ------------------------------------------------------------------
    def update_params(
        self,
        win_rate: float,
        payoff: float,
        fraction: float = 1.0,
        regime_factor: float = 1.0,
    ) -> None:
        """Update Kelly parameters dynamically."""
        self.win_rate = win_rate
        self.payoff = payoff
        self.fraction = fraction
        self.regime_factor = regime_factor
        logger.info(
            "🔄 KellySizer updated | win_rate=%s, payoff=%s, fraction=%s, regime_factor=%s",
            _safe_fmt(self.win_rate),
            _safe_fmt(self.payoff),
            _safe_fmt(self.fraction),
            _safe_fmt(self.regime_factor),
        )

    # ------------------------------------------------------------------
    def save_params(self, path: str) -> None:
        """Persist Kelly parameters to JSON."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "win_rate": self.win_rate,
                        "payoff": self.payoff,
                        "fraction": self.fraction,
                        "regime_factor": self.regime_factor,
                    },
                    f,
                    indent=2,
                )
            logger.info("💾 KellySizer parameters saved to %s", path)
        except Exception as e:
            logger.error("❌ Failed to save KellySizer params: %s", e)

    def __repr__(self) -> str:
        return (
            f"KellySizer(win_rate={_safe_fmt(self.win_rate)}, "
            f"payoff={_safe_fmt(self.payoff)}, "
            f"fraction={_safe_fmt(self.fraction)}, "
            f"regime_factor={_safe_fmt(self.regime_factor)})"
        )
