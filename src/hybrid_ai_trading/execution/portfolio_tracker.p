"""
Portfolio Tracker (Hybrid AI Quant Pro v69.0 – Stable Final Fixed)
------------------------------------------------------------------
- Tracks long & short positions with avg_price
- Books realized PnL correctly (long closes, short covers)
- Maintains cash, equity, realized/unrealized PnL
- Tracks equity curve and drawdowns
- Applies commissions
- Provides exposure metrics for RiskManager
- get_total_exposure works consistently:
  * None → fallback avg_price
  * {}   → fallback avg_price
  * dict with prices → explicit path
"""

import math
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PortfolioTracker:
    """
    Portfolio Tracker (Hybrid AI Quant Pro v69.0 – Stable Final Fixed)

    Responsibilities:
    - Track long & short positions with avg_price
    - Book realized PnL correctly (long closes, short covers)
    - Maintain cash, equity, realized/unrealized PnL
    - Track equity curve and drawdowns
    - Apply commissions
    - Provide exposure metrics for RiskManager
    - get_total_exposure works with explicit prices or fallback avg_price
    """

    def __init__(self, starting_equity: float = 100000.0):
        self.starting_equity = float(starting_equity)
        self.cash = float(starting_equity)
        self.equity = float(starting_equity)

        # Positions dict: {symbol: {"size": float, "avg_price": float}}
        self.positions = {}
        self.history = [(0, self.equity)]

        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self._step = 0

    # ------------------------------------------------------
    def update_position(
        self, symbol: str, side: str, size: float, price: float, commission: float = 0.0
    ):
        """Update portfolio after a trade execution."""
        if size <= 0 or price <= 0:
            raise ValueError("Invalid size or price for trade update")

        side = side.upper()
        size = float(size)
        price = float(price)

        if symbol not in self.positions:
            self.positions[symbol] = {"size": 0.0, "avg_price": price}

        pos = self.positions[symbol]
        old_size, old_avg = pos["size"], pos["avg_price"]

        # === BUY logic ===
        if side == "BUY":
            if old_size < 0:  # covering short
                cover_size = min(size, abs(old_size))
                pnl = (old_avg - price) * cover_size
                self.realized_pnl += pnl
                self.cash -= price * cover_size + commission
                pos["size"] += cover_size
                size -= cover_size

            if size > 0:  # opening or adding long
                new_total = max(pos["size"], 0) + size
                pos["avg_price"] = (
                    old_avg * max(pos["size"], 0) + price * size
                ) / new_total
                pos["size"] = max(pos["size"], 0) + size
                self.cash -= price * size + commission

        # === SELL logic ===
        elif side == "SELL":
            if old_size > 0:  # closing long
                close_size = min(size, old_size)
                pnl = (price - old_avg) * close_size
                self.realized_pnl += pnl
                self.cash += price * close_size - commission
                pos["size"] -= close_size
                size -= close_size

            if size > 0:  # opening or adding short
                new_total = abs(min(pos["size"], 0)) + size
                pos["avg_price"] = (
                    old_avg * abs(min(pos["size"], 0)) + price * size
                ) / new_total
                pos["size"] = min(pos["size"], 0) - size
                self.cash += price * size - commission

        # === Cleanup if flat ===
        if math.isclose(pos["size"], 0.0, abs_tol=1e-8):
            del self.positions[symbol]

        self.update_equity({symbol: price})

    # ------------------------------------------------------
    def update_equity(self, price_updates: dict = None):
        """Recalculate equity and unrealized PnL given latest prices."""
        total_value = self.cash
        unrealized = 0.0

        if price_updates:
            for sym, price in price_updates.items():
                if sym in self.positions:
                    pos = self.positions[sym]
                    total_value += pos["size"] * price
                    if pos["size"] > 0:
                        unrealized += (price - pos["avg_price"]) * pos["size"]
                    elif pos["size"] < 0:
                        unrealized += (pos["avg_price"] - price) * abs(pos["size"])

        self.equity = total_value
        self.unrealized_pnl = unrealized
        self._step += 1
        self.history.append((self._step, self.equity))

    # ------------------------------------------------------
    def get_total_exposure(self, price_updates: dict = None) -> float:
        """
        Return total exposure (absolute notional).
        - If price_updates is None or {} → fallback to stored avg_price.
        - If price_updates provided with symbols → use those prices.
        """
        exposure = 0.0

        # ✅ Fix: treat None and {} identically (both fallback)
        if not price_updates:
            for sym, pos in self.positions.items():
                exposure += abs(pos["size"] * pos["avg_price"])
        else:
            for sym, price in price_updates.items():
                if sym in self.positions:
                    exposure += abs(self.positions[sym]["size"] * price)

        return exposure

    # ------------------------------------------------------
    def get_positions(self):
        """Return a copy of current positions."""
        return {k: v.copy() for k, v in self.positions.items()}

    def get_drawdown(self):
        """Return current drawdown as fraction of peak equity."""
        if not self.history:
            return 0.0
        peak = max(eq for _, eq in self.history)
        return (peak - self.equity) / peak if peak > 0 else 0.0

    def report(self):
        """Return a dictionary snapshot of the portfolio state."""
        return {
            "cash": round(self.cash, 2),
            "equity": round(self.equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "positions": self.get_positions(),
            "total_exposure": self.get_total_exposure(),
            "drawdown_pct": round(self.get_drawdown() * 100, 2),
        }
