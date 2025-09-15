"""
Portfolio Tracker (Hybrid AI Quant Pro v76.1 – AAA Polished & 100% Coverage)
---------------------------------------------------------------------------
Responsibilities:
- Track long & short positions with average price
- Apply commissions correctly (buy/sell)
- Update realized & unrealized PnL
- Maintain equity, cash, and equity curve (history)
- Support exposure metrics (with and without price updates)
- Handle invalid inputs, cleanup when flat
- Provide reports with drawdowns
"""

import math
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PortfolioTracker:
    """
    Portfolio Tracker for Hybrid AI Quant Pro.

    Tracks positions, PnL, equity, and exposure in a clean, auditable way.
    """

    def __init__(self, starting_equity: float = 100000.0):
        self.starting_equity = float(starting_equity)
        self.cash = float(starting_equity)
        self.equity = float(starting_equity)

        # {symbol: {"size": float, "avg_price": float}}
        self.positions: Dict[str, Dict[str, float]] = {}
        self.history = [(0, self.equity)]

        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self._step = 0

        logger.debug(f"[PortfolioTracker] Initialized | Equity={self.equity}")

    # ------------------------------------------------------------------
    def update_position(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        commission: float = 0.0,
    ):
        """Update portfolio after a trade execution."""
        if size <= 0 or price <= 0:
            logger.error(
                f"[PortfolioTracker] Invalid trade update | {symbol} {side} {size} @ {price}"
            )
            raise ValueError("Invalid size or price for trade update")

        side = side.upper()
        size = float(size)
        price = float(price)

        if symbol not in self.positions:
            self.positions[symbol] = {"size": 0.0, "avg_price": price}

        pos = self.positions[symbol]
        old_size, old_avg = pos["size"], pos["avg_price"]

        logger.debug(
            f"[PortfolioTracker] Update {symbol} | Side={side}, Size={size}, Price={price}, Comm={commission}"
        )

        # === BUY logic ===
        if side == "BUY":
            if old_size < 0:  # covering short
                cover_size = min(size, abs(old_size))
                pnl = (old_avg - price) * cover_size
                self.realized_pnl += pnl
                self.cash -= price * cover_size + commission
                pos["size"] += cover_size
                size -= cover_size
                logger.debug(f"[PortfolioTracker] Cover short {symbol} | PnL={pnl:.2f}")

            if size > 0:  # opening or adding long
                new_total = max(pos["size"], 0) + size
                pos["avg_price"] = (
                    old_avg * max(pos["size"], 0) + price * size
                ) / new_total
                pos["size"] = max(pos["size"], 0) + size
                self.cash -= price * size + commission
                logger.debug(
                    f"[PortfolioTracker] Long {symbol} | NewSize={pos['size']} Avg={pos['avg_price']}"
                )

        # === SELL logic ===
        elif side == "SELL":
            if old_size > 0:  # closing long
                close_size = min(size, old_size)
                pnl = (price - old_avg) * close_size
                self.realized_pnl += pnl
                self.cash += price * close_size - commission
                pos["size"] -= close_size
                size -= close_size
                logger.debug(f"[PortfolioTracker] Close long {symbol} | PnL={pnl:.2f}")

            if size > 0:  # opening or adding short
                new_total = abs(min(pos["size"], 0)) + size
                pos["avg_price"] = (
                    old_avg * abs(min(pos["size"], 0)) + price * size
                ) / new_total
                pos["size"] = min(pos["size"], 0) - size
                self.cash += price * size - commission
                logger.debug(
                    f"[PortfolioTracker] Short {symbol} | NewSize={pos['size']} Avg={pos['avg_price']}"
                )

        # === Cleanup if flat ===
        if math.isclose(pos["size"], 0.0, abs_tol=1e-8):
            del self.positions[symbol]
            logger.debug(f"[PortfolioTracker] Flat {symbol} → position removed")

        # Always update equity
        self.update_equity({symbol: price})

    # ------------------------------------------------------------------
    def update_equity(self, price_updates: Optional[Dict[str, float]] = None):
        """Recalculate equity and unrealized PnL given latest prices."""
        total_value = self.cash
        unrealized = 0.0

        if price_updates is not None and price_updates:
            for sym, price in price_updates.items():
                if sym in self.positions:
                    pos = self.positions[sym]
                    total_value += pos["size"] * price
                    if pos["size"] > 0:  # long
                        unrealized += (price - pos["avg_price"]) * pos["size"]
                    elif pos["size"] < 0:  # short
                        unrealized += (pos["avg_price"] - price) * abs(pos["size"])

        # --- Clamp equity to never drop below 0 ---
        self.equity = max(0.0, total_value)
        self.unrealized_pnl = unrealized
        self._step += 1
        self.history.append((self._step, self.equity))

        logger.debug(
            f"[PortfolioTracker] Equity updated | Equity={self.equity:.2f}, "
            f"Unrealized={self.unrealized_pnl:.2f}"
        )

    # ------------------------------------------------------------------
    def get_total_exposure(self, price_updates: Optional[Dict[str, float]] = None) -> float:
        """
        Return total exposure (absolute notional).
        - If price_updates provided → use those prices.
        - Otherwise → fallback to stored avg_price.
        """
        exposure = 0.0
        if price_updates is not None:
            if price_updates:  # explicit branch
                for sym, price in price_updates.items():
                    if sym in self.positions:
                        exposure += abs(self.positions[sym]["size"] * price)
        else:
            for sym, pos in self.positions.items():
                exposure += abs(pos["size"] * pos["avg_price"])

        logger.debug(f"[PortfolioTracker] Exposure={exposure:.2f}")
        return exposure

    # ------------------------------------------------------------------
    def get_positions(self):
        """Return a copy of current positions."""
        return {k: v.copy() for k, v in self.positions.items()}

    def get_drawdown(self) -> float:
        """Return current drawdown as fraction of peak equity."""
        if not self.history:
            return 0.0

        peak = max(eq for _, eq in self.history)
        if peak > 0:
            dd = (peak - self.equity) / peak
        else:
            dd = 0.0

        logger.debug(f"[PortfolioTracker] Drawdown={dd:.4f}")
        return dd

    def report(self) -> Dict[str, float]:
        """Return a dictionary snapshot of the portfolio state."""
        snapshot = {
            "cash": round(self.cash, 2),
            "equity": round(self.equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "positions": self.get_positions(),
            "total_exposure": self.get_total_exposure(),
            "drawdown_pct": round(self.get_drawdown() * 100, 2),
        }
        logger.debug(f"[PortfolioTracker] Report generated | {snapshot}")
        return snapshot
