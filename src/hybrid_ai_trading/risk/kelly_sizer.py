"""
Kelly Sizer (Hybrid AI Quant Pro v13.2 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“ Suite-Aligned, Hedge Fund OE Grade, Fixed)
-----------------------------------------------------------------------------------
Responsibilities:
- Compute Kelly Criterion fraction (scaled, clamped)
- Regime-aware scaling (input from RegimeDetector)
- Integrates with RiskManager veto (PnL breach ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ return 0)
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
            "ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ KellySizer initialized | win_rate=%s, payoff=%s, fraction=%s, regime_factor=%s",
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
                logger.warning(
                    "ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Risk veto active ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Kelly fraction=0.0"
                )
                return 0.0
            if self.payoff <= 0 or not (0 <= self.win_rate <= 1):
                logger.warning(
                    "ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Invalid Kelly inputs ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ returning 0.0"
                )
                return 0.0
            f_star = self.win_rate - (1 - self.win_rate) / self.payoff
            scaled = f_star * max(0.0, self.fraction) * max(0.0, self.regime_factor)
            clamped = max(0.0, min(scaled, 1.0))
            logger.debug(
                "ÃƒÂ°Ã…Â¸Ã¢â‚¬Å“Ã…Â  Kelly fraction | f*=%.4f, scale=%.2f, regime=%.2f, clamped=%.4f",
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
                logger.warning(
                    "ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Invalid equity/price ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ returning 0.0"
                )
                return 0.0
            f = self.kelly_fraction(risk_veto=risk_veto)
            size = (equity * f) / price
            # SPECIAL-MODE size_multiplier (RiskEnvelope) — applied only when explicitly armed
            try:
                from pathlib import Path
                from hybrid_ai_trading.runtime.risk_envelope_loader import effective_size_multiplier
                size = float(size) * float(effective_size_multiplier(Path(".")))
            except Exception:
                pass
            decision = {
                "size": max(0.0, size),
                "fraction": f,
                "equity": equity,
                "price": price,
                "reason": "risk_veto" if risk_veto else "ok",
            }
            logger.info("ÃƒÂ°Ã…Â¸Ã¢â‚¬Å“Ã‹â€  Kelly sizing decision | %s", json.dumps(decision))
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
            "ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ¢â‚¬Å¾ KellySizer updated | win_rate=%s, payoff=%s, fraction=%s, regime_factor=%s",
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
            logger.info("ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â¾ KellySizer parameters saved to %s", path)
        except Exception as e:
            logger.error("ÃƒÂ¢Ã‚ÂÃ…â€™ Failed to save KellySizer params: %s", e)

    def __repr__(self) -> str:
        return (
            f"KellySizer(win_rate={_safe_fmt(self.win_rate)}, "
            f"payoff={_safe_fmt(self.payoff)}, "
            f"fraction={_safe_fmt(self.fraction)}, "
            f"regime_factor={_safe_fmt(self.regime_factor)})"
        )
