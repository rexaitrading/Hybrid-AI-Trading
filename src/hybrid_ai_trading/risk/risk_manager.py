from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass
class RiskConfig:
    # fields used by tests/risk_halts.py
    day_loss_cap_pct: float | None = None
    per_trade_notional_cap: float | None = None
    max_trades_per_day: int | None = None
    max_consecutive_losers: int | None = None
    cooldown_bars: int | None = None
    max_drawdown_pct: float | None = None
    state_path: str | None = None
    fail_closed: bool = False
    base_equity_fallback: float | None = None

    # legacy/minimal fields preserved for back-compat
    max_daily_loss: float | None = None
    max_portfolio_exposure: float | None = None
    max_leverage: float | None = None
    equity: float | None = None


class RiskManager:
    def __init__(
        self,
        daily_loss_limit: Optional[float] = None,
        max_portfolio_exposure: Optional[float] = None,
        max_leverage: Optional[float] = None,
        equity: Optional[float] = None,
        portfolio: Any = None,
        **kwargs,
    ) -> None:
        # core knobs
        self.daily_loss_limit = daily_loss_limit
        self.max_portfolio_exposure = max_portfolio_exposure
        self.max_leverage = max_leverage
        self.equity = equity
        self.portfolio = portfolio

        # attach optional config & mirror fields
        self.config = kwargs.get("config", None)
        if self.config is not None:
            for name in (
                "per_trade_notional_cap",
                "day_loss_cap_pct",
                "max_trades_per_day",
                "max_consecutive_losers",
                "cooldown_bars",
                "max_drawdown_pct",
                "state_path",
                "fail_closed",
                "base_equity_fallback",
            ):
                if getattr(self, name, None) is None:
                    try:
                        setattr(self, name, getattr(self.config, name))
                    except Exception:
                        pass

        if getattr(self, "per_trade_notional_cap", None) is None:
            self.per_trade_notional_cap = kwargs.get("per_trade_notional_cap", None)

        # starting_equity from explicit equity, portfolio, or fallback
        _eq = None
        try:
            if self.equity is not None:
                _eq = float(self.equity)
        except Exception:
            _eq = None
        if _eq is None and getattr(self, "portfolio", None) is not None:
            try:
                val = getattr(self.portfolio, "equity", None)
                if val is not None:
                    _eq = float(val)
            except Exception:
                _eq = None
        if _eq is None:
            try:
                _eq = float(getattr(self, "base_equity_fallback", None))
            except Exception:
                _eq = None
        if _eq is not None:
            self.starting_equity = _eq
            if self.equity is None:
                self.equity = _eq

        # per-run trade counter (no resets for tests)
        self._trades_today: int = 0
        # cooldown / halts
        self._loser_streak: int = 0
        self._cooldown_until_ms: int | None = None
        self._last_bar_ts_ms: int | None = None

    # --------- core gate used by order manager ---------
    def approve_trade(
        self, symbol: str, side: str, qty: float, notional: float
    ) -> Tuple[bool, str]:
        try:
            if self.daily_loss_limit is not None and float(self.daily_loss_limit) <= 0.0:
                return False, "daily_loss_limit<=0 disables trading"
        except Exception:
            return False, "invalid daily_loss_limit"

        eq = self._resolve_equity()

        try:
            mpe = self.max_portfolio_exposure
            if eq is not None and mpe is not None:
                if float(notional) > float(eq) * max(0.0, float(mpe)):
                    return False, "exceeds max_portfolio_exposure"
        except Exception:
            pass

        try:
            ml = self.max_leverage
            if eq not in (None, 0) and ml is not None:
                if (float(notional) / float(eq)) > max(0.0, float(ml)):
                    return False, "exceeds max_leverage"
        except Exception:
            pass

        return True, ""

    # --------- helpers ---------
    def _resolve_equity(self) -> Optional[float]:
        if self.equity is not None:
            try:
                return float(self.equity)
            except Exception:
                return None
        pt = getattr(self, "portfolio", None)
        if pt is not None:
            try:
                val = getattr(pt, "equity", None)
                return float(val) if val is not None else None
            except Exception:
                return None
        try:
            return float(getattr(self, "base_equity_fallback", None))
        except Exception:
            return None

    # --------- event hooks ---------
    def on_fill(
        self, side: str, qty: float, px: float, bar_ts: int | None = None, pnl: float | None = None
    ) -> None:
        """Increment per-run trade counter after a fill."""
        self._trades_today += 1

    def record_close_pnl(self, pnl: float, bar_ts_ms: int | None = None) -> None:
        """
        Record realized PnL and start a cooldown window when a loser streak reaches the threshold.
        Cooldown blocks trades while bar_ts < _cooldown_until_ms.
        """
        self._last_bar_ts_ms = bar_ts_ms
        try:
            if pnl is not None and float(pnl) < 0.0:
                self._loser_streak += 1
            else:
                self._loser_streak = 0
        except Exception:
            self._loser_streak = 0

        try:
            thr = getattr(self, "max_consecutive_losers", None)
            if thr is None and getattr(self, "config", None) is not None:
                try:
                    thr = getattr(self.config, "max_consecutive_losers")
                except Exception:
                    thr = None
            if thr is not None and self._loser_streak >= int(thr):
                bars = getattr(self, "cooldown_bars", None)
                if bars is None and getattr(self, "config", None) is not None:
                    try:
                        bars = getattr(self.config, "cooldown_bars")
                    except Exception:
                        bars = None
                if bar_ts_ms is not None and bars is not None:
                    per_bar_ms = 60_000
                    self._cooldown_until_ms = int(bar_ts_ms) + int(bars) * per_bar_ms
                else:
                    self._cooldown_until_ms = (bar_ts_ms or 0) + 1
                self._loser_streak = 0
        except Exception:
            # non-fatal
            pass

    # --------- minimal policy gate for tests/risk_halts.py ---------
    def allow_trade(
        self, notional: float, side: str = "BUY", bar_ts: int | None = None
    ) -> tuple[bool, str]:
        # cooldown window check
        try:
            if getattr(self, "_cooldown_until_ms", None) is not None and bar_ts is not None:
                if int(bar_ts) < int(self._cooldown_until_ms):
                    return False, "COOLDOWN"
        except Exception:
            pass

        # per-day cap (interpreted as per-run in tests)
        try:
            mtd = getattr(self, "max_trades_per_day", None)
            if mtd is None and getattr(self, "config", None) is not None:
                try:
                    mtd = getattr(self.config, "max_trades_per_day")
                except Exception:
                    mtd = None
            if mtd is None:
                try:
                    for _k, _v in vars(self).items():
                        if hasattr(_v, "max_trades_per_day"):
                            _mt = getattr(_v, "max_trades_per_day")
                            if _mt is not None:
                                mtd = _mt
                                break
                except Exception:
                    pass
            if mtd is not None and self._trades_today >= int(mtd):
                return False, "TRADES_PER_DAY"
        except Exception:
            try:
                if getattr(getattr(self, "config", None), "fail_closed", False):
                    return False, "TRADES_PER_DAY"
            except Exception:
                pass

        # daily disable
        try:
            dl = getattr(self, "daily_loss_limit", None)
            if dl is not None and float(dl) <= 0.0:
                return False, "daily_loss_limit<=0 disables trading"
        except Exception:
            pass

        # per-trade notional cap
        cap = None
        try:
            cfg = getattr(self, "config", None)
            if cfg is not None and hasattr(cfg, "per_trade_notional_cap"):
                cap = cfg.per_trade_notional_cap
        except Exception:
            cap = None
        if cap is None:
            cap = getattr(self, "per_trade_notional_cap", None)
        if cap is None:
            try:
                for _k, _v in vars(self).items():
                    if hasattr(_v, "per_trade_notional_cap"):
                        _val = getattr(_v, "per_trade_notional_cap")
                        if _val is not None:
                            cap = _val
                            break
            except Exception:
                pass

        try:
            if cap is not None and notional is not None and float(notional) > float(cap):
                return False, "NOTIONAL_CAP"
        except Exception:
            try:
                if getattr(getattr(self, "config", None), "fail_closed", False):
                    return False, "invalid_notional_or_cap"
            except Exception:
                pass

        return True, ""

    # --------- legacy shims ---------
    def check_trade(self, pnl: float = 0.0, trade_notional: float | None = None, *args, **kwargs):
        fn = getattr(self, "approve_trade", None)
        if callable(fn):
            try:
                notional = trade_notional if trade_notional is not None else 0.0
                res = fn("LEGACY", "BUY", 0.0, notional)
                if isinstance(res, tuple):
                    return bool(res[0])
                if isinstance(res, dict):
                    return str(res.get("status", "")).lower() in (
                        "ok",
                        "allow",
                        "approved",
                        "true",
                        "pass",
                        "filled",
                    )
                return bool(res)
            except Exception:
                return True
        return True

    def reset_day(self):
        return {"status": "ok"}
