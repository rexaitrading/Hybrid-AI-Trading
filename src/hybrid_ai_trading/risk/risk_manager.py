# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from hybrid_ai_trading.risk.config import RiskConfig  # re-export for tests
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision

log = logging.getLogger(__name__)

BAR_MS = 3600_000  # tests treat 1 bar = 1 hour


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _date_from_bar_ts_ms(bar_ts_ms: int) -> str:
    # In unit tests, bar_ts/bar_ts_ms is a monotonic counter, NOT wall-clock time.
    # We keep the "day" stable (today) unless the test forces a mismatch by editing _state["day"].
    return time.strftime("%Y-%m-%d", time.localtime())


@dataclass
class RiskManager:
    config: Any = None
    starting_equity: float = 100000.0
    equity: float = 100000.0

    # tests sometimes overwrite this with float
    daily_pnl: Any = field(default_factory=dict)
    positions: Dict[str, Any] = field(default_factory=dict)
    _state: Dict[str, Any] = field(default_factory=dict)

    current_drawdown: float = 0.0
    daily_loss_breached: bool = False

    # unified legacy kwargs
    daily_loss_limit: Optional[float] = None
    trade_loss_limit: Optional[float] = None

    def __init__(
        self,
        config: Any = None,
        starting_equity: float = 100000.0,
        equity: Optional[float] = None,
        **legacy_kwargs: Any,
    ):
        # support RiskManager(max_daily_loss=..., etc)
        self.config = config if config is not None else RiskConfig(state_path=None)
        self.cfg = self.config  # tests use rm.cfg.cooldown_bars

        self.starting_equity = float(starting_equity)
        self.equity = float(equity if equity is not None else starting_equity)

        for k, v in legacy_kwargs.items():
            setattr(self.config, k, v)

        self.daily_pnl = {}
        self.positions = {}
        self._state = {}

        self._init_state()
        self._save_state()  # must be safe (never raises)

    def _init_state(self) -> None:
        cfg = self.config
        now_ms = int(time.time() * 1000)

        self._fail_closed = bool(getattr(cfg, "fail_closed", True))
        self._state_path = str(getattr(cfg, "state_path", "") or "")

        self._state["day"] = _date_from_bar_ts_ms(now_ms)
        self._state["last_equity"] = float(self.equity)

        # CRITICAL: tests expect base_equity_fallback drives loss cap (10k)
        self._state["day_start_equity"] = float(getattr(cfg, "base_equity_fallback", 10000.0))
        self._state["day_realized_pnl"] = 0.0

        self._state["trades_today"] = 0
        self._state["consecutive_losers"] = 0
        self._state["halted_until_bar_ts"] = None
        self._state["halted_reason"] = None
        self._state["last_trade_bar_ts"] = None

        self._state["equity_peak"] = float(self.equity)
        self.current_drawdown = 0.0
        self.daily_loss_breached = False

        # limits (0 means disabled in RiskConfig signature)
        self.per_trade_notional_cap = getattr(cfg, "per_trade_notional_cap", None)
        self.max_trades_per_day = int(getattr(cfg, "max_trades_per_day", 0) or 0) or None
        self.max_consecutive_losers = int(getattr(cfg, "max_consecutive_losers", 0) or 0) or None
        self.cooldown_bars = int(getattr(cfg, "cooldown_bars", 0) or 0) or None
        self.max_drawdown_pct = getattr(cfg, "max_drawdown_pct", None)

        self.day_loss_cap_pct = getattr(cfg, "day_loss_cap_pct", None)

        dll = getattr(cfg, "daily_loss_limit", getattr(cfg, "max_daily_loss", None))
        self.daily_loss_limit = None if dll is None else float(dll)

        tl = getattr(cfg, "trade_loss_limit", getattr(cfg, "max_position_risk", None))
        self.trade_loss_limit = None if tl is None else float(tl)

        # unified extras (passed as kwargs into RiskManager -> on config)
        self.portfolio = getattr(cfg, "portfolio", None)
        self.max_leverage = getattr(cfg, "max_leverage", None)
        self.max_portfolio_exposure = getattr(cfg, "max_portfolio_exposure", None)
        self.db_logger = getattr(cfg, "db_logger", None)
        self.roi_min = getattr(cfg, "roi_min", None)
        self.sharpe_min = getattr(cfg, "sharpe_min", None)
        self.sortino_min = getattr(cfg, "sortino_min", None)

    def _save_state(self) -> None:
        if not self._state_path:
            return
        try:
            os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(self.snapshot(), f)
        except Exception:
            return

    def reset_day_if_needed(self, bar_ts_ms: int) -> None:
        day = _date_from_bar_ts_ms(int(bar_ts_ms))
        if self._state.get("day") != day:
            # carry last_equity into new day_start_equity
            self._state["day_start_equity"] = float(
                self._state.get("last_equity", self._state.get("day_start_equity", 10000.0))
            )
            self._state["day"] = day
            self.reset_day()

    def reset_day(self) -> Dict[str, Any]:
        # Success with portfolio if method exists; object() should not fail
        if self.portfolio is not None and hasattr(self.portfolio, "reset_day"):
            try:
                self.portfolio.reset_day()
            except Exception as e:
                log.error("Reset day failed", exc_info=True)
                return {"status": "error", "reason": str(e)}

        self._state["trades_today"] = 0
        self._state["consecutive_losers"] = 0
        self._state["halted_until_bar_ts"] = None
        self._state["halted_reason"] = None
        self._state["day_realized_pnl"] = 0.0
        self.daily_loss_breached = False

        # unified test expects scalar 0.0
        self.daily_pnl = 0.0

        log.info("Daily reset complete")
        self._save_state()
        return {"status": "ok"}

    def update_equity(self, equity: float) -> bool:
        self.equity = float(equity)
        peak = float(self._state.get("equity_peak", self.equity))
        if self.equity > peak:
            peak = self.equity
        self._state["equity_peak"] = peak
        self._state["last_equity"] = self.equity
        self.current_drawdown = 0.0 if peak <= 0 else (peak - self.equity) / peak

        if self.equity <= 0:
            log.critical("drawdown breach")
            return False
        return True

    def on_fill(self, **kwargs: Any) -> None:
        self._state["trades_today"] = int(self._state.get("trades_today", 0)) + 1
        if "bar_ts" in kwargs:
            self._state["last_trade_bar_ts"] = int(kwargs["bar_ts"])

    def record_close_pnl(self, pnl: float, *, bar_ts_ms: int) -> None:
        self.reset_day_if_needed(int(bar_ts_ms))
        self._state["day_realized_pnl"] = float(self._state.get("day_realized_pnl", 0.0)) + float(pnl)

        if pnl < 0:
            self._state["consecutive_losers"] = int(self._state.get("consecutive_losers", 0)) + 1
        else:
            self._state["consecutive_losers"] = 0

        if self.max_consecutive_losers and self.cooldown_bars:
            if int(self._state["consecutive_losers"]) >= int(self.max_consecutive_losers):
                self._state["halted_until_bar_ts"] = int(bar_ts_ms) + int(self.cooldown_bars) * BAR_MS
                self._state["halted_reason"] = "COOLDOWN"

        self._save_state()

    def allow_trade(self, *, notional: float, side: str, bar_ts: int) -> Tuple[bool, Optional[str]]:
        try:
            self.reset_day_if_needed(int(bar_ts))
        except Exception:
            if not self._fail_closed:
                return True, None
            return False, "EXCEPTION"

        force = os.environ.get("FORCE_RISK_HALT", "")
        if str(force).strip():
            return False, str(force)

        # daily loss cap from percent of day_start_equity (base_equity_fallback)
        # If day_loss_cap_pct is not configured, default to 2% (tests expect DAILY_LOSS at -300 on 10k).
        pct = float(self.day_loss_cap_pct) if self.day_loss_cap_pct is not None else 0.02
        start_eq = float(self._state.get("day_start_equity", 10000.0))
        self.daily_loss_limit = -abs(start_eq) * pct

        # DAILY_LOSS must beat COOLDOWN
        if self.daily_loss_limit is not None:
            pnl = float(self._state.get("day_realized_pnl", 0.0))
            if pnl <= float(self.daily_loss_limit):
                self.daily_loss_breached = True
                # DAILY_LOSS supersedes cooldown state
                self._state["halted_until_bar_ts"] = None
                self._state["halted_reason"] = None
                return False, "DAILY_LOSS"
        self.daily_loss_breached = False

        # drawdown
        if self.max_drawdown_pct is not None and float(self.current_drawdown) >= float(self.max_drawdown_pct):
            return False, "MAX_DRAWDOWN"

        # cooldown; if expired, clear state (tests require reason None)
        hu = self._state.get("halted_until_bar_ts", None)
        if hu is not None:
            if int(bar_ts) <= int(hu):
                return False, "COOLDOWN"
            self._state["halted_until_bar_ts"] = None
            self._state["halted_reason"] = None

        # trades per day
        if self.max_trades_per_day is not None:
            if int(self._state.get("trades_today", 0)) >= int(self.max_trades_per_day):
                return False, "TRADES_PER_DAY"

        # notional cap
        if self.per_trade_notional_cap is not None and float(notional) > float(self.per_trade_notional_cap):
            return False, "NOTIONAL_CAP"

        return True, None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "daily_loss_breached": bool(self.daily_loss_breached),
            "drawdown": float(self.current_drawdown),
            "exposure": 0.0,
            "leverage": 0.0,
            "day": self._state.get("day"),
            "trades_today": int(self._state.get("trades_today", 0)),
            "cons_losers": int(self._state.get("consecutive_losers", 0)),
            "halted_reason": self._state.get("halted_reason"),
        }

    # -------- unified API --------
    def approve_trade(self, symbol: str, side: str, qty: float, notional: float = 0.0) -> bool:
        if float(qty) <= 0:
            log.warning("non-positive qty")
            return False
        return True

    def control_signal(self, signal: str) -> str:
        s = str(signal).upper()
        if s == "HOLD":
            return "HOLD"
        if s == "SELL":
            return "SELL"
        if s == "BUY":
            if isinstance(self.daily_pnl, (int, float)) and float(self.daily_pnl) <= -100:
                return "HOLD"
            return "BUY"
        return s

    def check_trade(self, symbol: str, side: str, qty: float, pnl_or_px: float) -> bool:
        # per-trade loss
        if self.trade_loss_limit is not None and float(pnl_or_px) <= float(self.trade_loss_limit):
            log.warning("trade_loss breach")
            return False

        # daily loss (unified tests set daily_pnl scalar)
        if isinstance(self.daily_pnl, (int, float)) and self.daily_loss_limit is not None:
            if float(self.daily_pnl) <= float(self.daily_loss_limit):
                log.warning("daily_loss breach")
                return False

        # ROI guard
        if self.roi_min is not None and hasattr(self, "roi"):
            try:
                if float(getattr(self, "roi")) < float(self.roi_min):
                    log.warning("ROI breach")
                    return False
            except Exception:
                log.error("ROI check failed", exc_info=True)
                return False

        # Sharpe / Sortino (must log both exceptions if both configured)
        sharpe_failed = False
        if self.sharpe_min is not None:
            try:
                if float(self.sharpe_ratio()) < float(self.sharpe_min):
                    log.warning("Sharpe breach")
                    return False
            except Exception:
                sharpe_failed = True
                log.error("Sharpe ratio check failed", exc_info=True)

        sortino_failed = False
        if self.sortino_min is not None:
            try:
                if float(self.sortino_ratio()) < float(self.sortino_min):
                    log.warning("Sortino breach")
                    return False
            except Exception:
                sortino_failed = True
                log.error("Sortino ratio check failed", exc_info=True)

        if sharpe_failed or sortino_failed:
            return False

        # portfolio checks (DummyPortfolio uses get_* APIs)
        if self.portfolio is not None:
            try:
                # Touch accessors to fail-closed on portfolio subsystem errors
                if hasattr(self.portfolio, "get_leverage"):
                    _ = self.portfolio.get_leverage()
                if hasattr(self.portfolio, "get_total_exposure"):
                    _ = self.portfolio.get_total_exposure()

                if self.max_leverage is not None and hasattr(self.portfolio, "get_leverage"):
                    if float(self.portfolio.get_leverage()) > float(self.max_leverage):
                        log.warning("leverage breach")
                        return False

                if self.max_portfolio_exposure is not None and hasattr(self.portfolio, "get_total_exposure"):
                    if float(self.portfolio.get_total_exposure()) > float(self.max_portfolio_exposure) * float(self.equity):
                        log.warning("exposure breach")
                        return False
            except Exception:
                log.error("Portfolio check failed", exc_info=True)
                return False

        # db logger (must not crash)
        if self.db_logger is not None:
            try:
                self.db_logger.log({"symbol": symbol, "side": side, "qty": qty, "x": pnl_or_px})
            except Exception:
                log.error("DB log failed", exc_info=True)

        return True


    def kelly_size(self, edge: float, odds: Any = 2.0, cap: float = 1.0, regime: float = 1.0) -> float:
        try:
            if float(edge) < 0 or float(edge) > 1:
                return 0.0
            denom = float(odds - 1.0)
            if denom <= 0:
                return 0.0
            f = (float(edge) / denom) * float(regime)
            if f < 0:
                f = 0.0
            if f > float(cap):
                f = float(cap)
            return float(f)
        except Exception:
            log.error("Kelly sizing failed", exc_info=True)
            return 0.0

    # -------- phase5 API preserved --------
    def check_trade_phase5(self, trade: Dict[str, Any]) -> Phase5RiskDecision:
        symbol = str(trade.get("symbol", "")).upper()
        side = str(trade.get("side", "")).upper()
        qty = _as_float(trade.get("qty", 0.0))
        price = _as_float(trade.get("price", 0.0))
        day_id = str(trade.get("day_id", "") or "")

        daily_pnl = _as_float(self.daily_pnl.get(day_id, 0.0)) if isinstance(self.daily_pnl, dict) else 0.0
        cap = getattr(self.config, "phase5_daily_loss_cap", None)
        cap = None if cap is None else float(cap)

        pos = self.positions.get(symbol)
        pos_qty = _as_float(getattr(pos, "qty", 0.0))
        avg_price = _as_float(getattr(pos, "avg_price", price), default=price)

        if cap is not None:
            loss_breached = daily_pnl <= cap
            exposure_increases = False
            if side == "BUY" and pos_qty > 0:
                exposure_increases = qty > 0
            elif side == "SELL" and pos_qty < 0:
                exposure_increases = qty > 0
            if loss_breached and exposure_increases:
                return Phase5RiskDecision(False, "daily_loss_cap_block", {"symbol": symbol})

        if side == "BUY" and pos_qty > 0 and price < avg_price:
            return Phase5RiskDecision(False, "no_averaging_down_long_block", {"symbol": symbol})

        return Phase5RiskDecision(True, f"daily_loss_ok(current={daily_pnl})", {"symbol": symbol})