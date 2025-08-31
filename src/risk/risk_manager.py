"""
RiskManager module.

Provides a class to enforce daily, per-trade, and leverage-based limits
for systematic and AI-driven trading strategies.
"""

from typing import Optional


class RiskManager:
    def __init__(
        self,
        daily_loss_limit: Optional[float] = -0.03,   # -3% default
        trade_loss_limit: Optional[float] = -0.01,   # -1% per trade
        max_leverage: float = 1.0,
        equity: float = 100000.0,
    ):
        self.daily_loss_limit = daily_loss_limit
        self.trade_loss_limit = trade_loss_limit
        self.max_leverage = max_leverage
        self.start_equity = equity
        self.daily_pnl: float = 0.0
        self.open_exposure: float = 0.0

    def check_trade(self, trade_return: float, trade_notional: float) -> bool:
        """
        Check if a trade is allowed based on risk rules.

        Parameters
        ----------
        trade_return : float
            Expected trade PnL (positive or negative).
        trade_notional : float
            Notional exposure size of the trade (price * qty).

        Returns
        -------
        bool
            True if allowed, False if blocked.
        """
        # Always allow profits (but still check exposure)
        if trade_return > 0:
            if (self.open_exposure + trade_notional) > self.max_leverage * self.start_equity:
                return False
            self.daily_pnl += trade_return
            self.open_exposure += trade_notional
            return True

        # Per-trade loss
        if self.trade_loss_limit is not None and trade_return <= self.trade_loss_limit * self.start_equity:
            return False

        # Tentative new PnL
        new_pnl = self.daily_pnl + trade_return

        # Daily stop-loss
        if self.daily_loss_limit is not None and new_pnl <= self.daily_loss_limit * self.start_equity:
            return False

        # Exposure check
        if (self.open_exposure + trade_notional) > self.max_leverage * self.start_equity:
            return False

        # Update state
        self.daily_pnl = new_pnl
        self.open_exposure += trade_notional
        return True

    def control_signal(self, signal: str) -> str:
        """
        Gate signals through risk filter.
        """
        if self.daily_loss_limit is not None and self.daily_pnl <= self.daily_loss_limit * self.start_equity:
            return "HOLD"
        return signal

    def reset_day(self):
        """Reset PnL + exposure at the start of day."""
        self.daily_pnl = 0.0
        self.open_exposure = 0.0
