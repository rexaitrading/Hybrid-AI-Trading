"""
Order Manager (Hybrid AI Quant Pro v13.7 – AAA Stable & Fully Integrated)
-------------------------------------------------------------------------
- Dry run: deterministic fills
- Live mode: routes orders to Alpaca REST API
- Updates PortfolioTracker
- Risk-aware validation
- Structured logging for audit trail
- submit_order adapter for SmartRouter compatibility
"""

import uuid
import time
import logging
from typing import Dict, Optional, Any
import os
from dotenv import load_dotenv

from hybrid_ai_trading.execution.paper_simulator import PaperSimulator

# Alpaca SDK (only needed for live mode)
try:
    import alpaca_trade_api as tradeapi
except ImportError:
    tradeapi = None

logger = logging.getLogger(__name__)
load_dotenv()


class OrderManager:
    """Central order execution manager."""

    def __init__(
        self,
        risk_manager: Any,
        portfolio: Any,
        dry_run: bool = True,
        costs: Optional[Dict[str, float]] = None,
        use_paper_simulator: bool = False,
    ):
        self.risk_manager = risk_manager
        self.portfolio = portfolio
        self.dry_run = dry_run
        self.use_paper_simulator = use_paper_simulator

        # --- Cost model ---
        self.commission_per_share = (costs or {}).get("commission_per_share", 0.0)
        self.min_commission = (costs or {}).get("min_commission", 0.0)
        self.slippage_per_share = (costs or {}).get("slippage_per_share", 0.0)
        self.commission_pct = (costs or {}).get("commission_pct", 0.0)

        # --- Paper simulator ---
        self.simulator: Optional[PaperSimulator] = None
        if use_paper_simulator:
            self.simulator = PaperSimulator(
                slippage=(costs or {}).get("slippage_pct", 0.001),
                commission=(costs or {}).get("commission_pct", 0.0005),
                commission_per_share=(costs or {}).get("commission_per_share", 0.0),
                min_commission=(costs or {}).get("min_commission", 0.0),
            )

        # --- Live Alpaca client ---
        self.live_client = None
        if not dry_run and tradeapi:
            api_key = os.getenv("APCA_API_KEY_ID")
            api_secret = os.getenv("APCA_API_SECRET_KEY")
            base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
            try:
                self.live_client = tradeapi.REST(api_key, api_secret, base_url, api_version="v2")
                logger.info("✅ Live Alpaca client initialized.")
            except Exception as e:
                logger.error(f"❌ Failed to init Alpaca client: {e}")

    # ------------------------------------------------------------------
    def submit_order(self, **kwargs):
        """Adapter for SmartRouter compatibility (calls place_order)."""
        return self.place_order(
            symbol=kwargs.get("symbol"),
            side=kwargs.get("side"),
            size=kwargs.get("qty"),
            price=kwargs.get("price", 0),
        )

    # ------------------------------------------------------------------
    def place_order(self, symbol: str, side: str, size: float, price: float) -> Dict[str, Any]:
        """Place an order (dry run or live)."""
        order_id = str(uuid.uuid4())
        timestamp = time.time()
        side = (side or "").upper()

        # --- Validation ---
        if side not in ("BUY", "SELL"):
            return {"status": "rejected", "reason": "Invalid side"}
        if size is None or size <= 0 or price is None or price <= 0:
            return {"status": "rejected", "reason": "Invalid size/price"}

        # --- Dry run ---
        if self.dry_run:
            return self._simulate_order(symbol, side, size, price, order_id, timestamp)

        # --- Live ---
        if self.live_client:
            try:
                order = self.live_client.submit_order(
                    symbol=symbol,
                    qty=size,
                    side=side.lower(),
                    type="market",
                    time_in_force="day",
                )
                logger.info(f"📡 Live order submitted: {order}")
                return {
                    "status": "pending",
                    "reason": "submitted_to_alpaca",
                    "details": getattr(order, "_raw", str(order)),
                }
            except Exception as e:
                logger.error(f"❌ Live order failed: {e}")
                return {"status": "blocked", "reason": f"Alpaca error: {e}"}

        return {"status": "blocked", "reason": "live_order_not_available"}

    # ------------------------------------------------------------------
    def _simulate_order(self, symbol, side, size, price, order_id, timestamp):
        """Simulate fills in dry-run mode."""
        exec_price, commission, notional = None, 0.0, 0.0

        # --- Simulator ---
        if self.use_paper_simulator:
            if not self.simulator:
                return {"status": "blocked", "reason": "Simulator not initialized"}
            fill = self.simulator.simulate_fill(symbol, side, size, price)
            if fill.get("status") != "filled":
                return {"status": "blocked", "reason": fill.get("reason", "PaperSimulator veto")}
            exec_price, commission, notional = (
                fill["fill_price"],
                fill["commission"],
                fill["notional"],
            )
        else:
            slip = self.slippage_per_share if side == "BUY" else -self.slippage_per_share
            exec_price = price + slip
            notional = exec_price * size
            commission = self.commission_pct * notional + self.commission_per_share * size
            commission = max(commission, self.min_commission)

        # --- Risk check ---
        try:
            if not self.risk_manager.check_trade(0, trade_notional=notional):
                logger.warning(f"❌ Risk veto | {side} {size} {symbol} @ {exec_price:.2f}")
                return {"status": "blocked", "reason": "Risk veto"}
        except Exception as e:
            logger.error(f"❌ RiskManager failure: {e}")
            return {"status": "blocked", "reason": "RiskManager error"}

        # --- Portfolio update ---
        try:
            self.portfolio.update_position(symbol, side, size, exec_price, commission)
            snapshot = self.portfolio.report()
        except Exception as e:
            logger.error(f"❌ Portfolio update failed: {e}")
            return {"status": "blocked", "reason": "Portfolio update error"}

        # --- Logging ---
        logger.info(
            f"📊 Order Fill | {side} {size} {symbol} @ {exec_price:.2f} | "
            f"Notional={notional:.2f}, Comm={commission:.2f}, Cash={snapshot['cash']:.2f}, "
            f"Equity={snapshot['equity']:.2f}, Realized={snapshot['realized_pnl']:.2f}"
        )

        return {
            "status": "filled",
            "details": {
                "order_id": order_id,
                "timestamp": timestamp,
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": exec_price,
                "notional": round(notional, 2),
                "commission": round(commission, 2),
                "portfolio": snapshot,
            },
        }
