# src/hybrid_ai_trading/performance_tracker.py

import logging
from statistics import mean, pstdev
from typing import List

logger = logging.getLogger(__name__)


class PerformanceTracker:
    def __init__(self, window: int = 100):
        self.window = window
        self.trades: List[float] = []
        self.equity_curve: List[float] = []

    # ----------------------------------------------------
    def record_trade(self, pnl: float):
        self.trades.append(pnl)
        if len(self.trades) > self.window:
            self.trades.pop(0)  # trim oldest
        logger.debug(f"Recorded trade: {pnl}")

    def record_equity(self, equity: float):
        self.equity_curve.append(equity)
        if len(self.equity_curve) > self.window:
            self.equity_curve.pop(0)
        logger.debug(f"Recorded equity: {equity}")

    # ----------------------------------------------------
    def win_rate(self) -> float:
        if not self.trades:
            logger.info("No trades → win_rate=0.0")
            return 0.0
        wins = sum(1 for t in self.trades if t > 0)
        return wins / len(self.trades)

    def payoff_ratio(self) -> float:
        if not self.trades:
            logger.info("No trades → payoff_ratio=0.0")
            return 0.0
        gains = [t for t in self.trades if t > 0]
        losses = [abs(t) for t in self.trades if t < 0]
        if not losses:
            logger.info("No losses → payoff_ratio=0.0")
            return 0.0
        avg_gain = mean(gains) if gains else 0.0
        avg_loss = mean(losses)
        return avg_gain / avg_loss if avg_loss > 0 else 0.0

    def sharpe_ratio(self, risk_free: float = 0.0) -> float:
        if len(self.trades) < 2:
            logger.info("Not enough trades → Sharpe=0.0")
            return 0.0
        try:
            avg = mean(self.trades)
            std = pstdev(self.trades)
        except Exception as e:
            logger.error(f"Sharpe calc error: {e}", exc_info=True)
            return 0.0
        return (avg - risk_free) / std if std > 0 else 0.0

    def sortino_ratio(self, risk_free: float = 0.0) -> float:
        if len(self.trades) < 2:
            logger.info("Not enough trades → Sortino=0.0")
            return 0.0
        avg = mean(self.trades)
        downside_trades = [t for t in self.trades if t < 0]

        if not downside_trades:
            logger.warning("No downside trades → fallback denom=1.0")
            downside = 1.0
        else:
            try:
                downside = pstdev(downside_trades)
            except Exception as e:
                logger.error(f"Sortino calc error: {e}", exc_info=True)
                return 0.0
            if downside == 0:
                logger.warning("Downside stdev=0 → fallback denom=1.0")
                downside = 1.0

        return (avg - risk_free) / downside

    # ----------------------------------------------------
    def get_equity_curve(self) -> List[float]:
        return list(self.equity_curve)

    def get_drawdown(self) -> float:
        if not self.equity_curve:
            logger.info("No equity data → drawdown=0.0")
            return 0.0
        peak = max(self.equity_curve)
        trough = self.equity_curve[-1]
        return (peak - trough) / peak if peak > 0 else 0.0
