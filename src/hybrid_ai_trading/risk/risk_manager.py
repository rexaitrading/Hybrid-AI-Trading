from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    state_path: Optional[str] = None
    base_equity_fallback: float = 10000.0
    fail_closed: bool = True

    # Halts & limits
    day_loss_cap_pct: Optional[float] = None
    per_trade_notional_cap: Optional[float] = None
    max_trades_per_day: int = 0
    max_consecutive_losers: int = 0
    cooldown_bars: int = 0
    max_drawdown_pct: Optional[float] = None

    # Portfolio context
    equity: float = 100000.0
    max_leverage: Optional[float] = None
    max_portfolio_exposure: Optional[float] = None


class RiskManager:
    def __init__(
        self,
        cfg: Optional[RiskConfig] = None,
        *,
        starting_equity: Optional[float] = None,
        daily_loss_limit: Optional[float] = None,
        trade_loss_limit: Optional[float] = None,
        sharpe_min: Optional[float] = None,
        sortino_min: Optional[float] = None,
        roi_min: Optional[float] = None,
        max_leverage: Optional[float] = None,
        max_portfolio_exposure: Optional[float] = None,
        equity: Optional[float] = None,
        portfolio: Any = None,
        db_logger: Any = None,
        **_legacy,
    ) -> None:
        self.cfg = cfg if isinstance(cfg, RiskConfig) else RiskConfig()
        if equity is not None:
            self.cfg.equity = float(equity)
        if max_leverage is not None:
            self.cfg.max_leverage = float(max_leverage)
        if max_portfolio_exposure is not None:
            self.cfg.max_portfolio_exposure = float(max_portfolio_exposure)

        # guard knobs
        self.daily_loss_limit = daily_loss_limit
        self.trade_loss_limit = trade_loss_limit
        self.sharpe_min = sharpe_min
        self.sortino_min = sortino_min
        self.roi_min = roi_min

        self.portfolio = portfolio
        self.db_logger = db_logger

        # starting equity for engine assertions
        self.starting_equity = (
            float(starting_equity)
            if starting_equity is not None
            else float(self.cfg.equity)
        )

        # runtime metrics
        self.daily_pnl: float = 0.0
        self.equity_peak: float = self.starting_equity
        self.current_drawdown: float = 0.0

        # state (NB: day_start_equity uses base_equity_fallback by default)
        self._state: Dict[str, Any] = {
            "day": self._today(),
            "trades_today": 0,
            "consecutive_losers": 0,
            "cooldown_until_ts": None,
            "cooldown_reason": None,
            "halted_until_bar_ts": None,
            "halted_reason": None,
            "halted": False,
            "day_start_equity": float(self.cfg.base_equity_fallback),
            "day_realized_pnl": 0.0,
            "last_trade_bar_ts": None,
            "last_equity": float(self.starting_equity),
        }

        self.load_state(self.cfg.state_path or "")

        # try save once in __init__ (some tests count makedirs)
        try:
            self._save_state()
        except Exception:
            pass

    # -------- utilities
    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _daily_cap_amount(self) -> Optional[float]:
        """
        Return the negative daily loss cap amount (e.g., -100.0) based on today's base equity.
        Precedence:
          1) If cfg.day_loss_cap_pct is set -> use that percentage of day_start_equity (negative).
          2) Else if daily_loss_limit is set -> use that absolute (expected negative) value.
          3) Else -> default to 2% of day_start_equity (negative).
        """
        base = float(self._state.get("day_start_equity", self.cfg.base_equity_fallback))
        if self.cfg.day_loss_cap_pct is not None:
            return -abs(float(self.cfg.day_loss_cap_pct)) * base
        if self.daily_loss_limit is not None:
            return float(self.daily_loss_limit)
        return -0.02 * base  # DEFAULT: 2%

    @property
    def daily_loss_breached(self) -> bool:
        cap = self._daily_cap_amount()
        return cap is not None and float(
            self._state.get("day_realized_pnl", 0.0)
        ) <= float(cap)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "daily_loss_breached": self.daily_loss_breached,
            "drawdown": float(self.current_drawdown),
            "exposure": getattr(self.portfolio, "exposure", None),
            "leverage": getattr(self.portfolio, "leverage", None),
            "day": self._state.get("day"),
            "trades_today": int(self._state.get("trades_today", 0)),
            "cons_losers": int(self._state.get("consecutive_losers", 0)),
            "halted_reason": self._state.get("halted_reason") or "",
        }

    def _save_state(self) -> int:
        path = self.cfg.state_path
        if not path:
            return 0
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "state": self._state,
                        "daily_pnl": self.daily_pnl,
                        "equity_peak": self.equity_peak,
                        "current_drawdown": self.current_drawdown,
                    },
                    f,
                    ensure_ascii=False,
                )
            return 1
        except Exception as e:
            log.error("save_state failed: %s", e)
            return 0

    def save_state(self, path: str) -> int:
        old = self.cfg.state_path
        try:
            self.cfg.state_path = path
            return self._save_state()
        finally:
            self.cfg.state_path = old

    def load_state(self, path: str) -> bool:
        if not path or not os.path.exists(path):
            return False
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
            s = data.get("state") or {}
            if isinstance(s, dict):
                self._state.update(s)
            self.daily_pnl = float(data.get("daily_pnl", self.daily_pnl))
            self.equity_peak = float(data.get("equity_peak", self.equity_peak))
            self.current_drawdown = float(
                data.get("current_drawdown", self.current_drawdown)
            )
            return True
        except Exception as e:
            log.error("load_state failed: %s", e)
            return False

    # -------- day & portfolio
    def reset_day(self) -> Dict[str, str]:
        try:
            if self.portfolio and hasattr(self.portfolio, "reset_day"):
                self.portfolio.reset_day()
        except Exception as e:
            log.error("Portfolio reset_day failed: %s", e)
            return {"status": "error"}

        last_eq = float(self._state.get("last_equity", self.cfg.base_equity_fallback))
        self._state["day_start_equity"] = last_eq

        self._state["trades_today"] = 0
        self._state["consecutive_losers"] = 0
        self._state["cooldown_until_ts"] = None
        self._state["cooldown_reason"] = None
        self._state["halted_until_bar_ts"] = None
        self._state["halted_reason"] = None
        self._state["halted"] = False
        self._state["day_realized_pnl"] = 0.0
        self.daily_pnl = 0.0
        self.current_drawdown = 0.0
        self._state["day"] = self._today()
        log.info("Daily reset complete")
        return {"status": "ok"}

    def reset_day_if_needed(self, bar_ts_ms: int) -> None:
        if self._state.get("day") != self._today():
            self.reset_day()

    def record_close_pnl(self, realized: float, *, bar_ts_ms: int) -> None:
        self._state["day_realized_pnl"] = float(
            self._state.get("day_realized_pnl", 0.0)
        ) + float(realized)
        self.daily_pnl = float(self._state["day_realized_pnl"])
        if realized < 0:
            cons = int(self._state.get("consecutive_losers", 0)) + 1
            self._state["consecutive_losers"] = cons
            if self.cfg.cooldown_bars and self.cfg.cooldown_bars > 0:
                cap = int(self.cfg.max_consecutive_losers or 0)
                if (cap == 0) or (cap > 0 and cons >= cap):
                    until = int(bar_ts_ms) + int(self.cfg.cooldown_bars) * 3600_000
                    self._state["cooldown_until_ts"] = until
                    self._state["cooldown_reason"] = "COOLDOWN"
                    self._state["halted_until_bar_ts"] = until
                    self._state["halted_reason"] = "COOLDOWN"
        else:
            self._state["consecutive_losers"] = 0

    def on_fill(self, *, side: str, qty: float, px: float, bar_ts: int) -> None:
        self._state["trades_today"] = int(self._state.get("trades_today", 0)) + 1
        self._state["last_trade_bar_ts"] = int(bar_ts)

    def update_equity(self, equity: float) -> bool:
        try:
            e = float(equity)
        except Exception:
            return False
        self._state["last_equity"] = e
        self.equity_peak = max(self.equity_peak, e)
        if self.equity_peak > 0:
            self.current_drawdown = max(0.0, (self.equity_peak - e) / self.equity_peak)
        return True

    # -------- ratios (override in tests)
    def sharpe_ratio(self) -> Optional[float]:
        return None

    def sortino_ratio(self) -> Optional[float]:
        return None

    # -------- helpers / gates
    def _recalc_daily_loss_breached(self) -> bool:
        cap_amt = self._daily_cap_amount()
        realized = float(self._state.get("day_realized_pnl", 0.0))
        return cap_amt is not None and realized <= float(cap_amt)

    def control_signal(self, signal: str) -> str:
        s = (signal or "HOLD").strip().upper()
        if s not in ("BUY", "SELL", "HOLD"):
            s = "HOLD"
        if self._state.get("halted") or self.daily_loss_breached:
            if self.daily_loss_breached:
                log.warning(
                    "daily_loss: pnl=%s limit=%s",
                    self._state.get("day_realized_pnl", 0.0),
                    self._daily_cap_amount(),
                )
            return "HOLD"
        return s

    def approve_trade(self, symbol: str, side: str, *args) -> bool:
        if len(args) == 1:
            notional = args[0]
        elif len(args) >= 2:
            notional = args[-1]
        else:
            notional = None
        if notional is None or notional <= 0:
            log.warning("non-positive notional for approve_trade")
            return False
        return True

    def check_trade(self, symbol: str, side: str, qty: float, notional: float) -> bool:
        norm_side = self.control_signal(side)
        if norm_side == "HOLD":
            return False

        if self.roi_min is not None:
            roi_val = None
            try:
                roi_val = float(getattr(self, "roi", 0.0))
            except Exception:
                pass
            if roi_val is None or roi_val < float(self.roi_min):
                log.warning(
                    "ROI guard breached: roi=%s < min=%s", roi_val, self.roi_min
                )
                return False

        if self.sharpe_min is not None:
            try:
                sr = self.sharpe_ratio()
            except Exception as e:
                log.error("Sharpe ratio check failed: %s", e)
                return False
            if sr is None or sr < float(self.sharpe_min):
                log.warning(
                    "Sharpe guard breached: %.4f < %.4f",
                    sr or float("nan"),
                    float(self.sharpe_min),
                )
                return False

        if self.sortino_min is not None:
            try:
                so = self.sortino_ratio()
            except Exception as e:
                log.error("Sortino ratio check failed: %s", e)
                return False
            if so is None or so < float(self.sortino_min):
                log.warning(
                    "Sortino guard breached: %.4f < %.4f",
                    so or float("nan"),
                    float(self.sortino_min),
                )
                return False

        try:
            lev = (
                float(getattr(self.portfolio, "leverage", 0.0))
                if self.portfolio
                else 0.0
            )
            exp = (
                float(getattr(self.portfolio, "exposure", 0.0))
                if self.portfolio
                else 0.0
            )
        except Exception:
            lev, exp = 0.0, 0.0

        if self.cfg.max_leverage is not None and lev > float(self.cfg.max_leverage):
            log.warning("Leverage breach: %s > %s", lev, self.cfg.max_leverage)
            return False
        if self.cfg.max_portfolio_exposure is not None and exp > float(
            self.cfg.max_portfolio_exposure
        ) * float(self.cfg.equity):
            log.warning(
                "Exposure breach: %s > %s", exp, self.cfg.max_portfolio_exposure
            )
            return False

        try:
            if self.db_logger:
                self.db_logger.log(
                    {
                        "symbol": symbol,
                        "side": norm_side,
                        "qty": qty,
                        "notional": notional,
                    }
                )
        except Exception as e:
            log.error("DB log failed: %s", e)

        return True

    def allow_trade(
        self, *, notional: float, side: str, bar_ts: int
    ) -> Tuple[bool, Optional[str]]:
        force = os.getenv("FORCE_RISK_HALT", "").strip()
        if force:
            return False, force

        try:
            self.reset_day_if_needed(bar_ts)
        except Exception:
            return (False, "EXCEPTION") if self.cfg.fail_closed else (True, None)

        # DAILY LOSS  derive fresh each call (auto-clear if above cap)
        if self._recalc_daily_loss_breached():
            return False, "DAILY_LOSS"

        # DRAWDOWN
        if self.cfg.max_drawdown_pct is not None and self.current_drawdown is not None:
            if self.current_drawdown >= float(self.cfg.max_drawdown_pct):
                return False, "MAX_DRAWDOWN"

        # COOLDOWN / LOSERS
        cu = self._state.get("cooldown_until_ts")
        if isinstance(cu, int) and bar_ts <= cu:
            return False, "COOLDOWN"
        if isinstance(cu, int) and bar_ts > cu:
            self._state["cooldown_until_ts"] = None
            self._state["cooldown_reason"] = None
            self._state["halted_until_bar_ts"] = None
            self._state["halted_reason"] = None
            self._state["consecutive_losers"] = 0

        cons = int(self._state.get("consecutive_losers", 0))
        if self.cfg.max_consecutive_losers and cons >= int(
            self.cfg.max_consecutive_losers
        ):
            return False, "MAX_CONSECUTIVE_LOSERS"

        # per-trade notional cap
        if self.cfg.per_trade_notional_cap is not None and notional > float(
            self.cfg.per_trade_notional_cap
        ):
            return False, "NOTIONAL_CAP"

        # max trades/day
        if self.cfg.max_trades_per_day and int(
            self._state.get("trades_today", 0)
        ) >= int(self.cfg.max_trades_per_day):
            return False, "TRADES_PER_DAY"

        return True, None

    # Kelly sizing
    def kelly_size(self, edge: float, odds: float, regime: float = 1.0) -> float:
        try:
            e = float(edge)
            o = float(odds)
            r = float(regime)
            if o <= 0 or e < 0 or r <= 0:
                return 0.0
            f = e / o
        except Exception as ex:
            log.error("Kelly sizing failed: %s", ex)
            return 0.0
        if f < 0:
            return 0.0
        if f > 1:
            return 1.0
        return float(min(1.0, max(0.0, f * r)))
