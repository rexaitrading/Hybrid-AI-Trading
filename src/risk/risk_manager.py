"""
RiskManager module.

Provides a class to enforce daily and per-trade loss limits
for systematic and AI-driven trading strategies.
"""

from typing import Optional


class RiskManager:
    """
    A simple risk manager enforcing daily and per-trade risk limits,
    and gating trading signals (BUY/SELL/HOLD).

    Attributes
    ----------
    daily_loss_limit : Optional[float]
        Maximum cumulative daily loss allowed (as a negative decimal, e.g., -0.03 = -3%).
        If None, daily loss is not checked.
    trade_loss_limit : Optional[float]
        Maximum loss allowed per individual trade (as a negative decimal).
        If None, per-trade losses are not checked.
    daily_pnl : float
        Tracks cumulative daily profit & loss (P&L).
    """

    def __init__(
        self,
        daily_loss_limit: Optional[float] = -0.03,
        trade_loss_limit: Optional[float] = -0.01,
    ):
        self.daily_loss_limit = daily_loss_limit
        self.trade_loss_limit = trade_loss_limit
        self.daily_pnl: float = 0.0

    def check_trade(self, trade_return: float) -> bool:
        """
        Check whether a trade is allowed under current risk constraints.

        Parameters
        ----------
        trade_return : float
            The return of the proposed trade (positive for profit, negative for loss).

        Returns
        -------
        bool
            True if the trade is allowed, False if blocked by risk rules.
        """
        # Always allow profits
        if trade_return > 0:
            self.daily_pnl += trade_return
            return True

        # Check per-trade loss limit
        if self.trade_loss_limit is not None and trade_return <= self.trade_loss_limit:
            return False

        # Tentatively update PnL
        new_pnl = self.daily_pnl + trade_return

        # Check daily loss limit
        if self.daily_loss_limit is not None and new_pnl <= self.daily_loss_limit:
            return False

        # Update state and allow
        self.daily_pnl = new_pnl
        return True

    def control_signal(self, signal: str) -> str:
        """
        Gate trading signals through risk rules.

        Parameters
        ----------
        signal : str
            Trading signal ("BUY", "SELL", "HOLD").

        Returns
        -------
        str
            Either the original signal (if risk rules allow) or "HOLD" if blocked.
        """
        # Block everything if daily loss limit already hit
        if self.daily_loss_limit is not None and self.daily_pnl <= self.daily_loss_limit:
            return "HOLD"

        # HOLD signals always pass
        if signal == "HOLD":
            return "HOLD"

        # BUY/SELL allowed only if within risk
        return signal

    def reset_day(self) -> None:
        """
        Reset daily PnL at the start of a new trading day.
        """
        self.daily_pnl = 0.0
