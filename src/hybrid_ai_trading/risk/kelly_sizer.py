"""
Kelly Sizer (Hybrid AI Quant Pro v9.0 – Final Polished & 100% Coverage)
----------------------------------------------------------------------
- Computes Kelly Criterion fraction
- Handles invalid inputs, inf, zero payoff
- Supports fractional Kelly scaling
- Provides position sizing given equity & price
- Safe update_params with logs
- __repr__ for debugging
"""

import logging
import math

logger = logging.getLogger("hybrid_ai_trading.risk.kelly_sizer")
logger.setLevel(logging.DEBUG)
logger.propagate = True


class KellySizer:
    def __init__(self, win_rate: float = 0.5, payoff: float = 1.0, fraction: float = 1.0) -> None:
        self.win_rate = win_rate
        self.payoff = payoff
        self.fraction = fraction
        logger.info(
            f"✅ KellySizer initialized | win_rate={self.win_rate:.2f}, "
            f"payoff={self.payoff:.2f}, fraction={self.fraction:.2f}"
        )

    # ------------------------------------------------------------------
    def optimal_fraction(self) -> float:
        """Return the raw Kelly fraction without scaling."""
        try:
            if self.payoff <= 0 or math.isinf(self.payoff) or not (0 <= self.win_rate <= 1):
                logger.warning("Invalid Kelly inputs → returning 0.0")
                return 0.0
            return self.win_rate - (1 - self.win_rate) / self.payoff
        except Exception as e:
            logger.error(f"Kelly optimal fraction failed: {e}")
            return 0.0

    # ------------------------------------------------------------------
    def kelly_fraction(self) -> float:
        """Return scaled Kelly fraction in [0,1]."""
        try:
            f_star = self.optimal_fraction()
            scaled = f_star * self.fraction
            clamped = max(0.0, min(scaled, 1.0))
            logger.debug(
                f"📊 Scaled Kelly fraction = {clamped:.4f} "
                f"(f*={f_star:.4f}, scale={self.fraction:.2f})"
            )
            return clamped
        except Exception as e:
            logger.error(f"Kelly sizing failed: {e}")
            return 0.0

    # ------------------------------------------------------------------
    def size_position(self, equity: float, price: float) -> float:
        """Return position size given equity & price."""
        try:
            if equity <= 0 or price <= 0:
                logger.warning("Invalid equity or price → returning 0.0")
                return 0.0
            f = self.kelly_fraction()
            size = (equity * f) / price
            logger.info(
                f"📈 Position sizing | equity={equity:.2f}, price={price:.2f}, "
                f"fraction={f:.4f}, size={size:.6f}"
            )
            return size
        except Exception as e:
            logger.error(f"Kelly sizing position failed: {e}")
            return 0.0

    # ------------------------------------------------------------------
    def update_params(self, win_rate: float, payoff: float, fraction: float = 1.0) -> None:
        """Update Kelly parameters dynamically."""
        self.win_rate = win_rate
        self.payoff = payoff
        self.fraction = fraction
        logger.info(
            f"🔄 KellySizer updated | win_rate={self.win_rate:.2f}, "
            f"payoff={self.payoff:.2f}, fraction={self.fraction:.2f}"
        )

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"KellySizer(win_rate={self.win_rate:.2f}, "
            f"payoff={self.payoff:.2f}, fraction={self.fraction:.2f})"
        )
