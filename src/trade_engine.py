"""
Trade Engine

Coordinates strategy signals, risk management, and execution.
"""

import logging
from typing import Dict, Optional

from src.execution.order_manager import OrderManager
from src.execution.portfolio_tracker import PortfolioTracker
from src.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class TradeEngine:
    """
    Central trading engine that connects:
    - Strategy signals
    - Risk Manager
    - Order Manager
    - Portfolio Tracker
    """

    def __init__(self, config: Dict):
        """
        Initialize the Trade Engine.

        Parameters
        ----------
        config : dict
            Configuration dictionary with keys:
            - daily_loss_limit (float)
            - trade_loss_limit (float)
            - leverage (float)
            - equity (float)
            - brokers (list)
            - dry_run (bool)
        """
        self.config = config

        # Initialize Risk Manager
        self.risk_manager = RiskManager(
            daily_loss_limit=config.get("daily_loss_limit", -0.03),
            trade_loss_limit=config.get("trade_loss_limit", -0.01),
            max_leverage=config.get("leverage", 1.0),
            equity=config.get("equity", 100000.0),
        )

        # Initialize Order Manager + Portfolio
        self.order_manager = OrderManager(config, self.risk_manager)
        self.portfolio = PortfolioTracker()

        logger.info("✅ TradeEngine initialized with config: %s", config)

    # --------------------------------------------------------
    # Signal Processing
    # --------------------------------------------------------
    def process_signal(
        self, symbol: str, signal: str, size: float, price: Optional[float] = None
    ) -> Dict:
        """
        Process a trading signal from a strategy.

        Parameters
        ----------
        symbol : str
            Asset symbol (e.g., 'BTC/USDT')
        signal : str
            Trading signal: "BUY", "SELL", or "HOLD"
        size : float
            Order size
        price : float, optional
            Price (if limit order)

        Returns
        -------
        dict
            Order result with status and details.
        """
        # Validate signal
        if signal not in ["BUY", "SELL", "HOLD"]:
            logger.warning("⚠️ Unknown signal received: %s", signal)
            return {"status": "error", "reason": "invalid_signal"}

        # Gate signal with risk manager
        gated_signal = self.risk_manager.control_signal(signal)
        if gated_signal == "HOLD":
            logger.info("🚫 Signal blocked by Risk Manager: %s → HOLD", signal)
            return {"status": "blocked", "reason": "risk"}

        # Convert to order side
        side = "buy" if signal == "BUY" else "sell"

        # Place the order
        order = self.order_manager.place_order(symbol, side, size, price=price)

        # Update portfolio if executed
        if order.get("status") in ["filled", "submitted"]:
            exec_price = price or order.get("details", {}).get("price", 100)
            self.portfolio.update_position(symbol, side, size, exec_price)
            logger.info("📈 Portfolio updated after %s: %s %s @ %s",
                        side.upper(), size, symbol, exec_price)

        return order

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------
    def get_positions(self) -> Dict:
        """Return current open positions."""
        return dict(self.portfolio.positions)

    def get_cash(self) -> float:
        """Return current cash balance."""
        return self.portfolio.cash

    def get_history(self):
        """Return trade history."""
        return self.portfolio.history
