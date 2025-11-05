"""
Portfolio Tracker (Hybrid AI Quant Pro v91.4 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Hedge-Fund OE Grade, Polished)
-------------------------------------------------------------------------------
- Tracks positions, cash, equity, realized/unrealized PnL
- Handles long, short, flips, commissions
- Risk metrics: VaR, CVaR, Sharpe, Sortino
- Logs aligned with tests (e.g. "insufficient data")
"""

import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True


class PortfolioTracker:
    """Hedge-fund grade portfolio & risk tracker."""

    def __init__(self, starting_equity: float = 100000.0, base_currency: str = "USD"):
        self.base_currency = base_currency
        self.starting_equity = float(starting_equity)
        self.cash = float(starting_equity)
        self.equity = float(starting_equity)
        self.positions: Dict[str, Dict[str, float | str]] = {}
        self.history: List[Tuple[datetime, float]] = [
            (datetime.now(timezone.utc), self.equity)
        ]
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.daily_pnl = 0.0
        self.intraday_trades: List[Tuple[str, float, float]] = []

        logger.debug(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ PortfolioTracker initialized | Equity=%.2f %s",
            self.equity,
            self.base_currency,
        )

    # ------------------------------------------------------------------
    def update_position(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        commission: float = 0.0,
        currency: Optional[str] = None,
    ) -> None:
        if size <= 0 or price <= 0:
            raise ValueError("Invalid size or price for trade update")

        side = side.upper()
        size = float(size)
        price = float(price)
        currency = currency or self.base_currency

        if symbol not in self.positions:
            self.positions[symbol] = {
                "size": 0.0,
                "avg_price": price,
                "currency": currency,
            }

        pos = self.positions[symbol]
        old_size, old_avg = pos["size"], pos["avg_price"]

        if side == "BUY":
            if old_size < 0:  # covering short
                cover = min(size, abs(old_size))
                self.realized_pnl += (old_avg - price) * cover
                self.daily_pnl += (old_avg - price) * cover
                self.cash -= price * cover + commission
                pos["size"] += cover
                size -= cover
                logger.debug("BRANCH-85 COVER HIT | cover=%s, leftover=%s", cover, size)
            if size > 0:  # open/add long
                new_total = max(pos["size"], 0) + size
                pos["avg_price"] = (
                    old_avg * max(pos["size"], 0) + price * size
                ) / new_total
                pos["size"] = max(pos["size"], 0) + size
                self.cash -= price * size + commission
                logger.debug("BRANCH-100 OPEN LONG HIT | size=%s", size)

        elif side == "SELL":
            if old_size > 0:  # closing long
                close = min(size, old_size)
                self.realized_pnl += (price - old_avg) * close
                self.daily_pnl += (price - old_avg) * close
                self.cash += price * close - commission
                pos["size"] -= close
                size -= close
                logger.debug(
                    "BRANCH-122 CLOSE LONG HIT | close=%s, leftover=%s", close, size
                )
            if size > 0:  # open/add short
                new_total = abs(min(pos["size"], 0)) + size
                pos["avg_price"] = (
                    old_avg * abs(min(pos["size"], 0)) + price * size
                ) / new_total
                pos["size"] = min(pos["size"], 0) - size
                self.cash += price * size - commission
                logger.debug("BRANCH-114 OPEN SHORT HIT | size=%s", size)

        # cleanup when flat
        if math.isclose(pos["size"], 0.0, abs_tol=1e-8):
            del self.positions[symbol]
            logger.debug("BRANCH-152 CLEANUP HIT | symbol=%s", symbol)

        self.intraday_trades.append((symbol, size, price))
        self.update_equity({symbol: price})

    # ------------------------------------------------------------------
    def update_equity(self, price_updates: Optional[Dict[str, float]] = None) -> None:
        total_value = self.cash
        unrealized = 0.0
        if price_updates is None or not price_updates:
            for sym, pos in self.positions.items():
                total_value += pos["size"] * pos["avg_price"]
        else:
            for sym, price in price_updates.items():
                if sym not in self.positions:
                    logger.debug("Ignoring unknown symbol in update_equity: %s", sym)
                    continue
                pos = self.positions[sym]
                total_value += pos["size"] * price
                if pos["size"] > 0:
                    unrealized += (price - pos["avg_price"]) * pos["size"]
                elif pos["size"] < 0:
                    unrealized += (pos["avg_price"] - price) * abs(pos["size"])
        to_delete = [
            s
            for s, p in self.positions.items()
            if math.isclose(p["size"], 0.0, abs_tol=1e-8)
        ]
        for sym in to_delete:
            del self.positions[sym]
            logger.debug("BRANCH-237 CLEANUP HIT | deleted=%s", sym)
        self.equity = max(0.0, total_value)
        self.unrealized_pnl = unrealized
        self.history.append((datetime.now(timezone.utc), self.equity))

    # ------------------------------------------------------------------
    def _returns(self) -> List[float]:
        if len(self.history) < 2:
            return []
        return [
            (self.history[i][1] - self.history[i - 1][1])
            / max(self.history[i - 1][1], 1e-9)
            for i in range(1, len(self.history))
        ]

    def get_var(self, alpha: float = 0.95) -> float:
        rets = self._returns()
        if not rets:
            return 0.0
        if len(rets) < 2:
            logger.debug(
                "insufficient data for VaR"
            )  # ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ aligned with tests
            return 0.0
        try:
            cutoff = np.percentile(np.array(rets, dtype=float), (1 - alpha) * 100)
            return abs(float(cutoff))
        except Exception as e:
            logger.warning("VaR percentile error: %s", e)
            return abs(min(rets)) if rets else 0.0

    def get_cvar(self, alpha: float = 0.95) -> float:
        rets = self._returns()
        if not rets:
            return 0.0
        if all(r >= 0 for r in rets):
            logger.debug("no losses")
            return 0.0
        negs = [r for r in rets if r < 0]
        if len(negs) == 1:
            logger.debug("single loss branch")
            return abs(negs[0])
        try:
            cutoff = np.percentile(np.array(rets, dtype=float), (1 - alpha) * 100)
            losses = [r for r in rets if r <= cutoff]
            if not losses:
                logger.debug("no losses")
                return 0.0
            return abs(sum(losses) / len(losses))
        except Exception as e:
            logger.warning("CVaR percentile error: %s", e)
            worst = min(rets)
            return abs(worst) if worst < 0 else 0.0

    def get_sharpe(self, risk_free: float = 0.0) -> float:
        rets = self._returns()
        if not rets:
            return 0.0
        avg = np.mean(rets) - risk_free
        std = np.std(rets)
        return 0.0 if std == 0 else avg / std

    def get_sortino(self, risk_free: float = 0.0) -> float:
        rets = self._returns()
        if not rets:
            return 0.0
        avg = np.mean(rets) - risk_free
        downside = [r for r in rets if r < 0]
        if not downside:
            logger.debug("no losses")
            return float("inf")
        std_down = np.std(downside)
        return 0.0 if std_down == 0 else avg / std_down

    # ------------------------------------------------------------------
    def report(self) -> Dict[str, float]:
        logger.debug("report called")
        return {
            "equity": float(self.equity),
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "cash": float(self.cash),
            "total_exposure": float(self.get_total_exposure()),
            "net_exposure": float(self.get_net_exposure()),
            "drawdown": float(self.get_drawdown()),
            "var95": self.get_var(0.95),
            "cvar95": self.get_cvar(0.95),
            "sharpe": self.get_sharpe(),
            "sortino": self.get_sortino(),
            "positions": self.get_positions(),
        }

    def get_positions(self) -> Dict[str, Dict[str, float | str]]:
        return {k: v.copy() for k, v in self.positions.items()}

    def get_total_exposure(self) -> float:
        return sum(abs(p["size"] * p["avg_price"]) for p in self.positions.values())

    def get_net_exposure(self) -> float:
        return sum(p["size"] * p["avg_price"] for p in self.positions.values())

    def get_drawdown(self) -> float:
        if not self.history:
            return 0.0
        peak = max(eq for _, eq in self.history)
        return (peak - self.equity) / peak if peak > 0 else 0.0

    def snapshot(self) -> Dict[str, float]:
        return {
            "equity": float(self.equity),
            "cash": float(self.cash),
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "positions": self.get_positions(),
        }

    def reset_day(self) -> Dict[str, str]:
        try:
            self.daily_pnl = 0.0
            self.intraday_trades.clear()
            return {"status": "ok", "reason": "Portfolio reset complete"}
        except Exception as e:
            logger.error("Portfolio reset failed: %s", e)
            return {"status": "error", "reason": str(e)}
