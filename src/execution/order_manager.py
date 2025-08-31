"""
Order Manager

Handles routing of orders to exchanges/brokers (CCXT, IBKR, paper),
applies risk checks, and returns structured results.
"""

import os
import ccxt
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from src.risk.risk_manager import RiskManager

try:
    from ib_insync import IB, MarketOrder
except ImportError:
    IB = None

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Order manager that routes orders to exchanges (crypto via CCXT, equities via IBKR),
    with support for dry-run (paper trading).
    """

    def __init__(self, config: dict, risk_manager: RiskManager):
        """
        Initialize OrderManager.

        Parameters
        ----------
        config : dict
            Trading configuration (brokers, dry_run, etc.)
        risk_manager : RiskManager
            RiskManager instance for validating trades.
        """
        self.config = config
        self.risk_manager = risk_manager
        self.dry_run = config.get("dry_run", True)

        # CCXT exchange (crypto)
        self.ccxt_exchange = None
        if "binance" in config.get("brokers", []):
            self.ccxt_exchange = ccxt.binance({
                "apiKey": os.getenv("BINANCE_API_KEY"),
                "secret": os.getenv("BINANCE_API_SECRET"),
                "enableRateLimit": True,
            })
            logger.info("✅ CCXT Binance client initialized")

        # IBKR (stubbed for now)
        self.ib = None
        if "ibkr" in config.get("brokers", []) and IB:
            self.ib = IB()
            # self.ib.connect("127.0.0.1", 7497, clientId=1)
            logger.info("✅ IBKR client initialized (not connected)")

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------
    def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None
    ) -> Dict:
        """
        Place an order with risk checks and routing.

        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC/USDT").
        side : str
            "buy" or "sell".
        size : float
            Quantity to trade.
        order_type : str, default "market"
            Order type ("market" or "limit").
        price : float, optional
            Limit price (required if order_type="limit").

        Returns
        -------
        dict
            Structured result (status, details, reason).
        """
        logger.info(f"📝 New Order Request → {side.upper()} {size} {symbol} ({order_type})")

        # Risk check
        if not self.risk_manager.check_order(symbol, side, size, price):
            logger.warning("🚫 Order blocked by RiskManager")
            return {"status": "rejected", "reason": "risk_block"}

        # Dry run / paper trading
        if self.dry_run:
            logger.info("📊 Dry-run mode: order filled immediately")
            return {
                "status": "filled",
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": price or "market",
                "mode": "paper",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # CCXT live trading
        if self.ccxt_exchange:
            try:
                if order_type == "market":
                    order = self.ccxt_exchange.create_market_order(symbol, side, size)
                elif order_type == "limit" and price:
                    order = self.ccxt_exchange.create_limit_order(symbol, side, size, price)
                else:
                    raise ValueError("Invalid order type/price")
                logger.info("✅ Order submitted to CCXT exchange")
                return {"status": "submitted", "details": order}
            except Exception as e:
                logger.error("❌ CCXT order error: %s", str(e))
                return {"status": "error", "reason": str(e)}

        # IBKR live trading (stub)
        if self.ib:
            logger.warning("⚠️ IBKR support not fully implemented yet")
            return {"status": "error", "reason": "IBKR not implemented yet"}

        logger.error("❌ No available broker for order routing")
        return {"status": "error", "reason": "no broker available"}
