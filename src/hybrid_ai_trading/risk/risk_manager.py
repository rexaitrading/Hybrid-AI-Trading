"""
Risk Manager (Hybrid AI Quant Pro v16.6 – ROI + Sharpe/Sortino Guardrails)
--------------------------------------------------------------------------
Responsibilities:
- Enforce per-trade and daily loss limits
- Monitor leverage, portfolio exposure, and drawdowns
- Provide Kelly sizing (with invalid input + special cases)
- Override trade signals when risk breached
- Enforce profitability guardrails:
  * ROI threshold
  * Sharpe ratio minimum
  * Sortino ratio minimum
- Reset daily PnL and optionally portfolio state
- Structured logging for every branch (audit-friendly)
"""

import logging
import math
from typing import Optional

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.performance_tracker import PerformanceTracker

logger = logging.getLogger("hybrid_ai_trading.risk.risk_manager")


class RiskManager:
    def __init__(
        self,
        daily_loss_limit: Optional[float] = -0.03,
        trade_loss_limit: Optional[float] = -0.01,
        max_leverage: float = 5.0,
        equity: float = 100000.0,
        max_portfolio_exposure: float = 0.5,
        max_drawdown: float = -0.20,
        roi_min: float = -1.0,  # ✅ New: enforce ROI guardrail
        sharpe_min: float = -1.0,  # ✅ New: enforce Sharpe guardrail
        sortino_min: float = -1.0,  # ✅ New: enforce Sortino guardrail
        portfolio: Optional[PortfolioTracker] = None,
        performance_tracker: Optional[PerformanceTracker] = None,
    ):
        self.daily_loss_limit = daily_loss_limit
        self.trade_loss_limit = trade_loss_limit
        self.max_leverage = max_leverage
        self.starting_equity = equity
        self.max_portfolio_exposure = max_portfolio_exposure
        self.max_drawdown = max_drawdown

        # ✅ New guardrails
        self.roi_min = roi_min
        self.sharpe_min = sharpe_min
        self.sortino_min = sortino_min

        self.daily_pnl: float = 0.0
        self.portfolio = portfolio
        self.performance_tracker = performance_tracker

    # --------------------------------------------------
    def check_trade(self, pnl: float, trade_notional: Optional[float] = None) -> bool:
        """
        Return True if trade passes all risk checks, else False.

        pnl is expressed as a fraction of starting equity (e.g., -0.02 = -2%).
        """
        new_daily_pnl = self.daily_pnl + pnl

        # Daily loss guard
        if self.daily_loss_limit is not None and new_daily_pnl <= self.daily_loss_limit:
            logger.warning(
                f"[RiskManager] ❌ Daily Loss Breach | "
                f"DailyPnL={new_daily_pnl:.4f} | Cap={self.daily_loss_limit:.2%}"
            )
            return False

        # Per-trade guard
        if self.trade_loss_limit is not None and pnl <= self.trade_loss_limit:
            logger.warning(
                f"[RiskManager] ❌ Trade Loss Breach | "
                f"TradePnL={pnl:.4f} | Cap={self.trade_loss_limit:.2%}"
            )
            return False

        # Leverage guard
        if trade_notional and trade_notional > self.max_leverage * self.starting_equity:
            logger.warning(
                f"[RiskManager] ❌ Leverage Breach | Notional={trade_notional:.2f} > "
                f"{self.max_leverage:.1f}× Equity"
            )
            return False

        # Exposure guard
        if self.portfolio:
            try:
                current_exposure = self.portfolio.get_total_exposure()
                logger.debug(f"[RiskManager] ℹ️ Exposure fetched: {current_exposure:.2f}")
            except Exception as e:
                logger.debug(f"[RiskManager] ⚠️ get_total_exposure failed ({e}) → fallback")
                current_exposure = sum(
                    abs(pos.get("size", 0.0)) * pos.get("avg_price", 0.0)
                    for pos in self.portfolio.positions.values()
                )

            projected_exposure = current_exposure + (trade_notional or 0.0)
            exposure_ratio = projected_exposure / self.starting_equity

            if exposure_ratio > self.max_portfolio_exposure:
                logger.warning(
                    f"[RiskManager] ❌ Exposure Breach | "
                    f"Exposure={exposure_ratio:.2%} > Cap={self.max_portfolio_exposure:.2%}"
                )
                return False
            logger.debug(f"[RiskManager] ✅ Exposure Safe | {exposure_ratio:.2%}")

        # Drawdown guard
        if (
            self.portfolio
            and self.portfolio.equity is not None
            and self.portfolio.equity < (1 + self.max_drawdown) * self.starting_equity
        ):
            logger.warning(
                f"[RiskManager] ❌ Drawdown Breach | Equity={self.portfolio.equity:.2f}"
            )
            return False

        # ✅ ROI guardrail
        if self.portfolio:
            roi = (self.portfolio.equity - self.starting_equity) / self.starting_equity
            if roi < self.roi_min:
                logger.warning(
                    f"[RiskManager] ❌ ROI Breach | ROI={roi:.2%} < Min={self.roi_min:.2%}"
                )
                return False

        # ✅ Sharpe/Sortino guardrails
        if self.performance_tracker:
            sharpe = self.performance_tracker.sharpe_ratio()
            sortino = self.performance_tracker.sortino_ratio()
            if sharpe < self.sharpe_min:
                logger.warning(
                    f"[RiskManager] ❌ Sharpe Breach | Sharpe={sharpe:.2f} < Min={self.sharpe_min:.2f}"
                )
                return False
            if sortino < self.sortino_min:
                logger.warning(
                    f"[RiskManager] ❌ Sortino Breach | Sortino={sortino:.2f} < Min={self.sortino_min:.2f}"
                )
                return False

        # Passed all checks
        self.daily_pnl = new_daily_pnl
        logger.info(
            f"[RiskManager] ✅ Trade Allowed | PnL={pnl:.4f}, DailyPnL={self.daily_pnl:.4f}"
        )
        return True

    # --------------------------------------------------
    def kelly_size(self, win_rate: float, win_loss_ratio: float) -> float:
        """Return Kelly fraction, clamped [0,1]."""
        try:
            if (
                win_loss_ratio <= 0
                or math.isinf(win_loss_ratio)
                or not (0 <= win_rate <= 1)
            ):
                logger.debug("[RiskManager] ℹ️ Invalid Kelly inputs → 0.0")
                return 0.0

            if win_rate == 1.0:
                logger.debug("[RiskManager] ✅ Kelly: perfect certainty → 1.0")
                return 1.0

            kelly_fraction = win_rate - (1 - win_rate) / win_loss_ratio
            return max(0.0, min(kelly_fraction, 1.0))
        except Exception as e:
            logger.error(f"[RiskManager] ❌ Kelly sizing failed: {e}")
            return 0.0

    # --------------------------------------------------
    def control_signal(self, signal: str) -> str:
        """Return HOLD if risk breached, else pass signal unchanged."""
        if signal.upper() == "HOLD":
            return "HOLD"

        if self.daily_loss_limit is not None and self.daily_pnl <= self.daily_loss_limit:
            logger.info("[RiskManager] ⚠️ Risk breached → overriding signal to HOLD")
            return "HOLD"

        return signal.upper()

    # --------------------------------------------------
    def reset_day(self):
        """Reset daily PnL and optionally portfolio state."""
        self.daily_pnl = 0.0
        if self.portfolio and hasattr(self.portfolio, "reset_day"):
            self.portfolio.reset_day()
        logger.info("[RiskManager] 🔄 Daily reset complete")
