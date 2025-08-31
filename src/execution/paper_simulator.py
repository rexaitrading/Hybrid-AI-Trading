import logging
import random
from typing import Dict

logger = logging.getLogger(__name__)


class PaperSimulator:
    """
    Paper trading simulator for backtests and dry-run mode.
    Applies slippage + commission and returns structured fills.
    """

    def __init__(self, slippage: float = 0.001, commission: float = 0.0005):
        """
        Parameters
        ----------
        slippage : float
            Slippage fraction (0.001 = 0.1%)
        commission : float
            Commission fraction of notional (0.0005 = 0.05%)
        """
        self.slippage = slippage
        self.commission = commission

    def simulate_fill(self, symbol: str, side: str, size: float, price: float) -> Dict:
        """
        Simulate a trade fill.

        Parameters
        ----------
        symbol : str
            Asset being traded (e.g., "AAPL").
        side : str
            "buy" or "sell".
        size : float
            Quantity traded.
        price : float
            Intended execution price.

        Returns
        -------
        dict
            Fill details including commission + final fill price.
        """
        if side not in ["buy", "sell"]:
            logger.warning("⚠️ Invalid order side: %s", side)
            return {"status": "error", "reason": "invalid_side"}

        # Random slippage up or down
        slip = price * self.slippage * random.choice([-1, 1])
        fill_price = price + slip

        # Commission on notional
        notional = fill_price * size
        commission_cost = notional * self.commission

        logger.info(
            "📊 Paper fill: %s %s %s @ %.2f (slip=%.2f, commission=%.2f)",
            side.upper(), size, symbol, fill_price, slip, commission_cost
        )

        return {
            "status": "filled",
            "symbol": symbol,
            "side": side,
            "size": size,
            "fill_price": round(fill_price, 4),
            "notional": round(notional, 2),
            "commission": round(commission_cost, 2),
            "mode": "paper",
        }
