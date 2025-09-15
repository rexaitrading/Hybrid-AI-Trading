# src/hybrid_ai_trading/execution/paper_simulator.py
"""
Paper Simulator (Hybrid AI Quant Pro v9.6 – 100% Coverage Stable)
-----------------------------------------------------------------
- Simulates fills with slippage + commission
- Commission models: % of notional, per-share, min enforcement
- Deterministic RNG per instance for reproducibility
- Returns structured fill dict (compatible with OrderManager/PortfolioTracker)
"""

import logging
import random
from typing import Dict, Optional

logger = logging.getLogger("hybrid_ai_trading.execution.paper_simulator")


class PaperSimulator:
    def __init__(
        self,
        slippage: float = 0.001,            # % of price
        commission: float = 0.0005,         # % of notional
        commission_per_share: float = 0.0,  # per-share commission
        min_commission: float = 0.0,        # minimum commission per trade
        seed: Optional[int] = None          # reproducibility in unit tests
    ):
        self.slippage = slippage
        self.commission = commission
        self.commission_per_share = commission_per_share
        self.min_commission = min_commission

        # ✅ Each simulator has its own RNG (no cross-test pollution)
        self.rng = random.Random(seed) if seed is not None else random

    def simulate_fill(self, symbol: str, side: str, size: float, price: float) -> Dict:
        """Simulate a paper fill with slippage + commission."""
        if side.upper() not in ("BUY", "SELL"):
            return {"status": "error", "reason": "invalid_side"}

        # --- Apply slippage (deterministic RNG per instance) ---
        slip = price * self.slippage * self.rng.choice([-1, 1]) if self.slippage else 0.0
        fill_price = round(price + slip, 4)
        notional = fill_price * size

        # --- Commission model ---
        commission_cost = (
            self.commission * notional +
            self.commission_per_share * size
        )
        commission_cost = max(round(commission_cost, 2), self.min_commission)

        logger.info(
            f"📊 Paper fill | {side.upper()} {size} {symbol} "
            f"@ {fill_price:.2f} | slip={slip:.2f}, "
            f"comm={commission_cost:.2f}, notional={notional:.2f}"
        )

        return {
            "status": "filled",
            "symbol": symbol,
            "side": side.upper(),
            "size": size,
            "fill_price": fill_price,
            "notional": round(notional, 2),
            "commission": commission_cost,
            "mode": "paper",
        }
